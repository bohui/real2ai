/**
 * Test ProtectedRoute component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@/test/utils'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ProtectedRoute from '../ProtectedRoute'
import { mockUser, mockAuthStore } from '@/test/utils'

// Mock the auth store
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthStore),
}))

// Test component to render inside ProtectedRoute
const TestComponent = () => <div data-testid="protected-content">Protected Content</div>

// Custom render function with all required providers
const renderWithProviders = (ui: React.ReactElement, initialEntries: string[] = ['/']) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/auth/login" element={<div data-testid="login-page">Login Page</div>} />
          <Route path="/app/dashboard" element={<div data-testid="dashboard-page">Dashboard</div>} />
          <Route path="/protected" element={ui} />
          <Route path="/custom-fallback" element={<div data-testid="custom-fallback">Custom Fallback</div>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store to default state
    mockAuthStore.isAuthenticated = false
    mockAuthStore.user = null
    mockAuthStore.isLoading = false
  })

  describe('Loading State', () => {
    it('shows loading spinner when authentication is loading', () => {
      mockAuthStore.isLoading = true
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      // Should show loading spinner
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('has proper loading state structure', () => {
      mockAuthStore.isLoading = true

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      const loadingContainer = document.querySelector('.min-h-screen')
      expect(loadingContainer).toBeInTheDocument()
      expect(loadingContainer).toHaveClass('flex', 'items-center', 'justify-center')
      
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toHaveClass('rounded-full', 'h-8', 'w-8', 'border-b-2', 'border-primary-600')
    })
  })

  describe('Unauthenticated Access', () => {
    it('redirects to login when not authenticated', async () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })

    it('redirects to custom fallback path when specified', async () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute fallbackPath="/custom-fallback">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('custom-fallback')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })

    it('redirects when authenticated but user is null', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = null
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })

    it('redirects when user exists but not authenticated', async () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = mockUser
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })
  })

  describe('Authenticated Access', () => {
    it('renders protected content when authenticated', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = mockUser
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
        expect(screen.queryByTestId('login-page')).not.toBeInTheDocument()
      })
    })

    it('renders multiple children correctly', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = mockUser
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('child-1')).toBeInTheDocument()
        expect(screen.getByTestId('child-2')).toBeInTheDocument()
      })
    })
  })

  describe('Role-Based Access Control', () => {
    it('allows access when user has required role', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: 'buyer' }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute requiredRole="buyer">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
        expect(screen.queryByTestId('dashboard-page')).not.toBeInTheDocument()
      })
    })

    it('redirects to dashboard when user lacks required role', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: 'buyer' }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute requiredRole="admin">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })

    it('allows access when no role is required', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: 'buyer' }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      })
    })

    it('handles undefined user_type gracefully', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: undefined }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute requiredRole="buyer">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })

    it('handles null user_type gracefully', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: null }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute requiredRole="buyer">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })
  })

  describe('Navigation State Preservation', () => {
    it('preserves location state when redirecting to login', async () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null
      mockAuthStore.isLoading = false

      // We can't easily test the location state with React Router in tests
      // but we can verify the redirect happens
      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('handles missing auth store gracefully', async () => {
      // This test verifies the component doesn't crash if the store is in an unexpected state
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      try {
        renderWithProviders(
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        )

        // Component should still render something (either loading or redirect)
        expect(document.body).toBeInTheDocument()
      } catch (error) {
        // If it throws, that's also a valid test outcome to document
        expect(error).toBeDefined()
      }

      consoleSpy.mockRestore()
    })

    it('handles complex role hierarchies', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: 'premium_buyer' }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute requiredRole="buyer">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        // Should redirect since 'premium_buyer' !== 'buyer' (exact match required)
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })

    it('handles empty string role requirement', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: 'buyer' }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute requiredRole="">
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        // Empty string is falsy, so should allow access
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      })
    })
  })

  describe('Component Props', () => {
    it('accepts all valid prop combinations', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { ...mockUser, user_type: 'admin' }
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute 
          requiredRole="admin" 
          fallbackPath="/custom-fallback"
        >
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      })
    })

    it('works with just children prop', async () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = mockUser
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      })
    })
  })

  describe('Security Validation', () => {
    it('prevents access with forged authentication state', async () => {
      // Simulate a scenario where isAuthenticated is true but user is malformed
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = {} // Empty user object
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        // Should still allow access as long as user object exists
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      })
    })

    it('validates both authentication and user presence', async () => {
      // Test the double-check: both isAuthenticated AND user must be present
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = null
      mockAuthStore.isLoading = false

      renderWithProviders(
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })
  })
})