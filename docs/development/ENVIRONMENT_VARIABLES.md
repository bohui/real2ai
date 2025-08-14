# Environment Variables Reference

Complete guide to all environment variables used in Real2.AI platform.

## Backend Environment Variables

### Core Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Application environment (development/staging/production) |
| `DEBUG` | No | `true` | Enable debug mode for development |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Database Configuration (Supabase)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | **Yes** | - | Supabase project URL |
| `SUPABASE_ANON_KEY` | **Yes** | - | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | **Yes** | - | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Prod: **Yes** | - | Supabase JWT secret used by backend to verify HS256 access tokens for DB RLS |
| `DATABASE_URL` | No | - | Direct PostgreSQL connection URL (for local development) |

### AI Services Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | - | OpenAI API key for GPT models |
| `GEMINI_API_KEY` | **Yes** | - | Google Gemini API key for OCR |
| `LANGSMITH_API_KEY` | No | - | LangSmith API key for tracing |
| `LANGSMITH_PROJECT` | No | `real2ai-development` | LangSmith project name |
| `LANGSMITH_ENDPOINT` | No | `https://api.smith.langchain.com` | LangSmith API endpoint |

### Background Processing (Celery)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELERY_BROKER_URL` | **Yes** | `redis://localhost:6379/0` | Celery message broker URL |
| `CELERY_RESULT_BACKEND` | **Yes** | `redis://localhost:6379/1` | Celery result backend URL |
| `CELERY_TASK_SERIALIZER` | No | `json` | Task serialization format |
| `CELERY_RESULT_SERIALIZER` | No | `json` | Result serialization format |
| `CELERY_ACCEPT_CONTENT` | No | `json` | Accepted content types |
| `CELERY_TIMEZONE` | No | `UTC` | Celery timezone |
| `CELERY_ENABLE_UTC` | No | `true` | Enable UTC for Celery |
| `CELERY_CONCURRENCY` | No | `2` | Number of concurrent workers |

### External API Integration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | No | - | Stripe secret key for payments |
| `STRIPE_PUBLISHABLE_KEY` | No | - | Stripe publishable key |
| `DOMAIN_API_KEY` | No | - | Domain.com.au API key |
| `CORELOGIC_API_KEY` | No | - | CoreLogic API key |

### Security Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | **Yes** | - | JWT signing secret key |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRATION_HOURS` | No | `24` | JWT token expiration time |

### File Storage

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAX_FILE_SIZE` | No | `52428800` | Maximum file size in bytes (50MB) |
| `ALLOWED_FILE_TYPES` | No | `pdf,doc,docx` | Allowed file extensions |

### Monitoring & Observability

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis URL for caching |

### Australian Specific Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEFAULT_AUSTRALIAN_STATE` | No | `NSW` | Default Australian state |
| `ENABLE_STAMP_DUTY_CALCULATION` | No | `true` | Enable stamp duty calculations |
| `ENABLE_COOLING_OFF_VALIDATION` | No | `true` | Enable cooling-off period validation |

## Frontend Environment Variables

### API Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | **Yes** | `http://localhost:8000` | Backend API base URL |
| `VITE_WS_BASE_URL` | **Yes** | `ws://localhost:8000` | WebSocket base URL |
| `VITE_APP_URL` | No | `http://localhost:5173` | Frontend application URL |

### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_APP_NAME` | No | `Real2.AI` | Application name |
| `VITE_APP_DESCRIPTION` | No | `Australian Contract Analysis Platform` | App description |

### External Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_SENTRY_DSN` | No | - | Sentry DSN for frontend error tracking |
| `VITE_LANGSMITH_API_KEY` | No | - | LangSmith API key for frontend tracing |

### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_ENABLE_ANALYTICS` | No | `false` | Enable analytics tracking |
| `VITE_ENABLE_WEBSOCKETS` | No | `true` | Enable WebSocket functionality |
| `VITE_ENABLE_DEMO_MODE` | No | `true` | Enable demo mode features |

### Regional Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_DEFAULT_STATE` | No | `NSW` | Default Australian state |
| `VITE_DEFAULT_TIMEZONE` | No | `Australia/Sydney` | Default timezone |

### Development

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_LOG_LEVEL` | No | `info` | Frontend logging level |
| `VITE_ENABLE_DEBUG` | No | `false` | Enable debug mode |

## Environment-Specific Configurations

### Development Environment

```bash
# Backend (.env)
ENVIRONMENT=development
DEBUG=true
SUPABASE_URL=https://your-dev-project.supabase.co
SUPABASE_ANON_KEY=your-dev-anon-key
SUPABASE_SERVICE_KEY=your-dev-service-key
SUPABASE_JWT_SECRET=your-dev-supabase-jwt-secret
OPENAI_API_KEY=sk-your-openai-dev-key
GEMINI_API_KEY=your-gemini-dev-key
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Frontend (.env)
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_ENABLE_DEMO_MODE=true
VITE_LOG_LEVEL=debug
```

### Production Environment

```bash
# Backend (.env.production)
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SUPABASE_URL=https://your-prod-project.supabase.co
SUPABASE_ANON_KEY=your-prod-anon-key
SUPABASE_SERVICE_KEY=your-prod-service-key
SUPABASE_JWT_SECRET=your-prod-supabase-jwt-secret
OPENAI_API_KEY=sk-your-openai-prod-key
GEMINI_API_KEY=your-gemini-prod-key
LANGSMITH_API_KEY=ls-your-langsmith-key
LANGSMITH_PROJECT=real2ai-production
CELERY_BROKER_URL=redis://prod-redis:6379/0
CELERY_RESULT_BACKEND=redis://prod-redis:6379/1
CELERY_CONCURRENCY=8
SENTRY_DSN=https://your-sentry-dsn
STRIPE_SECRET_KEY=sk_live_your-stripe-key
DOMAIN_API_KEY=your-domain-prod-key
CORELOGIC_API_KEY=your-corelogic-prod-key

# Frontend (.env.production)
VITE_API_BASE_URL=https://api.real2.ai
VITE_WS_BASE_URL=wss://api.real2.ai
VITE_APP_URL=https://real2.ai
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEMO_MODE=false
VITE_LOG_LEVEL=warn
VITE_SENTRY_DSN=https://your-frontend-sentry-dsn
```

## Security Best Practices

### 1. Secret Management
- Never commit API keys or secrets to version control
- Use different keys for development/staging/production
- Rotate keys regularly (quarterly recommended)
- Use environment-specific secret management services

### 2. Access Control
- Limit API key permissions to minimum required
- Use separate service accounts for different environments
- Monitor API key usage and set up alerts for unusual activity
- Implement key rotation procedures

### 3. Environment Isolation
- Keep development and production environments completely separate
- Use different database instances for each environment
- Implement proper network security for production

## Validation and Testing

### Required Variables Checker

The backend includes automatic validation for required environment variables:

```python
# Check if required variables are set
required_vars = [
    "SUPABASE_URL", 
    "SUPABASE_ANON_KEY", 
    "SUPABASE_SERVICE_KEY",
    "OPENAI_API_KEY", 
    "GEMINI_API_KEY",
    "JWT_SECRET_KEY"
]

for var in required_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Required environment variable {var} is not set")
```

### Environment Variable Loading Priority

1. System environment variables (highest priority)
2. `.env.local` file (local overrides)
3. `.env.{environment}` file (environment-specific)
4. `.env` file (default values)

## Troubleshooting

### Common Issues

**1. Missing Required Variables**
```
Error: Required environment variable OPENAI_API_KEY is not set
```
Solution: Set all required variables in your `.env` file

**2. Invalid Supabase Configuration**
```
Error: Failed to connect to Supabase
```
Solution: Verify URL and keys are correct for your Supabase project

**3. Celery Connection Issues**
```
Error: Cannot connect to broker
```
Solution: Ensure Redis is running and `CELERY_BROKER_URL` is correct

**4. WebSocket Connection Fails**
```
Error: WebSocket connection failed
```
Solution: Check `VITE_WS_BASE_URL` matches your backend WebSocket URL

### Environment Variable Debugging

```bash
# Backend - Check loaded environment variables
python -c "
import os
from app.core.config import settings
print('Environment:', os.getenv('ENVIRONMENT'))
print('Debug mode:', os.getenv('DEBUG'))
print('Supabase URL:', settings.supabase_url[:20] + '...' if settings.supabase_url else 'NOT SET')
"

# Frontend - Check Vite environment variables
npm run dev -- --mode development
# Check browser console for environment variable values
```

---

*This documentation covers all environment variables used in Real2.AI as of January 2025. Keep this updated as new variables are added.*