# Real2.AI Backend

Australian Real Estate AI Assistant - FastAPI Backend Implementation

## Overview

This is the backend implementation for Real2.AI, an AI-powered assistant for Australian real estate contract analysis. The system uses LangGraph for intelligent agent orchestration and provides comprehensive analysis of property purchase agreements according to Australian state laws.

## Architecture

### Core Components

- **FastAPI Application** (`app/main.py`): RESTful API with async support
- **LangGraph Workflow** (`app/agents/contract_workflow.py`): Multi-step contract analysis
- **Australian Tools** (`app/agents/australian_tools.py`): State-specific legal analysis
- **Document Service** (`app/services/document_service.py`): File processing and OCR
- **WebSocket Service** (`app/services/websocket_service.py`): Real-time updates
- **Authentication** (`app/core/auth.py`): JWT-based user authentication
- **Database** (`app/core/database.py`): Supabase PostgreSQL integration

### Technology Stack

- **Framework**: FastAPI 0.104.1 with async/await
- **AI/ML**: OpenAI GPT-4, LangChain, LangGraph
- **Database**: Supabase (PostgreSQL with Row Level Security)
- **Document Processing**: PyPDF2, python-docx, unstructured
- **Authentication**: JWT tokens with Supabase Auth
- **Real-time**: WebSocket connections
- **Storage**: Supabase Storage for document files

## Features

### 📄 Document Processing
- PDF, DOC, DOCX file upload and processing
- OCR text extraction with confidence scoring
- Document validation and quality assessment
- Secure file storage with user isolation

### 🧠 AI-Powered Analysis
- Multi-step LangGraph workflow
- Australian state-specific legal compliance
- Risk assessment with severity scoring
- Automated recommendation generation

### 🇦🇺 Australian Real Estate Expertise
- **Stamp Duty Calculation**: All states with exemptions/surcharges
- **Cooling-off Periods**: State-specific validation
- **Special Conditions**: Finance, building/pest, strata analysis
- **Compliance Checking**: Property law requirements by state

### 🔐 Security & Authentication
- JWT-based authentication
- Row Level Security (RLS) policies
- User data isolation
- Secure file access controls

### 📊 Real-time Updates
- WebSocket progress tracking
- Live analysis status updates
- Document processing notifications
- Error handling and retry mechanisms

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication

### Document Management
- `POST /api/documents/upload` - Upload contract documents
- `GET /api/documents/{document_id}` - Get document details

### Contract Analysis
- `POST /api/contracts/analyze` - Start contract analysis
- `GET /api/contracts/{contract_id}/analysis` - Get analysis results
- `GET /api/contracts/{contract_id}/report` - Download analysis report

### User Management
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/preferences` - Update preferences
- `GET /api/users/usage-stats` - Usage statistics

### Real-time
- `WS /ws/contracts/{contract_id}/progress` - WebSocket for live updates

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── models.py          # Request/response models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── auth.py            # Authentication utilities
│   │   └── database.py        # Database client
│   ├── models/
│   │   ├── __init__.py
│   │   └── contract_state.py  # LangGraph state models
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── contract_workflow.py    # Main analysis workflow
│   │   └── australian_tools.py    # Australian-specific tools
│   └── services/
│       ├── __init__.py
│       ├── document_service.py     # Document processing
│       └── websocket_service.py    # Real-time communications
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── database_schema.sql       # Database schema and policies
├── test_startup.py          # Startup test script
└── README.md                # This file
```

## Setup Instructions

### 1. Environment Setup

```bash
# Clone the repository
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# AI Services
OPENAI_API_KEY=sk-your-openai-key
OPENAI_API_BASE=https://api.openai.com/v1

# Security
JWT_SECRET_KEY=your-jwt-secret-key

# Australian Specific
DEFAULT_AUSTRALIAN_STATE=NSW
ENABLE_STAMP_DUTY_CALCULATION=true
ENABLE_COOLING_OFF_VALIDATION=true
```

### 3. Database Setup

1. Create a Supabase project
2. Run the SQL schema in `database_schema.sql`
3. Configure Row Level Security policies
4. Create the documents storage bucket

### 4. Testing

```bash
# Test application startup
python test_startup.py

# Run the application
python -m uvicorn app.main:app --reload --port 8000
```

### 5. API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Usage Examples

### Upload and Analyze a Contract

```python
import httpx

# Upload document
files = {"file": ("contract.pdf", open("contract.pdf", "rb"), "application/pdf")}
response = httpx.post("http://localhost:8000/api/documents/upload", files=files)
document_id = response.json()["document_id"]

# Start analysis
analysis_request = {
    "document_id": document_id,
    "analysis_options": {
        "include_financial_analysis": True,
        "include_risk_assessment": True,
        "include_compliance_check": True
    }
}
response = httpx.post("http://localhost:8000/api/contracts/analyze", json=analysis_request)
contract_id = response.json()["contract_id"]

# Get results
response = httpx.get(f"http://localhost:8000/api/contracts/{contract_id}/analysis")
analysis_results = response.json()
```

### WebSocket Real-time Updates

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/contracts/${contractId}/progress`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`Analysis progress: ${data.data.progress_percent}%`);
};
```

## Australian Real Estate Features

### Stamp Duty Calculation

Supports all Australian states with accurate calculations including:
- First home buyer exemptions and concessions
- Foreign buyer surcharges
- Investment property surcharges
- State-specific thresholds and rates

### Cooling-off Period Validation

State-specific validation for:
- **NSW**: 5 business days (with exceptions)
- **VIC**: 3 business days
- **QLD**: 5 business days (no waiver)
- **SA**: 2 clear days
- **WA**: 5 business days
- **ACT**: 5 business days
- **TAS/NT**: No statutory period

### Special Conditions Analysis

Automated analysis of common Australian contract conditions:
- Finance clause validation
- Building and pest inspection requirements
- Strata/body corporate searches
- Council rates and approvals
- Settlement terms and time of essence clauses

## Development

### Adding New Features

1. **New API Endpoints**: Add to `app/main.py`
2. **Data Models**: Define in `app/api/models.py`
3. **Business Logic**: Implement in appropriate service modules
4. **Database Changes**: Update `database_schema.sql`

### Testing

```bash
# Run startup tests
python test_startup.py

# Add unit tests
pytest tests/

# Test specific endpoints
python -m pytest tests/test_contracts.py -v
```

### Deployment

The application is designed for deployment on:
- **Render**: Web service deployment
- **Supabase**: Database and authentication
- **Cloudflare**: CDN and domain management

## Monitoring and Logging

- Structured logging with contextual information
- Error tracking and performance monitoring
- Usage analytics and billing tracking
- Real-time system health monitoring

## Contributing

1. Follow PEP 8 style guidelines
2. Add type hints for all functions
3. Include docstrings for public methods
4. Test new features thoroughly
5. Update documentation as needed

## License

Proprietary - Real2.AI Platform