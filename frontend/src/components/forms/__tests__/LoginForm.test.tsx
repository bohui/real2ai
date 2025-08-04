/**
 * Test LoginForm component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { LoginForm } from '../LoginForm'

// Mock the auth store
vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    login: vi.fn(),
    isLoading: false,
    error: null,
  }),
}))

describe('LoginForm Component', () => {
  it('renders login form with required fields', () => {
    render(<LoginForm />)
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows validation errors for empty fields', async () => {
    render(<LoginForm />)
    
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    })
  })

  it('shows validation error for invalid email', async () => {
    render(<LoginForm />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
    })
  })

  it('submits form with valid data', async () => {
    const mockLogin = vi.fn().mockResolvedValue({})
    
    vi.mocked(vi.importActual('@/store/authStore')).useAuthStore.mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: null,
    })
    
    render(<LoginForm />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })

  it('shows loading state during submission', () => {
    vi.mocked(vi.importActual('@/store/authStore')).useAuthStore.mockReturnValue({
      login: vi.fn(),
      isLoading: true,
      error: null,
    })
    
    render(<LoginForm />)
    
    const submitButton = screen.getByRole('button', { name: /signing in/i })
    expect(submitButton).toBeDisabled()
  })

  it('displays authentication error', () => {
    vi.mocked(vi.importActual('@/store/authStore')).useAuthStore.mockReturnValue({
      login: vi.fn(),
      isLoading: false,
      error: 'Invalid credentials',
    })
    
    render(<LoginForm />)
    
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
  })

  it('has remember me checkbox', () => {
    render(<LoginForm />)
    
    const rememberCheckbox = screen.getByRole('checkbox', { name: /remember me/i })
    expect(rememberCheckbox).toBeInTheDocument()
    expect(rememberCheckbox).not.toBeChecked()
    
    fireEvent.click(rememberCheckbox)
    expect(rememberCheckbox).toBeChecked()
  })

  it('has forgot password link', () => {
    render(<LoginForm />)
    
    const forgotLink = screen.getByRole('link', { name: /forgot password/i })
    expect(forgotLink).toBeInTheDocument()
    expect(forgotLink).toHaveAttribute('href', '/auth/forgot-password')
  })

  it('has sign up link', () => {
    render(<LoginForm />)
    
    const signUpLink = screen.getByRole('link', { name: /sign up/i })
    expect(signUpLink).toBeInTheDocument()
    expect(signUpLink).toHaveAttribute('href', '/auth/register')
  })

  it('handles password visibility toggle', () => {
    render(<LoginForm />)
    
    const passwordInput = screen.getByLabelText(/password/i)
    const toggleButton = screen.getByRole('button', { name: /show password/i })
    
    expect(passwordInput).toHaveAttribute('type', 'password')
    
    fireEvent.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'text')
    
    fireEvent.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('prevents multiple submissions', async () => {
    const mockLogin = vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))
    
    vi.mocked(vi.importActual('@/store/authStore')).useAuthStore.mockReturnValue({
      login: mockLogin,
      isLoading: true,
      error: null,
    })
    
    render(<LoginForm />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button')
    
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    
    fireEvent.click(submitButton)
    fireEvent.click(submitButton)
    fireEvent.click(submitButton)
    
    expect(submitButton).toBeDisabled()
  })

  it('has proper accessibility attributes', () => {
    render(<LoginForm />)
    
    const form = screen.getByRole('form', { name: /sign in/i })
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    
    expect(form).toBeInTheDocument()
    expect(emailInput).toHaveAttribute('type', 'email')
    expect(emailInput).toHaveAttribute('autoComplete', 'email')
    expect(passwordInput).toHaveAttribute('type', 'password')
    expect(passwordInput).toHaveAttribute('autoComplete', 'current-password')
  })
})