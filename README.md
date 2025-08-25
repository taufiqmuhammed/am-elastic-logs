# RAG-Powered Log Analysis POC for AccessMatrix

This project is a proof-of-concept (POC) for a local-first, Retrieval-Augmented Generation (RAG) system designed to analyze AccessMatrix logs and documentation. It provides a streamlined solution for ingesting, indexing, and querying large volumes of log data and PDFs using local Large Language Models (LLMs).

[cite_start]The primary goal is to create a system that makes messy logs and dense technical documents easily navigable, enabling quick fault diagnosis, anomaly detection, and natural language Q&A[cite: 73, 74].

## 📋 Project Overview

[cite_start]This system is built on a containerized stack of open-source tools designed for quick ingestion, local reasoning, and expandable API endpoints[cite: 16].

* [cite_start]**Log Ingestion & Parsing**: Continuously streams and parses multi-gigabyte log files into structured JSONL format without loading entire files into memory, using Vector[cite: 110].
* [cite_start]**Semantic Indexing**: Converts both structured log data and unstructured PDF documents into a searchable "memory" using sentence-transformer embeddings and a FAISS vector store[cite: 111, 118]. This allows for querying based on meaning, not just keywords.
* [cite_start]**LLM-Powered Analysis**: Uses a local LLM run via Ollama to provide grounded Q&A over documents, identify anomalies in logs, and suggest actionable next steps[cite: 113, 114].
* [cite_start]**API Endpoints**: Exposes a minimal Flask API with `/query`, `/anomalies`, and `/health` endpoints for easy integration with other services, such as a React widget in the AccessMatrix portal[cite: 79, 115].

## 🏗️ Architecture

The architecture is designed for a local-first, resource-efficient deployment.


---

## 🛠️ Tech Stack

This project leverages a curated stack of powerful open-source tools:

| Component | Role | Rationale |
| :--- | :--- | :--- |
| **Vector** | Log Ingestion & Parser | [cite_start]Lightweight, high-performance, and uses VRL for powerful, declarative log parsing[cite: 117]. |
| **FAISS** | Vector Store | [cite_start]Simple, fast, and memory-efficient vector storage, ideal for a local POC[cite: 118]. |
| **Ollama** | Local LLM Serving | [cite_start]Runs powerful language models like Llama 3.1 and Phi-3 on local hardware, ensuring data privacy and no API costs[cite: 119, 120]. |
| **LangChain** | LLM Orchestration | [cite_start]The "glue" that connects the vector store to the LLM, handling retrieval logic, prompt engineering, and response formatting[cite: 119, 120]. |
| **Flask** | API Server | [cite_start]A minimal Python framework for exposing the system's capabilities via a simple REST API[cite: 115]. |

## 🚀 Setup and Usage

This project is fully containerized and can be run with Docker Compose.

### 1. Prepare Folders and Configuration
[cite_start]First, create the required directory structure[cite: 429].
```bash
mkdir -p am-rag-logs/{logs,clean,docs,index}
