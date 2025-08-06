import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import LoginPage from '../LoginPage'
import { useAuthStore } from '@/store/authStore'

// Mock the auth store
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn()
}))

// Mock react-router-dom navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

const mockUseAuthStore = vi.mocked(useAuthStore)

const renderLoginPage = () => {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  )
}

describe('LoginPage', () => {
  const mockLogin = vi.fn()
  const mockClearError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    
    mockUseAuthStore.mockReturnValue({
      login: mockLogin,
      clearError: mockClearError,
      isLoading: false,
      error: null,
      isAuthenticated: false,
      user: null,
      register: vi.fn(),
      logout: vi.fn(),
      updateUser: vi.fn(),
      updateProfile: vi.fn(),
      refreshUser: vi.fn(),
      initializeAuth: vi.fn()
    })
  })

  describe('Rendering', () => {
    it('should render login page with all elements', () => {
      renderLoginPage()
      
      expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument()
      expect(screen.getByText(/sign in to your real2\.ai account/i)).toBeInTheDocument()
      expect(screen.getByRole('form')).toBeInTheDocument()
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should render link to register page', () => {
      renderLoginPage()
      
      const registerLink = screen.getByRole('link', { name: /create account/i })
      expect(registerLink).toBeInTheDocument()
      expect(registerLink).toHaveAttribute('href', '/auth/register')
    })

    it('should render forgot password link', () => {
      renderLoginPage()
      
      const forgotPasswordLink = screen.getByRole('link', { name: /forgot your password/i })
      expect(forgotPasswordLink).toBeInTheDocument()
      expect(forgotPasswordLink).toHaveAttribute('href', '/auth/forgot-password')
    })

    it('should render company branding', () => {
      renderLoginPage()
      
      expect(screen.getByText('Real2.AI')).toBeInTheDocument()
      expect(screen.getByText(/ai-powered contract analysis/i)).toBeInTheDocument()
    })
  })

  describe('Form Interaction', () => {
    it('should allow user to type in email field', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const emailInput = screen.getByLabelText(/email/i)
      await user.type(emailInput, 'test@example.com')
      
      expect(emailInput).toHaveValue('test@example.com')
    })

    it('should allow user to type in password field', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const passwordInput = screen.getByLabelText(/password/i)
      await user.type(passwordInput, 'password123')
      
      expect(passwordInput).toHaveValue('password123')
    })

    it('should toggle password visibility', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const passwordInput = screen.getByLabelText(/password/i)
      const toggleButton = screen.getByRole('button', { name: /show password/i })
      
      expect(passwordInput).toHaveAttribute('type', 'password')
      
      await user.click(toggleButton)
      expect(passwordInput).toHaveAttribute('type', 'text')
      
      await user.click(toggleButton)
      expect(passwordInput).toHaveAttribute('type', 'password')
    })

    it('should handle remember me checkbox', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const rememberCheckbox = screen.getByLabelText(/remember me/i)
      expect(rememberCheckbox).not.toBeChecked()
      
      await user.click(rememberCheckbox)
      expect(rememberCheckbox).toBeChecked()
    })
  })

  describe('Form Submission', () => {
    it('should submit form with valid credentials', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123'
        })
      })
    })

    it('should show validation errors for empty fields', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('should show validation error for invalid email', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument()
      })
    })

    it('should disable submit button during loading', () => {
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        clearError: mockClearError,
        isLoading: true,
        error: null,
        isAuthenticated: false,
        user: null,
        register: vi.fn(),
        logout: vi.fn(),
        updateUser: vi.fn(),
        updateProfile: vi.fn(),
        refreshUser: vi.fn(),
        initializeAuth: vi.fn()
      })

      renderLoginPage()
      
      const submitButton = screen.getByRole('button', { name: /signing in/i })
      expect(submitButton).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('should display authentication error', () => {
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        clearError: mockClearError,
        isLoading: false,
        error: 'Invalid credentials',
        isAuthenticated: false,
        user: null,
        register: vi.fn(),
        logout: vi.fn(),
        updateUser: vi.fn(),
        updateProfile: vi.fn(),
        refreshUser: vi.fn(),
        initializeAuth: vi.fn()
      })

      renderLoginPage()
      
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('should clear error when user starts typing', async () => {
      const user = userEvent.setup()
      
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        clearError: mockClearError,
        isLoading: false,
        error: 'Invalid credentials',
        isAuthenticated: false,
        user: null,
        register: vi.fn(),
        logout: vi.fn(),
        updateUser: vi.fn(),
        updateProfile: vi.fn(),
        refreshUser: vi.fn(),
        initializeAuth: vi.fn()
      })

      renderLoginPage()
      
      const emailInput = screen.getByLabelText(/email/i)
      await user.type(emailInput, 'a')
      
      expect(mockClearError).toHaveBeenCalled()
    })
  })

  describe('Navigation', () => {
    it('should redirect to dashboard when already authenticated', () => {
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        clearError: mockClearError,
        isLoading: false,
        error: null,
        isAuthenticated: true,
        user: { id: '1', email: 'test@example.com' } as any,
        register: vi.fn(),
        logout: vi.fn(),
        updateUser: vi.fn(),
        updateProfile: vi.fn(),
        refreshUser: vi.fn(),
        initializeAuth: vi.fn()
      })

      renderLoginPage()
      
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })

    it('should navigate to dashboard after successful login', async () => {
      const user = userEvent.setup()
      
      // Mock successful login
      mockLogin.mockImplementation(async () => {
        // Simulate successful login by updating the store state
        mockUseAuthStore.mockReturnValue({
          login: mockLogin,
          clearError: mockClearError,
          isLoading: false,
          error: null,
          isAuthenticated: true,
          user: { id: '1', email: 'test@example.com' } as any,
          register: vi.fn(),
          logout: vi.fn(),
          updateUser: vi.fn(),
          updateProfile: vi.fn(),
          refreshUser: vi.fn(),
          initializeAuth: vi.fn()
        })
      })

      renderLoginPage()
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      renderLoginPage()
      
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument()
    })

    it('should have proper heading hierarchy', () => {
      renderLoginPage()
      
      const mainHeading = screen.getByRole('heading', { level: 1 })
      expect(mainHeading).toHaveTextContent(/welcome back/i)
    })

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup()
      renderLoginPage()
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.tab()
      expect(emailInput).toHaveFocus()
      
      await user.tab()
      expect(passwordInput).toHaveFocus()
      
      // Continue tabbing to reach submit button
      await user.tab()
      await user.tab()
      expect(submitButton).toHaveFocus()
    })

    it('should announce errors to screen readers', () => {
      mockUseAuthStore.mockReturnValue({
        login: mockLogin,
        clearError: mockClearError,
        isLoading: false,
        error: 'Invalid credentials',
        isAuthenticated: false,
        user: null,
        register: vi.fn(),
        logout: vi.fn(),
        updateUser: vi.fn(),
        updateProfile: vi.fn(),
        refreshUser: vi.fn(),
        initializeAuth: vi.fn()
      })

      renderLoginPage()
      
      const alert = screen.getByRole('alert')
      expect(alert).toHaveAttribute('aria-live', 'polite')
      expect(alert).toHaveTextContent('Invalid credentials')
    })
  })

  describe('SEO and Meta', () => {
    it('should have proper page title', () => {
      renderLoginPage()
      
      // This would typically be handled by a title management library like React Helmet
      expect(document.title).toContain('Login')
    })
  })
})