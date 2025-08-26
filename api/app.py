# api/app.py
import os, json, requests
from flask import Flask, request, jsonify
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL = os.getenv("MODEL", "llama3.1") 
INDEX_DIR = os.getenv("INDEX_DIR", "/app/index")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

app = Flask(__name__)

# Initialize embeddings and vector store
print("Loading embeddings model...")
embed = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

print(f"Loading vector store from {INDEX_DIR}...")
try:
    vs = FAISS.load_local(INDEX_DIR, embed, allow_dangerous_deserialization=True)
    print("Vector store loaded successfully")
except Exception as e:
    print(f"Warning: Could not load vector store: {e}")
    vs = None

@app.route("/query", methods=["POST"])
def query():
    if vs is None:
        return jsonify({"error": "Vector store not available"}), 503
        
    body = request.get_json(force=True)
    q = body.get("query", "")
    k = int(body.get("k", 8))
    
    try:
        hits = vs.similarity_search(q, k=k)
        return jsonify([{"text": h.page_content, "meta": h.metadata} for h in hits])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

SYSTEM = "You are a precise log analysis expert. Use only the provided lines. Return valid JSON."

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

def ollama_generate(prompt):
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat",
                          json={"model": MODEL, "messages":[{"role": "user", "content": prompt}], "stream": False},
                          timeout=120)
        r.raise_for_status()
        response_data = r.json()
#        return r.json().get("response", "{}")
        return response_data.get("message", {}).get("content", "{}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ollama API error: {e}")

@app.route("/anomalies", methods=["POST"]) 
def anomalies():
    if vs is None:
        return jsonify({"error": "Vector store not available"}), 503
        
    body = request.get_json(force=True)
    q = body.get("query", "recent anomalies")
    k = int(body.get("k", 60))

    try:
        # Get relevant log lines
        hits = vs.similarity_search(q, k=k)
        # Filter for log entries only
        log_hits = [h for h in hits if h.metadata.get("kind") == "log"]
        
        lines = [{"i": i, "text": h.page_content, "meta": h.metadata} for i, h in enumerate(log_hits)]
        lines = lines[:100]  # Cap input size

        prompt = SYSTEM + "\n\n" + USER_TMPL.format(lines=json.dumps(lines, ensure_ascii=False))
        data = ollama_generate(prompt)
        
        # Clean the response to remove markdown backticks and "json" label
        cleaned_data = data.strip().replace("```json", "").replace("```", "")

        try:
            result = json.loads(cleaned_data)
            return jsonify(result)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON response from LLM", "raw_response": data}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    idx_ready = vs is not None and os.path.isdir(INDEX_DIR) and len(os.listdir(INDEX_DIR)) > 0
    
    # Test Ollama connectivity
    ollama_ready = False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_ready = r.status_code == 200
    except:
        pass
        
    return jsonify({
        "index": idx_ready,
        "ollama": ollama_ready, 
        "model": MODEL,
        "status": "healthy" if (idx_ready and ollama_ready) else "degraded"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
