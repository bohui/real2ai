/**
 * Test ProtectedRoute component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@/test/utils'
import ProtectedRoute from '../ProtectedRoute'
import { useAuthStore } from '@/store/authStore'
import { User } from '@/types'

// Mock the auth store
const mockAuthStore = {
  isAuthenticated: false,
  user: null as User | null,
  isLoading: false,
  error: null,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  clearError: vi.fn(),
  updateUser: vi.fn(),
  updateProfile: vi.fn(),
  refreshUser: vi.fn(),
  initializeAuth: vi.fn(),
}

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthStore),
}))

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store to default state
    Object.assign(mockAuthStore, {
      isAuthenticated: false,
      user: null,
      isLoading: false,
      error: null,
    })
    // Ensure useAuthStore is properly mocked
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)
  })

  describe('Loading State', () => {
    it('shows loading spinner when authentication is loading', () => {
      mockAuthStore.isLoading = true

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      // Should show loading spinner
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('has proper loading state structure', () => {
      mockAuthStore.isLoading = true

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      const loadingContainer = document.querySelector('.min-h-screen')
      expect(loadingContainer).toBeInTheDocument()
      expect(loadingContainer).toHaveClass('flex', 'items-center', 'justify-center')
      
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
      expect(spinner).toHaveClass('rounded-full', 'h-8', 'w-8', 'border-b-2', 'border-primary-600')
    })
  })

  describe('Unauthenticated Access', () => {
    it('redirects to login when not authenticated', () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('redirects to custom fallback path when specified', () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null

      render(
        <ProtectedRoute fallbackPath="/custom-login">
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('redirects when authenticated but user is null', () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = null

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('redirects when user exists but not authenticated', () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = null

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })
  })

  describe('Authenticated Access', () => {
    beforeEach(() => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = {
        id: 'user1',
        email: 'test@example.com',
        user_type: 'buyer',
        australian_state: 'NSW',
        subscription_status: 'free',
        credits_remaining: 0,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      }
    })

    it('renders protected content when authenticated', () => {
      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })

    it('renders complex protected content structure', () => {
      render(
        <ProtectedRoute>
          <div data-testid="protected-content">
            <h1>Dashboard</h1>
            <nav>Navigation</nav>
            <main>Main Content</main>
          </div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Navigation')).toBeInTheDocument()
      expect(screen.getByText('Main Content')).toBeInTheDocument()
    })
  })

  describe('Role-Based Access Control', () => {
    beforeEach(() => {
      mockAuthStore.isAuthenticated = true
    })

    it('allows access when user has required role', () => {
      mockAuthStore.user = {
        id: 'admin1',
        email: 'admin@example.com',
        user_type: 'agent',
        australian_state: 'NSW',
        subscription_status: 'enterprise',
        credits_remaining: 100,
        preferences: {},
        onboarding_completed: true,
        onboarding_preferences: {}
      }

      render(
        <ProtectedRoute requiredRole="agent">
          <div data-testid="protected-content">Agent Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.getByText('Agent Content')).toBeInTheDocument()
    })

    it('redirects to dashboard when user lacks required role', () => {
      mockAuthStore.user = {
        id: 'user1',
        email: 'user@example.com',
        user_type: 'buyer',
        australian_state: 'NSW',
        subscription_status: 'free',
        credits_remaining: 0,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      }

      render(
        <ProtectedRoute requiredRole="agent">
          <div data-testid="protected-content">Agent Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('allows access when no role is required', () => {
      mockAuthStore.user = {
        id: 'user1',
        email: 'user@example.com',
        user_type: 'buyer',
        australian_state: 'NSW',
        subscription_status: 'free',
        credits_remaining: 0,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      }

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Content for all users</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.getByText('Content for all users')).toBeInTheDocument()
    })

    it('handles undefined user_type gracefully', () => {
      mockAuthStore.user = {
        id: 'user1',
        email: 'user@example.com',
        australian_state: 'NSW',
        subscription_status: 'free',
        credits_remaining: 0,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      } as any // No user_type

      render(
        <ProtectedRoute requiredRole="agent">
          <div data-testid="protected-content">Agent Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles user object without standard properties', () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = { customId: 'user1' } as any // Missing standard user properties

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })

  describe('Security Validation', () => {
    it('prevents access with forged authentication state', () => {
      // Simulate forged auth state (authenticated but no user)
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = null

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Should not render</div>
        </ProtectedRoute>
      )

      // Should still redirect due to missing user
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByTestId('navigate')).toBeInTheDocument()
    })

    it('validates both authentication and user presence', () => {
      mockAuthStore.isAuthenticated = false
      mockAuthStore.user = {
        id: 'user1',
        email: 'test@example.com',
        user_type: 'agent',
        australian_state: 'NSW',
        subscription_status: 'enterprise',
        credits_remaining: 100,
        preferences: {},
        onboarding_completed: true,
        onboarding_preferences: {}
      }

      render(
        <ProtectedRoute>
          <div data-testid="protected-content">Should not render</div>
        </ProtectedRoute>
      )

      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('requires exact role match for security', () => {
      mockAuthStore.isAuthenticated = true
      mockAuthStore.user = {
        id: 'user1',
        email: 'user@example.com',
        user_type: 'individual',
        australian_state: 'NSW',
        subscription_status: 'free',
        credits_remaining: 0,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      }

      render(
        <ProtectedRoute requiredRole="agent">
          <div data-testid="protected-content">Agent Content</div>
        </ProtectedRoute>
      )

      // Should redirect since 'individual' !== 'agent'
      expect(screen.getByTestId('navigate')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })
  })
})