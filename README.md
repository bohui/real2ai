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
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 10GB+ disk space

### Get Started
```bash
# Clone the repository
git clone <repository-url>
cd real2ai

# Start the application
docker-compose up -d

# Access the application
open http://localhost:3000
```

For detailed setup instructions, see our [Deployment Guide](docs/deployment/DOCKER_README.md).

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI with async/await support
- **Database**: Supabase (PostgreSQL) with real-time capabilities
- **AI/ML**: OpenAI GPT-4 with LangGraph multi-agent workflows
- **OCR**: Gemini 2.5 Pro for advanced document processing
- **Storage**: Supabase Storage for secure document management

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with responsive design
- **State Management**: Zustand
- **Testing**: Vitest with React Testing Library

## 📚 Documentation

Our documentation is organized by category:

- **📋 [Requirements](docs/requirements/)** - Business requirements and specifications
- **🏗️ [Architecture](docs/architecture/)** - System design and technical architecture
- **🚀 [Deployment](docs/deployment/)** - Setup and deployment guides
- **💻 [Development](docs/development/)** - Development notes and implementation details
- **🧪 [Testing](docs/testing/)** - Test reports and quality metrics
- **🔄 [Workflows](docs/workflows/)** - LangGraph workflows and diagrams
- **🔗 [API](docs/api/)** - API documentation (coming soon)

## 🛠️ Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

See [Backend README](backend/README.md) for detailed setup.

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

See [Frontend README](frontend/README.md) for detailed setup.

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