#!/usr/bin/env python3
# api/analyze.py
import sys
import json
import requests

API_URL = "http://localhost:8000/anomalies"
DEFAULT_K = 32
TIMEOUT = 600  # seconds for long-running calls

def pretty_print(resp):
    print("\n=== Summary ===\n")
    print(resp.get("summary") or "No summary.\n")
    print("\n=== Confirmed Anomalies ===\n")
    for a in resp.get("confirmed_anomalies", []):
        i = a.get("i")
        reason = a.get("reason") or ""
        action = a.get("next_action") or ""
        timestamp = a.get("timestamp") or ""
        print(f"- [i={i}] {reason} ({timestamp})\n    Next action: {action}\n")
    print("\n=== Raw Anomalies ===\n")
    for a in resp.get("raw_anomalies", []):
        print(f"- [i={a.get('i')}] {a.get('reason')} ({a.get('severity')})")
    print("\n=== Layman ===\n")
    print(resp.get("layman_explanation") or "")

def main():
    if len(sys.argv) < 2:
        print("Usage: analyze.py \"your question here\" [k]")
        sys.exit(1)
    query = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_K

    payload = {"query": query, "k": k}
    try:
        r = requests.post(API_URL, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        sys.exit(2)

    try:
        resp = r.json()
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON response: {e}")
        print("Raw response:")
        print(r.text)
        sys.exit(3)

    pretty_print(resp)

if __name__ == "__main__":
    main()