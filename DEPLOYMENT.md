# Deployment Guide

This guide covers deploying AM Elastic Logs in various environments, from local development to production systems.

## 📋 Table of Contents
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security Considerations](#security-considerations)
- [Performance Tuning](#performance-tuning)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites Verification
```bash
# Check Docker installation
docker --version
docker-compose --version

# Verify system resources
free -h
df -h
```

### Minimum Requirements
- **CPU**: 4+ cores (8+ recommended for production)
- **Memory**: 8GB RAM (16GB+ recommended)
- **Storage**: 20GB available space (50GB+ for production)
- **Network**: Internet access for initial model downloads

### One-Command Deployment
```bash
git clone https://github.com/yourusername/am-elastic-logs.git
cd am-elastic-logs
docker-compose up -d
```

---

## 🔧 Development Setup

### Local Development Environment
```bash
# 1. Clone repository
git clone https://github.com/yourusername/am-elastic-logs.git
cd am-elastic-logs

# 2. Create development directories
mkdir -p logs docs clean index

# 3. Add sample logs (optional)
cp /path/to/your/sample/*.log logs/

# 4. Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Development Docker Compose Override
Create `docker-compose.dev.yml`:
```yaml
version: '3.8'
services:
  api:
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
    volumes:
      - ./api:/app
    ports:
      - "8000:8000"
      - "5000:5000"  # Debug port
    
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"  # Lower memory for dev
    
  ollama:
    environment:
      - OLLAMA_DEBUG=1
```

### IDE Integration
For VS Code development:
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/api/app.py",
            "env": {
                "FLASK_ENV": "development",
                "ELASTICSEARCH_URL": "http://localhost:9200",
                "OLLAMA_URL": "http://localhost:11434"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

---

## 🏭 Production Deployment

### Production Docker Compose
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'
services:
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms4g -Xmx4g"  # Production memory
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
    ulimits:
      memlock:
        soft: -1
        hard: -1
    deploy:
      resources:
        limits:
          memory: 6g
        reservations:
          memory: 4g
  
  ollama:
    deploy:
      resources:
        limits:
          memory: 4g
        reservations:
          memory: 2g
  
  api:
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=0
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2g
        reservations:
          memory: 1g
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - api
```

### Environment Configuration
Create `.env.prod`:
```bash
# Elasticsearch
ELASTIC_PASSWORD=your_secure_password
ES_JAVA_OPTS=-Xms4g -Xmx4g

# API Configuration
FLASK_ENV=production
MODEL=phi3
EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
TOP_K=16
CHUNK_SIZE=16

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here
```

### Production Startup
```bash
# Load production environment
source .env.prod

# Deploy with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose ps
docker-compose logs --tail=50
```

### Nginx Configuration
Create `nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/ssl/cert.pem;
        ssl_certificate_key /etc/ssl/key.pem;

        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://api/health;
            access_log off;
        }
    }
}
```

---

## ☁️ Cloud Deployment

### AWS Deployment

#### EC2 Instance
```bash
# Launch EC2 instance (t3.xlarge or larger)
# Install Docker and Docker Compose
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Deploy application
git clone https://github.com/yourusername/am-elastic-logs.git
cd am-elastic-logs
docker-compose up -d
```

#### ECS Deployment
Create `task-definition.json`:
```json
{
  "family": "am-elastic-logs",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "elasticsearch",
      "image": "docker.elastic.co/elasticsearch/elasticsearch:8.12.0",
      "memory": 4096,
      "environment": [
        {"name": "discovery.type", "value": "single-node"},
        {"name": "ES_JAVA_OPTS", "value": "-Xms2g -Xmx2g"}
      ]
    },
    {
      "name": "api",
      "image": "your-ecr-repo/am-elastic-logs:latest",
      "memory": 2048,
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"}
      ]
    }
  ]
}
```

### Google Cloud Platform

#### Cloud Run Deployment
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/am-elastic-logs

# Deploy to Cloud Run
gcloud run deploy am-elastic-logs \
  --image gcr.io/PROJECT-ID/am-elastic-logs \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --port 8000
```

### Azure Container Instances
```bash
# Create resource group
az group create --name am-elastic-logs --location eastus

# Deploy container group
az container create \
  --resource-group am-elastic-logs \
  --name am-elastic-logs \
  --image your-registry/am-elastic-logs:latest \
  --memory 8 \
  --cpu 4 \
  --ports 8000 \
  --dns-name-label am-elastic-logs
```

---

## 🔒 Security Considerations

### Authentication Setup
Add API key authentication:
```python
# In api/app.py
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('API_KEY'):
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/query', methods=['POST'])
@require_api_key
def query():
    # Existing code...
```

### SSL/TLS Configuration
```yaml
# In docker-compose.prod.yml
services:
  nginx:
    volumes:
      - /etc/letsencrypt/live/yourdomain.com:/etc/ssl:ro
```

### Network Security
```yaml
# Create isolated network
networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge

services:
  elasticsearch:
    networks:
      - internal
  
  api:
    networks:
      - internal
      - external
```

### Secrets Management
Use Docker secrets or environment files:
```bash
# Create secrets
echo "your_elastic_password" | docker secret create elastic_password -
echo "your_api_key" | docker secret create api_key -
```

---

## ⚡ Performance Tuning

### Resource Allocation
```yaml
# Optimized for high-load production
services:
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms8g -Xmx8g"
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 12g
  
  ollama:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 6g
```

### Elasticsearch Optimization
```bash
# Increase file descriptor limits
echo "elasticsearch soft nofile 65536" >> /etc/security/limits.conf
echo "elasticsearch hard nofile 65536" >> /etc/security/limits.conf

# Optimize for SSD storage
curl -X PUT "localhost:9200/_cluster/settings" -H "Content-Type: application/json" -d'
{
  "persistent": {
    "indices.store.throttle.type": "none"
  }
}'
```

### Caching Strategy
Add Redis for API response caching:
```yaml
services:
  redis:
    image: redis:alpine
    deploy:
      resources:
        limits:
          memory: 1g
```

---

## 📊 Monitoring & Maintenance

### Health Monitoring
Create monitoring stack with Prometheus:
```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
```

### Log Monitoring
```bash
# Monitor container logs
docker-compose logs -f --tail=100

# Check system resources
docker stats

# Monitor Elasticsearch health
curl -X GET "localhost:9200/_cluster/health?pretty"
```

### Automated Backups
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/am-elastic-logs_$DATE"

# Backup Elasticsearch indices
docker-compose exec elasticsearch curl -X PUT "localhost:9200/_snapshot/backup/snapshot_$DATE"

# Backup application data
tar -czf "$BACKUP_DIR/app_data.tar.gz" clean/ index/ logs/

# Upload to cloud storage (example)
aws s3 cp "$BACKUP_DIR" s3://your-backup-bucket/ --recursive
```

### Update Strategy
```bash
#!/bin/bash
# update.sh - Rolling update script
docker-compose pull
docker-compose up -d --no-deps --remove-orphans
docker image prune -f
```

---

## 🐛 Troubleshooting

### Common Deployment Issues

#### Container Startup Failures
```bash
# Check container logs
docker-compose logs elasticsearch
docker-compose logs ollama

# Check resource constraints
docker stats
free -h
df -h

# Verify port availability
netstat -tulpn | grep :9200
netstat -tulpn | grep :11434
```

#### Memory Issues
```bash
# Increase swap if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Adjust container memory limits
docker-compose down
# Edit docker-compose.yml memory limits
docker-compose up -d
```

#### Network Connectivity
```bash
# Test inter-container communication
docker-compose exec api ping elasticsearch
docker-compose exec api ping ollama

# Check Docker networks
docker network ls
docker network inspect am-elastic-logs_default
```

### Performance Troubleshooting

#### Slow Query Response
```bash
# Check Elasticsearch query performance
curl -X GET "localhost:9200/_nodes/stats/indices/search"

# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s "localhost:8000/health"
```

#### High Memory Usage
```bash
# Check memory usage by service
docker stats --no-stream

# Optimize Elasticsearch heap
# Edit ES_JAVA_OPTS in docker-compose.yml
```

### Recovery Procedures

#### Service Recovery
```bash
# Restart individual services
docker-compose restart elasticsearch
docker-compose restart ollama
docker-compose restart api

# Full system recovery
docker-compose down
docker system prune -f
docker-compose up -d
```

#### Data Recovery
```bash
# Restore from backup
tar -xzf backup/app_data.tar.gz -C ./

# Rebuild indices if corrupted
docker-compose exec api python build_index.py
```

---

## 📈 Scaling Considerations

### Horizontal Scaling
```yaml
# Scale API service
services:
  api:
    deploy:
      replicas: 3
  
  # Add load balancer
  haproxy:
    image: haproxy:alpine
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
```

### Elasticsearch Cluster
```yaml
services:
  elasticsearch-master:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - node.name=master
      - cluster.name=am-elastic-cluster
      - discovery.seed_hosts=elasticsearch-data1,elasticsearch-data2
      - cluster.initial_master_nodes=master
  
  elasticsearch-data1:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - node.name=data1
      - cluster.name=am-elastic-cluster
      - node.roles=data
```

This deployment guide provides comprehensive coverage for deploying AM Elastic Logs across different environments. Choose the appropriate section based on your deployment needs and infrastructure requirements.