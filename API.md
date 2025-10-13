# API Documentation

## Base URL
- Local development: `http://localhost:8000`
- Docker deployment: `http://localhost:8000`

## Authentication
Currently, no authentication is required. All endpoints are publicly accessible.

## Content Type
All API requests should include:
```
Content-Type: application/json
```

---

## Endpoints

### 1. Home Page
**GET** `/`

Returns the main web interface HTML page.

**Response:**
- **200 OK**: HTML page content
- **Content-Type**: `text/html`

---

### 2. Health Check
**GET** `/health`

Returns the health status of all system components.

**Response:**
```json
{
  "elasticsearch": true,
  "ollama": true,
  "status": "healthy"
}
```

**Status Codes:**
- **200 OK**: Health check completed
- **500 Internal Server Error**: Service connectivity issues

**Response Fields:**
- `elasticsearch` (boolean): Elasticsearch connectivity status
- `ollama` (boolean): Ollama LLM service status  
- `status` (string): Overall system status (`"healthy"` or `"degraded"`)

---

### 3. Query Logs
**POST** `/query`

Performs semantic search on indexed logs using vector similarity.

**Request Body:**
```json
{
  "query": "authentication failed",
  "k": 10
}
```

**Parameters:**
- `query` (string, required): Natural language search query
- `k` (integer, optional): Number of results to return (default: 8, max: 100)

**Response:**
```json
[
  {
    "score": 1.8945,
    "timestamp": "2024-01-15 10:30:45.123",
    "level": "ERROR",
    "thread": "thread-1",
    "message": "Authentication failed for user john@example.com",
    "text": "2024-01-15 10:30:45.123 [thread-1] ERROR - Authentication failed for user john@example.com"
  }
]
```

**Response Fields:**
- `score` (float): Semantic similarity score (higher = more relevant)
- `timestamp` (string): Log entry timestamp
- `level` (string): Log level (ERROR, WARN, INFO, DEBUG)
- `thread` (string): Thread/process identifier
- `message` (string): Parsed log message
- `text` (string): Full original log line

**Status Codes:**
- **200 OK**: Search completed successfully
- **400 Bad Request**: Invalid request format
- **500 Internal Server Error**: Search execution failed

---

### 4. Anomaly Detection
**POST** `/anomalies`

Performs AI-powered anomaly detection and analysis using local LLM.

**Request Body:**
```json
{
  "query": "recent errors",
  "k": 32
}
```

**Parameters:**
- `query` (string, optional): Search context for log retrieval (default: "recent anomalies")
- `k` (integer, optional): Number of logs to analyze (default: 32, max: 32)

**Response:**
```json
{
  "summary": "Analysis found several authentication failures and database connection issues between 10:30-11:45.",
  "raw_anomalies": [
    {
      "i": 5,
      "reason": "Multiple authentication failures from same IP",
      "severity": "high"
    }
  ],
  "confirmed_anomalies": [
    {
      "i": 5,
      "timestamp": "2024-01-15 10:30:45.123",
      "timestamp (when)": "2024-01-15 10:30:45.123",
      "thread": "auth-service",
      "thread (where)": "auth-service", 
      "text": "Authentication failed for user john@example.com",
      "text (message)": "Authentication failed for user john@example.com",
      "reason": "Multiple authentication failures from same IP",
      "severity": "high",
      "next_action": "Block IP address and review security logs"
    }
  ],
  "layman_explanation": "The model flagged 3 issue(s); 2 were verified in your logs."
}
```

**Response Fields:**

#### Top Level:
- `summary` (string): AI-generated overview of findings
- `raw_anomalies` (array): All anomalies flagged by AI model
- `confirmed_anomalies` (array): Anomalies matched to actual log entries
- `layman_explanation` (string): Simple explanation of results

#### Raw Anomalies:
- `i` (integer): Log index position
- `reason` (string): Why this was flagged as anomalous
- `severity` (string): Severity level (`"low"`, `"medium"`, `"high"`)

#### Confirmed Anomalies:
- `i` (integer): Log index position
- `timestamp` (string): When the anomaly occurred
- `timestamp (when)` (string): Duplicate field for clarity
- `thread` (string): Where the anomaly occurred (service/thread)
- `thread (where)` (string): Duplicate field for clarity
- `text` (string): The log message content
- `text (message)` (string): Duplicate field for clarity
- `reason` (string): AI explanation of the anomaly
- `severity` (string): Risk level assessment
- `next_action` (string): Recommended response action

**Status Codes:**
- **200 OK**: Analysis completed successfully
- **400 Bad Request**: Invalid request parameters
- **500 Internal Server Error**: Analysis failed (LLM or search issues)
- **504 Gateway Timeout**: LLM processing timeout

---

### 5. Static Files
**GET** `/static/<path:filename>`

Serves static assets (CSS, JavaScript, images) for the web interface.

**Parameters:**
- `filename` (string): Path to static file

**Examples:**
- `GET /static/css/styles.css`
- `GET /static/js/analyze.js`

**Response:**
- **200 OK**: File content with appropriate MIME type
- **404 Not Found**: File doesn't exist

---

## Error Handling

### Error Response Format
```json
{
  "error": "Detailed error message describing what went wrong"
}
```

### Common Error Scenarios

#### 400 Bad Request
- Missing required fields
- Invalid JSON format
- Parameter out of valid range

#### 500 Internal Server Error  
- Elasticsearch connection failure
- Ollama LLM service unavailable
- Index corruption or missing data
- Vector embedding processing errors

#### 504 Gateway Timeout
- LLM processing taking too long
- Large dataset causing timeouts
- Resource exhaustion

---

## Rate Limiting
Currently no rate limiting is implemented. Consider implementing rate limiting for production deployments.

---

## Examples

### Complete Workflow Example

1. **Check system health:**
```bash
curl http://localhost:8000/health
```

2. **Search for specific issues:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "payment processing failed",
    "k": 15
  }'
```

3. **Get AI analysis:**
```bash
curl -X POST http://localhost:8000/anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "query": "payment errors and failures", 
    "k": 25
  }'
```

### JavaScript Integration

```javascript
// Search logs
async function searchLogs(query, count = 10) {
  const response = await fetch('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k: count })
  });
  return response.json();
}

// Detect anomalies
async function detectAnomalies(query = 'recent issues', count = 20) {
  const response = await fetch('/anomalies', {
    method: 'POST', 
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k: count })
  });
  return response.json();
}
```

### Python Integration

```python
import requests
import json

# API client
class LogAnalyzer:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def search(self, query, k=10):
        response = requests.post(
            f"{self.base_url}/query",
            json={"query": query, "k": k}
        )
        return response.json()
    
    def detect_anomalies(self, query="recent issues", k=20):
        response = requests.post(
            f"{self.base_url}/anomalies", 
            json={"query": query, "k": k}
        )
        return response.json()

# Usage
analyzer = LogAnalyzer()
results = analyzer.search("database connection failed")
anomalies = analyzer.detect_anomalies("authentication errors")
```

---

## Performance Considerations

### Query Optimization
- Use specific, targeted queries for better relevance
- Limit `k` parameter to reduce processing time
- Consider caching frequent queries

### Anomaly Detection Optimization  
- Smaller `k` values process faster
- LLM processing is CPU-intensive
- Consider batching multiple queries

### Monitoring Recommendations
- Monitor `/health` endpoint regularly
- Track response times for performance degradation
- Monitor Elasticsearch and Ollama resource usage