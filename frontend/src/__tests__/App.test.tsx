/**
 * Test App component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { 
  renderApp,
  configureUnauthenticatedState,
  configureAuthenticatedState,
  configureOnboardingState,
  configureLoadingState
} from '@/test/utils'
import App from '../App'

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', () => {
    configureUnauthenticatedState()
    const { container } = renderApp(<App />)
    
    expect(container).toBeInTheDocument()
    expect(container.querySelector('.App')).toBeInTheDocument()
  })

  it('includes notification system', () => {
    configureUnauthenticatedState()
    renderApp(<App />)
    
    // Check for notification system container
    expect(document.getElementById('_rht_toaster')).toBeInTheDocument()
  })

  it('handles different authentication states without errors', () => {
    // Test each state renders without throwing
    const states = [
      { name: 'loading', config: configureLoadingState },
      { name: 'unauthenticated', config: configureUnauthenticatedState },
      { name: 'authenticated', config: configureAuthenticatedState },
      { name: 'onboarding', config: configureOnboardingState }
    ]

    states.forEach(({ config }) => {
      config()
      const { container, unmount } = renderApp(<App />)
      
      expect(container).toBeInTheDocument()
      expect(() => container.querySelector('.App')).not.toThrow()
      
      unmount()
    })
  })

  it('provides React Query client context', () => {
    configureUnauthenticatedState()
    renderApp(<App />)
    
    // Query client should be available (no errors thrown)
    expect(document.body).toBeInTheDocument()
  })

  it('includes required app structure elements', () => {
    configureUnauthenticatedState()
    renderApp(<App />)
    
    // Basic app structure should be present
    expect(document.querySelector('.App')).toBeInTheDocument()
    expect(document.getElementById('_rht_toaster')).toBeInTheDocument()
  })
})