# Real2.AI - Australian Real Estate AI Assistant

> "Your AI step before the deal."

Real2.AI is a specialized AI-powered platform for the Australian real estate market, providing intelligent contract analysis and comprehensive buyer agent assistance. Built with cutting-edge LangGraph multi-agent architecture specifically for Australian property laws, market conditions, and transaction processes.

## 🇦🇺 Australian Market Focus

- **State-Specific Compliance**: NSW, VIC, QLD contract understanding
- **Local Expertise**: Australian property laws and regulations
- **Market Intelligence**: Local market conditions and pricing insights
- **Legal Framework**: Compliance with Australian privacy and legal requirements

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ and pip
- Node.js 18+ and npm
- Supabase account and project
- OpenAI API key
- Google Gemini API key (for OCR)
- 4GB+ RAM

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Run database migrations
python manage.py migrate

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
# Navigate to frontend directory  
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the development server
npm run dev

# Access the application
open http://localhost:5173
```

For detailed setup instructions, see our [Development Guide](docs/development/SETUP_GUIDE.md).

## 🏗️ Architecture

### Backend (Current Implementation)
- **Framework**: FastAPI with async/await support
- **Database**: Supabase (PostgreSQL) with real-time capabilities  
- **AI/ML**: OpenAI GPT-4 with LangGraph multi-agent workflows
- **OCR**: Gemini 2.5 Pro with advanced prompt management
- **Prompt System**: Comprehensive PromptManager with template system
- **Caching**: Redis for performance optimization
- **Storage**: Supabase Storage for secure document management
- **External APIs**: Domain.com.au and CoreLogic integration

### Frontend (Current Implementation)
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite with hot module replacement
- **Styling**: Tailwind CSS with responsive design system
- **State Management**: Zustand with persistent storage
- **Real-time**: WebSocket integration for live updates
- **Testing**: Vitest with React Testing Library and comprehensive coverage
- **UI Components**: Custom component library with accessibility support

## 📚 Documentation

Our documentation is organized by category:

- **📋 [Requirements](docs/requirements/)** - Business requirements and specifications
- **🏗️ [Architecture](docs/architecture/)** - System design and technical architecture  
- **🚀 [Deployment](docs/deployment/)** - Setup and deployment guides
- **💻 [Development](docs/development/)** - Development notes and implementation details
- **🧪 [Testing](docs/testing/)** - Test reports and quality metrics
- **🔄 [Workflows](docs/workflows/)** - LangGraph workflows and diagrams
- **🔗 [API](docs/api/)** - Complete API reference and integration guides
- **🤖 [Prompt Management](docs/prompts/)** - PromptManager system documentation

## 🛠️ Development

### Current Implementation Status

✅ **Core Features Completed:**
- Advanced LangGraph workflow system with multi-agent orchestration
- Comprehensive PromptManager with template system and caching
- Gemini 2.5 Pro OCR integration with Australian legal document focus
- Complete CRUD operations for documents and contract analysis
- Real-time WebSocket progress tracking and notifications
- Australian state-specific legal compliance validation
- External API integrations (Domain.com.au, CoreLogic)
- Responsive React frontend with component library

📊 **Current Capabilities:**
- Document upload and processing (PDF, DOC, DOCX)
- OCR extraction with 95%+ accuracy for Australian contracts  
- Contract analysis with risk scoring and compliance checking
- Stamp duty calculations for all Australian states
- Real-time progress tracking via WebSocket
- Property profile analysis and market data integration
- User authentication and subscription management

### Backend Development
```bash
cd backend
pip install -r requirements.txt
# Configure .env with required API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend Development  
```bash
cd frontend
npm install
# Configure .env with API endpoints
npm run dev
```

See component READMEs for detailed setup and architecture information.

## 🧪 Testing

- **Backend**: `cd backend && python -m pytest`
- **Frontend**: `cd frontend && npm test`
- **E2E**: Integration tests with Playwright

View detailed test reports in [docs/testing/](docs/testing/).

## 📊 Key Features

### Contract Analysis
- **AI-Powered Review**: Advanced contract analysis using GPT-4
- **Risk Assessment**: Comprehensive risk scoring and recommendations
- **Compliance Check**: Australian legal compliance verification
- **Document OCR**: Gemini 2.5 Pro for scanned document processing

### User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Live progress tracking via WebSocket
- **Secure Processing**: Enterprise-grade security for sensitive documents
- **Accessibility**: WCAG 2.1 AA compliant interface

## 🏢 Business Model

- **Target Market**: Australian property buyers and real estate professionals
- **Pricing**: Subscription-based with per-document analysis
- **Launch**: Australia-first market entry
- **Growth**: Expand to additional markets and services

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: Use GitHub Issues for bug reports
- **Development**: See individual component READMEs

## 🔐 Security

- End-to-end encryption for document processing
- Supabase Auth with JWT tokens
- Australian privacy law compliance
- Secure document storage and processing

## 📄 License

Proprietary - All rights reserved

---

*Real2.AI - Making Australian property transactions smarter and safer.*