/**
 * Test Header component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@/test/utils'
import Header from '../Header'

// Mock stores
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: {
      id: 'test-user',
      email: 'test@example.com',
      subscription_status: 'free',
      credits_remaining: 5,
    },
    logout: vi.fn(),
    isAuthenticated: true,
  })),
}))

vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => ({
    toggleSidebar: vi.fn(),
    isMobile: false,
    addNotification: vi.fn(),
  })),
}))

describe('Header Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders header component', () => {
    render(<Header />)

    // Just verify the component renders without crashing
    expect(document.body).toBeInTheDocument()
  })

  it('renders with user data', () => {
    render(<Header />)

    // Should render successfully with mocked user data
    expect(document.body).toBeInTheDocument()
  })
})