# Real2.AI API Reference

*Version: 2.0 - Current Implementation*  
*Last Updated: August 2025*

## Overview

This document provides comprehensive API reference for the Real2.AI platform, based on the current implementation with LangGraph workflows, advanced prompt management, and Australian legal compliance features.

## Base URL

```
Production: https://api.real2.ai/api
Staging: https://staging-api.real2.ai/api
Development: http://localhost:8000/api
```

## Authentication

All API endpoints require JWT authentication via Supabase Auth.

```bash
Authorization: Bearer <jwt_token>
```

## Core API Endpoints

### Authentication Endpoints

#### POST `/auth/login`
User login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "australian_state": "NSW",
    "subscription_status": "premium"
  }
}
```

#### POST `/auth/register`
Register new user account.

**Request:**
```json
{
  "email": "user@example.com", 
  "password": "password123",
  "australian_state": "NSW",
  "user_type": "buyer"
}
```

### Document Management

#### POST `/documents/upload`
Upload contract document for analysis.

**Request:** Multipart form data
- `file`: Document file (PDF, DOC, DOCX, max 50MB)
- `australian_state`: State code (NSW, VIC, QLD, etc.)
- `contract_type`: Contract type (purchase_agreement, lease_agreement)
- `metadata`: Optional JSON metadata

**Response:**
```json
{
  "document_id": "uuid",
  "filename": "contract.pdf",
  "file_size": 2048576,
  "upload_status": "processed",
  "processing_time": 12.5
}
```

#### GET `/documents/{document_id}`
Get document details and status.

**Response:**
```json
{
  "id": "uuid",
  "filename": "contract.pdf",
  "status": "processed",
  "metadata": {
    "page_count": 25,
    "ocr_confidence": 0.95,
    "contract_type": "nsw_standard"
  },
  "uploaded_at": "2024-08-06T10:30:00Z"
}
```

#### GET `/documents`
List user's uploaded documents with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `status`: Filter by status (uploaded, processing, processed, failed)

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "filename": "contract.pdf",
      "status": "processed",
      "uploaded_at": "2024-08-06T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

### Contract Analysis

#### POST `/contracts/analyze`
Start comprehensive contract analysis using LangGraph workflow.

**Request:**
```json
{
  "document_id": "uuid",
  "analysis_options": {
    "include_risk_assessment": true,
    "include_stamp_duty": true,
    "include_compliance_check": true,
    "analysis_depth": "comprehensive",
    "use_enhanced_prompts": true,
    "enable_langsmith_tracing": true
  }
}
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "contract_id": "uuid",
  "status": "processing",
  "estimated_completion_minutes": 3,
  "langraph_workflow_id": "workflow_uuid",
  "created_at": "2025-01-07T10:30:00Z",
  "workflow_steps": [
    "document_validation",
    "ocr_extraction", 
    "contract_structure_analysis",
    "compliance_check",
    "risk_assessment",
    "recommendations_generation"
  ]
}
```

#### GET `/contracts/{contract_id}/analysis`
Get contract analysis results.

**Response:**
```json
{
  "contract_id": "uuid",
  "analysis_id": "uuid",
  "status": "completed",
  "processed_at": "2024-08-06T10:42:30Z",
  "processing_time": 45.2,
  "contract_terms": {
    "purchase_price": 850000.00,
    "deposit_amount": 85000.00,
    "settlement_date": "2024-10-15",
    "cooling_off_period": "5 business days",
    "property_address": "123 Main Street, Sydney NSW 2000",
    "vendor_details": {
      "name": "John Smith",
      "solicitor": "Smith & Partners"
    },
    "purchaser_details": {
      "name": "Jane Doe", 
      "solicitor": "Doe Legal"
    },
    "special_conditions": [
      "Finance approval within 21 days",
      "Building and pest inspection",
      "Strata inspection"
    ]
  },
  "risk_assessment": {
    "overall_risk_score": 6.5,
    "risk_factors": [
      {
        "factor": "Short settlement period",
        "severity": "medium",
        "description": "45 day settlement may not provide sufficient time",
        "recommendations": ["Consider extending settlement period"]
      }
    ],
    "confidence_scores": {
      "term_extraction": 0.94,
      "risk_analysis": 0.88,
      "compliance_check": 0.92
    }
  },
  "compliance_check": {
    "state_compliance": true,
    "australian_state": "NSW",
    "compliance_details": {
      "cooling_off_period": {
        "compliant": true,
        "required": "5 business days",
        "contract_provides": "5 business days"
      },
      "disclosure_requirements": {
        "compliant": true,
        "section_149_certificate": "required",
        "home_building_act": "compliant"
      }
    },
    "warnings": []
  },
  "stamp_duty_calculation": {
    "base_duty": 32750.00,
    "exemptions": 0.00,
    "surcharges": 0.00,
    "total_duty": 32750.00,
    "calculation_details": {
      "state": "NSW",
      "property_value": 850000.00,
      "first_home_buyer": false,
      "foreign_buyer": false
    }
  },
  "recommendations": [
    {
      "priority": "high",
      "category": "legal_review",
      "recommendation": "Review special conditions with solicitor",
      "action_required": true,
      "details": "Finance clause requires careful review of terms"
    }
  ],
  "report_urls": {
    "pdf": "/api/contracts/uuid/report?format=pdf",
    "json": "/api/contracts/uuid/report?format=json"
  }
}
```

#### GET `/contracts/{contract_id}/report`
Download comprehensive analysis report.

**Query Parameters:**
- `format`: pdf or json (default: pdf)
- `sections`: Comma-separated sections to include

**Response:** PDF file or JSON data

### Property Profile Integration

#### POST `/property/analyze`
Analyze property using external data sources.

**Request:**
```json
{
  "property_address": "123 Main Street, Sydney NSW 2000",
  "analysis_type": "comprehensive",
  "include_market_data": true,
  "include_valuation": true
}
```

**Response:**
```json
{
  "property_id": "uuid",
  "address": "123 Main Street, Sydney NSW 2000",
  "property_details": {
    "bedrooms": 3,
    "bathrooms": 2,
    "car_spaces": 2,
    "land_size": 450,
    "property_type": "house"
  },
  "market_analysis": {
    "estimated_value": 850000,
    "recent_sales": [
      {
        "address": "125 Main Street",
        "sale_price": 820000,
        "sale_date": "2024-06-15"
      }
    ],
    "market_trends": {
      "growth_12_months": 0.08,
      "median_price": 825000
    }
  },
  "risk_indicators": [
    "Property in flood-prone area",
    "Major development planned nearby"
  ]
}
```

### OCR Services

#### POST `/ocr/extract`
Extract text from document using enhanced Gemini OCR.

**Request:** Multipart form data
- `file`: Image or PDF file
- `australian_state`: State for context-specific processing
- `quality_level`: high, medium, or standard
- `use_enhanced_prompts`: boolean (default: true)

**Response:**
```json
{
  "extracted_text": "Full document text...",
  "confidence": 0.94,
  "processing_time": 8.2,
  "metadata": {
    "page_count": 1,
    "enhancement_used": true,
    "template_used": "ocr_extraction"
  },
  "quality_metrics": {
    "clarity_score": 0.91,
    "completeness_score": 0.96,
    "accuracy_confidence": 0.94
  }
}
```

#### GET `/ocr/{extraction_id}/status`
Check OCR processing status.

**Response:**
```json
{
  "extraction_id": "uuid",
  "status": "completed",
  "progress": 100,
  "estimated_completion": null,
  "result_url": "/api/ocr/uuid/result"
}
```

### User Management

#### GET `/users/profile`
Get user profile information.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "australian_state": "NSW",
  "user_type": "buyer",
  "subscription_status": "premium",
  "credits_remaining": 25,
  "preferences": {
    "notification_email": true,
    "analysis_depth": "comprehensive"
  },
  "created_at": "2024-01-15T09:30:00Z"
}
```

#### PUT `/users/profile`
Update user profile.

**Request:**
```json
{
  "australian_state": "VIC",
  "preferences": {
    "notification_email": false,
    "analysis_depth": "standard"
  }
}
```

#### GET `/users/usage-stats`
Get usage statistics and billing information.

**Response:**
```json
{
  "current_period": {
    "documents_analyzed": 12,
    "credits_used": 48,
    "credits_remaining": 27
  },
  "historical": {
    "total_documents": 156,
    "total_credits_used": 624,
    "member_since": "2024-01-15"
  },
  "subscription": {
    "plan": "premium",
    "status": "active",
    "next_billing": "2024-09-06",
    "monthly_credits": 75
  }
}
```

### Health and Monitoring

#### GET `/health`
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-08-06T15:30:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy", 
    "openai": "healthy",
    "gemini": "healthy",
    "supabase": "healthy"
  },
  "metrics": {
    "uptime": 99.98,
    "average_response_time": 145,
    "active_analyses": 23
  }
}
```

#### GET `/health/detailed`
Detailed service diagnostics (admin only).

**Response:**
```json
{
  "system_status": "operational",
  "components": {
    "prompt_manager": {
      "status": "healthy",
      "cache_hit_rate": 0.87,
      "templates_loaded": 156,
      "average_render_time": 42
    },
    "langgraph_engine": {
      "status": "healthy", 
      "active_workflows": 8,
      "completed_today": 147,
      "average_completion_time": 38.5
    },
    "ocr_service": {
      "status": "healthy",
      "queue_size": 3,
      "processing_rate": 0.95,
      "average_confidence": 0.91
    }
  }
}
```

## WebSocket Events

### Connection
```
wss://api.real2.ai/ws/contracts/{contract_id}/progress
```

### Event Types

#### Analysis Progress
```json
{
  "event_type": "analysis_progress",
  "data": {
    "contract_id": "uuid",
    "current_step": "risk_assessment",
    "progress_percentage": 65,
    "step_details": {
      "name": "Risk Assessment",
      "description": "Analyzing contract risks and compliance",
      "estimated_remaining": 15
    }
  },
  "timestamp": "2024-08-06T10:35:00Z"
}
```

#### Analysis Complete
```json
{
  "event_type": "analysis_completed",
  "data": {
    "contract_id": "uuid",
    "analysis_id": "uuid",
    "summary": {
      "risk_score": 6.5,
      "recommendations_count": 8,
      "compliance_status": "compliant"
    },
    "report_url": "/api/contracts/uuid/report"
  },
  "timestamp": "2024-08-06T10:42:30Z"
}
```

#### Error Events
```json
{
  "event_type": "analysis_error",
  "data": {
    "contract_id": "uuid",
    "error": {
      "code": "EXTRACTION_FAILED",
      "message": "Document quality too low for reliable extraction",
      "recoverable": true,
      "retry_suggestions": ["Upload higher quality scan"]
    }
  },
  "timestamp": "2024-08-06T10:32:15Z"
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Document validation failed",
    "details": {
      "field": "file",
      "issue": "File size exceeds 50MB limit"
    },
    "request_id": "uuid",
    "timestamp": "2024-08-06T10:30:00Z"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Invalid or missing authentication |
| `INSUFFICIENT_CREDITS` | 402 | User has insufficient credits |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `DOCUMENT_TOO_LARGE` | 413 | File exceeds size limit |
| `ANALYSIS_FAILED` | 500 | Contract analysis could not complete |
| `SERVICE_UNAVAILABLE` | 503 | External service unavailable |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

## Rate Limits

| Endpoint Category | Limit | Window |
|-------------------|-------|---------|
| Authentication | 5 requests | 1 minute |
| Document Upload | 10 uploads | 1 hour |
| Analysis | 20 analyses | 1 hour |
| OCR | 50 requests | 1 hour |
| General API | 1000 requests | 1 hour |

### Property Intelligence

#### POST `/property/analyze`
Analyze property with market intelligence.

**Request:**
```json
{
  "address": "123 Collins Street, Melbourne VIC 3000",
  "analysis_depth": "comprehensive",
  "include_market_trends": true,
  "include_comparable_sales": true,
  "include_investment_metrics": true
}
```

**Response:**
```json
{
  "property_id": "uuid",
  "address": "123 Collins Street, Melbourne VIC 3000",
  "market_data": {
    "estimated_value": 850000,
    "confidence_level": 0.89,
    "price_trend_12m": 0.12,
    "days_on_market_avg": 28
  },
  "investment_metrics": {
    "rental_yield": 0.042,
    "capital_growth_5y": 0.067,
    "roi_projection": 0.089
  }
}
```

### OCR Processing

#### POST `/ocr/extract`
Extract text from documents using Gemini 2.5 Pro.

**Request:** Multipart form data
- `file`: Document file
- `extraction_options`: JSON options

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "estimated_completion_seconds": 30,
  "ocr_engine": "gemini_2_5_pro",
  "created_at": "2025-01-07T10:30:00Z"
}
```

### Evaluation System

#### POST `/evaluation/analyze`
Analyze AI model performance with LangSmith integration.

**Request:**
```json
{
  "evaluation_type": "contract_analysis",
  "test_dataset_id": "uuid",
  "model_config": {
    "model": "gpt-4",
    "temperature": 0.1,
    "prompt_version": "v2.1"
  },
  "metrics": ["accuracy", "recall", "f1_score"]
}
```

**Response:**
```json
{
  "evaluation_id": "uuid",
  "status": "processing",
  "langsmith_run_id": "langsmith_uuid",
  "estimated_completion_minutes": 15
}
```

### WebSocket Events

Connect to: `wss://api.real2.ai/ws/documents/{document_id}`

#### Event Types:

**`cache_status`** - Initial cache status check
```json
{
  "event_type": "cache_status",
  "data": {
    "cache_status": "miss",
    "document_id": "uuid",
    "content_hash": "hash"
  }
}
```

**`analysis_progress`** - Real-time progress updates
```json
{
  "event_type": "analysis_progress",
  "data": {
    "progress_percent": 65,
    "current_step": "risk_assessment",
    "step_description": "Analyzing contract terms for potential risks",
    "estimated_completion_minutes": 1
  }
}
```

**`analysis_complete`** - Analysis completion
```json
{
  "event_type": "analysis_complete",
  "data": {
    "contract_id": "uuid",
    "analysis_id": "uuid",
    "processing_time": 45.2,
    "status": "completed"
  }
}
```

## SDK and Integration Examples

### Python SDK Example
```python
from real2ai import Real2AIClient

client = Real2AIClient(api_key="your_jwt_token")

# Upload and analyze contract
document = client.documents.upload(
    file_path="contract.pdf",
    australian_state="NSW",
    contract_type="purchase_agreement"
)

analysis = client.contracts.analyze(
    document_id=document.id,
    include_risk_assessment=True,
    include_stamp_duty=True
)

# Wait for completion
result = client.contracts.wait_for_completion(analysis.id)
print(f"Risk Score: {result.risk_assessment.overall_risk_score}")
```

### JavaScript/TypeScript Example
```typescript
import { Real2AIClient } from '@real2ai/sdk';

const client = new Real2AIClient({
  apiKey: process.env.REAL2AI_API_KEY,
  baseUrl: 'https://api.real2.ai'
});

// Upload and analyze
const document = await client.documents.upload({
  file: contractFile,
  australianState: 'NSW',
  contractType: 'purchase_agreement'
});

const analysis = await client.contracts.analyze({
  documentId: document.id,
  options: {
    includeRiskAssessment: true,
    includeStampDuty: true
  }
});

// Subscribe to progress updates
client.websocket.subscribe(`contracts/${analysis.contractId}/progress`, 
  (event) => {
    console.log(`Progress: ${event.data.progress_percentage}%`);
  }
);
```

## Changelog

### Version 2.0.0 (Current)
- Advanced LangGraph workflow implementation
- Enhanced prompt management system with PromptManager
- Gemini 2.5 Pro OCR integration
- Comprehensive Australian legal compliance
- Real-time WebSocket progress tracking
- Property profile integration with external APIs

### Version 1.0.0 (Legacy)
- Basic contract analysis
- Simple OCR processing
- NSW-only compliance checking
- PDF report generation

---

*This API reference reflects the current Real2.AI implementation with all advanced features including LangGraph workflows, enhanced prompt management, and comprehensive Australian legal compliance.*