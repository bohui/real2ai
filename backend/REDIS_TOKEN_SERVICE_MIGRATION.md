# Redis-Based Token Service Migration

## Overview

This document describes the migration of the `BackendTokenService` from in-memory storage to Redis-based persistent storage. This change resolves the authentication issues that occur when the backend restarts, as tokens are now persisted across restarts.

## Problem

The original implementation used an in-memory Python dictionary (`_token_store`) to store token mappings. When the backend process restarted, all tokens were lost, causing 401 authentication errors:

```
"Backend token not found in store. Available tokens: 0"
```

## Solution

Replaced the in-memory storage with Redis-based storage that persists across backend restarts.

## Changes Made

### 1. BackendTokenService Updates

- **File**: `backend/app/services/backend_token_service.py`
- **Changes**:
  - Added Redis client management with connection pooling
  - Replaced `_token_store` dictionary with Redis operations
  - Made all token operations async for Redis compatibility
  - Added Redis connection error handling and logging

### 2. New Redis Methods

- `_get_redis_client()`: Manages Redis connection
- `_store_token_data()`: Stores token data in Redis with TTL
- `_get_token_data()`: Retrieves token data from Redis
- `_delete_token_data()`: Deletes token data from Redis
- `get_store_stats()`: Provides token store statistics
- `cleanup_expired_tokens()`: Cleans up expired tokens

### 3. Updated Method Signatures

The following methods are now async and must be called with `await`:

- `issue_backend_token()` → `async def issue_backend_token()`
- `ensure_supabase_access_token()` → `async def ensure_supabase_access_token()`
- `refresh_coordinated_tokens()` → `async def refresh_coordinated_tokens()`
- `reissue_backend_token()` → `async def reissue_backend_token()`
- `get_mapping()` → `async def get_mapping()`

### 4. Updated Call Sites

Updated all calling code to use `await`:

- `backend/app/router/auth.py`: Login endpoint
- `backend/app/core/auth_context.py`: Auth context management
- `backend/app/router/websockets.py`: WebSocket authentication
- `backend/app/core/task_context.py`: Background task context

## Benefits

1. **Persistence**: Tokens survive backend restarts
2. **Scalability**: Multiple backend instances can share the same token store
3. **Automatic Expiration**: Redis TTL handles token cleanup
4. **Better Error Handling**: Graceful fallback when Redis is unavailable
5. **Monitoring**: Store statistics and cleanup capabilities

## Configuration

The service uses the existing Redis configuration from `app/core/config.py`:

```python
redis_url: str = "redis://localhost:6379"
```

## Testing

A test script is provided at `backend/test_redis_token_service.py` to verify the Redis integration works correctly.

## Migration Notes

### Breaking Changes

- All token service methods are now async
- Callers must use `await` when calling token service methods

### Rollback Plan

If issues arise, the service can be temporarily reverted to in-memory storage by:
1. Restoring the `_token_store` dictionary
2. Removing `async/await` keywords
3. Reverting method calls to synchronous versions

### Performance Impact

- **Latency**: Slight increase due to Redis network calls
- **Throughput**: Improved due to persistent storage and better scalability
- **Memory**: Reduced backend memory usage (tokens stored in Redis)

## Monitoring

The service now provides:

- Redis connection status logging
- Token store statistics
- Automatic cleanup of expired tokens
- Detailed error logging for debugging

## Future Enhancements

1. **Redis Cluster Support**: For high-availability deployments
2. **Token Encryption**: Encrypt sensitive token data in Redis
3. **Metrics**: Prometheus metrics for token operations
4. **Backup**: Redis persistence configuration for disaster recovery
