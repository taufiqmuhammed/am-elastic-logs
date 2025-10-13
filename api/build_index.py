#!/usr/bin/env python3
import os
import json
import glob
import requests
from sentence_transformers import SentenceTransformer
from pdf_chunker import iter_pdf_chunks

# Configuration
ES_HOST       = os.getenv("ES_HOST",      "http://elasticsearch:9200")
ES_INDEX_LOGS = os.getenv("ES_INDEX_LOGS","logs_vector")
ES_INDEX_DOCS = os.getenv("ES_INDEX_DOCS","docs_vector")
EMBED_MODEL   = os.getenv("EMBED_MODEL",  "sentence-transformers/all-MiniLM-L6-v2")
LOG_JSONL     = os.getenv("LOG_JSONL",    "/app/clean/parsed.jsonl")
DOC_DIR       = os.getenv("DOC_DIR",      "/app/docs")
VECTOR_DIMS   = int(os.getenv("VECTOR_DIMS","384"))

headers = {"Content-Type": "application/json"}

def ensure_index(name):
    """
    Create an ES index with:
      • text
      • dense_vector
      • timestamp parsed either as ISO or space-separated
    """
    mapping = {
      "mappings": {
        "properties": {
          "text": {
            "type": "text"
          },
          "embedding": {
            "type":       "dense_vector",
            "dims":       VECTOR_DIMS,
            "index":      True,
            "similarity": "cosine"
          },
          "timestamp": {
            "type":   "date",
            "format": "strict_date_optional_time||yyyy-MM-dd HH:mm:ss.SSS"
          },
          "thread": {"type": "keyword"},
          "level":  {"type": "keyword"}
        }
      }
    }

    resp = requests.put(f"{ES_HOST}/{name}", json=mapping, headers=headers)
    if resp.status_code not in (200, 201):
        print(f"[WARN] Could not create index {name}: {resp.text}")
    else:
        print(f"[+] Created index '{name}' with extended timestamp parsing")

def index_doc(index, payload):
    url = f"{ES_HOST}/{index}/_doc"
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code not in (200, 201):
        print(f"[ERROR] Failed to index doc: {r.status_code} {r.text}")

def index_logs():
    if not os.path.exists(LOG_JSONL):
        print(f"[WARN] No logs JSONL at {LOG_JSONL}")
        return
    count = 0
    with open(LOG_JSONL, "r", errors="ignore") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except:
                continue
            text = f"{rec.get('timestamp')} [{rec.get('thread')}] {rec.get('level')} - {rec.get('message')}"
            vector = model.encode(text).tolist()
            doc = {"text": text, "embedding": vector, **{k: v for k, v in rec.items()}}
            index_doc(ES_INDEX_LOGS, doc)
            count += 1
    print(f"[+] Indexed {count} log lines")

def index_pdfs():
    if not os.path.isdir(DOC_DIR):
        print(f"[WARN] No docs folder at {DOC_DIR}")
        return
    files = glob.glob(os.path.join(DOC_DIR, "*.pdf"))
    print(f"[+] Found {len(files)} PDFs")
    count = 0
    for pdf in files:
        for chunk in iter_pdf_chunks(pdf):
            text = chunk.page_content
            vector = model.encode(text).tolist()
            doc = {"text": text, "embedding": vector, **chunk.metadata}
            index_doc(ES_INDEX_DOCS, doc)
            count += 1
    print(f"[+] Indexed {count} PDF chunks")

if __name__ == "__main__":
    print("▶️  Starting ES indexer…")
    model = SentenceTransformer(EMBED_MODEL)

    ensure_index(ES_INDEX_LOGS)
    ensure_index(ES_INDEX_DOCS)

    index_logs()
    index_pdfs()

    print("✅  Indexing complete!")