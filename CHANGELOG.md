# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation suite
- API documentation with detailed endpoint specifications
- Deployment guide for various environments
- GitHub Actions CI/CD pipeline (planned)
- Performance monitoring dashboard (planned)

### Changed
- Improved error handling in API endpoints
- Enhanced logging for better debugging

### Fixed
- Vector configuration parsing for multi-line log entries
- Elasticsearch connection timeout handling

## [1.0.0] - 2024-02-22

### Added
- **Core Features**
  - AI-powered log analysis system with Elasticsearch, Vector, and Ollama
  - Semantic search capabilities using sentence transformers
  - Real-time anomaly detection with local LLM (Phi3 model)
  - Interactive web interface for log exploration
  - RESTful API with comprehensive endpoints

- **Infrastructure**
  - Full Docker Compose deployment
  - Health checks for all services
  - Automated service orchestration
  - Volume mounting for data persistence

- **Data Processing**
  - Vector-based log parsing and processing
  - Support for multiple log formats (AM-style, GC logs, generic)
  - PDF document processing and indexing
  - JSONL output for processed logs

- **Web Interface**
  - Clean, responsive HTML interface
  - Real-time query processing
  - Anomaly visualization
  - Interactive log exploration

- **API Endpoints**
  - `/query` - Semantic log search
  - `/anomalies` - AI-powered anomaly detection  
  - `/health` - System health monitoring
  - Static file serving for web assets

- **Configuration**
  - Environment-based configuration
  - Configurable embedding models
  - Adjustable query parameters
  - Flexible log format parsing

### Technical Implementation

#### Backend Services
- **Flask API Server**
  - Python-based REST API
  - Sentence Transformers integration
  - Elasticsearch client
  - Ollama LLM integration

- **Elasticsearch**
  - Version 8.12.0
  - Vector similarity search
  - Dense vector storage (384 dimensions)
  - Cosine similarity scoring

- **Ollama LLM Service**  
  - Phi3 model for analysis
  - Local inference (no cloud dependencies)
  - Containerized deployment
  - Automatic model downloading

- **Vector Log Processor**
  - Real-time log parsing
  - Multi-format support
  - Throttling and rate limiting
  - JSONL output generation

#### Data Flow Architecture
1. **Log Ingestion**: Vector reads log files from mounted volumes
2. **Processing**: Parses logs using regex patterns and transformations
3. **Indexing**: Builds Elasticsearch indices with embeddings
4. **Query Processing**: Semantic search using vector similarity
5. **AI Analysis**: LLM-based anomaly detection and summarization
6. **Web Interface**: Interactive exploration and visualization

#### Supported Log Formats
- **AM-style Logs**: `YYYY-MM-DD HH:mm:ss.SSS [thread] LEVEL - (Class:line) message`
- **GC Logs**: `[uptime][level][category] message`
- **Generic**: Any unrecognized format preserved as raw text

### Configuration Options

#### Environment Variables
- `MODEL`: Ollama model name (default: phi3)
- `OLLAMA_URL`: Ollama service URL
- `ES_HOST`: Elasticsearch connection URL
- `EMBED_MODEL`: Sentence transformer model
- `TOP_K`: Default search result count
- `CHUNK_SIZE`: LLM processing chunk size

#### Docker Compose Services
- **elasticsearch**: Search engine and vector store
- **vector**: Log processing pipeline  
- **ollama**: Local LLM inference
- **api**: Flask web application
- **indexer**: One-time indexing service

### File Structure
```
am-elastic-logs/
├── api/                    # Flask API application
│   ├── app.py             # Main application logic
│   ├── build_index.py     # Elasticsearch indexing
│   ├── pdf_chunker.py     # PDF processing utilities
│   ├── templates/         # HTML templates
│   ├── static/           # CSS/JS assets
│   └── requirements.txt  # Python dependencies
├── vector/               # Log processing service
│   ├── vector.toml      # Processing configuration
│   └── Dockerfile       # Container definition
├── logs/                # Input log files
├── docs/                # PDF documents
├── clean/               # Processed output
├── index/               # Search indices
└── docker-compose.yml   # Service orchestration
```

### Dependencies

#### Python Packages
- **Flask**: Web framework and API server
- **sentence-transformers**: Text embedding generation
- **elasticsearch**: Elasticsearch client library
- **requests**: HTTP client for service communication
- **langchain**: LLM framework components
- **pypdf**: PDF text extraction
- **faiss-cpu**: Vector similarity search (alternative backend)

#### System Services
- **Docker Engine**: Container runtime
- **Docker Compose**: Multi-container orchestration
- **Elasticsearch 8.12.0**: Search and analytics
- **Vector**: High-performance log processor
- **Ollama**: Local LLM inference engine

### Performance Characteristics
- **Memory Usage**: 8GB minimum, 16GB recommended
- **CPU Requirements**: 4+ cores for optimal performance
- **Storage**: ~10GB for base system, varies with log volume
- **Query Response Time**: <2 seconds for typical searches
- **Anomaly Analysis**: 10-30 seconds depending on log count

### Known Limitations
- Single-node Elasticsearch deployment (clustering requires manual setup)
- No built-in authentication (suitable for internal use)
- Limited to 32 logs maximum for anomaly analysis
- Ollama model download required on first startup
- Log file changes require container restart for Vector pickup

### Initial Release Notes
This first release establishes the core functionality for AI-powered log analysis. The system successfully demonstrates:

- Semantic understanding of log content through vector embeddings
- Intelligent anomaly detection using local LLMs
- Real-time processing of various log formats
- User-friendly web interface for log exploration
- Scalable architecture with containerized services

The system has been tested with various log formats and demonstrates reliable performance for log volumes up to several GB. Future releases will focus on scalability improvements, authentication, and advanced analytics features.

---

## Version History Summary

- **v1.0.0**: Initial release with core AI log analysis functionality
- **Future**: Enhanced scaling, authentication, advanced analytics

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.