/**
 * Test cases to verify onboarding doesn't show for unauthenticated users
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import App from '../App'
import {
  renderApp,
  configureUnauthenticatedState,
  configureAuthenticatedState,
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
    // Configure authenticated state with onboarding needed
    configureAuthenticatedState({
      onboarding_completed: false
    })
    mockUIStore.showOnboarding = true

    renderApp(<App />)

    // Now onboarding should show because user is fully authenticated
    await waitFor(() => {
      expect(screen.queryByTestId('onboarding-wizard')).toBeInTheDocument()
    })
  })
})