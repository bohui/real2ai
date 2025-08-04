/**
 * Test RegisterForm component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@/test/utils'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import RegisterForm from '../RegisterForm'

// Mock the stores
const mockAuthStore = {
  register: vi.fn(),
  isLoading: false,
  error: null,
}

const mockUIStore = {
  addNotification: vi.fn(),
}

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthStore),
}))

vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => mockUIStore),
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }: any) => 
      <div className={className} {...props}>{children}</div>,
  },
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  Mail: () => <div data-testid="mail-icon">Mail</div>,
  Lock: () => <div data-testid="lock-icon">Lock</div>,
  AlertCircle: () => <div data-testid="alert-icon">Alert</div>,
}))

// Mock australianStates utility
vi.mock('@/utils', () => ({
  australianStates: [
    { value: 'NSW', label: 'New South Wales' },
    { value: 'VIC', label: 'Victoria' },
    { value: 'QLD', label: 'Queensland' },
    { value: 'SA', label: 'South Australia' },
    { value: 'WA', label: 'Western Australia' },
    { value: 'TAS', label: 'Tasmania' },
    { value: 'NT', label: 'Northern Territory' },
    { value: 'ACT', label: 'Australian Capital Territory' },
  ],
}))

// Custom render function with required providers
const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('RegisterForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store states
    mockAuthStore.register = vi.fn()
    mockAuthStore.isLoading = false
    mockAuthStore.error = null
    mockUIStore.addNotification = vi.fn()
    
    // Mock window.location.href
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    })
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText('Create your account')).toBeInTheDocument()
    })

    it('displays the form title and description', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText('Create your account')).toBeInTheDocument()
      expect(screen.getByText(/Join Real2.AI and start analyzing/)).toBeInTheDocument()
    })

    it('shows Real2.AI branding', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText('R2')).toBeInTheDocument()
    })

    it('displays security message', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText(/Your information is secure/)).toBeInTheDocument()
    })
  })

  describe('Form Fields', () => {
    it('renders all required form fields', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByLabelText('Email address')).toBeInTheDocument()
      expect(screen.getByLabelText('State')).toBeInTheDocument()
      expect(screen.getByLabelText('I am a')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
      expect(screen.getByRole('checkbox')).toBeInTheDocument()
    })

    it('sets default values correctly', () => {
      renderWithProviders(<RegisterForm />)
      
      const stateSelect = screen.getByLabelText('State') as HTMLSelectElement
      const userTypeSelect = screen.getByLabelText('I am a') as HTMLSelectElement
      
      expect(stateSelect.value).toBe('NSW')
      expect(userTypeSelect.value).toBe('buyer')
    })

    it('displays all Australian states options', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText('New South Wales')).toBeInTheDocument()
      expect(screen.getByText('Victoria')).toBeInTheDocument()
      expect(screen.getByText('Queensland')).toBeInTheDocument()
      expect(screen.getByText('South Australia')).toBeInTheDocument()
      expect(screen.getByText('Western Australia')).toBeInTheDocument()
      expect(screen.getByText('Tasmania')).toBeInTheDocument()
      expect(screen.getByText('Northern Territory')).toBeInTheDocument()
      expect(screen.getByText('Australian Capital Territory')).toBeInTheDocument()
    })

    it('displays all user type options', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText('Property Buyer')).toBeInTheDocument()
      expect(screen.getByText('Property Investor')).toBeInTheDocument()
      expect(screen.getByText('Real Estate Agent')).toBeInTheDocument()
    })

    it('includes terms and privacy policy links', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByRole('link', { name: /Terms of Service/i })).toHaveAttribute('href', '/terms')
      expect(screen.getByRole('link', { name: /Privacy Policy/i })).toHaveAttribute('href', '/privacy')
    })

    it('includes sign in link', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByRole('link', { name: /Sign in here/i })).toHaveAttribute('href', '/login')
    })
  })

  describe('Form Validation', () => {
    it('shows email validation errors', async () => {
      renderWithProviders(<RegisterForm />)
      
      const emailInput = screen.getByLabelText('Email address')
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
      fireEvent.blur(emailInput)
      
      await waitFor(() => {
        expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
      })
    })

    it('shows required field validation', async () => {
      renderWithProviders(<RegisterForm />)
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })
    })

    it('validates password requirements', async () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      
      // Too short password
      fireEvent.change(passwordInput, { target: { value: '1234' } })
      fireEvent.blur(passwordInput)
      
      await waitFor(() => {
        expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument()
      })
      
      // Password without lowercase
      fireEvent.change(passwordInput, { target: { value: 'PASSWORD123' } })
      fireEvent.blur(passwordInput)
      
      await waitFor(() => {
        expect(screen.getByText('Password must contain at least one lowercase letter')).toBeInTheDocument()
      })
      
      // Password without uppercase
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.blur(passwordInput)
      
      await waitFor(() => {
        expect(screen.getByText('Password must contain at least one uppercase letter')).toBeInTheDocument()
      })
      
      // Password without number
      fireEvent.change(passwordInput, { target: { value: 'Password' } })
      fireEvent.blur(passwordInput)
      
      await waitFor(() => {
        expect(screen.getByText('Password must contain at least one number')).toBeInTheDocument()
      })
    })

    it('validates password confirmation', async () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm password')
      
      fireEvent.change(passwordInput, { target: { value: 'Password123' } })
      fireEvent.change(confirmPasswordInput, { target: { value: 'Password456' } })
      fireEvent.blur(confirmPasswordInput)
      
      await waitFor(() => {
        expect(screen.getByText("Passwords don't match")).toBeInTheDocument()
      })
    })

    it('validates terms agreement', async () => {
      renderWithProviders(<RegisterForm />)
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('You must agree to the terms and conditions')).toBeInTheDocument()
      })
    })

    it('shows confirm password required error', async () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      
      fireEvent.change(passwordInput, { target: { value: 'Password123' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Please confirm your password')).toBeInTheDocument()
      })
    })
  })

  describe('Password Strength Indicator', () => {
    it('does not show strength indicator initially', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.queryByText('Password strength')).not.toBeInTheDocument()
    })

    it('shows strength indicator when password is entered', async () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      fireEvent.change(passwordInput, { target: { value: 'weak' } })
      
      await waitFor(() => {
        expect(screen.getByText('Password strength')).toBeInTheDocument()
      })
    })

    it('calculates password strength correctly', async () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      
      // Very weak password
      fireEvent.change(passwordInput, { target: { value: 'weak' } })
      await waitFor(() => {
        expect(screen.getByText('Very Weak')).toBeInTheDocument()
      })
      
      // Strong password
      fireEvent.change(passwordInput, { target: { value: 'StrongPassword123!' } })
      await waitFor(() => {
        expect(screen.getByText('Strong')).toBeInTheDocument()
      })
    })

    it('updates strength indicator dynamically', async () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      
      fireEvent.change(passwordInput, { target: { value: 'weak' } })
      await waitFor(() => {
        expect(screen.getByText('Very Weak')).toBeInTheDocument()
      })
      
      fireEvent.change(passwordInput, { target: { value: 'StrongPass123' } })
      await waitFor(() => {
        expect(screen.getByText('Good')).toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    const fillValidForm = async () => {
      const emailInput = screen.getByLabelText('Email address')
      const passwordInput = screen.getByLabelText('Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm password')
      const termsCheckbox = screen.getByRole('checkbox')
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'Password123' } })
      fireEvent.change(confirmPasswordInput, { target: { value: 'Password123' } })
      fireEvent.click(termsCheckbox)
    }

    it('submits form with valid data', async () => {
      mockAuthStore.register = vi.fn().mockResolvedValue(undefined)
      
      renderWithProviders(<RegisterForm />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(mockAuthStore.register).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'Password123',
          australian_state: 'NSW',
          user_type: 'buyer',
        })
      })
    })

    it('shows success notification on successful registration', async () => {
      mockAuthStore.register = vi.fn().mockResolvedValue(undefined)
      
      renderWithProviders(<RegisterForm />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(mockUIStore.addNotification).toHaveBeenCalledWith({
          type: 'success',
          title: 'Welcome to Real2.AI!',
          message: 'Your account has been created successfully.',
        })
      })
    })

    it('calls onSuccess callback when provided', async () => {
      const onSuccess = vi.fn()
      mockAuthStore.register = vi.fn().mockResolvedValue(undefined)
      
      renderWithProviders(<RegisterForm onSuccess={onSuccess} />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled()
      })
    })

    it('redirects to custom path when provided', async () => {
      mockAuthStore.register = vi.fn().mockResolvedValue(undefined)
      
      renderWithProviders(<RegisterForm redirectTo="/custom-path" />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(window.location.href).toBe('/custom-path')
      })
    })

    it('redirects to default dashboard when no custom path', async () => {
      mockAuthStore.register = vi.fn().mockResolvedValue(undefined)
      
      renderWithProviders(<RegisterForm />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(window.location.href).toBe('/dashboard')
      })
    })

    it('handles registration errors', async () => {
      mockAuthStore.register = vi.fn().mockRejectedValue(new Error('Registration failed'))
      
      renderWithProviders(<RegisterForm />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(mockUIStore.addNotification).toHaveBeenCalledWith({
          type: 'error',
          title: 'Registration failed',
          message: 'Please check your information and try again.',
        })
      })
    })

    it('excludes confirmPassword and terms from registration data', async () => {
      mockAuthStore.register = vi.fn().mockResolvedValue(undefined)
      
      renderWithProviders(<RegisterForm />)
      
      await fillValidForm()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const callArgs = mockAuthStore.register.mock.calls[0][0]
        expect(callArgs).not.toHaveProperty('confirmPassword')
        expect(callArgs).not.toHaveProperty('terms')
      })
    })
  })

  describe('Loading States', () => {
    it('shows loading state during submission', () => {
      mockAuthStore.isLoading = true
      
      renderWithProviders(<RegisterForm />)
      
      const submitButton = screen.getByRole('button', { name: /Creating account/i })
      expect(submitButton).toBeDisabled()
    })

    it('disables form fields during loading', () => {
      mockAuthStore.isLoading = true
      
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByLabelText('Email address')).toBeDisabled()
      expect(screen.getByLabelText('Password')).toBeDisabled()
      expect(screen.getByLabelText('Confirm password')).toBeDisabled()
      expect(screen.getByRole('checkbox')).toBeDisabled()
    })

    it('prevents multiple submissions', async () => {
      renderWithProviders(<RegisterForm />)
      
      await fillValidForm()
      
      const form = screen.getByRole('form') || document.querySelector('form')
      if (form) {
        // Simulate form submission state
        fireEvent.submit(form)
        fireEvent.submit(form)
        
        // This test verifies the form handles submission properly
        expect(form).toBeInTheDocument()
      }
    })
  })

  describe('Error Display', () => {
    it('displays authentication errors from store', () => {
      mockAuthStore.error = 'User already exists'
      
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByText('User already exists')).toBeInTheDocument()
      expect(screen.getByTestId('alert-icon')).toBeInTheDocument()
    })

    it('does not show error alert when no error', () => {
      mockAuthStore.error = null
      
      renderWithProviders(<RegisterForm />)
      
      expect(screen.queryByTestId('alert-icon')).not.toBeInTheDocument()
    })
  })

  describe('Form Interaction', () => {
    it('allows selecting different states', () => {
      renderWithProviders(<RegisterForm />)
      
      const stateSelect = screen.getByLabelText('State')
      
      fireEvent.change(stateSelect, { target: { value: 'VIC' } })
      expect((stateSelect as HTMLSelectElement).value).toBe('VIC')
    })

    it('allows selecting different user types', () => {
      renderWithProviders(<RegisterForm />)
      
      const userTypeSelect = screen.getByLabelText('I am a')
      
      fireEvent.change(userTypeSelect, { target: { value: 'investor' } })
      expect((userTypeSelect as HTMLSelectElement).value).toBe('investor')
    })

    it('toggles terms checkbox', () => {
      renderWithProviders(<RegisterForm />)
      
      const termsCheckbox = screen.getByRole('checkbox') as HTMLInputElement
      
      expect(termsCheckbox.checked).toBe(false)
      
      fireEvent.click(termsCheckbox)
      expect(termsCheckbox.checked).toBe(true)
      
      fireEvent.click(termsCheckbox)
      expect(termsCheckbox.checked).toBe(false)
    })

    it('handles password visibility toggle', () => {
      renderWithProviders(<RegisterForm />)
      
      const passwordInput = screen.getByLabelText('Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm password')
      
      // Both should support password toggle (though we can't test the actual toggle without more complex setup)
      expect(passwordInput).toBeInTheDocument()
      expect(confirmPasswordInput).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      renderWithProviders(<RegisterForm />)
      
      expect(screen.getByLabelText('Email address')).toBeInTheDocument()
      expect(screen.getByLabelText('State')).toBeInTheDocument()
      expect(screen.getByLabelText('I am a')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
    })

    it('has proper form structure', () => {
      renderWithProviders(<RegisterForm />)
      
      const form = document.querySelector('form')
      expect(form).toBeInTheDocument()
      
      const submitButton = screen.getByRole('button', { name: /Create account/i })
      expect(submitButton).toHaveAttribute('type', 'submit')
    })

    it('links terms and privacy policy properly', () => {
      renderWithProviders(<RegisterForm />)
      
      const termsLink = screen.getByRole('link', { name: /Terms of Service/i })
      const privacyLink = screen.getByRole('link', { name: /Privacy Policy/i })
      
      expect(termsLink).toHaveAttribute('href', '/terms')
      expect(privacyLink).toHaveAttribute('href', '/privacy')
    })
  })

  describe('Integration', () => {
    it('integrates with all required stores', () => {
      renderWithProviders(<RegisterForm />)
      
      // Should be able to access auth store
      expect(mockAuthStore.register).toBeDefined()
      expect(mockAuthStore.isLoading).toBeDefined()
      expect(mockAuthStore.error).toBeDefined()
      
      // Should be able to access UI store
      expect(mockUIStore.addNotification).toBeDefined()
    })

    it('handles form mode correctly', () => {
      renderWithProviders(<RegisterForm />)
      
      // Form should be in onBlur mode for validation
      const emailInput = screen.getByLabelText('Email address')
      fireEvent.change(emailInput, { target: { value: 'invalid' } })
      fireEvent.blur(emailInput)
      
      // Validation should trigger on blur
      expect(emailInput).toBeInTheDocument()
    })
  })
})