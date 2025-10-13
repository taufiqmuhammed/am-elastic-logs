# api/app.py

import os, json, re, requests
import time
from requests.exceptions import ReadTimeout
from flask import Flask, request, jsonify, render_template, send_from_directory
from sentence_transformers import SentenceTransformer


# Env & constants
OLLAMA_URL    = os.getenv("OLLAMA_URL",    "http://ollama:11434")
MODEL         = os.getenv("MODEL",         "phi3")
EMBED_MODEL   = os.getenv("EMBED_MODEL",   "sentence-transformers/all-MiniLM-L6-v2")
ES_HOST       = os.getenv("ES_HOST",       "http://elasticsearch:9200")
ES_INDEX_LOGS = os.getenv("ES_INDEX_LOGS", "logs_vector")
TOP_K_DEFAULT = int(os.getenv("TOP_K","8"))

CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE","8"))
SYSTEM_PROMPT = (
  "You are a precise log analysis expert. Use only the provided lines. Return valid JSON."
)
USER_TMPL = """
Given these log lines (array of objects with text+meta):

{lines}

Tasks:
1) Brief summary of notable events/bursts.
2) anomalies: list items with fields: i, reason, severity (low|medium|high).
3) next_actions: concrete follow-ups.

Return JSON only:
{{"summary":"...", "anomalies":[{{"i":0,"reason":"...","severity":"medium"}}], "next_actions":["...","..."]}}
"""

app = Flask(__name__)

# load embedder once
print(f"Loading embedder {EMBED_MODEL}…")
embedder = SentenceTransformer(EMBED_MODEL)

def es_search_knn(q_vec, k):
    body = {
      "size": k,
      "query": {
        "script_score": {
          "query": {"match_all": {}},
          "script": {
            "source": "cosineSimilarity(params.query_vector,'embedding')+1.0",
            "params": {"query_vector": q_vec}
          }
        }
      },
      "_source": ["timestamp","level","thread","message","text"]
    }
    resp = requests.post(f"{ES_HOST}/{ES_INDEX_LOGS}/_search",
                         json=body, timeout=10)
    resp.raise_for_status()
    return resp.json()["hits"]["hits"]

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

# Serve static files
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json(force=True)
    text = data.get("query","")
    k    = int(data.get("k",TOP_K_DEFAULT))

    q_vec = embedder.encode(text).tolist()
    try:
        hits = es_search_knn(q_vec, k)
    except Exception as e:
        return jsonify({"error":str(e)}),500

    results = []
    for h in hits:
        s = h["_source"]
        results.append({
            "score":     h["_score"],
            "timestamp": s.get("timestamp"),
            "level":     s.get("level"),
            "thread":    s.get("thread"),
            "message":   s.get("message"),
            "text":      s.get("text")
        })
    return jsonify(results)

def ollama_generate(prompt: str) -> dict:
    url     = f"{OLLAMA_URL}/api/generate"
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    # 5s connect, no read timeout
    r = requests.post(url, json=payload, timeout=(5,None))
    r.raise_for_status()
    return r.json()

"""
POST /anomalies

Fetches the top‐k most relevant logs, chunks them for LLM analysis,
and then returns:

  • summary            – combined human summary from all chunks  
  • raw_anomalies      – exactly what the LLM flagged (i, reason, severity)  
  • confirmed_anomalies– those raw anomalies we could map back into hits[0..k-1]  
  • layman_explanation – plain-English note on how many matched  

Why do some anomalies disappear?
1) You ask for `k=16`, so we only load hits[0] through hits[15].  
2) If the LLM returns an anomaly at `i >= 16`, there is no hits[i] to attach it to.  
3) We silently drop out-of-range indices, since we can’t confirm them against real logs.  
   (If you need to see them, raise `k` in your request or remove the range check.)
"""

@app.route("/anomalies", methods=["POST"])
def anomalies():
    body  = request.get_json(force=True)
    query = body.get("query", "recent anomalies")
    k     = min(int(body.get("k", 32)), 32)
    
    #start timing
    start_time = time.time()

    # 1) Fetch top-k hits from Elasticsearch
    q_vec = embedder.encode(query).tolist()
    try:
        hits = es_search_knn(q_vec, k)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 2) Prepare simple lines for the LLM
    lines = [{"i": i, "text": h["_source"]["text"]}
             for i, h in enumerate(hits)]

    raw_anomalies       = []
    confirmed_anomalies = []
    summaries           = []

    # 3) Chunk logs and call Ollama
    for offset in range(0, len(lines), CHUNK_SIZE):
        chunk  = lines[offset : offset + CHUNK_SIZE]
        prompt = SYSTEM_PROMPT + "\n\n" + USER_TMPL.format(
            lines=json.dumps(chunk, ensure_ascii=False)
        )

        try:
            resp = ollama_generate(prompt)
            raw = (
                (resp.get("choices") or [{}])[0].get("text")
                or resp.get("response")
                or next(v for v in resp.values() if isinstance(v, str))
            )
        except ReadTimeout:
            app.logger.warning(f"Ollama timed out at offset {offset}")
            continue
        except Exception as e:
            app.logger.error(f"Ollama error at offset {offset}: {e}")
            continue

        # 4) Parse the LLM’s JSON output
        m    = re.search(r"(\{.*\})", raw, flags=re.S)
        blob = m.group(1) if m else raw
        try:
            data = json.loads(blob)
        except Exception as e:
            app.logger.error(f"JSON parse error at {offset}: {e}")
            continue

        summaries.append(data.get("summary", ""))

        # 5) Pair each anomaly with its next_action
        chunk_anos    = data.get("anomalies", [])
        chunk_actions = data.get("next_actions", [])

        for idx, entry in enumerate(chunk_anos):
            rel_i = entry.get("i", 0)
            abs_i = offset + (rel_i if isinstance(rel_i, int) else 0)

            # record what the model flagged
            raw_anomalies.append({
                "i":        abs_i,
                "reason":   entry.get("reason"),
                "severity": entry.get("severity")
            })

            # only confirm if we actually fetched that hit
            if not (0 <= abs_i < len(hits)):
                continue

            src    = hits[abs_i]["_source"]
            action = chunk_actions[idx] if idx < len(chunk_actions) else ""

            confirmed_anomalies.append({
                "i":                abs_i,
                "timestamp":        src.get("timestamp"),
                "timestamp (when)": src.get("timestamp"),
                "thread":           src.get("thread") or "n/a",
                "thread (where)":   src.get("thread") or "n/a",
                "text":             src.get("text"),
                "text (message)":   src.get("text"),
                "reason":           entry.get("reason"),
                "severity":         entry.get("severity"),
                "next_action":      action
            })

    # 6) Build a simple layman note
    raw_count  = len(raw_anomalies)
    conf_count = len(confirmed_anomalies)
    layman     = f"The model flagged {raw_count} issue(s); {conf_count} were verified in your logs."

    end_time = time.time()
    app.logger.info(f"/anomalies processed in {end_time - start_time:.2f}s (query='{query}' k={k} hits={len(hits)})")

    return jsonify({
        "summary":             " ".join(summaries).strip(),
        "raw_anomalies":       raw_anomalies,
        "confirmed_anomalies": confirmed_anomalies,
        "layman_explanation":  layman
    })

@app.route("/health", methods=["GET"])
def health():
    try: es_ok    = requests.get(f"{ES_HOST}/_cluster/health",timeout=2).ok
    except: es_ok = False
    try: ollama_ok= requests.get(f"{OLLAMA_URL}/api/tags",timeout=2).ok
    except: ollama_ok=False
    return jsonify({
      "elasticsearch": es_ok,
      "ollama":        ollama_ok,
      "status":        "healthy" if (es_ok and ollama_ok) else "degraded"
    })

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)