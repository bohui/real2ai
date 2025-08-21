# 401 Response Debugging Guide

## Problem
The frontend is receiving 401 responses from the backend (e.g., `/api/users/onboarding/status`) but is not redirecting to the login page as expected.

## What We've Implemented

### 1. Enhanced API Service
- **Global 401 interceptor** that catches ALL 401 responses
- **Backend token detection** to identify token types
- **Automatic redirect** to login page on 401 responses
- **Debug logging** to track what's happening

### 2. Test Component
Added `Test401Handler` component with buttons to test:
- **Test 401 Response**: Makes API call to non-existent endpoint
- **Test Backend Token Expiry**: Manually clears tokens
- **Test 401 Handling Directly**: Calls `handleUnauthorized()` method
- **Test Interceptors**: Verifies interceptors are working

## Debugging Steps

### Step 1: Check Console Logs
Open browser console and look for these debug messages:

```
🔧 API Service initialized with interceptors
🚨 401 response detected in interceptor: {...}
🚨 handleUnauthorized called - redirecting to login
🔄 Redirecting from /app/analysis to /auth/login
```

### Step 2: Test the Test Component
1. Add `Test401Handler` to any page (e.g., Analysis page)
2. Click each test button
3. Check console for results

### Step 3: Verify Token Type
The console should show:
```
🧪 Testing 401 handling...
🧪 Current token: eyJhbGciOiJIUzI1NiIs...
🧪 Is backend token: true/false
```

### Step 4: Check Interceptor Status
Look for:
```
🧪 Testing interceptors...
🧪 Interceptor test result: {...}
```

## Expected Behavior

### When 401 Response is Received:
1. **Console shows**: `🚨 401 response detected in interceptor`
2. **handleUnauthorized is called**: `🚨 handleUnauthorized called`
3. **Redirect happens**: `🔄 Redirecting from X to /auth/login`
4. **User lands on**: `/auth/login` page

### If Not Working:
1. **No console logs**: Interceptors not attached
2. **Logs but no redirect**: `handleUnauthorized` not working
3. **Partial logs**: Check for errors in the method

## Common Issues & Solutions

### Issue 1: No Console Logs
**Problem**: API service not initialized or interceptors not attached
**Solution**: Check if `apiService` is properly imported and used

### Issue 2: 401 Detected but No Redirect
**Problem**: `handleUnauthorized` method not working
**Solution**: Check for JavaScript errors in console

### Issue 3: Multiple Axios Instances
**Problem**: Different axios instances bypassing interceptors
**Solution**: Ensure all API calls use the same `apiService` instance

### Issue 4: Timing Issues
**Problem**: Interceptors not ready when API calls are made
**Solution**: Wait for API service to fully initialize

## Testing Commands

### In Browser Console:
```javascript
// Test if API service is working
console.log(apiService);

// Test 401 handling directly
apiService.test401Handling();

// Test interceptors
apiService.testInterceptors();

// Check current token
console.log(apiService.token);
```

### Manual Test:
1. **Navigate to** `/app/analysis` (or any protected page)
2. **Open console** and look for debug messages
3. **Make an API call** that returns 401
4. **Watch for** redirect to login page

## Next Steps

1. **Add Test401Handler** to your Analysis page
2. **Check console logs** for debug messages
3. **Test each button** to isolate the issue
4. **Report findings** based on console output

## Files Modified

- `frontend/src/services/api.ts` - Enhanced 401 handling
- `frontend/src/components/test/Test401Handler.tsx` - Test component
- `frontend/src/App.tsx` - Global error handler
- `frontend/src/store/authStore.ts` - Force logout method

The solution should now properly catch 401 responses and redirect users to login. If it's still not working, the debug logs will show exactly where the issue is occurring.
