# 🚀 Deployment Guide - Rural Advisory System v2.0

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Security & SSL](#security--ssl)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Setup

```bash
# 1. Clone repository
git clone https://github.com/yourorg/rural_advisory.git
cd rural_advisory

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.template .env
# Edit .env with your configuration

# 5. Initialize database
python -m alembic upgrade head

# 6. Load disease database
python -c "from services.database_service import get_database_service; db = get_database_service()"

# 7. Run tests
pytest tests/ -v --cov

# 8. Start development servers

# Terminal 1: FastAPI backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Streamlit UI
streamlit run app.py

# Terminal 3: Celery worker (optional)
celery -A tasks worker --loglevel=info
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# API documentation
# Visit http://localhost:8000/docs

# List diseases
curl http://localhost:8000/api/diseases

# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Farmer",
    "primary_crops": ["tomato"]
  }'
```

---

## Docker Deployment

### Build & Run

```bash
# 1. Build images
docker-compose build

# 2. Start services (production mode)
docker-compose up -d

# 3. Check service status
docker-compose ps

# 4. View logs
docker-compose logs -f api
docker-compose logs -f ui

# 5. Run migrations
docker-compose exec api alembic upgrade head

# 6. Access services
# API: http://localhost:8000
# UI: http://localhost:8501
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### Environment Variables

Create `.env` file in project root:

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# Database
DB_USER=rural_admin
DB_PASSWORD=secure_password_123
DB_NAME=rural_advisory

# Redis
REDIS_PASSWORD=redis_secure_123

# APIs
OPENWEATHER_API_KEY=your_api_key_here

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256

# Logging
LOG_LEVEL=INFO

# Monitoring
SENTRY_ENABLED=true
SENTRY_DSN=https://your-sentry-dsn

# Grafana
GRAFANA_PASSWORD=secure_grafana_password
```

### Docker Networks & Volumes

```bash
# View networks
docker network ls

# View volumes
docker volume ls

# Cleanup
docker-compose down -v  # Remove volumes too
```

### Scaling

```bash
# Scale API service
docker-compose up -d --scale api=3

# Use load balancer (nginx) for distribution
```

---

## Kubernetes Deployment

### Kubernetes Manifests

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rural-advisory-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rural-advisory-api
  template:
    metadata:
      labels:
        app: rural-advisory-api
    spec:
      containers:
      - name: api
        image: rural-advisory:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: redis_url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Helm Chart

```bash
# Create Helm chart
helm create rural-advisory

# Install
helm install rural-advisory ./rural-advisory -f values.yaml

# Upgrade
helm upgrade rural-advisory ./rural-advisory -f values.yaml

# Check status
helm status rural-advisory
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace production

# Create secrets
kubectl create secret generic db-credentials \
  --from-literal=url=postgresql://user:pass@host/db \
  -n production

# Apply manifests
kubectl apply -f k8s/ -n production

# Check deployment
kubectl get deployments -n production
kubectl get pods -n production
kubectl logs -f deployment/rural-advisory-api -n production

# Scale
kubectl scale deployment rural-advisory-api --replicas=5 -n production
```

---

## Cloud Deployment

### AWS Deployment

#### ECS with Fargate

```bash
# 1. Create ECS cluster
aws ecs create-cluster --cluster-name rural-advisory

# 2. Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 3. Create service
aws ecs create-service \
  --cluster rural-advisory \
  --service-name rural-advisory-api \
  --task-definition rural-advisory:1 \
  --desired-count 3
```

#### RDS for Database

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier rural-advisory-db \
  --db-instance-class db.t3.small \
  --engine postgres \
  --master-username admin \
  --master-user-password your_password \
  --allocated-storage 100
```

#### ElastiCache for Redis

```bash
# Create cache cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id rural-advisory-cache \
  --cache-node-type cache.t3.micro \
  --engine redis
```

### Google Cloud Deployment

```bash
# 1. Build image
gcloud builds submit --tag gcr.io/PROJECT_ID/rural-advisory:latest

# 2. Deploy to Cloud Run
gcloud run deploy rural-advisory \
  --image gcr.io/PROJECT_ID/rural-advisory:latest \
  --region us-central1 \
  --platform managed \
  --memory 1Gi \
  --cpu 1

# 3. Set environment variables
gcloud run services update rural-advisory \
  --set-env-vars DATABASE_URL=...
```

### Azure Deployment

```bash
# 1. Build and push image
az acr build --registry myregistry --image rural-advisory:latest .

# 2. Deploy container instance
az container create \
  --resource-group myresourcegroup \
  --name rural-advisory \
  --image myregistry.azurecr.io/rural-advisory:latest \
  --cpu 1 --memory 1
```

---

## Security & SSL

### SSL/TLS Certificate

```bash
# Using Let's Encrypt with Certbot
certbot certonly --standalone -d yourdomain.com

# Or with Docker
docker run -it --rm --name certbot \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d yourdomain.com
```

### Nginx Configuration with SSL

```nginx
upstream api {
    server api:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

---

## Monitoring & Logging

### Prometheus Monitoring

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rural-advisory'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboards

1. Create dashboard in Grafana UI
2. Add Prometheus as datasource
3. Create panels for:
   - API response time
   - Prediction accuracy
   - Error rate
   - Model performance

### ELK Stack Logging

```bash
# Elasticsearch
docker run -d --name elasticsearch \
  -e discovery.type=single-node \
  docker.elastic.co/elasticsearch/elasticsearch:latest

# Logstash
docker run -d --name logstash \
  -v /path/to/logstash.conf:/usr/share/logstash/pipeline/logstash.conf \
  docker.elastic.co/logstash/logstash:latest

# Kibana
docker run -d --name kibana \
  -e ELASTICSEARCH_HOSTS=http://elasticsearch:9200 \
  docker.elastic.co/kibana/kibana:latest
```

### CloudWatch Logs (AWS)

```bash
# Configure CloudWatch
aws logs create-log-group --log-group-name /aws/ecs/rural-advisory

# Stream logs
aws logs tail /aws/ecs/rural-advisory --follow
```

---

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -U rural_admin -h localhost rural_advisory > backup.sql

# Automated daily backup
0 2 * * * pg_dump -U rural_admin rural_advisory | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Restore
psql -U rural_admin -h localhost rural_advisory < backup.sql
```

### Redis Backup

```bash
# Save snapshot
redis-cli BGSAVE

# Copy persistence file
cp /var/lib/redis/dump.rdb /backups/redis_$(date +%Y%m%d).rdb
```

### Model Backup

```bash
# Backup models
tar -czf models_backup_$(date +%Y%m%d).tar.gz ./models/

# Restore
tar -xzf models_backup_20240101.tar.gz
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Error
```bash
# Check PostgreSQL status
docker-compose ps database

# View logs
docker-compose logs database

# Verify credentials
psql -U rural_admin -h localhost -d rural_advisory -c "SELECT 1"
```

#### 2. API Not Responding
```bash
# Check health
curl http://localhost:8000/health

# View API logs
docker-compose logs api

# Check ports
lsof -i :8000
```

#### 3. Model Loading Issues
```bash
# Check model directory
ls -la ./models/

# Download missing model
python scripts/download_models.py

# Test model loading
python -c "from services.model_manager import get_model_manager; m = get_model_manager(); print(m.get_model_info())"
```

#### 4. Memory Issues
```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
# Restart service
docker-compose restart api
```

#### 5. High CPU Usage
```bash
# Identify process
top -p $(pgrep -f "uvicorn|streamlit")

# Reduce worker count or batch size
# Adjust settings in config/settings.py
```

### Performance Tuning

```bash
# Database query optimization
VACUUM ANALYZE;
CREATE INDEX idx_predictions_disease ON predictions(predicted_disease);

# Redis optimization
CONFIG SET maxmemory 512mb
CONFIG SET maxmemory-policy allkeys-lru

# API optimization
# Increase workers in Dockerfile
# Enable response caching
```

### Logging & Debugging

```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker-compose up api

# View full request/response
# Enable in settings.py: logging middleware

# Use Sentry for error tracking
# Configure SENTRY_DSN in .env
```

---

## Post-Deployment Checklist

- [ ] Database migrated and verified
- [ ] Environment variables configured
- [ ] SSL/TLS certificates installed
- [ ] Monitoring (Prometheus/Grafana) working
- [ ] Logging (ELK/CloudWatch) working
- [ ] Backups scheduled
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Security audit done
- [ ] Documentation updated

---

## Support & Resources

- **Documentation**: https://docs.ruralavisory.com
- **GitHub**: https://github.com/yourorg/rural_advisory
- **Issues**: https://github.com/yourorg/rural_advisory/issues
- **Discussion**: https://github.com/yourorg/rural_advisory/discussions

---

**Happy Deploying! 🚀**
