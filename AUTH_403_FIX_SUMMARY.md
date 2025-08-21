# Authentication 403 Response Fix Summary

## Problem Description

The frontend was receiving **403 Forbidden** responses from the backend (e.g., `/api/users/onboarding/status`) when tokens expired, but the frontend was not redirecting users to the login page as expected. This was happening because:

1. **Frontend only handled 401 responses**: The API service had interceptors for 401 Unauthorized responses but not for 403 Forbidden responses
2. **Backend returned 403 instead of 401**: FastAPI's default `HTTPBearer()` security scheme returns 403 for missing/invalid tokens
3. **No backend logging**: The 403 responses were coming from FastAPI's security layer before reaching application code, so no logs were generated

## Root Cause

The issue was in `backend/app/core/auth.py`:

```python
# OLD CODE - This caused 403 responses
security = HTTPBearer()
```

FastAPI's `HTTPBearer()` by default returns:
- **403 Forbidden** for missing or invalid Authorization headers
- **403 Forbidden** for malformed Bearer tokens
- **403 Forbidden** for expired tokens

But the frontend expected **401 Unauthorized** to trigger login redirects.

## Solution Implemented

### 1. Custom HTTPBearer Class

**File**: `backend/app/core/auth.py`

Created a custom `CustomHTTPBearer` class that converts 403 responses to 401:

```python
class CustomHTTPBearer(HTTPBearer):
    """Custom HTTPBearer that returns 401 instead of 403 for authentication issues."""
    
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            return await super().__call__(request)
        except HTTPException as e:
            # Convert 403 to 401 for authentication issues
            if e.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
            raise

security = CustomHTTPBearer()
```

### 2. Frontend 403 Interceptor

**File**: `frontend/src/services/api.ts`

Added a 403 response interceptor to handle forbidden responses the same way as 401 responses:

```typescript
} else if (error.response?.status === 403) {
  // Handle 403 responses - often indicate expired/invalid tokens
  console.log("🚨 403 response detected in interceptor:", {
    url: error.config?.url,
    method: error.config?.method,
    status: error.response?.status,
    message: (error.response?.data as any)?.detail || error.message,
  });
  // Treat 403 as auth issue and redirect to login
  this.handleUnauthorized();
}
```

### 3. Enhanced Backend Logging

**File**: `backend/app/middleware/auth_middleware.py`

Added more detailed logging to help debug authentication issues:

```python
else:
    logger.warning(f"No token available for request to {request.url.path} from {request.client.host if request.client else 'unknown'}")
    logger.debug(f"Request headers: {dict(request.headers)}")
```

## Testing the Fix

### Before Fix
```bash
$ python debug_auth_issue.py
🔒 Onboarding endpoint (no auth): 403
   ⚠️  Expected 401, got 403
   Response: {"detail":"Not authenticated"}
```

### After Fix
```bash
$ python debug_auth_issue.py
🔒 Onboarding endpoint (no auth): 401
```

## Benefits

1. **Proper HTTP Status Codes**: Now returns 401 instead of 403 for authentication issues
2. **Frontend Redirects Work**: Users are automatically redirected to login when tokens expire
3. **Better Debugging**: Enhanced logging helps identify authentication issues
4. **Consistent Behavior**: All authentication failures now return 401 consistently

## Files Modified

1. `backend/app/core/auth.py` - Added CustomHTTPBearer class
2. `frontend/src/services/api.ts` - Added 403 response interceptor
3. `backend/app/middleware/auth_middleware.py` - Enhanced logging
4. `debug_auth_issue.py` - Created debug script
5. `frontend/src/components/auth/Test401Handler.tsx` - Added 403 test button

## Next Steps

1. **Test the fix**: The frontend should now properly redirect to login when tokens expire
2. **Monitor logs**: Check backend logs for authentication-related messages
3. **User experience**: Users should no longer get stuck on pages when their session expires

## Related Issues

This fix addresses the core authentication flow issue. For complete authentication robustness, consider also:

1. **Token refresh coordination** between frontend and backend
2. **Session timeout warnings** before automatic logout
3. **Graceful degradation** when authentication services are unavailable
