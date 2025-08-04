/**
 * Test ProfessionalInput component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@/test/utils'
import { render } from '@testing-library/react'
import Input from '../ProfessionalInput'

// Mock utils
vi.mock('@/utils', () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  Eye: ({ className }: any) => <div data-testid="eye-icon" className={className}>Eye</div>,
  EyeOff: ({ className }: any) => <div data-testid="eye-off-icon" className={className}>EyeOff</div>,
  Search: ({ className }: any) => <div data-testid="search-icon" className={className}>Search</div>,
  AlertCircle: ({ className }: any) => <div data-testid="alert-circle-icon" className={className}>AlertCircle</div>,
  CheckCircle: ({ className }: any) => <div data-testid="check-circle-icon" className={className}>CheckCircle</div>,
}))

describe('ProfessionalInput Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<Input />)
      
      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
    })

    it('renders with default props', () => {
      render(<Input placeholder="Enter text" />)
      
      const input = screen.getByPlaceholderText('Enter text')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'text')
    })

    it('has proper container structure', () => {
      render(<Input />)
      
      const container = document.querySelector('.space-y-2')
      expect(container).toBeInTheDocument()
      
      const inputContainer = document.querySelector('.relative')
      expect(inputContainer).toBeInTheDocument()
    })
  })

  describe('Label Functionality', () => {
    it('renders label when provided', () => {
      render(<Input label="Email Address" />)
      
      const label = screen.getByText('Email Address')
      expect(label).toBeInTheDocument()
      expect(label.tagName).toBe('LABEL')
      expect(label).toHaveClass('block', 'text-sm', 'font-medium', 'text-neutral-700')
    })

    it('does not render label when not provided', () => {
      render(<Input />)
      
      const label = document.querySelector('label')
      expect(label).not.toBeInTheDocument()
    })

    it('shows required asterisk when required prop is true', () => {
      render(<Input label="Required Field" required />)
      
      const asterisk = document.querySelector('.text-danger-500.ml-1')
      expect(asterisk).toBeInTheDocument()
      expect(asterisk).toHaveTextContent('*')
    })

    it('does not show asterisk when not required', () => {
      render(<Input label="Optional Field" />)
      
      const asterisk = document.querySelector('.text-danger-500.ml-1')
      expect(asterisk).not.toBeInTheDocument()
    })
  })

  describe('Input Types and Basic Props', () => {
    it('renders different input types correctly', () => {
      const { rerender } = render(<Input type="email" />)
      expect(screen.getByRole('textbox')).toHaveAttribute('type', 'email')
      
      rerender(<Input type="password" />)
      expect(document.querySelector('input')).toHaveAttribute('type', 'password')
      
      rerender(<Input type="number" />)
      expect(document.querySelector('input')).toHaveAttribute('type', 'number')
    })

    it('forwards standard input props correctly', () => {
      render(
        <Input
          placeholder="Test placeholder"
          value="test value"
          name="test-input"
          id="test-id"
          maxLength={50}
          readOnly
        />
      )
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveAttribute('placeholder', 'Test placeholder')
      expect(input).toHaveValue('test value')
      expect(input).toHaveAttribute('name', 'test-input')
      expect(input).toHaveAttribute('id', 'test-id')
      expect(input).toHaveAttribute('maxLength', '50')
      expect(input).toHaveAttribute('readOnly')
    })

    it('handles disabled state correctly', () => {
      render(<Input disabled />)
      
      const input = screen.getByRole('textbox')
      expect(input).toBeDisabled()
      expect(input).toHaveClass('cursor-not-allowed')
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('opacity-50', 'cursor-not-allowed', 'bg-neutral-100')
    })
  })

  describe('Variants and Styling', () => {
    it('applies default variant styling', () => {
      render(<Input />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('rounded-lg')
    })

    it('applies search variant styling', () => {
      render(<Input variant="search" />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('rounded-full')
      
      // Should have search icon
      expect(screen.getByTestId('search-icon')).toBeInTheDocument()
    })

    it('applies legal variant styling', () => {
      render(<Input variant="legal" />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('rounded-lg', 'border-l-4', 'border-l-trust-500')
    })

    it('shows search icon for search variant when no left icon', () => {
      render(<Input variant="search" />)
      
      expect(screen.getByTestId('search-icon')).toBeInTheDocument()
      expect(screen.getByTestId('search-icon')).toHaveClass('w-4', 'h-4')
    })

    it('does not show search icon when left icon is provided', () => {
      const customIcon = <div data-testid="custom-icon">Custom</div>
      render(<Input variant="search" leftIcon={customIcon} />)
      
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('search-icon')).not.toBeInTheDocument()
    })
  })

  describe('State Management and Visual States', () => {
    it('shows default state styling', () => {
      render(<Input />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('border-neutral-200', 'hover:border-neutral-300', 'bg-white')
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('text-neutral-900', 'placeholder-neutral-500')
    })

    it('shows focus state when input is focused', async () => {
      render(<Input />)
      
      const input = screen.getByRole('textbox')
      fireEvent.focus(input)
      
      await waitFor(() => {
        const container = document.querySelector('.relative.flex.items-center.border-2')
        expect(container).toHaveClass('border-primary-300', 'ring-primary-500/20', 'bg-primary-50/30', 'ring-4')
      })
    })

    it('removes focus state when input is blurred', async () => {
      render(<Input />)
      
      const input = screen.getByRole('textbox')
      fireEvent.focus(input)
      fireEvent.blur(input)
      
      await waitFor(() => {
        const container = document.querySelector('.relative.flex.items-center.border-2')
        expect(container).toHaveClass('border-neutral-200', 'hover:border-neutral-300', 'bg-white')
        expect(container).not.toHaveClass('ring-4')
      })
    })

    it('shows error state when error prop is provided', () => {
      render(<Input error="This field is required" />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('border-danger-300', 'ring-danger-500/20', 'bg-danger-50/50')
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('text-danger-900', 'placeholder-danger-400')
    })

    it('shows success state when success prop is provided', () => {
      render(<Input success="Valid input" />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('border-success-300', 'ring-success-500/20', 'bg-success-50/50')
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('text-success-900', 'placeholder-success-400')
    })

    it('shows error state when state prop is "error"', () => {
      render(<Input state="error" />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('border-danger-300', 'ring-danger-500/20', 'bg-danger-50/50')
    })

    it('shows success state when state prop is "success"', () => {
      render(<Input state="success" />)
      
      const container = document.querySelector('.relative.flex.items-center.border-2')
      expect(container).toHaveClass('border-success-300', 'ring-success-500/20', 'bg-success-50/50')
    })
  })

  describe('Icons and Visual Elements', () => {
    it('renders left icon correctly', () => {
      const leftIcon = <div data-testid="custom-left-icon">Left</div>
      render(<Input leftIcon={leftIcon} />)
      
      expect(screen.getByTestId('custom-left-icon')).toBeInTheDocument()
      
      const iconContainer = document.querySelector('.flex.items-center.justify-center.w-10.h-10')
      expect(iconContainer).toBeInTheDocument()
    })

    it('renders right icon correctly', () => {
      const rightIcon = <div data-testid="custom-right-icon">Right</div>
      render(<Input rightIcon={rightIcon} />)
      
      expect(screen.getByTestId('custom-right-icon')).toBeInTheDocument()
    })

    it('adjusts input padding when left icon is present', () => {
      const leftIcon = <div data-testid="left-icon">Left</div>
      render(<Input leftIcon={leftIcon} />)
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('pl-0')
      expect(input).not.toHaveClass('pl-3')
    })

    it('adjusts input padding when right elements are present', () => {
      render(<Input rightIcon={<div>Right</div>} />)
      
      const input = screen.getByRole('textbox')
      expect(input).toHaveClass('pr-0')
      expect(input).not.toHaveClass('pr-3')
    })

    it('shows state icons correctly', () => {
      const { rerender } = render(<Input error="Error message" />)
      expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
      expect(screen.getByTestId('alert-circle-icon')).toHaveClass('w-4', 'h-4', 'text-danger-500')
      
      rerender(<Input success="Success message" />)
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
      expect(screen.getByTestId('check-circle-icon')).toHaveClass('w-4', 'h-4', 'text-success-500')
    })

    it('shows state icons based on state prop', () => {
      const { rerender } = render(<Input state="error" />)
      expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
      
      rerender(<Input state="success" />)
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
    })
  })

  describe('Password Toggle Functionality', () => {
    it('shows password toggle button when showPasswordToggle is true and type is password', () => {
      render(<Input type="password" showPasswordToggle />)
      
      const toggleButton = screen.getByRole('button')
      expect(toggleButton).toBeInTheDocument()
      expect(screen.getByTestId('eye-icon')).toBeInTheDocument()
    })

    it('does not show password toggle for non-password inputs', () => {
      render(<Input type="text" showPasswordToggle />)
      
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
      expect(screen.queryByTestId('eye-icon')).not.toBeInTheDocument()
    })

    it('toggles password visibility when toggle button is clicked', () => {
      render(<Input type="password" showPasswordToggle />)
      
      const input = document.querySelector('input')
      const toggleButton = screen.getByRole('button')
      
      // Initially should be password type
      expect(input).toHaveAttribute('type', 'password')
      expect(screen.getByTestId('eye-icon')).toBeInTheDocument()
      
      // Click to show password
      fireEvent.click(toggleButton)
      
      expect(input).toHaveAttribute('type', 'text')
      expect(screen.getByTestId('eye-off-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('eye-icon')).not.toBeInTheDocument()
      
      // Click to hide password again
      fireEvent.click(toggleButton)
      
      expect(input).toHaveAttribute('type', 'password')
      expect(screen.getByTestId('eye-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('eye-off-icon')).not.toBeInTheDocument()
    })

    it('applies correct styling to password toggle button', () => {
      render(<Input type="password" showPasswordToggle />)
      
      const toggleButton = screen.getByRole('button')
      expect(toggleButton).toHaveClass('p-1', 'hover:bg-neutral-100', 'rounded', 'transition-colors')
    })

    it('maintains focus state styling on password toggle', () => {
      render(<Input type="password" showPasswordToggle />)
      
      const input = screen.getByRole('textbox')
      fireEvent.focus(input)
      
      const toggleButton = screen.getByRole('button')
      expect(toggleButton).toHaveClass('text-primary-500')
    })
  })

  describe('Helper Text and Messages', () => {
    it('displays error message when error prop is provided', () => {
      render(<Input error="This field is required" />)
      
      const errorMessage = screen.getByText('This field is required')
      expect(errorMessage).toBeInTheDocument()
      expect(errorMessage).toHaveClass('text-sm', 'text-danger-600')
      expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
    })

    it('displays success message when success prop is provided', () => {
      render(<Input success="Valid input" />)
      
      const successMessage = screen.getByText('Valid input')
      expect(successMessage).toBeInTheDocument()
      expect(successMessage).toHaveClass('text-sm', 'text-success-600')
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
    })

    it('displays hint message when hint prop is provided and no error/success', () => {
      render(<Input hint="Enter your email address" />)
      
      const hintMessage = screen.getByText('Enter your email address')
      expect(hintMessage).toBeInTheDocument()
      expect(hintMessage).toHaveClass('text-sm', 'text-neutral-500')
    })

    it('prioritizes error message over success and hint', () => {
      render(
        <Input 
          error="Error message"
          success="Success message"
          hint="Hint message"
        />
      )
      
      expect(screen.getByText('Error message')).toBeInTheDocument()
      expect(screen.queryByText('Success message')).not.toBeInTheDocument()
      expect(screen.queryByText('Hint message')).not.toBeInTheDocument()
    })

    it('prioritizes success message over hint when no error', () => {
      render(
        <Input 
          success="Success message"
          hint="Hint message"
        />
      )
      
      expect(screen.getByText('Success message')).toBeInTheDocument()
      expect(screen.queryByText('Hint message')).not.toBeInTheDocument()
    })

    it('maintains minimum height for helper text area', () => {
      render(<Input />)
      
      const helperTextContainer = document.querySelector('.min-h-\\[1\\.25rem\\]')
      expect(helperTextContainer).toBeInTheDocument()
    })

    it('includes icons in helper text messages', () => {
      const { rerender } = render(<Input error="Error message" />)
      
      const errorContainer = screen.getByText('Error message').closest('p')
      expect(errorContainer).toHaveClass('flex', 'items-center', 'gap-1')
      
      const errorIcon = errorContainer?.querySelector('[data-testid="alert-circle-icon"]')
      expect(errorIcon).toBeInTheDocument()
      expect(errorIcon).toHaveClass('w-3', 'h-3', 'flex-shrink-0', 'mt-0.5')
      
      rerender(<Input success="Success message" />)
      
      const successContainer = screen.getByText('Success message').closest('p')
      const successIcon = successContainer?.querySelector('[data-testid="check-circle-icon"]')
      expect(successIcon).toBeInTheDocument()
      expect(successIcon).toHaveClass('w-3', 'h-3', 'flex-shrink-0', 'mt-0.5')
    })
  })

  describe('Focus and Interaction Handling', () => {
    it('handles focus and blur events correctly', () => {
      const onFocus = vi.fn()
      const onBlur = vi.fn()
      
      render(<Input onFocus={onFocus} onBlur={onBlur} />)
      
      const input = screen.getByRole('textbox')
      
      fireEvent.focus(input)
      expect(onFocus).toHaveBeenCalledTimes(1)
      
      fireEvent.blur(input)
      expect(onBlur).toHaveBeenCalledTimes(1)
    })

    it('handles change events correctly', () => {
      const onChange = vi.fn()
      
      render(<Input onChange={onChange} />)
      
      const input = screen.getByRole('textbox')
      fireEvent.change(input, { target: { value: 'test value' } })
      
      expect(onChange).toHaveBeenCalledTimes(1)
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
        target: expect.objectContaining({ value: 'test value' })
      }))
    })

    it('prevents interaction when disabled', () => {
      const onChange = vi.fn()
      const onFocus = vi.fn()
      
      render(<Input disabled onChange={onChange} onFocus={onFocus} />)
      
      const input = screen.getByRole('textbox')
      
      fireEvent.change(input, { target: { value: 'test' } })
      fireEvent.focus(input)
      
      expect(onChange).not.toHaveBeenCalled()
      expect(onFocus).not.toHaveBeenCalled()
    })
  })

  describe('Ref Forwarding', () => {
    it('forwards ref to input element correctly', () => {
      const ref = { current: null }
      
      render(<Input ref={ref} />)
      
      expect(ref.current).not.toBeNull()
      expect(ref.current).toBeInstanceOf(HTMLInputElement)
    })

    it('allows programmatic focus via ref', () => {
      const ref = { current: null }
      
      render(<Input ref={ref} />)
      
      if (ref.current) {
        ref.current.focus()
        expect(document.activeElement).toBe(ref.current)
      }
    })
  })

  describe('Custom Styling and Classes', () => {
    it('applies custom className to input container', () => {
      render(<Input className="custom-input-class" />)
      
      const container = document.querySelector('.custom-input-class')
      expect(container).toBeInTheDocument()
    })

    it('combines custom classes with default styling', () => {
      render(<Input className="custom-class" error="Error" />)
      
      const container = document.querySelector('.custom-class')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('border-danger-300', 'ring-danger-500/20', 'bg-danger-50/50')
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('handles undefined props gracefully', () => {
      render(<Input label={undefined} error={undefined} success={undefined} />)
      
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('handles empty string values for text props', () => {
      render(<Input label="" error="" success="" hint="" />)
      
      expect(screen.getByRole('textbox')).toBeInTheDocument()
      expect(screen.queryByText('')).not.toBeInTheDocument()
    })

    it('handles complex children in icons', () => {
      const complexIcon = (
        <div>
          <span>Icon</span>
          <div>Complex</div>
        </div>
      )
      
      render(<Input leftIcon={complexIcon} />)
      
      expect(screen.getByText('Icon')).toBeInTheDocument()
      expect(screen.getByText('Complex')).toBeInTheDocument()
    })

    it('maintains proper layout with all elements present', () => {
      render(
        <Input
          label="Complex Input"
          leftIcon={<div data-testid="left">L</div>}
          rightIcon={<div data-testid="right">R</div>}
          type="password"
          showPasswordToggle
          error="Error message"
          required
        />
      )
      
      expect(screen.getByText('Complex Input')).toBeInTheDocument()
      expect(screen.getByText('*')).toBeInTheDocument()
      expect(screen.getByTestId('left')).toBeInTheDocument()
      expect(screen.getByTestId('right')).toBeInTheDocument()
      expect(screen.getByRole('button')).toBeInTheDocument() // Password toggle
      expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument() // Error state icon
      expect(screen.getByText('Error message')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('associates label with input correctly', () => {
      render(<Input label="Email" id="email-input" />)
      
      const label = screen.getByText('Email')
      const input = screen.getByRole('textbox')
      
      expect(label.tagName).toBe('LABEL')
      expect(input).toHaveAttribute('id', 'email-input')
    })

    it('provides accessible password toggle button', () => {
      render(<Input type="password" showPasswordToggle />)
      
      const toggleButton = screen.getByRole('button')
      expect(toggleButton).toHaveAttribute('type', 'button')
    })

    it('maintains focus management correctly', () => {
      render(<Input type="password" showPasswordToggle />)
      
      const input = screen.getByRole('textbox')
      const toggleButton = screen.getByRole('button')
      
      input.focus()
      expect(document.activeElement).toBe(input)
      
      toggleButton.click()
      // Focus should remain on input after toggle
      expect(document.activeElement).toBe(input)
    })

    it('provides semantic structure for error messages', () => {
      render(<Input error="Field is required" />)
      
      const errorMessage = screen.getByText('Field is required')
      expect(errorMessage.tagName).toBe('P')
      expect(errorMessage).toHaveClass('text-sm', 'text-danger-600', 'flex', 'items-center', 'gap-1')
    })
  })

  describe('Display Name', () => {
    it('has correct display name for debugging', () => {
      expect(Input.displayName).toBe('Input')
    })
  })
})