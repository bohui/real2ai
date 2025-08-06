# Client Decoupling Migration Guide

## Overview

This guide demonstrates how to migrate from direct client instantiation to the new decoupled client architecture.

## Migration Pattern

### Before: Direct Client Instantiation (Tightly Coupled)

```python
# OLD: Direct imports and instantiation
from supabase import create_client, Client
from google.generativeai import GenerativeModel
import openai

class MyService:
    def __init__(self):
        settings = get_settings()
        # Direct client creation - tightly coupled
        self.supabase = create_client(
            settings.supabase_url, 
            settings.supabase_anon_key
        )
        self.gemini = GenerativeModel("gemini-2.5-flash")
        self.openai = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def some_operation(self):
        # Direct usage - hard to test, no error handling
        result = self.supabase.table("users").select("*").execute()
        return result.data
```

### After: Decoupled Client Architecture (SOLID Principles)

```python
# NEW: Dependency injection with interfaces
from app.clients.factory import get_supabase_client, get_gemini_client
from app.clients.base.interfaces import DatabaseOperations, AIOperations

class MyService:
    def __init__(self, db_client: DatabaseOperations = None, ai_client: AIOperations = None):
        # Dependency injection - easily testable
        self._db_client = db_client
        self._ai_client = ai_client
    
    async def initialize(self):
        # Lazy initialization with error handling
        if not self._db_client:
            self._db_client = await get_supabase_client()
        if not self._ai_client:
            self._ai_client = await get_gemini_client()
    
    async def some_operation(self):
        # Interface-based usage - consistent error handling, retries
        result = await self._db_client.database.read("users", {})
        return result
```

## Key Benefits of Migration

### 1. **Testability** 
```python
# Easy mocking and testing
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
async def mock_db_client():
    mock = AsyncMock()
    mock.database.read.return_value = [{"id": "1", "name": "test"}]
    return mock

async def test_my_service(mock_db_client):
    service = MyService(db_client=mock_db_client)
    result = await service.some_operation()
    assert len(result) == 1
    mock_db_client.database.read.assert_called_once()
```

### 2. **Error Resilience**
```python
# Automatic retries and circuit breakers built-in
try:
    result = await client.database.read("users", {})
except ClientError as e:
    logger.error(f"Database operation failed: {e}")
    # Fallback logic or graceful degradation
```

### 3. **Configuration Management**
```python
# Centralized configuration with validation
from app.clients.supabase.config import SupabaseSettings

settings = SupabaseSettings()  # Auto-loads from environment
client = await get_supabase_client()  # Auto-configured
```

## Step-by-Step Migration Process

### Step 1: Identify Dependencies
```bash
# Find all direct client usage
grep -r "import.*supabase\|from.*supabase" app/
grep -r "import.*genai\|from.*genai" app/  
grep -r "import.*openai\|from.*openai" app/
```

### Step 2: Update Imports
```python
# Replace direct imports
- from supabase import create_client, Client
+ from app.clients.factory import get_supabase_client
+ from app.clients.base.interfaces import DatabaseOperations
```

### Step 3: Modify Constructor
```python
# Add dependency injection
class ServiceClass:
    def __init__(self, supabase_client: DatabaseOperations = None):
        self._supabase = supabase_client
    
    async def initialize(self):
        if not self._supabase:
            self._supabase = await get_supabase_client()
```

### Step 4: Update Method Calls
```python
# Use interface methods instead of direct client calls
- result = self.supabase.table("users").select("*").execute()
+ result = await self._supabase.database.read("users", {})
```

### Step 5: Add Error Handling
```python
# Leverage built-in error handling
from app.clients.base.exceptions import ClientError

try:
    result = await self._supabase.database.read("users", {})
except ClientError as e:
    logger.error(f"Database error: {e}")
    # Handle error appropriately
```

### Step 6: Update Tests
```python
# Create mock clients for testing
@pytest.fixture
async def service_with_mocks():
    mock_supabase = AsyncMock()
    service = ServiceClass(supabase_client=mock_supabase)
    return service, mock_supabase
```

## Migration Checklist

### Pre-Migration
- [ ] Identify all services using direct client instantiation
- [ ] Review current error handling patterns
- [ ] Document existing API usage patterns
- [ ] Backup current implementation

### During Migration
- [ ] Update imports to use client factory
- [ ] Modify constructors for dependency injection  
- [ ] Replace direct API calls with interface methods
- [ ] Add proper error handling
- [ ] Update initialization patterns

### Post-Migration
- [ ] Update unit tests with mocks
- [ ] Run integration tests
- [ ] Verify error handling works correctly
- [ ] Monitor performance metrics
- [ ] Update documentation

## Common Patterns

### Database Operations
```python
# Before
result = self.supabase.table("users").select("*").eq("id", user_id).execute()

# After  
result = await self._db_client.database.read("users", {"id": user_id})
```

### Authentication
```python
# Before
user = self.supabase.auth.get_user(token)

# After
user = await self._auth_client.authenticate_user(token)
```

### AI Operations
```python
# Before
response = self.gemini.generate_content(prompt)

# After
response = await self._ai_client.generate_content(prompt)
```

## Rollback Strategy

If issues arise during migration:

1. **Immediate Rollback**: Use feature flags to switch back to old implementation
2. **Gradual Rollback**: Migrate services back one at a time
3. **Partial Rollback**: Keep new architecture but revert specific service

## Performance Considerations

- **Connection Pooling**: New architecture includes connection pooling
- **Caching**: Built-in intelligent caching reduces API calls
- **Circuit Breakers**: Prevent cascading failures
- **Retry Logic**: Automatic retry with exponential backoff

## Next Steps

1. Start with low-risk services for initial migration
2. Monitor error rates and performance metrics
3. Gradually migrate high-traffic services
4. Remove old client code once migration is complete
5. Update documentation and team training

## Support

For migration assistance:
- Review `/backend/app/clients/` for implementation examples
- Check `/backend/CLIENT_ARCHITECTURE_DESIGN.md` for detailed architecture
- Consult test files in `/backend/tests/clients/` for testing patterns