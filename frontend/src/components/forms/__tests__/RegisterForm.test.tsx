/**
 * Test RegisterForm component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@/test/utils'
import RegisterForm from '../RegisterForm'

// Mock API service
vi.mock('@/services/api', () => ({
  apiService: {
    register: vi.fn(),
  },
}))

// Mock auth store
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    register: vi.fn(),
    error: null,
    isLoading: false,
  })),
}))

// Mock UI store
vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => ({
    addNotification: vi.fn(),
  })),
}))

describe('RegisterForm Component', () => {
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders registration form', () => {
    render(<RegisterForm onSuccess={mockOnSuccess} />)

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/state/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/i am a/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('renders component without crashing', () => {
    render(<RegisterForm onSuccess={mockOnSuccess} />)
    
    // Component should render successfully
    expect(document.body).toBeInTheDocument()
  })
})