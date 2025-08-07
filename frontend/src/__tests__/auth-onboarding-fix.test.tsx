/**
 * Test cases to verify onboarding doesn't show for unauthenticated users
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import App from '../App'
import {
  renderApp,
  configureUnauthenticatedState,
  mockUIStore
} from '@/test/utils'

describe('Auth Onboarding Fix', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not show onboarding for unauthenticated users', async () => {
    // Configure unauthenticated state
    configureUnauthenticatedState()
    mockUIStore.showOnboarding = false

    renderApp(<App />)

    // Should not show onboarding wizard
    expect(screen.queryByText('Welcome to Real2.AI')).not.toBeInTheDocument()
    expect(screen.queryByText('Let\'s get started')).not.toBeInTheDocument()
  })

  it('should not show onboarding when user becomes unauthenticated', async () => {
    // Configure unauthenticated state but with onboarding flag set (simulating token expiration)
    configureUnauthenticatedState()
    mockUIStore.showOnboarding = true // This might be true from previous state

    renderApp(<App />)

    // Even if showOnboarding is true, it should not show because user is not authenticated
    expect(screen.queryByText('Welcome to Real2.AI')).not.toBeInTheDocument()
    expect(screen.queryByText('Let\'s get started')).not.toBeInTheDocument()
  })

  it('should only show onboarding for fully authenticated users', async () => {
    // Import and configure stores
    const { useAuthStore } = await import('@/store/authStore')
    const { useUIStore } = await import('@/store/uiStore')
    const { apiService } = await import('@/services/api')
    
    // Configure authenticated state
    vi.mocked(useAuthStore).mockReturnValue({
      user: { 
        id: 'test-user', 
        email: 'test@example.com',
        australian_state: 'NSW',
        onboarding_completed: false
      },
      isAuthenticated: true,
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
      setUser: vi.fn(),
    })
    
    // Configure UI store to start with onboarding hidden
    const mockSetShowOnboarding = vi.fn()
    vi.mocked(useUIStore).mockReturnValue({
      showOnboarding: false,
      notifications: [],
      setShowOnboarding: mockSetShowOnboarding,
      addNotification: vi.fn(),
      removeNotification: vi.fn(),
      clearNotifications: vi.fn(),
    })
    
    // Mock the API call to return onboarding not completed
    vi.mocked(apiService.getOnboardingStatus).mockResolvedValue({
      onboarding_completed: false,
      onboarding_preferences: {}
    })

    renderApp(<App />)

    // Wait for the onboarding to show - the App should call setShowOnboarding(true)
    await waitFor(() => {
      expect(mockSetShowOnboarding).toHaveBeenCalledWith(true)
    }, { timeout: 2000 })
    
    // Now mock the UI store to return showOnboarding: true to simulate the state update
    vi.mocked(useUIStore).mockReturnValue({
      showOnboarding: true,
      notifications: [],
      setShowOnboarding: mockSetShowOnboarding,
      addNotification: vi.fn(),
      removeNotification: vi.fn(),
      clearNotifications: vi.fn(),
    })
    
    // Re-render to get the updated state
    renderApp(<App />)

    // Now onboarding should show because user is fully authenticated
    await waitFor(() => {
      expect(screen.queryByTestId('onboarding-wizard')).toBeInTheDocument()
    }, { timeout: 2000 })
  })
})