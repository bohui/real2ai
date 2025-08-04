# Service Layer Refactoring Guide

## Overview

This guide documents the refactoring of backend services to properly use the client architecture with service role authentication support.

## Architecture Changes

### Before (Anti-pattern)
```
Services → Direct API Usage (genai.configure)
         ↓
    Gemini API
```

### After (Proper Architecture)
```
Services → Client Factory → GeminiClient (with service role auth)
         ↓                      ↓
    Business Logic      Abstracted API Communication
```

## Refactored Services

### 1. GeminiOCRService → GeminiOCRServiceV2

**Key Changes:**
- Removed direct `genai` API usage
- Now uses `GeminiClient` via factory
- Supports service role authentication
- Maintains all OCR-specific business logic

**Migration:**
```python
# Old
self.gemini_ocr = GeminiOCRService()

# New
self.gemini_ocr = GeminiOCRServiceV2()
await self.gemini_ocr.initialize()
```

### 2. DocumentService → DocumentServiceV2

**Key Changes:**
- Uses `GeminiClient` directly instead of `GeminiOCRService`
- Uses `SupabaseClient` for storage operations
- Cleaner separation between storage and AI operations

**Migration:**
```python
# Old
self.document_service = DocumentService()

# New
self.document_service = DocumentServiceV2()
await self.document_service.initialize()
```

### 3. ContractAnalysisService → ContractAnalysisServiceV2

**Key Changes:**
- Removed duplicate Gemini initialization
- Uses `GeminiClient` from factory
- Reports authentication method in health checks

**Migration:**
```python
# Old
self.contract_analysis = ContractAnalysisService()

# New
self.contract_analysis = ContractAnalysisServiceV2()
await self.contract_analysis.initialize()
```

## Benefits

1. **Service Role Authentication**: All services now support service role auth
2. **Single Source of Truth**: One Gemini configuration
3. **Better Error Handling**: Consistent error types across services
4. **Resource Efficiency**: Shared client instances
5. **Easier Testing**: Mock clients instead of APIs
6. **Health Monitoring**: Unified health check reporting

## Migration Steps

### 1. Update Service Imports

```python
# Old imports
from app.services.gemini_ocr_service import GeminiOCRService
from app.services.document_service import DocumentService
from app.services.contract_analysis_service import ContractAnalysisService

# New imports
from app.services.gemini_ocr_service_v2 import GeminiOCRServiceV2
from app.services.document_service_v2 import DocumentServiceV2
from app.services.contract_analysis_service_v2 import ContractAnalysisServiceV2
```

### 2. Update Service Initialization

```python
# In your application startup (e.g., FastAPI lifespan)
async def startup():
    # Initialize client factory first
    factory = get_client_factory()
    await factory.initialize_all()
    
    # Then initialize services
    document_service = DocumentServiceV2()
    await document_service.initialize()
    
    contract_service = ContractAnalysisServiceV2()
    await contract_service.initialize()
```

### 3. Update Environment Variables

Ensure service role authentication is configured:

```bash
# For service account authentication (recommended)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
export GEMINI_USE_SERVICE_ACCOUNT=true

# Or for API key authentication (fallback)
export GEMINI_API_KEY="your-api-key"
export GEMINI_USE_SERVICE_ACCOUNT=false
```

### 4. Update Health Checks

All services now report authentication method:

```python
health = await service.health_check()
print(f"Auth method: {health.get('authentication_method', 'unknown')}")
```

## Error Handling

### Consistent Error Types

All services now use client exceptions:

```python
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientAuthenticationError,
    ClientQuotaExceededError,
)

try:
    result = await service.some_operation()
except ClientQuotaExceededError:
    # Handle quota errors
    return HTTPException(status_code=429, detail="Quota exceeded")
except ClientAuthenticationError:
    # Handle auth errors
    return HTTPException(status_code=401, detail="Authentication failed")
```

## Testing

### Mock Client for Testing

```python
# In tests
from unittest.mock import AsyncMock

async def test_document_extraction():
    # Mock the client factory
    mock_gemini_client = AsyncMock()
    mock_gemini_client.extract_text.return_value = {
        "extracted_text": "Test content",
        "confidence": 0.95
    }
    
    with patch('app.clients.get_gemini_client', return_value=mock_gemini_client):
        service = DocumentServiceV2()
        await service.initialize()
        
        result = await service.extract_text(...)
        assert result["extracted_text"] == "Test content"
```

## Rollback Plan

If issues arise, you can temporarily use the old services:

1. Keep old service files in place during transition
2. Use feature flags to switch between versions
3. Monitor error rates and performance
4. Gradually migrate endpoints

## Performance Considerations

- Client instances are cached and reused
- Connection pooling is handled by the client layer
- Service role auth may have different rate limits than API keys
- Monitor quota usage in production

## Next Steps

1. Update all API routes to use V2 services
2. Add comprehensive logging for auth method tracking
3. Set up monitoring for service role auth failures
4. Plan deprecation of old service files
5. Update documentation and API specs