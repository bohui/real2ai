# User Token Propagation Architecture Design

## Executive Summary

**Problem**: Current system has mixed patterns where service role clients are used when user context should be maintained, especially in background tasks that process user-specific data.

**Solution**: Implement a comprehensive user token propagation system that maintains user context through background tasks while preserving security boundaries.

## 🏗️ Architecture Overview

### Current State Analysis

**Service Role Usage Patterns Found**:
- ✅ **Legitimate Service Role**: System maintenance, bucket creation, WebSocket broadcasting
- ❌ **Should Use User Context**: User document processing, user-specific background tasks
- ⚠️ **Mixed Patterns**: OCR tasks, some service initializations

**Key Challenge**: Background tasks (Celery) lose user authentication context but still need to operate on user data with proper RLS enforcement.

## 🎯 Design Principles

1. **Principle of Least Privilege**: Use user tokens whenever possible
2. **Context Preservation**: Maintain user context through async boundaries
3. **Security by Default**: Never expose user tokens to unauthorized contexts
4. **Clear Boundaries**: Explicit distinction between user and system operations

## 🔧 Proposed Architecture

### 1. Enhanced Auth Context with Task Support

```python
class AuthContext:
    """Enhanced auth context with background task support"""
    
    @classmethod
    def create_task_context(cls) -> Dict[str, Any]:
        """Create serializable context for background tasks"""
        return {
            "user_token": cls.get_user_token(),
            "user_id": cls.get_user_id(),
            "user_email": cls.get_user_email(),
            "auth_metadata": cls.get_auth_metadata(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    
    @classmethod
    def restore_task_context(cls, task_context: Dict[str, Any]) -> None:
        """Restore auth context in background task"""
        cls.set_auth_context(
            token=task_context.get("user_token"),
            user_id=task_context.get("user_id"),
            user_email=task_context.get("user_email"),
            metadata=task_context.get("auth_metadata", {}),
        )
```

### 2. User-Aware Supabase Client Dependency

```python
from typing import Annotated
from fastapi import Depends

async def get_user_supabase_client() -> SupabaseClient:
    """Get Supabase client with user authentication"""
    return await AuthContext.get_authenticated_client(require_auth=True)

async def get_system_supabase_client() -> SupabaseClient:
    """Get Supabase client with service role (explicit system operations)"""
    return await get_supabase_client(use_service_role=True)

# Type aliases for clarity
UserSupabaseClient = Annotated[SupabaseClient, Depends(get_user_supabase_client)]
SystemSupabaseClient = Annotated[SupabaseClient, Depends(get_system_supabase_client)]
```

### 3. Service Base Class with Client Injection

```python
class UserAwareService:
    """Base class for services that need user context"""
    
    def __init__(self, user_client: Optional[SupabaseClient] = None):
        self._user_client = user_client
    
    async def get_user_client(self) -> SupabaseClient:
        """Get user-authenticated Supabase client"""
        if self._user_client:
            return self._user_client
        return await AuthContext.get_authenticated_client()
    
    async def get_system_client(self) -> SupabaseClient:
        """Get system client for legitimate admin operations"""
        return await get_supabase_client(use_service_role=True)

class SystemService:
    """Base class for services that operate at system level"""
    
    async def get_system_client(self) -> SupabaseClient:
        return await get_supabase_client(use_service_role=True)
```

### 4. Background Task Token Propagation

#### Option A: Secure Token Store (Recommended)

```python
import redis
from cryptography.fernet import Fernet
from datetime import timedelta

class SecureTaskContextStore:
    """Secure storage for task authentication context"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.cipher = Fernet(settings.TASK_ENCRYPTION_KEY)
        self.default_ttl = timedelta(hours=1)  # Task token expiry
    
    async def store_context(self, task_id: str, auth_context: Dict[str, Any]) -> str:
        """Store encrypted auth context for task"""
        # Encrypt sensitive data
        encrypted_context = self.cipher.encrypt(
            json.dumps(auth_context).encode()
        )
        
        # Store with TTL
        context_key = f"task_auth:{task_id}"
        self.redis_client.setex(
            context_key, 
            self.default_ttl, 
            encrypted_context
        )
        
        return context_key
    
    async def retrieve_context(self, context_key: str) -> Dict[str, Any]:
        """Retrieve and decrypt auth context"""
        encrypted_context = self.redis_client.get(context_key)
        if not encrypted_context:
            raise ValueError("Task context expired or not found")
        
        # Decrypt and parse
        decrypted_data = self.cipher.decrypt(encrypted_context)
        return json.loads(decrypted_data.decode())
    
    async def cleanup_context(self, context_key: str) -> None:
        """Clean up stored context"""
        self.redis_client.delete(context_key)

# Global instance
task_store = SecureTaskContextStore()
```

#### Option B: Direct Token Passing (Alternative)

```python
class TaskAuthContext:
    """Task-specific auth context with automatic cleanup"""
    
    @staticmethod
    def create_task_token(user_token: str, expires_in: int = 3600) -> str:
        """Create short-lived task token"""
        payload = {
            "original_token": user_token,
            "task_issued": datetime.now(UTC).timestamp(),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).timestamp(),
            "purpose": "background_task",
        }
        return jwt.encode(payload, settings.TASK_SECRET_KEY, algorithm="HS256")
    
    @staticmethod
    def validate_task_token(task_token: str) -> str:
        """Validate and extract original user token"""
        try:
            payload = jwt.decode(task_token, settings.TASK_SECRET_KEY, algorithms=["HS256"])
            
            if payload["expires_at"] < datetime.now(UTC).timestamp():
                raise ValueError("Task token expired")
            
            return payload["original_token"]
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid task token: {e}")
```

### 5. Enhanced Background Task Pattern

```python
from celery import Celery
from contextlib import asynccontextmanager

@asynccontextmanager
async def task_auth_context(context_key: str):
    """Context manager for background task authentication"""
    try:
        # Restore auth context
        auth_context = await task_store.retrieve_context(context_key)
        AuthContext.restore_task_context(auth_context)
        
        yield AuthContext
        
    finally:
        # Clean up context
        AuthContext.clear_auth_context()
        await task_store.cleanup_context(context_key)

# Enhanced task decorator
def user_aware_task(func):
    """Decorator for tasks that need user context"""
    @wraps(func)
    async def wrapper(context_key: str, *args, **kwargs):
        async with task_auth_context(context_key):
            return await func(*args, **kwargs)
    return wrapper

# Usage in tasks
@celery_app.task
@user_aware_task
async def process_user_document_background(document_id: str, user_id: str):
    """Process document with preserved user context"""
    # AuthContext is automatically restored
    document_service = DocumentService()  # Will use user context
    await document_service.initialize()
    
    result = await document_service.process_document(document_id)
    return result
```

## 🔄 Migration Strategy

### Phase 1: Foundation (Week 1)
1. ✅ Implement enhanced AuthContext with task support
2. ✅ Create user-aware dependency injection pattern
3. ✅ Set up secure task context store
4. ✅ Update base service classes

### Phase 2: Service Migration (Week 2)
1. **DocumentService**: Convert from service role to user context where appropriate
2. **OCR Services**: Maintain user context for user-specific processing
3. **Semantic Services**: User context for analysis, system role for model management

### Phase 3: Background Task Migration (Week 3)
1. **Document Processing Tasks**: Use user context
2. **OCR Processing Tasks**: Use user context
3. **Report Generation**: Use user context
4. **System Maintenance**: Keep service role

### Phase 4: Validation & Optimization (Week 4)
1. **RLS Policy Validation**: Ensure all user operations are properly scoped
2. **Performance Testing**: Token encryption/decryption overhead
3. **Security Audit**: Context storage and cleanup
4. **Documentation**: Updated patterns and guidelines

## 🛡️ Security Considerations

### Token Security
- **Encryption**: All stored tokens encrypted with Fernet (AES-256)
- **TTL**: Short-lived task contexts (1 hour default)
- **Cleanup**: Automatic context cleanup after task completion
- **Key Rotation**: Support for encryption key rotation

### Access Control
- **Service Boundaries**: Clear separation between user and system operations
- **Audit Trail**: Enhanced logging with context information
- **Token Validation**: JWT validation for task tokens
- **Context Isolation**: No cross-user context leakage

### Operational Security
- **Redis Security**: Encrypted connections, authentication
- **Key Management**: Secure key storage (environment variables)
- **Monitoring**: Token usage and failure monitoring
- **Alerting**: Unusual token access patterns

## 📊 Implementation Examples

### Service Refactoring Example

```python
# BEFORE: Service role for everything
class DocumentService:
    async def process_document(self, document_id: str):
        # Uses service role - bypasses RLS
        client = await get_supabase_client()
        # Process document...

# AFTER: User context aware
class DocumentService(UserAwareService):
    async def process_document(self, document_id: str):
        # Uses user context - RLS enforced
        client = await self.get_user_client()
        # Process document with proper user scoping...
    
    async def create_system_bucket(self, bucket_name: str):
        # Legitimate system operation
        client = await self.get_system_client()
        # Create bucket with admin privileges...
```

### API Endpoint Pattern

```python
@router.post("/documents/{document_id}/process")
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    user_client: UserSupabaseClient,  # Injected user client
):
    # Create task context
    task_context = AuthContext.create_task_context()
    context_key = await task_store.store_context(
        task_id=f"process_{document_id}_{int(time.time())}", 
        auth_context=task_context
    )
    
    # Launch background task with context
    task = process_user_document_background.delay(
        context_key, document_id, user.id
    )
    
    return {"task_id": task.id, "message": "Processing started"}
```

### Background Task Implementation

```python
@celery_app.task
@user_aware_task
async def process_user_document_background(document_id: str, user_id: str):
    """Process document maintaining user context"""
    
    # Service automatically uses restored user context
    document_service = DocumentService()
    await document_service.initialize()
    
    # All operations are user-scoped via RLS
    result = await document_service.process_document(document_id)
    
    # Send user-specific notification
    notification_service = NotificationService()
    await notification_service.notify_user(user_id, "Processing complete")
    
    return result
```

## 🎯 Success Metrics

### Security Metrics
- **Zero Cross-User Data Access**: RLS violations = 0
- **Token Security**: No plaintext tokens in logs or storage
- **Context Isolation**: Each task operates only on authorized data

### Performance Metrics  
- **Token Operations**: < 10ms for encrypt/decrypt
- **Context Restoration**: < 5ms for background tasks
- **Memory Usage**: Minimal context storage overhead

### Operational Metrics
- **Task Success Rate**: > 99.9% context restoration success
- **Security Incidents**: Zero token leakage incidents
- **Developer Experience**: Clear patterns, reduced complexity

## 🔍 Alternative Approaches Considered

### 1. Session-Based Context
❌ **Rejected**: Doesn't work across async boundaries
❌ **Scalability**: Session storage complexity

### 2. Database Token Storage  
❌ **Rejected**: Performance overhead for every operation
❌ **Security**: More attack surface

### 3. JWT Task Tokens (Alternative)
✅ **Viable**: Stateless, good performance
⚠️ **Consideration**: Token size, expiration management

### 4. Message Queue Context Headers
❌ **Rejected**: Celery doesn't support custom headers easily
❌ **Portability**: Tied to specific queue implementation

## 📋 Implementation Checklist

### Core Infrastructure
- [ ] Enhanced AuthContext with task support
- [ ] Secure task context store (Redis + encryption)
- [ ] User-aware dependency injection
- [ ] Base service classes (UserAwareService, SystemService)

### Service Migration
- [ ] DocumentService user context migration  
- [ ] OCR services context preservation
- [ ] Semantic analysis service boundaries
- [ ] WebSocket service (keep system role)

### Background Tasks
- [ ] Task context storage pattern
- [ ] User-aware task decorator
- [ ] Document processing tasks
- [ ] OCR processing tasks
- [ ] Report generation tasks

### Security & Validation
- [ ] RLS policy validation
- [ ] Token encryption testing
- [ ] Context cleanup verification
- [ ] Cross-user access prevention testing

### Documentation & Training
- [ ] Architecture documentation
- [ ] Migration guidelines
- [ ] Security best practices
- [ ] Developer training materials

This architecture provides a comprehensive solution for maintaining user context throughout the system while preserving security boundaries and performance requirements.