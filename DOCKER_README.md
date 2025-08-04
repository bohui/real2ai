# Real2.AI Docker Setup

This document explains how to run the Real2.AI application using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB of available RAM
- 10GB of available disk space

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd real2ai

# Copy environment template
cp docker.env.example .env

# Edit the .env file with your actual values
nano .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your actual API keys and configuration:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# Required: Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key

# Required: JWT Secret
JWT_SECRET_KEY=your-secure-jwt-secret-key

# Optional: Other API keys
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
```

### 3. Start the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Services Overview

### Core Services (Always Running)

- **backend**: FastAPI application on port 8000
- **postgres**: PostgreSQL database on port 5432
- **redis**: Redis cache on port 6379
- **celery-worker**: Background task processing
- **celery-beat**: Scheduled task processing

### Optional Services

- **frontend**: React development server (port 3000)
  ```bash
  docker-compose --profile frontend-dev up -d
  ```

- **nginx**: Reverse proxy for production (ports 80, 443)
  ```bash
  docker-compose --profile production up -d
  ```

## Development Workflow

### 1. Development Mode

```bash
# Start backend services only
docker-compose up backend postgres redis celery-worker celery-beat

# Run frontend locally (outside Docker)
cd frontend
npm install
npm run dev
```

### 2. Full Stack Development

```bash
# Start all services including frontend
docker-compose --profile frontend-dev up -d
```

### 3. Production Mode

```bash
# Start with nginx reverse proxy
docker-compose --profile production up -d
```

## Database Management

### Initialize Database

```bash
# The database will be automatically initialized with the schema
# from database_schema.sql when the postgres container starts
```

### Access Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U real2ai_user -d real2ai

# Backup database
docker-compose exec postgres pg_dump -U real2ai_user real2ai > backup.sql

# Restore database
docker-compose exec -T postgres psql -U real2ai_user -d real2ai < backup.sql
```

### Reset Database

```bash
# Remove database volume and restart
docker-compose down
docker volume rm real2ai_postgres_data
docker-compose up -d
```

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Health Checks

```bash
# Check service health
docker-compose ps

# Manual health check
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :8000
   lsof -i :5432
   lsof -i :6379
   ```

2. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

3. **Memory Issues**
   ```bash
   # Increase Docker memory limit in Docker Desktop
   # Or use swap space
   ```

4. **Database Connection Issues**
   ```bash
   # Check if postgres is ready
   docker-compose exec postgres pg_isready -U real2ai_user
   
   # Restart postgres
   docker-compose restart postgres
   ```

### Debug Mode

```bash
# Run with debug output
docker-compose up --verbose

# Access container shell
docker-compose exec backend bash
docker-compose exec postgres bash
```

## Production Deployment

### 1. Environment Setup

```bash
# Create production environment
cp docker.env.example .env.production
# Edit .env.production with production values
```

### 2. Build Production Images

```bash
# Build optimized images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start production stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 3. SSL Configuration

```bash
# Create SSL certificates
mkdir ssl
# Add your SSL certificates to ssl/ directory

# Start with nginx
docker-compose --profile production up -d
```

## Performance Tuning

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

### Database Optimization

```yaml
services:
  postgres:
    environment:
      POSTGRES_SHARED_PRELOAD_LIBRARIES: pg_stat_statements
      POSTGRES_MAX_CONNECTIONS: 100
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U real2ai_user real2ai > backup_$DATE.sql
gzip backup_$DATE.sql
EOF

chmod +x backup.sh
```

### Restore from Backup

```bash
# Restore database
gunzip -c backup_20240101_120000.sql.gz | docker-compose exec -T postgres psql -U real2ai_user -d real2ai
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **Network Security**: Use Docker networks for service communication
3. **User Permissions**: Run containers as non-root users
4. **SSL/TLS**: Use proper SSL certificates in production
5. **Regular Updates**: Keep base images updated

## Support

For issues and questions:
- Check the logs: `docker-compose logs`
- Review this documentation
- Create an issue in the repository 