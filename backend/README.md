# Real2.AI Backend

A FastAPI-based backend for Real2.AI, providing contract analysis and real estate document processing capabilities.

## Features

- **Document Processing** (`app/services/document_service.py`): PDF and document upload/processing
- **Contract Analysis** (`app/agents/contract_workflow.py`): AI-powered contract analysis
- **Authentication** (`app/core/auth.py`): Supabase-based user authentication
- **WebSocket Support** (`app/services/websocket_service.py`): Real-time progress updates
- **Database Integration** (`app/core/database.py`): Supabase database operations

## Architecture

- **Framework**: FastAPI with async/await support
- **Database**: Supabase (PostgreSQL) with real-time capabilities
- **Authentication**: Supabase Auth with JWT tokens
- **Storage**: Supabase Storage for document management
- **AI/ML**: OpenAI GPT-4 with LangChain for document analysis
- **Caching**: Redis for session and data caching
- **Monitoring**: Sentry for error tracking and performance monitoring

## Quick Start

### Prerequisites

- Python 3.11+
- Supabase project
- OpenAI API key
- Redis server

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

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Redis Configuration
REDIS_URL=redis://localhost:6379

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
- `POST /api/contracts/analyze` - Start contract analysis
- `GET /api/contracts/{contract_id}/analysis` - Get analysis results
- `GET /api/contracts/{contract_id}/report` - Download analysis report

### User Management
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/preferences` - Update user preferences
- `GET /api/users/usage-stats` - Get usage statistics

### WebSocket
- `WS /ws/contracts/{contract_id}/progress` - Real-time progress updates

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
isort .
```

### Linting
```bash
flake8 .
```

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT License