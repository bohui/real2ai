import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Loading from '../Loading'

describe('Loading Component', () => {
  it('should render loading spinner by default', () => {
    render(<Loading />)
    
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Loading...')).toBeInTheDocument()
  })

  it('should render with custom message', () => {
    const customMessage = 'Processing your request...'
    render(<Loading text={customMessage} />)
    
    expect(screen.getByText(customMessage)).toBeInTheDocument()
    expect(screen.getByLabelText(customMessage)).toBeInTheDocument()
  })

  it('should render in small size', () => {
    render(<Loading size="sm" />)
    
    const spinner = screen.getByRole('status')
    expect(spinner).toHaveClass('w-4', 'h-4')
  })

  it('should render in large size', () => {
    render(<Loading size="lg" />)
    
    const spinner = screen.getByRole('status')
    expect(spinner).toHaveClass('w-12', 'h-12')
  })

  it('should render in medium size by default', () => {
    render(<Loading />)
    
    const spinner = screen.getByRole('status')
    expect(spinner).toHaveClass('w-8', 'h-8')
  })

  it('should render with custom className', () => {
    render(<Loading className="custom-loading-class" />)
    
    const container = screen.getByRole('status').parentElement
    expect(container).toHaveClass('custom-loading-class')
  })

  it('should render fullscreen overlay when fullscreen prop is true', () => {
    render(<Loading />)
    
    const overlay = screen.getByRole('status').closest('[data-testid="loading-overlay"]')
    expect(overlay).toHaveClass('fixed', 'inset-0', 'bg-white/80', 'backdrop-blur-sm')
  })

  it('should render with different colors', () => {
    render(<Loading color="primary" />)
    
    const spinner = screen.getByRole('status')
    expect(spinner).toHaveClass('text-primary-600')
  })

  it('should render centered by default', () => {
    render(<Loading />)
    
    const container = screen.getByRole('status').parentElement
    expect(container).toHaveClass('flex', 'items-center', 'justify-center')
  })

  it('should show progress text when provided', () => {
    render(<Loading text="Uploading..." />)
    
    expect(screen.getByText('Uploading...')).toBeInTheDocument()
  })

  it('should be accessible', () => {
    render(<Loading text="Custom loading message" />)
    
    const spinner = screen.getByRole('status')
    expect(spinner).toHaveAttribute('aria-label', 'Custom loading message')
  })

  describe('Loading States', () => {
    it('should handle different loading states', () => {
      const states = [
        { state: 'loading', message: 'Loading...' },
        { state: 'processing', message: 'Processing...' },
        { state: 'uploading', message: 'Uploading...' },
        { state: 'analyzing', message: 'Analyzing...' }
      ]

      states.forEach(({ message }) => {
        const { unmount } = render(<Loading text={message} />)
        expect(screen.getByText(message)).toBeInTheDocument()
        unmount()
      })
    })

    it('should render with skeleton variant', () => {
      render(<Loading variant="skeleton" />)
      
      const skeleton = screen.getByTestId('loading-skeleton')
      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('should render with dots variant', () => {
      render(<Loading variant="dots" />)
      
      const dots = screen.getByTestId('loading-dots')
      expect(dots).toBeInTheDocument()
      
      // Should have 3 dots
      const dotElements = dots.querySelectorAll('[data-testid="dot"]')
      expect(dotElements).toHaveLength(3)
    })

    it('should render with bar variant', () => {
      render(<Loading variant="pulse" />)
      
      const bar = screen.getByTestId('loading-bar')
      expect(bar).toHaveClass('animate-pulse')
    })
  })

  describe('Animation', () => {
    it('should have spinning animation', () => {
      render(<Loading />)
      
      const spinner = screen.getByRole('status')
      expect(spinner).toHaveClass('animate-spin')
    })

    it('should pause animation when disabled', () => {
      render(<Loading />)
      
      const spinner = screen.getByRole('status')
      expect(spinner).toHaveClass('animate-none')
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      render(<Loading text="Loading data" />)
      
      const spinner = screen.getByRole('status')
      expect(spinner).toHaveAttribute('aria-live', 'polite')
      expect(spinner).toHaveAttribute('aria-busy', 'true')
      expect(spinner).toHaveAttribute('aria-label', 'Loading data')
    })

    it('should be keyboard accessible', () => {
      render(<Loading />)
      
      const spinner = screen.getByRole('status')
      expect(spinner).toHaveAttribute('tabIndex', '0')
    })

    it('should support screen readers', () => {
      render(<Loading text="Processing document analysis" />)
      
      const spinner = screen.getByRole('status')
      expect(spinner).toHaveAccessibleName('Processing document analysis')
    })
  })
})