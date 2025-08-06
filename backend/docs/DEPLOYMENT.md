# LLM Evaluation System Deployment Guide

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Environment variables configured (see `.env.example`)
- Database access (Supabase recommended)
- Redis instance or use Docker Compose

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Configure required variables
export DATABASE_URL="postgresql://..."
export SUPABASE_URL="https://..."
export SUPABASE_KEY="eyJhb..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
export LANGSMITH_API_KEY="ls_..."
export LANGSMITH_PROJECT="evaluation-system"
export REDIS_URL="redis://localhost:6379/0"
```

### 2. Database Migration

```bash
# Run database migrations
python -m alembic upgrade head

# Or apply SQL directly
psql $DATABASE_URL -f migrations/create_evaluation_tables.sql
```

### 3. Start Services

```bash
# Start all services with Docker Compose
docker-compose -f docker-compose.evaluation.yml up -d

# Or start specific services
docker-compose -f docker-compose.evaluation.yml up -d evaluation-worker redis prometheus grafana
```

### 4. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health

# Check worker status
curl http://localhost:5555/api/workers

# Check metrics
curl http://localhost:9090/api/v1/query?query=up
```

## Production Deployment

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│   FastAPI App   │────│   Database      │
│   (nginx/ALB)   │    │   (main)        │    │   (Supabase)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Evaluation    │    │     Redis       │    │   Monitoring    │
│   Workers       │────│   (message      │────│   (Prometheus   │
│   (Celery)      │    │    broker)      │    │   /Grafana)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Infrastructure Requirements

**Minimum Production Setup:**
- **API Server**: 2 vCPUs, 4GB RAM, 20GB storage
- **Evaluation Workers**: 4 vCPUs, 8GB RAM per worker (2-4 workers recommended)
- **Redis**: 2 vCPUs, 4GB RAM, 10GB storage
- **Database**: Managed PostgreSQL with 100GB+ storage
- **Monitoring**: 2 vCPUs, 4GB RAM, 50GB storage

**Recommended Production Setup:**
- **API Server**: 4 vCPUs, 8GB RAM, 50GB storage
- **Evaluation Workers**: 8 vCPUs, 16GB RAM per worker (4-8 workers)
- **Redis Cluster**: 3 nodes, 2 vCPUs, 4GB RAM each
- **Database**: Multi-zone PostgreSQL with 500GB+ storage
- **Monitoring**: 4 vCPUs, 8GB RAM, 200GB storage
- **Load Balancer**: Application Load Balancer or nginx

### Environment Configuration

#### Production Environment Variables

```bash
# Application settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_VERSION=1.0.0

# Database
DATABASE_URL=postgresql://user:pass@host:port/db
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI Services
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json
LANGSMITH_API_KEY=ls-your-langsmith-key
LANGSMITH_PROJECT=evaluation-production

# Task Queue
REDIS_URL=redis://redis-cluster:6379/0
CELERY_BROKER_URL=redis://redis-cluster:6379/0
CELERY_RESULT_BACKEND=redis://redis-cluster:6379/1

# Monitoring
PROMETHEUS_PORT=8001
GRAFANA_PASSWORD=secure-password
FLOWER_USERNAME=admin
FLOWER_PASSWORD=secure-password

# Security
SECRET_KEY=your-very-long-secure-secret-key
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Performance
CELERY_CONCURRENCY=4
MAX_WORKERS=8
REQUEST_TIMEOUT=300
```

#### Docker Compose Production Override

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  evaluation-worker:
    image: your-registry/evaluation-worker:latest
    deploy:
      replicas: 4
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - CELERY_CONCURRENCY=6
      - LOG_LEVEL=INFO
    volumes:
      - /path/to/credentials:/app/credentials:ro
      - /path/to/logs:/app/logs
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: evaluation.worker

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
    volumes:
      - redis_data:/data
    sysctls:
      - net.core.somaxconn=1024

  prometheus:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'
      - '--storage.tsdb.retention.size=50GB'
      - '--web.enable-lifecycle'
```

### Kubernetes Deployment (Alternative)

#### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: llm-evaluation

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: evaluation-config
  namespace: llm-evaluation
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  CELERY_CONCURRENCY: "4"
  PROMETHEUS_PORT: "8001"
```

#### Deployment Manifests

```yaml
# k8s/evaluation-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: evaluation-worker
  namespace: llm-evaluation
spec:
  replicas: 4
  selector:
    matchLabels:
      app: evaluation-worker
  template:
    metadata:
      labels:
        app: evaluation-worker
    spec:
      containers:
      - name: worker
        image: your-registry/evaluation-worker:latest
        resources:
          requests:
            cpu: 2
            memory: 4Gi
          limits:
            cpu: 4
            memory: 8Gi
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        envFrom:
        - configMapRef:
            name: evaluation-config
        - secretRef:
            name: evaluation-secrets
        volumeMounts:
        - name: credentials
          mountPath: /app/credentials
          readOnly: true
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import redis; r=redis.Redis.from_url('redis://redis-service:6379'); r.ping()"
          initialDelaySeconds: 30
          periodSeconds: 30
      volumes:
      - name: credentials
        secret:
          secretName: gcp-credentials

---
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: llm-evaluation
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 1
            memory: 4Gi
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: llm-evaluation
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### Monitoring Setup

#### Prometheus Configuration

```yaml
# monitoring/prometheus-prod.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    datacenter: 'us-west-2'

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'evaluation-api'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - llm-evaluation
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: evaluation-api
    
  - job_name: 'evaluation-workers'
    kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - llm-evaluation
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: evaluation-worker

alerting:
  alertmanagers:
  - kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
        - monitoring
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      action: keep
      regex: alertmanager
```

#### Grafana Dashboard

```json
{
  "dashboard": {
    "id": null,
    "title": "LLM Evaluation System",
    "tags": ["evaluation", "llm"],
    "timezone": "UTC",
    "panels": [
      {
        "title": "Evaluation Jobs per Hour",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(evaluation_jobs_total[1h])",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Model Performance Scores",
        "type": "graph",
        "targets": [
          {
            "expr": "model_performance_score{metric=\"overall_score\"}",
            "legendFormat": "{{model}}"
          }
        ]
      },
      {
        "title": "API Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Security Considerations

#### Network Security

```yaml
# Security group rules (AWS example)
security_groups:
  api:
    ingress:
      - protocol: tcp
        from_port: 80
        to_port: 80
        cidr_blocks: ["0.0.0.0/0"]
      - protocol: tcp
        from_port: 443
        to_port: 443
        cidr_blocks: ["0.0.0.0/0"]
    egress:
      - protocol: tcp
        from_port: 5432
        to_port: 5432
        source_security_group: database
      - protocol: tcp
        from_port: 6379
        to_port: 6379
        source_security_group: redis

  workers:
    ingress:
      - protocol: tcp
        from_port: 8001
        to_port: 8001
        source_security_group: monitoring
    egress:
      - protocol: tcp
        from_port: 443
        to_port: 443
        cidr_blocks: ["0.0.0.0/0"]  # For AI API calls
```

#### Secrets Management

```bash
# Using AWS Secrets Manager
aws secretsmanager create-secret \
  --name "evaluation/openai-key" \
  --secret-string "sk-your-key"

# Using Kubernetes secrets
kubectl create secret generic evaluation-secrets \
  --from-literal=OPENAI_API_KEY="sk-your-key" \
  --from-literal=DATABASE_URL="postgresql://..." \
  --namespace=llm-evaluation

# Using environment files with proper permissions
chmod 600 .env.production
chown root:root .env.production
```

#### TLS/SSL Configuration

```nginx
# nginx configuration
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /metrics {
        deny all;  # Restrict metrics endpoint
    }
}
```

### Performance Tuning

#### Database Optimization

```sql
-- Indexes for performance
CREATE INDEX CONCURRENTLY idx_evaluation_results_job_model 
ON evaluation_results(job_id, model_name);

CREATE INDEX CONCURRENTLY idx_evaluation_jobs_status_created 
ON evaluation_jobs(status, created_at DESC) 
WHERE status IN ('running', 'pending');

-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET work_mem = '32MB';
```

#### Redis Configuration

```conf
# redis.conf production settings
maxmemory 4gb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
tcp-backlog 511
save 900 1
save 300 10
save 60 10000
```

#### Celery Worker Tuning

```python
# celery_config.py
from kombu import Queue

# Optimized task routing
task_routes = {
    'evaluation_tasks.process_evaluation_job': {'queue': 'evaluation'},
    'evaluation_tasks.batch_evaluate_prompts': {'queue': 'batch'},
    'evaluation_tasks.generate_reports': {'queue': 'reports'},
}

# Worker settings
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 1000
task_time_limit = 1800  # 30 minutes
task_soft_time_limit = 1500  # 25 minutes

# Queue definitions
task_default_queue = 'default'
task_queues = (
    Queue('evaluation', routing_key='evaluation'),
    Queue('batch', routing_key='batch'),
    Queue('reports', routing_key='reports'),
    Queue('maintenance', routing_key='maintenance'),
)
```

### Backup and Disaster Recovery

#### Database Backup Strategy

```bash
#!/bin/bash
# backup-database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/evaluation"
DATABASE_URL="postgresql://..."

# Create backup
pg_dump $DATABASE_URL | gzip > "$BACKUP_DIR/evaluation_backup_$DATE.sql.gz"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/evaluation_backup_$DATE.sql.gz" \
  s3://your-backup-bucket/database/

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

#### Disaster Recovery Plan

1. **Database Recovery**:
   ```bash
   # Restore from backup
   gunzip -c evaluation_backup_20240101_120000.sql.gz | psql $NEW_DATABASE_URL
   ```

2. **Redis Recovery**:
   ```bash
   # Redis data is primarily transient, restart workers to rebuild queues
   docker-compose restart evaluation-worker priority-worker
   ```

3. **Application Recovery**:
   ```bash
   # Deploy to new environment
   docker-compose -f docker-compose.prod.yml up -d
   
   # Verify health
   curl http://new-api-endpoint/health
   ```

### Maintenance Procedures

#### Regular Maintenance Tasks

```bash
#!/bin/bash
# maintenance.sh

# 1. Update performance cache
curl -X POST http://localhost:8000/api/v1/evaluation/maintenance/update-cache

# 2. Clean up old results (automated via Celery beat)
# This runs automatically but can be triggered manually
curl -X POST http://localhost:8000/api/v1/evaluation/maintenance/cleanup

# 3. Generate monthly reports
curl -X POST http://localhost:8000/api/v1/evaluation/reports/monthly

# 4. Health check all components
curl http://localhost:8000/health/detailed
```

#### Scaling Operations

```bash
# Scale workers horizontally
docker-compose -f docker-compose.prod.yml up -d --scale evaluation-worker=6

# Kubernetes scaling
kubectl scale deployment evaluation-worker --replicas=8 -n llm-evaluation

# Monitor scaling impact
watch kubectl top pods -n llm-evaluation
```

### Troubleshooting

#### Common Issues

1. **High Memory Usage**:
   ```bash
   # Check memory usage
   docker stats
   
   # Reduce Celery concurrency
   export CELERY_CONCURRENCY=2
   docker-compose restart evaluation-worker
   ```

2. **Queue Backup**:
   ```bash
   # Check queue size
   redis-cli llen celery
   
   # Scale workers
   docker-compose up -d --scale evaluation-worker=4
   ```

3. **Database Connection Issues**:
   ```bash
   # Check connection pool
   psql $DATABASE_URL -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
   
   # Restart API if needed
   docker-compose restart fastapi-app
   ```

#### Log Analysis

```bash
# Centralized logging with grep
grep "ERROR" logs/evaluation-*.log | tail -20

# Worker status
curl http://localhost:5555/api/workers

# System metrics
curl http://localhost:9090/api/v1/query?query=up
```

This completes the comprehensive production deployment guide for the LLM Evaluation System.