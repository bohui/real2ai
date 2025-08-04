/**
 * Test App component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@/test/utils'
import App from '../App'
import { mockUser, mockApiService, mockAuthStore, mockUIStore } from '@/test/utils'

// Mock all the stores and services
vi.mock('@/store/authStore', () => ({
  useAuthStore: () => mockAuthStore,
}))

vi.mock('@/store/uiStore', () => ({
  useUIStore: () => mockUIStore,
}))

vi.mock('@/services/api', () => ({
  default: mockApiService,
}))

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock state
    mockAuthStore.user = null
    mockAuthStore.isAuthenticated = false
    mockAuthStore.isLoading = false
    mockUIStore.showOnboarding = false
  })

  it('shows loading spinner while initializing auth', () => {
    mockAuthStore.isLoading = true
    
    render(<App />)
    
    expect(screen.getByText(/loading real2\.ai/i)).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('initializes authentication on startup', () => {
    render(<App />)
    
    expect(mockAuthStore.initializeAuth).toHaveBeenCalledTimes(1)
  })

  it('redirects unauthenticated users to login', () => {
    mockAuthStore.isAuthenticated = false
    
    render(<App />)
    
    // Should redirect to /auth/login
    expect(window.location.pathname).toBe('/')
  })

  it('shows main app for authenticated users', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockApiService.getOnboardingStatus.mockResolvedValue({
      onboarding_completed: true,
      onboarding_preferences: {},
    })
    
    render(<App />)
    
    await waitFor(() => {
      expect(screen.getByRole('main')).toBeInTheDocument()
    })
  })

  it('checks onboarding status for authenticated users', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockApiService.getOnboardingStatus.mockResolvedValue({
      onboarding_completed: false,
      onboarding_preferences: {},
    })
    
    render(<App />)
    
    await waitFor(() => {
      expect(mockApiService.getOnboardingStatus).toHaveBeenCalledTimes(1)
    })
  })

  it('shows onboarding wizard for incomplete onboarding', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockApiService.getOnboardingStatus.mockResolvedValue({
      onboarding_completed: false,
      onboarding_preferences: {},
    })
    
    render(<App />)
    
    await waitFor(() => {
      expect(mockUIStore.setShowOnboarding).toHaveBeenCalledWith(true)
    })
  })

  it('does not show onboarding for completed users', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockApiService.getOnboardingStatus.mockResolvedValue({
      onboarding_completed: true,
      onboarding_preferences: {
        practice_area: 'property',
        jurisdiction: 'nsw',
      },
    })
    
    render(<App />)
    
    await waitFor(() => {
      expect(mockUIStore.setShowOnboarding).not.toHaveBeenCalledWith(true)
    })
  })

  it('handles onboarding completion', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockUIStore.showOnboarding = true
    mockApiService.completeOnboarding.mockResolvedValue({
      message: 'Onboarding completed successfully',
      skip_onboarding: false,
    })
    
    render(<App />)
    
    const onboardingWizard = screen.getByRole('dialog', { name: /onboarding/i })
    expect(onboardingWizard).toBeInTheDocument()
    
    // Simulate onboarding completion
    const completeButton = screen.getByRole('button', { name: /complete/i })
    fireEvent.click(completeButton)
    
    await waitFor(() => {
      expect(mockApiService.completeOnboarding).toHaveBeenCalled()
      expect(mockUIStore.setShowOnboarding).toHaveBeenCalledWith(false)
    })
  })

  it('handles onboarding skip', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockUIStore.showOnboarding = true
    
    render(<App />)
    
    const onboardingWizard = screen.getByRole('dialog', { name: /onboarding/i })
    expect(onboardingWizard).toBeInTheDocument()
    
    // Simulate onboarding skip
    const skipButton = screen.getByRole('button', { name: /skip/i })
    fireEvent.click(skipButton)
    
    await waitFor(() => {
      expect(mockUIStore.setShowOnboarding).toHaveBeenCalledWith(false)
    })
  })

  it('handles onboarding status check errors gracefully', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockApiService.getOnboardingStatus.mockRejectedValue(new Error('API Error'))
    
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation()
    
    render(<App />)
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to check onboarding status:', expect.any(Error))
      expect(mockUIStore.setShowOnboarding).toHaveBeenCalledWith(true)
    })
    
    consoleSpy.mockRestore()
  })

  it('renders notification system', () => {
    render(<App />)
    
    expect(screen.getByRole('region', { name: /notifications/i })).toBeInTheDocument()
  })

  it('shows React Query devtools in development', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'development'
    
    render(<App />)
    
    // React Query devtools should be present (though may not be visible)
    expect(document.querySelector('[data-testid="react-query-devtools"]')).toBeInTheDocument()
    
    process.env.NODE_ENV = originalEnv
  })

  it('does not show devtools in production', () => {
    const originalEnv = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'
    
    render(<App />)
    
    expect(document.querySelector('[data-testid="react-query-devtools"]')).not.toBeInTheDocument()
    
    process.env.NODE_ENV = originalEnv
  })

  it('handles already completed onboarding gracefully', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockUIStore.showOnboarding = true
    mockApiService.completeOnboarding.mockResolvedValue({
      message: 'Onboarding already completed',
      skip_onboarding: true,
    })
    
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation()
    
    render(<App />)
    
    // Simulate onboarding completion
    const completeButton = screen.getByRole('button', { name: /complete/i })
    fireEvent.click(completeButton)
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('User already completed onboarding')
      expect(mockUIStore.setShowOnboarding).toHaveBeenCalledWith(false)
    })
    
    consoleSpy.mockRestore()
  })

  it('handles onboarding completion errors gracefully', async () => {
    mockAuthStore.user = mockUser
    mockAuthStore.isAuthenticated = true
    mockUIStore.showOnboarding = true
    mockApiService.completeOnboarding.mockRejectedValue(new Error('Completion failed'))
    
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation()
    
    render(<App />)
    
    // Simulate onboarding completion
    const completeButton = screen.getByRole('button', { name: /complete/i })
    fireEvent.click(completeButton)
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to complete onboarding:', expect.any(Error))
      expect(mockUIStore.setShowOnboarding).toHaveBeenCalledWith(false)
    })
    
    consoleSpy.mockRestore()
  })
})