# Client Architecture Design Document

## Overview

This document outlines the decoupling strategy for all external service clients in the Real2.AI backend application. The goal is to create a clean, maintainable, and testable architecture that separates concerns and follows SOLID principles.

## Current State Analysis

### Identified External Clients
1. **Supabase** - Database and authentication
2. **Google Gemini** - OCR and AI analysis 
3. **OpenAI/LangChain** - Contract workflow processing
4. **Redis** - Caching (configured but not directly used)
5. **Stripe** - Payment processing (configured)
6. **External APIs** - Domain/CoreLogic APIs (configured)

### Current Issues
- Direct client instantiation in service classes
- Tight coupling between services and external APIs
- Difficult to test and mock
- Configuration scattered across files
- No consistent error handling patterns
- No retry/circuit breaker patterns

## Proposed Architecture

### 1. Client Layer Structure
```
app/
├── clients/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── client.py          # Abstract base client
│   │   ├── config.py          # Client configurations
│   │   └── exceptions.py      # Custom exceptions
│   ├── supabase/
│   │   ├── __init__.py
│   │   ├── client.py          # Supabase client wrapper
│   │   ├── auth_client.py     # Authentication operations
│   │   └── database_client.py # Database operations
│   ├── gemini/
│   │   ├── __init__.py
│   │   ├── client.py          # Gemini client wrapper
│   │   └── ocr_client.py      # OCR-specific operations
│   ├── openai/
│   │   ├── __init__.py
│   │   ├── client.py          # OpenAI client wrapper
│   │   └── langchain_client.py # LangChain operations
│   ├── redis/
│   │   ├── __init__.py
│   │   └── client.py          # Redis client wrapper
│   └── factory.py             # Client factory for DI
```

### 2. Core Principles

#### SOLID Compliance
- **Single Responsibility**: Each client handles one external service
- **Open/Closed**: Extensible for new clients without modifying existing code
- **Liskov Substitution**: All clients implement common interface
- **Interface Segregation**: Separate interfaces for different operations
- **Dependency Inversion**: Services depend on abstractions, not concrete clients

#### Design Patterns
- **Factory Pattern**: Centralized client creation
- **Adapter Pattern**: Consistent interface across different APIs
- **Decorator Pattern**: Cross-cutting concerns (logging, metrics, retries)
- **Strategy Pattern**: Different implementation strategies for clients

### 3. Interface Definitions

#### Base Client Interface
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class ClientConfig:
    """Base configuration for all clients"""
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0
    enable_metrics: bool = True
    enable_logging: bool = True

class BaseClient(ABC):
    """Abstract base class for all external service clients"""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client connection"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check client health and connectivity"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up client resources"""
        pass
```

#### Service-Specific Interfaces
```python
# Database operations interface
class DatabaseOperations(ABC):
    @abstractmethod
    async def create(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def read(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def update(self, table: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def delete(self, table: str, id: str) -> bool:
        pass

# AI operations interface
class AIOperations(ABC):
    @abstractmethod
    async def generate_content(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def analyze_document(self, content: bytes, content_type: str) -> Dict[str, Any]:
        pass
```

### 4. Implementation Strategy

#### Phase 1: Base Infrastructure
1. Create base client classes and interfaces
2. Implement client factory with dependency injection
3. Set up configuration management
4. Create custom exceptions and error handling

#### Phase 2: Client Implementations
1. Supabase client wrapper with auth and database operations
2. Gemini client wrapper with OCR and analysis capabilities
3. OpenAI/LangChain client wrapper with workflow operations
4. Redis client wrapper for caching

#### Phase 3: Service Integration
1. Update existing services to use new client architecture
2. Implement proper dependency injection
3. Add comprehensive testing with mocks
4. Update configuration management

#### Phase 4: Advanced Features
1. Add circuit breaker patterns
2. Implement client-side metrics and monitoring
3. Add request/response middleware
4. Implement client pooling and connection management

### 5. Dependency Injection Container

```python
from typing import Dict, Type, Any, Optional
from functools import lru_cache

class ClientContainer:
    """Dependency injection container for clients"""
    
    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._initialized = False
    
    def register_factory(self, name: str, factory: callable) -> None:
        """Register a client factory"""
        self._factories[name] = factory
    
    def get_client(self, name: str) -> Any:
        """Get a client instance"""
        if name not in self._clients:
            if name not in self._factories:
                raise ValueError(f"No factory registered for client: {name}")
            self._clients[name] = self._factories[name]()
        return self._clients[name]
    
    async def initialize_all(self) -> None:
        """Initialize all registered clients"""
        for client in self._clients.values():
            if hasattr(client, 'initialize'):
                await client.initialize()
        self._initialized = True
    
    async def close_all(self) -> None:
        """Close all client connections"""
        for client in self._clients.values():
            if hasattr(client, 'close'):
                await client.close()
        self._clients.clear()
        self._initialized = False

# Global container instance
container = ClientContainer()

@lru_cache()
def get_container() -> ClientContainer:
    """Get the global client container"""
    return container
```

### 6. Configuration Management

#### Client-Specific Configurations
```python
from pydantic import BaseSettings
from typing import Optional

class SupabaseClientConfig(BaseSettings):
    url: str
    anon_key: str
    service_key: str
    timeout: int = 30
    max_retries: int = 3
    pool_size: int = 10
    
    class Config:
        env_prefix = "SUPABASE_"

class GeminiClientConfig(BaseSettings):
    api_key: str
    model_name: str = "gemini-2.5-pro"
    timeout: int = 120
    max_retries: int = 3
    rate_limit_rpm: int = 60
    
    class Config:
        env_prefix = "GEMINI_"

class OpenAIClientConfig(BaseSettings):
    api_key: str
    api_base: Optional[str] = None
    model_name: str = "gpt-4"
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.1
    
    class Config:
        env_prefix = "OPENAI_"
```

### 7. Error Handling Strategy

#### Custom Exceptions
```python
class ClientError(Exception):
    """Base exception for client errors"""
    pass

class ClientConnectionError(ClientError):
    """Connection-related errors"""
    pass

class ClientAuthenticationError(ClientError):
    """Authentication-related errors"""
    pass

class ClientRateLimitError(ClientError):
    """Rate limiting errors"""
    pass

class ClientTimeoutError(ClientError):
    """Timeout errors"""
    pass

class ClientValidationError(ClientError):
    """Request validation errors"""
    pass
```

#### Retry and Circuit Breaker Patterns
```python
import asyncio
from functools import wraps
from typing import Any, Callable, Optional

class CircuitBreaker:
    """Simple circuit breaker implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time < self.timeout:
                raise ClientConnectionError("Circuit breaker is OPEN")
            else:
                self.state = "HALF_OPEN"
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

def with_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for automatic retries with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (ClientConnectionError, ClientTimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(delay)
                    continue
                except Exception:
                    # Don't retry on non-retryable errors
                    raise
            raise last_exception
        return wrapper
    return decorator
```

### 8. Testing Strategy

#### Mock Client Implementations
```python
from unittest.mock import AsyncMock
from typing import Dict, Any, List

class MockSupabaseClient(BaseClient):
    """Mock Supabase client for testing"""
    
    def __init__(self, config: ClientConfig):
        super().__init__(config)
        self._data: Dict[str, List[Dict[str, Any]]] = {}
    
    async def initialize(self) -> None:
        self._initialized = True
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "mock": True}
    
    async def close(self) -> None:
        self._initialized = False
    
    # Database operations
    async def create(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if table not in self._data:
            self._data[table] = []
        data['id'] = len(self._data[table]) + 1
        self._data[table].append(data)
        return data
    
    async def read(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        if table not in self._data:
            return []
        # Simple filter implementation for testing
        results = []
        for item in self._data[table]:
            match = True
            for key, value in filters.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results

class MockGeminiClient(BaseClient):
    """Mock Gemini client for testing"""
    
    async def generate_content(self, prompt: str, **kwargs) -> str:
        return f"Mock response to: {prompt[:50]}..."
    
    async def analyze_document(self, content: bytes, content_type: str) -> Dict[str, Any]:
        return {
            "extracted_text": "Mock extracted text",
            "confidence": 0.95,
            "processing_time": 1.2
        }
```

### 9. Migration Plan

#### Step 1: Create Base Infrastructure (Week 1)
- [ ] Create `/app/clients/` directory structure
- [ ] Implement base client classes and interfaces
- [ ] Set up client factory and dependency injection container
- [ ] Create custom exceptions and error handling

#### Step 2: Implement Client Wrappers (Week 2-3)
- [ ] Supabase client wrapper with auth and database operations
- [ ] Gemini client wrapper with OCR capabilities  
- [ ] OpenAI/LangChain client wrapper
- [ ] Redis client wrapper
- [ ] Comprehensive unit tests for all clients

#### Step 3: Service Integration (Week 4)
- [ ] Update `GeminiOCRService` to use new Gemini client
- [ ] Update `ContractAnalysisService` to use new clients
- [ ] Update `ContractAnalysisWorkflow` to use new OpenAI client
- [ ] Update database services to use new Supabase client

#### Step 4: Configuration and Testing (Week 5)
- [ ] Update configuration management
- [ ] Add comprehensive integration tests
- [ ] Performance testing and optimization
- [ ] Documentation updates

#### Step 5: Advanced Features (Week 6)
- [ ] Circuit breaker implementation
- [ ] Client metrics and monitoring
- [ ] Connection pooling optimization
- [ ] Production deployment and monitoring

### 10. Backward Compatibility Strategy

To ensure zero downtime during migration:

1. **Gradual Migration**: Services will be updated one at a time
2. **Feature Flags**: Use configuration to switch between old and new implementations
3. **Parallel Testing**: Run both implementations in parallel during transition
4. **Rollback Plan**: Keep old implementations available for quick rollback
5. **Monitoring**: Enhanced monitoring during migration phase

### 11. Benefits of New Architecture

#### Maintainability
- Clear separation of concerns
- Consistent patterns across all clients
- Easy to add new external services
- Simplified testing and mocking

#### Reliability
- Built-in retry mechanisms
- Circuit breaker patterns
- Comprehensive error handling
- Health check capabilities

#### Performance
- Connection pooling
- Client-side caching
- Request batching where applicable
- Optimized resource usage

#### Testability
- Easy mocking and stubbing
- Isolated unit testing
- Integration test support
- Performance testing capabilities

### 12. Success Metrics

- **Code Quality**: Reduced cyclomatic complexity, improved test coverage (>90%)
- **Reliability**: Reduced error rates, improved uptime (>99.9%)
- **Performance**: Faster response times, reduced resource usage
- **Developer Experience**: Faster development cycles, easier debugging
- **Maintainability**: Lower defect rates, faster feature delivery

This architecture provides a solid foundation for scalable, maintainable, and testable external service integration while following industry best practices and SOLID principles.