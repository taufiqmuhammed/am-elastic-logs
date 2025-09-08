# api/app.py

import os
import json
import requests
from flask import Flask, request, jsonify
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

# Environment & constants
OLLAMA_URL    = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL         = os.getenv("MODEL", "phi3")
INDEX_DIR     = os.getenv("INDEX_DIR", "/app/index")
EMBED_MODEL   = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

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

SYSTEM = (
    "You are a precise log analysis expert. "
    "Use only the provided lines. Return valid JSON."
)

USER_TMPL = """
Given these log lines (array of objects with text+meta):

{lines}

Tasks:
1) Brief summary of notable events/bursts.
2) anomalies: list items with fields: index (i), reason, severity (low|medium|high).
3) next_actions: concrete follow-ups.

Return JSON only:
{{"summary":"...", "anomalies":[{{"i":0,"reason":"...","severity":"medium"}}], "next_actions":["...","..."]}}
"""

def ollama_generate(prompt: str) -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {"model": MODEL, "prompt": prompt, "stream": False}

    try:
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        # Ollama v0.11.7 /api/generate returns {"choices":[{"text":...}], ...}
        return data["choices"][0]["text"].strip()
    except Exception as e:
        raise Exception(f"Ollama API error: {e}")

@app.route("/anomalies", methods=["POST"])
def anomalies():
    if vs is None:
        return jsonify({"error": "Vector store not available"}), 503

    body = request.get_json(force=True)
    q    = body.get("query", "recent anomalies")
    k    = int(body.get("k", 60))

    try:
        hits = vs.similarity_search(q, k=k)

        # Prepare up to 100 entries for the LLM
        lines = [
            {"i": i, "text": h.page_content, "meta": h.metadata}
            for i, h in enumerate(hits)
        ][:100]

        prompt       = SYSTEM + "\n\n" + USER_TMPL.format(
            lines=json.dumps(lines, ensure_ascii=False)
        )
        raw_response = ollama_generate(prompt).strip()

        # Strip any markdown fencing
        cleaned = raw_response.replace("```json", "").replace("```", "")
        result  = json.loads(cleaned)

        return jsonify(result)
    except json.JSONDecodeError:
        return jsonify({
            "error": "Invalid JSON from LLM",
            "raw_response": raw_response
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

    # Test Ollama connectivity via /api/tags
    ollama_ready = False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_ready = (r.status_code == 200)
    except:
        pass

    status = "healthy" if (idx_ready and ollama_ready) else "degraded"
    return jsonify({
        "index":  idx_ready,
        "ollama": ollama_ready,
        "model":  MODEL,
        "status": status
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)