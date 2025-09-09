# api/app.py

import os
import json
import re
import requests
from flask import Flask, request, jsonify
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

# Environment & constants
OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL       = os.getenv("MODEL", "phi3")
INDEX_DIR   = os.getenv("INDEX_DIR", "/app/index")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Chunking & summarization settings
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "8"))
SYSTEM        = (
    "You are a precise log analysis expert. "
    "Use only the provided lines. Return valid JSON."
)
USER_TMPL     = """
Given these log lines (array of objects with text+meta):

{lines}

Tasks:
1) Brief summary of notable events/bursts.
2) anomalies: list items with fields: index (i), reason, severity (low|medium|high).
3) next_actions: concrete follow-ups.

Return JSON only:
{{"summary":"...", "anomalies":[{{"i":0,"reason":"...","severity":"medium"}}], "next_actions":["...","..."]}}
"""

app = Flask(__name__)

# Initialize embeddings and vector store
print("Loading embeddings model...")
embed = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

print(f"Loading vector store from {INDEX_DIR}...")
try:
    vs = FAISS.load_local(
        INDEX_DIR,
        embed,
        allow_dangerous_deserialization=True
    )
    print("Vector store loaded successfully")
except Exception as e:
    print(f"Warning: Could not load vector store: {e}")
    vs = None

@app.route("/query", methods=["POST"])
def query():
    if vs is None:
        return jsonify({"error": "Vector store not available"}), 503

    body = request.get_json(force=True)
    q    = body.get("query", "")
    k    = int(body.get("k", 8))

    try:
        hits = vs.similarity_search(q, k=k)
        return jsonify([
            {"text": h.page_content, "meta": h.metadata}
            for h in hits
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def ollama_generate(prompt: str) -> str:
    """
    Call Ollama’s HTTP /api/generate endpoint and
    extract the generated text from whatever shape it returns.
    """
    url     = f"{OLLAMA_URL}/api/generate"
    payload = {"model": MODEL, "prompt": prompt, "stream": False}

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()

    # 1) Standard OpenAI-like: choices → text
    if "choices" in data and isinstance(data["choices"], list):
        text = data["choices"][0].get("text")
        if text is not None:
            return text.strip()

    # 2) Ollama v0.11+ shape: response
    if "response" in data and isinstance(data["response"], str):
        return data["response"].strip()

    # 3) Some versions use results or outputs arrays
    for key in ("results", "outputs"):
        if key in data and isinstance(data[key], list):
            item = data[key][0]
            if isinstance(item, dict) and "text" in item:
                return item["text"].strip()
            if isinstance(item, str):
                return item.strip()

    # 4) Fallback: any top-level string field
    for v in data.values():
        if isinstance(v, str):
            return v.strip()

    raise KeyError("no text field in response JSON")

@app.route("/anomalies", methods=["POST"])
def anomalies():
    if vs is None:
        return jsonify({"error": "Vector store not available"}), 503

    body = request.get_json(force=True)
    q    = body.get("query", "recent anomalies")
    k    = min(int(body.get("k", 32)), 32)  # cap at 32 hits

    try:
        # 1) FAISS search
        hits = vs.similarity_search(q, k=k)

        # 2) Build up to 32 simplified lines (no meta, just text)
        lines = [
            {"i": i, "text": h.page_content}
            for i, h in enumerate(hits)
        ][:32]

        # 3) Chunk into size 4
        chunk_size = 4
        chunks = [
            lines[i : i + chunk_size]
            for i in range(0, len(lines), chunk_size)
        ]

        chunk_summaries  = []
        anomalies_all    = []
        next_actions_all = []

        # 4) Map: LLM each chunk
        for idx, chunk in enumerate(chunks):
            prompt = SYSTEM + "\n\n" + USER_TMPL.format(
                lines=json.dumps(chunk, ensure_ascii=False)
            )
            raw = ollama_generate(prompt)

            # ─── SANITIZE JSON ───────────────────────────────────────────
            clean = raw.replace("```json", "").replace("```", "").strip()
            clean = re.sub(r'//.*', '', clean)             # strip // comments
            clean = re.sub(r',\s*(\]|\})', r'\1', clean)   # remove trailing commas
            data  = json.loads(clean)
            # ─────────────────────────────────────────────────────────────

            chunk_summaries.append(data["summary"])
            for a in data["anomalies"]:
                a["i"] += idx * chunk_size
                anomalies_all.append(a)
            next_actions_all.extend(data["next_actions"])

        # 5) Local reduce: concatenate summaries
        final_summary = " ".join(chunk_summaries)

        return jsonify({
            "summary":      final_summary,
            "anomalies":    anomalies_all,
            "next_actions": next_actions_all
        })

    except json.JSONDecodeError:
        return jsonify({
            "error":        "Invalid JSON from LLM",
            "raw_response": raw
        }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    idx_ready = (
        vs is not None
        and os.path.isdir(INDEX_DIR)
        and len(os.listdir(INDEX_DIR)) > 0
    )

    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_ready = (r.status_code == 200)
    except:
        ollama_ready = False

    status = "healthy" if (idx_ready and ollama_ready) else "degraded"
    return jsonify({
        "index":  idx_ready,
        "ollama": ollama_ready,
        "model":  MODEL,
        "status": status
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)