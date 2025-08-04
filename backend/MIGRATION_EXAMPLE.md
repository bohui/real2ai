# Client Architecture Migration Example

This document demonstrates how to migrate existing services to use the new client architecture.

## Example: Migrating GeminiOCRService

### Before (Original Implementation)

```python
# app/services/gemini_ocr_service.py (original)

import google.generativeai as genai
from app.core.config import get_settings

class GeminiOCRService:
    def __init__(self):
        self.settings = get_settings()
        
        # Direct API initialization - tightly coupled
        if self.settings.gemini_api_key:
            genai.configure(api_key=self.settings.gemini_api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-pro",
                safety_settings={...}
            )
        else:
            self.model = None
    
    async def extract_text_from_document(self, file_content: bytes, file_type: str, filename: str):
        if not self.model:
            raise HTTPException(status_code=503, detail="Service not available")
        
        # Direct model usage - no error handling patterns
        response = self.model.generate_content([prompt, image_part])
        return response.text
```

### After (Using New Client Architecture)

```python
# app/services/gemini_ocr_service_v2.py (migrated)

from app.clients.factory import get_gemini_client
from app.clients.base.exceptions import ClientError, ClientConnectionError

class GeminiOCRService:
    def __init__(self):
        self._gemini_client = None
    
    async def _get_client(self):
        """Get initialized Gemini client."""
        if not self._gemini_client:
            self._gemini_client = await get_gemini_client()
        return self._gemini_client
    
    async def extract_text_from_document(self, file_content: bytes, file_type: str, filename: str):
        try:
            client = await self._get_client()
            
            # Use the standardized interface
            result = await client.ocr.extract_text(
                content=file_content,
                content_type=file_type,
                filename=filename
            )
            
            return result
            
        except ClientConnectionError as e:
            raise HTTPException(status_code=503, detail="OCR service temporarily unavailable")
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))
```

## Migration Benefits Demonstrated

### 1. Dependency Injection & Testing

**Before:**
```python
# Hard to test - direct API calls
def test_ocr_service():
    service = GeminiOCRService()  # Real API calls!
    # Difficult to mock genai.configure()
```

**After:**
```python
# Easy to test with mock clients
@pytest.fixture
def mock_gemini_client():
    from app.clients.base.client import BaseClient
    
    class MockGeminiClient(BaseClient):
        async def extract_text(self, content, content_type, **kwargs):
            return {"extracted_text": "Mock text", "confidence": 0.95}
    
    return MockGeminiClient(config=None)

def test_ocr_service(mock_gemini_client):
    # Clean, isolated testing
    service = GeminiOCRService()
    service._gemini_client = mock_gemini_client
    result = await service.extract_text_from_document(b"test", "pdf", "test.pdf")
    assert result["extracted_text"] == "Mock text"
```

### 2. Consistent Error Handling

**Before:**
```python
# Inconsistent error types across services
try:
    response = self.model.generate_content(...)
except Exception as e:  # Too broad
    # Different error handling per service
    logger.error(f"Gemini error: {e}")
    raise HTTPException(status_code=500, detail="Something broke")
```

**After:**
```python
# Consistent, typed error handling
try:
    result = await client.ocr.extract_text(...)
except ClientConnectionError:
    # Standard 503 for connection issues
    raise HTTPException(status_code=503, detail="Service temporarily unavailable")
except ClientAuthenticationError:
    # Standard 401 for auth issues  
    raise HTTPException(status_code=401, detail="Authentication failed")
except ClientQuotaExceededError:
    # Standard 429 for quota issues
    raise HTTPException(status_code=429, detail="Service quota exceeded")
```

### 3. Built-in Resilience

**Before:**
```python
# No retry logic, circuit breakers, or health checks
response = self.model.generate_content(prompt)  # Single point of failure
```

**After:**
```python
# Automatic retries, circuit breakers, health monitoring
result = await client.ocr.extract_text(...)  # Built-in resilience
# Retries happen automatically
# Circuit breaker prevents cascading failures
# Health checks detect issues early
```

### 4. Configuration Management

**Before:**
```python
# Configuration scattered across services
class GeminiOCRService:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.gemini_api_key
        self.model_name = "gemini-2.5-pro"  # Hardcoded
        self.timeout = 120  # Hardcoded
```

**After:**
```python
# Centralized, environment-aware configuration
# Settings come from environment variables:
# GEMINI_API_KEY=your_key
# GEMINI_MODEL_NAME=gemini-2.5-pro
# GEMINI_PROCESSING_TIMEOUT=120
# GEMINI_MAX_RETRIES=3
# GEMINI_CIRCUIT_BREAKER_ENABLED=true

client = await get_gemini_client()  # All config handled automatically
```

## Step-by-Step Migration Process

### Phase 1: Create New Service Version

1. **Create new service file** (e.g., `gemini_ocr_service_v2.py`)
2. **Import new client factory**
3. **Replace direct API calls with client interface calls**
4. **Update error handling to use typed exceptions**
5. **Add comprehensive tests with mock clients**

### Phase 2: Feature Flag Migration

```python
# app/core/config.py
class Settings(BaseSettings):
    use_new_client_architecture: bool = False  # Feature flag

# app/services/gemini_ocr_service.py
class GeminiOCRService:
    def __init__(self):
        self.settings = get_settings()
        if self.settings.use_new_client_architecture:
            self._use_new_architecture = True
        else:
            self._use_new_architecture = False
    
    async def extract_text_from_document(self, ...):
        if self._use_new_architecture:
            return await self._extract_with_new_client(...)
        else:
            return await self._extract_with_old_client(...)
```

### Phase 3: Gradual Rollout

1. **Deploy with feature flag disabled**
2. **Enable feature flag for test environments**
3. **Monitor metrics and error rates**
4. **Gradually enable for production traffic (10%, 25%, 50%, 100%)**
5. **Remove old implementation after successful migration**

### Phase 4: Cleanup

1. **Remove old implementation code**
2. **Remove feature flags**
3. **Update documentation**
4. **Clean up unused dependencies**

## Migration Checklist

### Pre-Migration
- [ ] Review current service implementation
- [ ] Identify all external API calls
- [ ] Document current error handling patterns
- [ ] Create comprehensive test suite for existing functionality

### During Migration
- [ ] Create client configuration for the service
- [ ] Implement new service using client architecture
- [ ] Add comprehensive error handling
- [ ] Create mock clients for testing
- [ ] Write tests for new implementation
- [ ] Set up feature flag for gradual rollout

### Post-Migration
- [ ] Monitor error rates and performance
- [ ] Compare metrics before and after migration
- [ ] Gather developer feedback on new architecture
- [ ] Document lessons learned
- [ ] Plan next service migration

## Expected Outcomes

### Developer Experience
- **Faster development**: Consistent patterns across services
- **Easier testing**: Mock clients and dependency injection
- **Better debugging**: Structured error handling and logging
- **Reduced cognitive load**: Standard interfaces and patterns

### System Reliability
- **Improved uptime**: Circuit breakers and retry mechanisms
- **Better observability**: Consistent health checks and metrics
- **Faster recovery**: Automatic failover and degradation
- **Reduced cascading failures**: Isolated client errors

### Maintenance Benefits
- **Centralized client management**: Single place to update API configurations
- **Consistent upgrades**: Update client library affects all services
- **Security improvements**: Centralized credential management
- **Performance optimizations**: Connection pooling and caching

This migration approach ensures zero downtime and provides a clear path for gradually adopting the new architecture across all services.