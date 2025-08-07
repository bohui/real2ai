# Real2.AI Backend

A FastAPI-based backend for Real2.AI, providing advanced AI-powered contract analysis and real estate document processing capabilities using LangGraph multi-agent workflows and Gemini 2.5 Pro OCR.

## Features

- **Advanced Document Processing** (`app/services/document_service.py`): Multi-format document processing with Gemini 2.5 Pro OCR
- **LangGraph Workflows** (`app/agents/contract_workflow.py`): Multi-agent AI orchestration for contract analysis
- **Prompt Management** (`app/core/prompts/`): Comprehensive prompt system with template management and versioning
- **Authentication** (`app/core/auth.py`): Supabase Auth with JWT token management and refresh logic
- **Real-time Updates** (`app/services/websocket_service.py`): WebSocket support for live progress tracking
- **Intelligent Caching** (`app/services/cache_service.py`): Content-hash based caching with cross-user sharing
- **External Integrations** (`app/clients/`): Domain.com.au and CoreLogic API integration
- **Background Processing** (`app/tasks/`): Celery integration for async document processing
- **Evaluation System** (`app/services/evaluation_service.py`): LangSmith integration for AI model evaluation

## Architecture

- **Framework**: FastAPI with async/await support
- **Database**: Supabase (PostgreSQL) with real-time capabilities
- **Authentication**: Supabase Auth with JWT tokens
- **Storage**: Supabase Storage for document management
- **AI Orchestration**: LangGraph multi-agent workflow system with GPT-4 and Gemini 2.5 Pro
- **OCR**: Gemini 2.5 Pro with advanced prompt engineering for Australian legal documents
- **Prompt System**: PromptManager with template caching and version control
- **Caching**: Content-hash based shared resource caching with Supabase
- **Background Tasks**: Celery with Redis for async processing
- **Evaluation**: LangSmith integration for AI performance monitoring
- **Monitoring**: Sentry for error tracking and performance monitoring

## Quick Start

### Prerequisites

- Python 3.11+
- Supabase project
- OpenAI API key
- Google Gemini API key
- LangSmith API key
- Redis server (for Celery)
- Domain.com.au API key (optional)
- CoreLogic API key (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd real2ai/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the development server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

## Environment Variables

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# AI Configuration
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
LANGSMITH_API_KEY=your_langsmith_api_key

# Background Processing
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379

# Optional: External APIs
STRIPE_SECRET_KEY=your_stripe_key
DOMAIN_API_KEY=your_domain_api_key
CORELOGIC_API_KEY=your_corelogic_api_key

# Monitoring
SENTRY_DSN=your_sentry_dsn
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Document Management
- `POST /api/documents/upload` - Upload contract documents
- `GET /api/documents/{document_id}` - Get document details

### Contract Analysis
- `POST /api/contracts/analyze` - Start LangGraph-powered contract analysis
- `GET /api/contracts/{contract_id}/analysis` - Get comprehensive analysis results with risk scoring
- `GET /api/contracts/{contract_id}/progress` - Get real-time analysis progress
- `GET /api/contracts/{contract_id}/report` - Download detailed analysis report

### Property Intelligence
- `POST /api/property/analyze` - Analyze property data with market insights
- `GET /api/property/{address}/profile` - Get property profile and market data
- `POST /api/property/valuation` - Get property valuation estimates

### OCR Processing
- `POST /api/ocr/extract` - Extract text from documents using Gemini 2.5 Pro
- `GET /api/ocr/{job_id}/status` - Get OCR processing status

### Evaluation System
- `POST /api/evaluation/analyze` - Analyze AI model performance
- `GET /api/evaluation/metrics` - Get evaluation metrics and insights

### User Management
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/preferences` - Update user preferences
- `GET /api/users/usage-stats` - Get usage statistics

### WebSocket
- `WS /ws/documents/{document_id}` - Real-time document processing updates
- Real-time events: document_uploaded, processing_started, analysis_progress, analysis_complete

## Development

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/performance/

# Run with coverage
python -m pytest --cov=app --cov-report=html
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Run comprehensive tests
python scripts/run_comprehensive_tests.py
```

### Background Tasks
```bash
# Start Celery worker
celery -A app.tasks.celery worker --loglevel=info

# Monitor tasks
celery -A app.tasks.celery flower
```

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT License