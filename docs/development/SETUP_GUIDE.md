# Real2.AI Development Setup Guide

*Complete development environment setup for Real2.AI platform*  
*Last Updated: August 2025*

## Prerequisites

### System Requirements
- **OS**: macOS 10.15+, Ubuntu 20.04+, or Windows 10+ (with WSL2)
- **Memory**: 8GB+ RAM (16GB recommended for optimal performance)
- **Storage**: 10GB+ free disk space
- **Network**: Stable internet connection for API services

### Required Software

#### Core Development Tools
- **Python**: 3.11+ with pip
- **Node.js**: 18+ with npm
- **Git**: Latest version
- **Docker**: Optional but recommended for database services

#### Code Editors (Recommended)
- **VS Code** with extensions:
  - Python (Microsoft)
  - TypeScript and JavaScript Language Features
  - Tailwind CSS IntelliSense
  - REST Client
  - Docker (if using containers)

### Required API Keys and Services

#### Essential Services
1. **Supabase Project**
   - Sign up at [supabase.com](https://supabase.com)
   - Create a new project
   - Note your Project URL and API keys

2. **OpenAI API Key**
   - Sign up at [platform.openai.com](https://platform.openai.com)
   - Generate API key with GPT-4 access
   - Ensure billing is set up

3. **Google Gemini API Key**
   - Enable Gemini API at [aistudio.google.com](https://aistudio.google.com)
   - Generate API key
   - Ensure quota is sufficient for OCR usage

#### Optional External Services
- **Redis Cloud**: For production-level caching
- **Domain.com.au API**: For property data integration
- **CoreLogic API**: For advanced property analytics
- **Stripe**: For payment processing (production)

## Backend Setup

### 1. Clone and Navigate
```bash
# Clone the repository
git clone <repository-url>
cd real2ai/backend

# Check Python version
python --version  # Should be 3.11+
```

### 2. Virtual Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Verify critical packages
python -c "import fastapi, langgraph, openai, google.generativeai; print('All packages installed successfully')"
```

### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
```

**.env Configuration:**
```bash
# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# AI/ML Configuration
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-key

# External APIs (Optional)
DOMAIN_API_KEY=your-domain-key
CORELOGIC_API_KEY=your-corelogic-key

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379

# Development Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=info

# Application Settings
APP_NAME=Real2AI
APP_VERSION=2.0.0
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 5. Database Setup

#### Using Supabase (Recommended)
```bash
# Install Supabase CLI (optional)
npm install -g supabase

# Initialize Supabase (if using local development)
supabase init
supabase start
```

#### Database Schema
The application uses Supabase with the following key tables:
- `profiles` - User profiles and preferences
- `documents` - Uploaded contract documents
- `contracts` - Parsed contract data
- `contract_analyses` - Analysis results and reports
- `agent_sessions` - LangGraph workflow sessions

### 6. Verify Backend Setup
```bash
# Test database connection
python -c "from app.core.config import get_settings; print('Config loaded successfully')"

# Test API dependencies
python -c "from app.clients.openai import get_openai_client; print('OpenAI client ready')"
python -c "from app.clients.gemini import get_gemini_client; print('Gemini client ready')"

# Run basic health check
python -c "from app.main import app; print('FastAPI app created successfully')"
```

### 7. Start Backend Server
```bash
# Start development server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Alternative with more verbose logging
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### 8. Verify Backend is Running
```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "2.0.0",
#   "services": {
#     "database": "healthy",
#     "openai": "healthy",
#     "gemini": "healthy"
#   }
# }
```

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd ../frontend  # From backend directory
# OR
cd real2ai/frontend  # From root

# Check Node.js version
node --version  # Should be 18+
npm --version
```

### 2. Install Dependencies
```bash
# Install all dependencies
npm install

# Verify critical packages
npm list react vite @types/react tailwindcss zustand
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file
```

**.env Configuration:**
```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000

# Application Settings
VITE_APP_NAME=Real2.AI
VITE_APP_VERSION=2.0.0

# Feature Flags
VITE_ENABLE_DEMO_MODE=true
VITE_ENABLE_ANALYTICS=false

# Australian Settings
VITE_DEFAULT_STATE=NSW
VITE_DEFAULT_TIMEZONE=Australia/Sydney

# Development Settings
VITE_NODE_ENV=development
VITE_LOG_LEVEL=debug
```

### 4. Start Frontend Development Server
```bash
# Start development server with hot reload
npm run dev

# Alternative with specific host/port
npm run dev -- --host 0.0.0.0 --port 5173
```

### 5. Verify Frontend is Running
Open your browser to: http://localhost:5173

You should see the Real2.AI landing page with:
- Australian-themed branding
- Document upload interface
- Login/registration forms
- Responsive design

### 6. Test Frontend-Backend Integration
```bash
# Test API connectivity from browser console
fetch('http://localhost:8000/api/health')
  .then(r => r.json())
  .then(console.log)
```

## Development Workflow

### 1. Daily Development Setup
```bash
# Backend terminal (Terminal 1)
cd real2ai/backend
source .venv/bin/activate  # Activate virtual environment
uvicorn app.main:app --reload --port 8000

# Frontend terminal (Terminal 2) 
cd real2ai/frontend
npm run dev
```

### 2. Code Quality Tools

#### Backend Code Quality
```bash
# Format code with Black
black .

# Sort imports with isort
isort .

# Lint with flake8
flake8 .

# Type checking with mypy
mypy app/

# Run all quality checks
./scripts/lint.sh  # If available
```

#### Frontend Code Quality
```bash
# Lint TypeScript and JavaScript
npm run lint

# Fix linting issues
npm run lint:fix

# Type checking
npm run type-check

# Format with Prettier
npm run format
```

### 3. Testing

#### Backend Testing
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run specific test modules
python -m pytest tests/test_contract_analysis.py -v

# Run integration tests
python -m pytest tests/integration/ -v
```

#### Frontend Testing
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run coverage

# Run specific test suites
npm test -- --grep="DocumentUpload"
```

### 4. Database Development

#### Managing Schema Changes
```bash
# If using Alembic for migrations
alembic revision --autogenerate -m "Add new table"
alembic upgrade head

# If using Supabase migrations
supabase db diff --file new_migration
supabase db push
```

#### Database Reset (Development Only)
```bash
# Reset local database
supabase db reset

# Or manually clear tables via Supabase dashboard
```

### 5. API Testing

#### Using curl
```bash
# Test document upload
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -F "file=@contract.pdf" \
  -F "australian_state=NSW" \
  -F "contract_type=purchase_agreement"

# Test contract analysis
curl -X POST "http://localhost:8000/api/contracts/analyze" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "uuid-here", "analysis_options": {"include_risk_assessment": true}}'
```

#### Using REST Client (VS Code)
Create a `.http` file:
```http
### Health Check
GET http://localhost:8000/api/health

### Document Upload
POST http://localhost:8000/api/documents/upload
Authorization: Bearer {{auth_token}}
Content-Type: multipart/form-data; boundary=boundary

--boundary
Content-Disposition: form-data; name="file"; filename="contract.pdf"
Content-Type: application/pdf

< ./test_documents/sample_contract.pdf
--boundary
Content-Disposition: form-data; name="australian_state"

NSW
--boundary--
```

## Advanced Development Features

### 1. Hot Reload and Live Updates

#### Backend Hot Reload
FastAPI with `--reload` automatically reloads on file changes. For more advanced hot reload:

```bash
# Install watchdog for better file monitoring
pip install watchdog

# Use with uvicorn
uvicorn app.main:app --reload --reload-dir app/
```

#### Frontend Hot Module Replacement (HMR)
Vite provides automatic HMR. For custom HMR configuration:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    hmr: {
      overlay: true
    }
  }
})
```

### 2. Debugging Setup

#### Backend Debugging with VS Code
Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/app/main.py",
      "console": "integratedTerminal",
      "args": [
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ]
    }
  ]
}
```

#### Frontend Debugging
```javascript
// Browser dev tools debugging
if (import.meta.env.DEV) {
  console.log('Development mode - enhanced debugging enabled');
  window.debugAPI = api; // Expose API for debugging
}
```

### 3. Performance Monitoring

#### Backend Performance
```python
# Add to app/main.py for request timing
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

#### Frontend Performance
```typescript
// Performance monitoring
if (import.meta.env.DEV) {
  // Monitor component renders
  import('react-performance-devtool').then(
    ({ whyDidYouRender }) => whyDidYouRender(React)
  );
}
```

### 4. Environment-Specific Configuration

#### Multi-Environment Setup
```bash
# Development
cp .env.example .env.development

# Testing
cp .env.example .env.test

# Load specific environment
export NODE_ENV=development
# or
export NODE_ENV=test
```

## Troubleshooting Common Issues

### 1. Backend Issues

#### "ModuleNotFoundError" for app modules
```bash
# Ensure you're in the backend directory and virtual environment is activated
cd backend
source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### "Authentication failed" with Supabase
```bash
# Check your Supabase credentials
python -c "from app.clients.supabase import get_supabase_client; client = get_supabase_client(); print('Connected successfully')"

# Verify environment variables
python -c "import os; print('SUPABASE_URL:', os.getenv('SUPABASE_URL'))"
```

#### "OpenAI API key not found"
```bash
# Verify API key is set
python -c "import os; print('OpenAI key starts with:', os.getenv('OPENAI_API_KEY', 'NOT SET')[:10])"
```

### 2. Frontend Issues

#### "Cannot connect to backend"
- Ensure backend is running on port 8000
- Check CORS settings in backend configuration
- Verify `VITE_API_BASE_URL` in frontend `.env`

#### "Module not found" errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Build errors with TypeScript
```bash
# Run type checking
npm run type-check

# Fix common issues
npm run lint:fix
```

### 3. Integration Issues

#### WebSocket connection failures
- Check firewall settings
- Verify WebSocket URL format (`ws://` not `wss://` for local development)
- Ensure backend WebSocket handler is properly configured

#### File upload failures
- Check file size limits (50MB default)
- Verify CORS settings allow file uploads
- Check backend storage configuration

### 4. Performance Issues

#### Slow API responses
- Check database connection and query performance
- Monitor OpenAI API response times
- Verify Redis caching is working (if configured)

#### Frontend rendering issues
- Check for React component re-rendering loops
- Verify state management efficiency
- Monitor network requests in browser dev tools

## Development Best Practices

### 1. Code Organization
- Follow existing directory structure
- Use TypeScript interfaces for API contracts
- Implement error handling at service boundaries
- Write comprehensive tests for new features

### 2. Git Workflow
```bash
# Feature branch workflow
git checkout -b feature/new-analysis-feature
git commit -m "feat: add enhanced risk analysis"
git push origin feature/new-analysis-feature
# Create pull request
```

### 3. Documentation
- Update API documentation for new endpoints
- Add docstrings for Python functions
- Document React component props and usage
- Keep README files current

### 4. Testing Strategy
- Write unit tests for business logic
- Create integration tests for API endpoints
- Add component tests for React components
- Maintain >80% test coverage

---

This comprehensive setup guide provides everything needed to get the Real2.AI development environment running. For specific implementation details, refer to the component-level documentation in the respective backend and frontend directories.