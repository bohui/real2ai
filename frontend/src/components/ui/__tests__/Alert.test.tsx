/**
 * Test Alert component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@/test/utils'
import { render } from '@testing-library/react'
import Alert from '../Alert'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }: any) => 
      <div className={className} {...props}>{children}</div>,
  },
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  CheckCircle: ({ className }: any) => <div data-testid="check-circle-icon" className={className}>CheckCircle</div>,
  AlertTriangle: ({ className }: any) => <div data-testid="alert-triangle-icon" className={className}>AlertTriangle</div>,
  XCircle: ({ className }: any) => <div data-testid="x-circle-icon" className={className}>XCircle</div>,
  Info: ({ className }: any) => <div data-testid="info-icon" className={className}>Info</div>,
  Shield: ({ className }: any) => <div data-testid="shield-icon" className={className}>Shield</div>,
  AlertCircle: ({ className }: any) => <div data-testid="alert-circle-icon" className={className}>AlertCircle</div>,
  X: ({ className }: any) => <div data-testid="x-icon" className={className}>X</div>,
}))

describe('Alert Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<Alert />)
      
      expect(document.querySelector('[role="alert"]')).toBeInTheDocument()
    })

    it('has proper accessibility role', () => {
      render(<Alert />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toBeInTheDocument()
    })

    it('applies default props correctly', () => {
      render(<Alert />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('rounded-lg', 'border', 'transition-all', 'duration-200')
      expect(screen.getByTestId('info-icon')).toBeInTheDocument() // Default type is 'info'
    })
  })

  describe('Alert Types', () => {
    it('renders success alert correctly', () => {
      render(<Alert type="success" title="Success" description="Operation completed" />)
      
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
      expect(screen.getByText('Success')).toBeInTheDocument()
      expect(screen.getByText('Operation completed')).toBeInTheDocument()
    })

    it('renders warning alert correctly', () => {
      render(<Alert type="warning" title="Warning" description="Please review" />)
      
      expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument()
      expect(screen.getByText('Warning')).toBeInTheDocument()
      expect(screen.getByText('Please review')).toBeInTheDocument()
    })

    it('renders danger alert correctly', () => {
      render(<Alert type="danger" title="Error" description="Something went wrong" />)
      
      expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument()
      expect(screen.getByText('Error')).toBeInTheDocument()
      expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    })

    it('renders info alert correctly', () => {
      render(<Alert type="info" title="Information" description="For your reference" />)
      
      expect(screen.getByTestId('info-icon')).toBeInTheDocument()
      expect(screen.getByText('Information')).toBeInTheDocument()
      expect(screen.getByText('For your reference')).toBeInTheDocument()
    })

    it('renders legal alert correctly', () => {
      render(<Alert type="legal" title="Legal Notice" description="Important legal information" />)
      
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      expect(screen.getByText('Legal Notice')).toBeInTheDocument()
      expect(screen.getByText('Important legal information')).toBeInTheDocument()
    })

    it('renders compliance alert correctly', () => {
      render(<Alert type="compliance" title="Compliance" description="Regulatory requirement" />)
      
      expect(screen.getByTestId('alert-circle-icon')).toBeInTheDocument()
      expect(screen.getByText('Compliance')).toBeInTheDocument()
      expect(screen.getByText('Regulatory requirement')).toBeInTheDocument()
    })
  })

  describe('Alert Variants', () => {
    it('renders filled variant correctly', () => {
      render(<Alert type="success" variant="filled" title="Success" />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-success-500', 'text-white', 'border-success-500')
      
      const icon = screen.getByTestId('check-circle-icon')
      expect(icon).toHaveClass('text-white')
    })

    it('renders outlined variant correctly', () => {
      render(<Alert type="success" variant="outlined" title="Success" />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-white', 'text-success-700', 'border-success-500', 'border-2')
      
      const icon = screen.getByTestId('check-circle-icon')
      expect(icon).toHaveClass('text-success-500')
    })

    it('renders subtle variant correctly', () => {
      render(<Alert type="success" variant="subtle" title="Success" />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-success-50', 'text-success-800', 'border-success-200')
      
      const icon = screen.getByTestId('check-circle-icon')
      expect(icon).toHaveClass('text-success-600')
    })

    it('renders minimal variant correctly', () => {
      render(<Alert type="success" variant="minimal" title="Success" />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('bg-transparent', 'text-success-700', 'p-2')
      
      const icon = screen.getByTestId('check-circle-icon')
      expect(icon).toHaveClass('text-success-500')
    })
  })

  describe('Content Rendering', () => {
    it('renders title only when provided', () => {
      render(<Alert title="Test Title" />)
      
      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test Title')).toHaveClass('font-semibold', 'mb-1', 'text-sm', 'leading-tight')
    })

    it('renders description only when provided', () => {
      render(<Alert description="Test description" />)
      
      expect(screen.getByText('Test description')).toBeInTheDocument()
      expect(screen.getByText('Test description')).toHaveClass('text-sm', 'leading-relaxed', 'opacity-90')
    })

    it('renders both title and description', () => {
      render(<Alert title="Test Title" description="Test description" />)
      
      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test description')).toBeInTheDocument()
    })

    it('renders children content', () => {
      render(
        <Alert title="Test Title">
          <div data-testid="custom-content">Custom content</div>
        </Alert>
      )
      
      expect(screen.getByTestId('custom-content')).toBeInTheDocument()
      expect(screen.getByText('Custom content')).toBeInTheDocument()
    })

    it('renders without title or description', () => {
      render(<Alert />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toBeInTheDocument()
      expect(screen.getByTestId('info-icon')).toBeInTheDocument()
    })
  })

  describe('Custom Icons', () => {
    it('uses custom icon when provided', () => {
      const CustomIcon = () => <div data-testid="custom-icon">Custom</div>
      
      render(<Alert icon={<CustomIcon />} />)
      
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument()
      expect(screen.queryByTestId('info-icon')).not.toBeInTheDocument()
    })

    it('uses default icon when custom icon is not provided', () => {
      render(<Alert type="warning" />)
      
      expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('renders action buttons when provided', () => {
      const actions = (
        <div>
          <button data-testid="action-1">Action 1</button>
          <button data-testid="action-2">Action 2</button>
        </div>
      )
      
      render(<Alert title="Test" actions={actions} />)
      
      expect(screen.getByTestId('action-1')).toBeInTheDocument()
      expect(screen.getByTestId('action-2')).toBeInTheDocument()
    })

    it('does not render actions section when not provided', () => {
      render(<Alert title="Test" />)
      
      // Actions container should not exist
      const actionContainer = document.querySelector('.mt-3.flex.items-center.gap-2')
      expect(actionContainer).not.toBeInTheDocument()
    })
  })

  describe('Dismissible Functionality', () => {
    it('shows dismiss button when dismissible is true', () => {
      const onDismiss = vi.fn()
      
      render(<Alert title="Test" dismissible onDismiss={onDismiss} />)
      
      expect(screen.getByTestId('x-icon')).toBeInTheDocument()
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('does not show dismiss button when dismissible is false', () => {
      render(<Alert title="Test" dismissible={false} />)
      
      expect(screen.queryByTestId('x-icon')).not.toBeInTheDocument()
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('calls onDismiss when dismiss button is clicked', () => {
      const onDismiss = vi.fn()
      
      render(<Alert title="Test" dismissible onDismiss={onDismiss} />)
      
      const dismissButton = screen.getByRole('button')
      fireEvent.click(dismissButton)
      
      expect(onDismiss).toHaveBeenCalledTimes(1)
    })

    it('has proper accessibility for dismiss button', () => {
      const onDismiss = vi.fn()
      
      render(<Alert title="Test" dismissible onDismiss={onDismiss} />)
      
      const dismissButton = screen.getByRole('button')
      expect(dismissButton).toBeInTheDocument()
      
      const srText = screen.getByText('Dismiss')
      expect(srText).toHaveClass('sr-only')
    })

    it('applies correct styles to dismiss button for filled variant', () => {
      const onDismiss = vi.fn()
      
      render(<Alert type="success" variant="filled" title="Test" dismissible onDismiss={onDismiss} />)
      
      const dismissButton = screen.getByRole('button')
      expect(dismissButton).toHaveClass('text-white', 'hover:bg-white/20')
    })

    it('applies correct styles to dismiss button for non-filled variants', () => {
      const onDismiss = vi.fn()
      
      render(<Alert type="success" variant="subtle" title="Test" dismissible onDismiss={onDismiss} />)
      
      const dismissButton = screen.getByRole('button')
      expect(dismissButton).toHaveClass('text-current')
    })

    it('does not show dismiss button when onDismiss is not provided', () => {
      render(<Alert title="Test" dismissible />)
      
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })
  })

  describe('Styling and Layout', () => {
    it('applies custom className', () => {
      render(<Alert className="custom-class" />)
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('custom-class')
    })

    it('has proper layout structure', () => {
      render(<Alert title="Test Title" description="Test description" />)
      
      const alert = document.querySelector('[role="alert"]')
      const flexContainer = alert?.querySelector('.flex.items-start.gap-3')
      const iconContainer = flexContainer?.querySelector('.flex-shrink-0')
      const contentContainer = flexContainer?.querySelector('.flex-1.min-w-0')
      
      expect(flexContainer).toBeInTheDocument()
      expect(iconContainer).toBeInTheDocument()
      expect(contentContainer).toBeInTheDocument()
    })

    it('applies correct padding for different variants', () => {
      const { rerender } = render(<Alert variant="minimal" />)
      
      let alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('p-2')
      expect(alert).not.toHaveClass('p-4')
      
      rerender(<Alert variant="subtle" />)
      
      alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('p-4')
      expect(alert).not.toHaveClass('p-2')
    })

    it('has proper icon sizing', () => {
      render(<Alert type="success" />)
      
      const icon = screen.getByTestId('check-circle-icon')
      expect(icon).toHaveClass('w-5', 'h-5')
    })
  })

  describe('Animation Props', () => {
    it('handles animated prop correctly', () => {
      render(<Alert animated={true} />)
      
      // Component should render (animation behavior can't be easily tested)
      expect(document.querySelector('[role="alert"]')).toBeInTheDocument()
    })

    it('handles animated=false correctly', () => {
      render(<Alert animated={false} />)
      
      // Component should render without animation
      expect(document.querySelector('[role="alert"]')).toBeInTheDocument()
    })
  })

  describe('Color Configurations', () => {
    it('applies correct colors for different types and variants', () => {
      const testCases = [
        { type: 'success', variant: 'filled', expectedClasses: ['bg-success-500', 'text-white'] },
        { type: 'warning', variant: 'outlined', expectedClasses: ['bg-white', 'text-warning-700', 'border-warning-500'] },
        { type: 'danger', variant: 'subtle', expectedClasses: ['bg-danger-50', 'text-danger-800'] },
        { type: 'info', variant: 'minimal', expectedClasses: ['bg-transparent', 'text-primary-700'] },
      ] as const
      
      testCases.forEach(({ type, variant, expectedClasses }) => {
        const { unmount } = render(<Alert type={type} variant={variant} />)
        
        const alert = document.querySelector('[role="alert"]')
        expectedClasses.forEach(cls => {
          expect(alert).toHaveClass(cls)
        })
        
        unmount()
      })
    })
  })

  describe('Complex Content', () => {
    it('renders complex content with all elements', () => {
      const actions = <button data-testid="test-action">Test Action</button>
      const onDismiss = vi.fn()
      
      render(
        <Alert
          type="warning"
          variant="outlined"
          title="Complex Alert"
          description="This is a complex alert with all features"
          dismissible
          onDismiss={onDismiss}
          actions={actions}
          className="custom-alert"
        >
          <div data-testid="custom-children">Custom children content</div>
        </Alert>
      )
      
      expect(screen.getByText('Complex Alert')).toBeInTheDocument()
      expect(screen.getByText('This is a complex alert with all features')).toBeInTheDocument()
      expect(screen.getByTestId('custom-children')).toBeInTheDocument()
      expect(screen.getByTestId('test-action')).toBeInTheDocument()
      expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument()
      expect(screen.getByRole('button')).toBeInTheDocument() // Dismiss button
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toHaveClass('custom-alert')
    })

    it('handles empty content gracefully', () => {
      render(<Alert />)
      
      expect(document.querySelector('[role="alert"]')).toBeInTheDocument()
      expect(screen.getByTestId('info-icon')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing onDismiss with dismissible=true', () => {
      render(<Alert title="Test" dismissible />)
      
      // Should not show dismiss button without onDismiss
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('handles invalid alert type gracefully', () => {
      // TypeScript would prevent this, but test runtime behavior
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      try {
        render(<Alert type={'invalid' as any} />)
        expect(document.querySelector('[role="alert"]')).toBeInTheDocument()
      } catch (error) {
        // If it throws, that's also acceptable behavior
        expect(error).toBeDefined()
      }
      
      consoleSpy.mockRestore()
    })

    it('handles long content correctly', () => {
      const longTitle = 'This is a very long title that should wrap correctly and not break the layout of the alert component'
      const longDescription = 'This is a very long description that should wrap correctly and maintain proper spacing and readability within the alert component layout structure'
      
      render(<Alert title={longTitle} description={longDescription} />)
      
      expect(screen.getByText(longTitle)).toBeInTheDocument()
      expect(screen.getByText(longDescription)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('maintains focus management for interactive elements', () => {
      const onDismiss = vi.fn()
      
      render(<Alert title="Test" dismissible onDismiss={onDismiss} />)
      
      const dismissButton = screen.getByRole('button')
      dismissButton.focus()
      
      expect(document.activeElement).toBe(dismissButton)
    })

    it('provides proper semantic structure', () => {
      render(
        <Alert 
          title="Important Alert" 
          description="This is important information"
        />
      )
      
      const alert = document.querySelector('[role="alert"]')
      expect(alert).toBeInTheDocument()
      
      // Title should be in a heading element
      const title = screen.getByText('Important Alert')
      expect(title.tagName).toBe('H4')
      
      // Description should be in a paragraph
      const description = screen.getByText('This is important information')
      expect(description.tagName).toBe('P')
    })
  })
})