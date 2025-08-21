# Frontend 401 Response Handling Solution

## Problem

When the backend returns 401 responses (e.g., "Session mapping unavailable. Please log in again."), the frontend was not properly handling these responses to redirect users to the login page. Users would see 401 errors but remain on the current page without being redirected.

## Solution

Implemented a comprehensive 401 handling system that:

1. **Catches 401 responses globally** from all API calls
2. **Automatically redirects users** to the login page
3. **Clears authentication state** when sessions expire
4. **Provides user feedback** about session expiration

## Implementation Details

### 1. Enhanced API Service (`frontend/src/services/api.ts`)

#### Global 401 Interceptor
```typescript
// Global error handler for 401 responses
this.client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle 401 globally - redirect to login
      this.handleUnauthorized();
    }
    return Promise.reject(error);
  }
);
```

#### Backend Token Detection
```typescript
private isBackendToken(): boolean {
  if (!this.token) return false;
  
  try {
    const payload = JSON.parse(atob(this.token.split('.')[1]));
    return payload.type === 'api';
  } catch {
    return false;
  }
}
```

#### Unauthorized Handler
```typescript
private handleUnauthorized(): void {
  // Clear any existing auth state
  this.clearTokens();
  
  // Dispatch custom event for components to listen to
  window.dispatchEvent(new CustomEvent("auth:unauthorized", {
    detail: { message: "Session expired. Please log in again." }
  }));
  
  // Force redirect to login page
  if (window.location.pathname !== "/auth/login") {
    window.location.href = "/auth/login";
  }
}
```

### 2. Enhanced Auth Store (`frontend/src/store/authStore.ts`)

#### Force Logout Method
```typescript
forceLogout: (message?: string) => {
  apiService.clearTokens();
  set({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: message || "Session expired. Please log in again.",
  });

  // Reset onboarding state and redirect
  import("@/store/uiStore").then(({ useUIStore }) => {
    useUIStore.getState().resetOnboardingState();
  });

  if (window.location.pathname !== "/auth/login") {
    window.location.href = "/auth/login";
  }
}
```

### 3. Global Error Handler (`frontend/src/App.tsx`)

#### Authentication Error Listener
```typescript
React.useEffect(() => {
  const handleUnauthorized = (event: CustomEvent) => {
    logger.warn("Authentication error detected, redirecting to login", event.detail);
    
    // Clear auth state
    useAuthStore.getState().logout();
    
    // Show notification if not on login page
    if (window.location.pathname !== "/auth/login") {
      console.warn("Session expired. Please log in again.");
    }
  };

  window.addEventListener("auth:unauthorized", handleUnauthorized as EventListener);
  
  return () => {
    window.removeEventListener("auth:unauthorized", handleUnauthorized as EventListener);
  };
}, []);
```

## How It Works

### 1. **API Call Returns 401**
- Any API endpoint returns 401 (e.g., expired backend token)
- Global axios interceptor catches the 401 response

### 2. **Automatic Token Cleanup**
- `handleUnauthorized()` method is called
- All tokens are cleared from localStorage
- Authentication state is reset

### 3. **User Redirect**
- User is automatically redirected to `/auth/login`
- Custom event is dispatched for additional handling
- Auth store state is cleared

### 4. **User Experience**
- User sees login page with clear indication they need to re-authenticate
- No more 401 errors displayed on protected pages
- Seamless transition from expired session to login

## Benefits

1. **Automatic Handling**: No manual intervention required for 401 responses
2. **User Experience**: Users are automatically redirected to login
3. **State Management**: Authentication state is properly cleared
4. **Global Coverage**: Works for all API calls across the application
5. **Backend Token Support**: Specifically handles backend token expiration

## Testing

A test component (`Test401Handler.tsx`) is provided to verify the functionality:

- **Test 401 Response**: Simulates API calls returning 401
- **Test Backend Token Expiry**: Manually clears tokens to test redirect

## Expected Behavior

1. **User on `/app/analysis` with expired token**
2. **API call returns 401**
3. **Frontend automatically:**
   - Clears authentication state
   - Redirects to `/auth/login`
   - Shows appropriate message about session expiration
4. **User can log in again and continue**

## Configuration

No additional configuration required. The system automatically:
- Detects backend vs Supabase tokens
- Handles different token types appropriately
- Redirects users based on current location
- Maintains proper error logging

This solution ensures that users never get stuck on protected pages with expired sessions and always have a clear path to re-authentication.
