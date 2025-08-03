# Real2.AI Frontend

A modern React TypeScript application for Australian contract analysis powered by AI.

## Features

- 🏢 **Australian Real Estate Focus**: Specialized for Australian property contracts and compliance
- 🤖 **AI-Powered Analysis**: Advanced contract analysis using LangGraph and GPT-4
- 📊 **Risk Assessment**: Comprehensive risk scoring and recommendations
- 🔒 **Secure Processing**: Enterprise-grade security for sensitive documents
- 📱 **Responsive Design**: Works seamlessly across desktop, tablet, and mobile
- ♿ **Accessibility**: WCAG 2.1 AA compliant interface
- 🌐 **Real-time Updates**: Live progress tracking with WebSocket integration

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Forms**: React Hook Form with Zod validation
- **Routing**: React Router DOM
- **Animation**: Framer Motion
- **Icons**: Lucide React
- **Testing**: Vitest + React Testing Library

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser to `http://localhost:5173`

## Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality
npm run lint         # Run ESLint
npm run lint:fix     # Fix ESLint issues
npm run type-check   # Run TypeScript compiler

# Testing
npm run test         # Run tests
npm run test:ui      # Run tests with UI
npm run coverage     # Generate test coverage
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components (Button, Input, etc.)
│   ├── forms/          # Form components
│   ├── layout/         # Layout components
│   ├── analysis/       # Analysis-specific components
│   ├── auth/           # Authentication components
│   └── notifications/  # Notification system
├── pages/              # Page components
│   └── auth/          # Authentication pages
├── store/              # Zustand stores
├── services/           # API services and utilities
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
├── hooks/              # Custom React hooks
└── styles/             # Global styles and Tailwind config
```

## Key Features

### Authentication
- JWT-based authentication
- Secure token storage
- Protected routes
- Demo mode support

### Contract Analysis
- Drag-and-drop file upload
- Real-time progress tracking
- Comprehensive risk assessment
- Australian compliance checking
- Executive summary generation

### User Interface
- Modern, clean design
- Australian-inspired color scheme
- Responsive layout
- Dark mode support (coming soon)
- Accessibility features

### State Management
- Zustand for client state
- TanStack Query for server state
- Persistent storage for auth
- Real-time WebSocket integration

## Australian Compliance

This application is specifically designed for Australian real estate:

- **State-specific regulations**: Support for all Australian states and territories
- **Legal compliance**: ACCC and fair trading compliance checks
- **Local terminology**: Australian legal and real estate terminology
- **Currency and dates**: Australian dollar and date formats
- **Time zones**: Australian time zone support

## Environment Variables

Key environment variables in `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_APP_NAME=Real2.AI
VITE_ENABLE_DEMO_MODE=true
VITE_DEFAULT_STATE=NSW
VITE_DEFAULT_TIMEZONE=Australia/Sydney
```

## API Integration

The frontend integrates with the FastAPI backend through:

- RESTful API endpoints for CRUD operations
- WebSocket connections for real-time updates
- File upload handling for document processing
- Authentication token management

## Contributing

1. Follow the existing code style and conventions
2. Write tests for new features
3. Ensure accessibility compliance
4. Test across different screen sizes
5. Update documentation as needed

## Browser Support

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

Copyright (c) 2024 Real2.AI. All rights reserved.