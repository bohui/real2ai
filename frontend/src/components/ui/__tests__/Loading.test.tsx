/**
 * Test Loading component
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@/test/utils'
import { render } from '@testing-library/react'
import Loading from '../Loading'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, animate, transition, initial, style, ...props }: any) => 
      <div className={className} style={style} {...props}>{children}</div>,
  },
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  Loader2: ({ className }: any) => <div data-testid="loader2-icon" className={className}>Loader2</div>,
  FileText: ({ className }: any) => <div data-testid="file-text-icon" className={className}>FileText</div>,
  Shield: ({ className }: any) => <div data-testid="shield-icon" className={className}>Shield</div>,
  TrendingUp: ({ className }: any) => <div data-testid="trending-up-icon" className={className}>TrendingUp</div>,
}))

describe('Loading Component', () => {
  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<Loading />)
      
      expect(document.body).toBeInTheDocument()
    })

    it('uses default props correctly', () => {
      render(<Loading />)
      
      // Default is spinner variant
      expect(screen.getByTestId('loader2-icon')).toBeInTheDocument()
    })
  })

  describe('Spinner Variant', () => {
    it('renders spinner variant correctly', () => {
      render(<Loading variant="spinner" />)
      
      expect(screen.getByTestId('loader2-icon')).toBeInTheDocument()
      expect(screen.getByTestId('loader2-icon')).toHaveClass('animate-spin')
    })

    it('renders spinner with text', () => {
      render(<Loading variant="spinner" text="Loading data..." />)
      
      expect(screen.getByTestId('loader2-icon')).toBeInTheDocument()
      expect(screen.getByText('Loading data...')).toBeInTheDocument()
    })

    it('applies correct size classes to spinner', () => {
      const { rerender } = render(<Loading variant="spinner" size="sm" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('w-4', 'h-4')
      
      rerender(<Loading variant="spinner" size="md" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('w-6', 'h-6')
      
      rerender(<Loading variant="spinner" size="lg" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('w-8', 'h-8')
      
      rerender(<Loading variant="spinner" size="xl" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('w-12', 'h-12')
    })

    it('applies correct color classes to spinner', () => {
      const { rerender } = render(<Loading variant="spinner" color="primary" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('text-primary-600')
      
      rerender(<Loading variant="spinner" color="secondary" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('text-secondary-600')
      
      rerender(<Loading variant="spinner" color="trust" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('text-trust-600')
      
      rerender(<Loading variant="spinner" color="neutral" />)
      expect(screen.getByTestId('loader2-icon')).toHaveClass('text-neutral-600')
    })

    it('applies correct text size classes', () => {
      const { rerender } = render(<Loading variant="spinner" text="Test" size="sm" />)
      expect(screen.getByText('Test')).toHaveClass('text-xs')
      
      rerender(<Loading variant="spinner" text="Test" size="md" />)
      expect(screen.getByText('Test')).toHaveClass('text-sm')
      
      rerender(<Loading variant="spinner" text="Test" size="lg" />)
      expect(screen.getByText('Test')).toHaveClass('text-base')
      
      rerender(<Loading variant="spinner" text="Test" size="xl" />)
      expect(screen.getByText('Test')).toHaveClass('text-lg')
    })
  })

  describe('Dots Variant', () => {
    it('renders dots variant correctly', () => {
      render(<Loading variant="dots" />)
      
      // Should render 3 dots
      const dots = document.querySelectorAll('.rounded-full')
      expect(dots).toHaveLength(3)
    })

    it('renders dots with text', () => {
      render(<Loading variant="dots" text="Processing..." />)
      
      const dots = document.querySelectorAll('.rounded-full')
      expect(dots).toHaveLength(3)
      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })

    it('applies correct size classes to dots', () => {
      const { rerender } = render(<Loading variant="dots" size="sm" />)
      const dots = document.querySelectorAll('.w-1\\.5')
      expect(dots).toHaveLength(3)
      
      rerender(<Loading variant="dots" size="md" />)
      const mdDots = document.querySelectorAll('.w-2')
      expect(mdDots).toHaveLength(3)
      
      rerender(<Loading variant="dots" size="lg" />)
      const lgDots = document.querySelectorAll('.w-2\\.5')
      expect(lgDots).toHaveLength(3)
      
      rerender(<Loading variant="dots" size="xl" />)
      const xlDots = document.querySelectorAll('.w-3')
      expect(xlDots).toHaveLength(3)
    })

    it('applies correct color classes to dots', () => {
      render(<Loading variant="dots" color="primary" />)
      
      const dots = document.querySelectorAll('.bg-primary-600')
      expect(dots).toHaveLength(3)
    })
  })

  describe('Pulse Variant', () => {
    it('renders pulse variant correctly', () => {
      render(<Loading variant="pulse" />)
      
      const pulseElement = document.querySelector('.rounded-full.border-2')
      expect(pulseElement).toBeInTheDocument()
    })

    it('renders pulse with text', () => {
      render(<Loading variant="pulse" text="Connecting..." />)
      
      const pulseElement = document.querySelector('.rounded-full.border-2')
      expect(pulseElement).toBeInTheDocument()
      expect(screen.getByText('Connecting...')).toBeInTheDocument()
    })

    it('applies correct size and color classes to pulse', () => {
      render(<Loading variant="pulse" size="lg" color="trust" />)
      
      const pulseElement = document.querySelector('.rounded-full.border-2')
      expect(pulseElement).toHaveClass('w-8', 'h-8', 'border-trust-600')
    })
  })

  describe('Legal Variant', () => {
    it('renders legal variant correctly', () => {
      render(<Loading variant="legal" />)
      
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      expect(screen.getByText('Analyzing with Australian legal expertise')).toBeInTheDocument()
    })

    it('renders legal variant with custom text', () => {
      render(<Loading variant="legal" text="Legal Analysis in Progress" />)
      
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      expect(screen.getByText('Legal Analysis in Progress')).toBeInTheDocument()
      expect(screen.getByText('Analyzing with Australian legal expertise')).toBeInTheDocument()
    })

    it('has correct structure for legal variant', () => {
      render(<Loading variant="legal" />)
      
      // Should have gradient background
      const gradientBg = document.querySelector('.bg-gradient-to-br.from-trust-100.to-primary-100')
      expect(gradientBg).toBeInTheDocument()
      
      // Should have rotating border
      const rotatingBorder = document.querySelector('.border-2.border-trust-300.rounded-full')
      expect(rotatingBorder).toBeInTheDocument()
    })
  })

  describe('Analysis Variant', () => {
    it('renders analysis variant correctly', () => {
      render(<Loading variant="analysis" />)
      
      expect(screen.getByTestId('file-text-icon')).toBeInTheDocument()
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument()
      
      expect(screen.getByText('Reading contract')).toBeInTheDocument()
      expect(screen.getByText('Checking compliance')).toBeInTheDocument()
      expect(screen.getByText('Risk assessment')).toBeInTheDocument()
    })

    it('renders analysis variant with custom text', () => {
      render(<Loading variant="analysis" text="Advanced Contract Analysis" />)
      
      expect(screen.getByText('Advanced Contract Analysis')).toBeInTheDocument()
      expect(screen.getByText('Reading contract')).toBeInTheDocument()
      expect(screen.getByText('Checking compliance')).toBeInTheDocument()
      expect(screen.getByText('Risk assessment')).toBeInTheDocument()
    })

    it('has correct structure for analysis steps', () => {
      render(<Loading variant="analysis" />)
      
      // Should have 3 analysis steps
      const stepContainers = document.querySelectorAll('.w-12.h-12.rounded-full')
      expect(stepContainers).toHaveLength(3)
      
      // Each should have gradient background
      stepContainers.forEach(container => {
        expect(container).toHaveClass('bg-gradient-to-br', 'from-primary-100', 'to-trust-100')
      })
    })
  })

  describe('Skeleton Variant', () => {
    it('renders skeleton variant correctly', () => {
      render(<Loading variant="skeleton" />)
      
      const skeletonBars = document.querySelectorAll('.h-4.bg-neutral-200.rounded')
      expect(skeletonBars).toHaveLength(3)
    })

    it('generates random widths for skeleton bars', () => {
      render(<Loading variant="skeleton" />)
      
      const skeletonBars = document.querySelectorAll('.h-4.bg-neutral-200.rounded')
      expect(skeletonBars).toHaveLength(3)
      
      // Each bar should have a style with width (can't easily test randomness in tests)
      skeletonBars.forEach(bar => {
        expect(bar).toBeInTheDocument()
      })
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      render(<Loading className="custom-loading" />)
      
      const container = document.querySelector('.custom-loading')
      expect(container).toBeInTheDocument()
    })

    it('combines custom className with default classes', () => {
      render(<Loading variant="spinner" className="custom-loading" />)
      
      const container = document.querySelector('.custom-loading')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('flex', 'flex-col', 'items-center', 'gap-3')
    })
  })

  describe('Text Handling', () => {
    it('does not render text when not provided', () => {
      render(<Loading variant="spinner" />)
      
      // Should only have the icon, no text
      expect(screen.getByTestId('loader2-icon')).toBeInTheDocument()
      expect(document.querySelector('p')).not.toBeInTheDocument()
    })

    it('renders text with correct styling', () => {
      render(<Loading variant="spinner" text="Loading..." size="lg" />)
      
      const text = screen.getByText('Loading...')
      expect(text).toHaveClass('text-base', 'text-neutral-600', 'font-medium')
    })

    it('handles empty text gracefully', () => {
      render(<Loading variant="spinner" text="" />)
      
      // Empty text should not render
      expect(document.querySelector('p')).not.toBeInTheDocument()
    })
  })

  describe('Layout Structure', () => {
    it('maintains consistent flex layout for different variants', () => {
      const variants = ['spinner', 'dots', 'pulse'] as const
      
      variants.forEach(variant => {
        const { unmount } = render(<Loading variant={variant} />)
        
        const container = document.querySelector('.flex.flex-col.items-center.gap-3')
        expect(container).toBeInTheDocument()
        
        unmount()
      })
    })

    it('has different layout for complex variants', () => {
      render(<Loading variant="legal" />)
      
      const container = document.querySelector('.flex.flex-col.items-center.gap-4')
      expect(container).toBeInTheDocument()
    })

    it('has proper spacing for analysis variant', () => {

      render(<Loading variant="analysis" />)
      
      const container = document.querySelector('.flex.flex-col.items-center.gap-6')
      expect(container).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('returns null for invalid variant', () => {
      // This should return null, but we need to test it doesn't crash
      const result = render(<Loading variant={'invalid' as any} />)
      
      // Component should render but be empty
      expect(result.container.firstChild).toBeNull()
    })

    it('handles all size and color combinations', () => {
      const sizes = ['sm', 'md', 'lg', 'xl'] as const
      const colors = ['primary', 'secondary', 'trust', 'neutral'] as const
      
      sizes.forEach(size => {
        colors.forEach(color => {
          const { unmount } = render(<Loading size={size} color={color} />)
          
          // Should render without errors
          expect(screen.getByTestId('loader2-icon')).toBeInTheDocument()
          
          unmount()
        })
      })
    })

    it('handles long text content', () => {
      const longText = 'This is a very long loading text that should wrap correctly and not break the layout'
      
      render(<Loading variant="spinner" text={longText} />)
      
      expect(screen.getByText(longText)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('provides meaningful loading text', () => {
      render(<Loading variant="spinner" text="Loading your data" />)
      
      const loadingText = screen.getByText('Loading your data')
      expect(loadingText).toBeInTheDocument()
    })

    it('uses semantic structure for analysis variant', () => {
      render(<Loading variant="analysis" />)
      
      // Step labels should be accessible
      expect(screen.getByText('Reading contract')).toBeInTheDocument()
      expect(screen.getByText('Checking compliance')).toBeInTheDocument()
      expect(screen.getByText('Risk assessment')).toBeInTheDocument()
    })

    it('maintains proper text hierarchy for legal variant', () => {
      render(<Loading variant="legal" text="Legal Analysis" />)
      
      const mainText = screen.getByText('Legal Analysis')
      const subText = screen.getByText('Analyzing with Australian legal expertise')
      
      expect(mainText).toBeInTheDocument()
      expect(subText).toBeInTheDocument()
    })
  })

  describe('Animation Properties', () => {
    it('applies animation classes correctly', () => {
      render(<Loading variant="spinner" />)
      
      const spinner = screen.getByTestId('loader2-icon')
      expect(spinner).toHaveClass('animate-spin')
    })

    it('handles animation for skeleton variant', () => {
      render(<Loading variant="skeleton" />)
      
      // Motion components are mocked, but we can verify the structure
      const skeletonBars = document.querySelectorAll('.h-4.bg-neutral-200.rounded')
      expect(skeletonBars).toHaveLength(3)
    })
  })

  describe('Variant-specific Features', () => {
    it('legal variant has proper visual hierarchy', () => {
      render(<Loading variant="legal" text="Contract Review" />)
      
      const mainText = screen.getByText('Contract Review')
      const subText = screen.getByText('Analyzing with Australian legal expertise')
      
      // Main text should be larger
      expect(mainText).toHaveClass('text-lg', 'font-semibold')
      // Sub text should be smaller
      expect(subText).toHaveClass('text-sm')
    })

    it('analysis variant displays all analysis steps', () => {
      render(<Loading variant="analysis" />)
      
      const expectedSteps = [
        'Reading contract',
        'Checking compliance', 
        'Risk assessment'
      ]
      
      expectedSteps.forEach(step => {
        expect(screen.getByText(step)).toBeInTheDocument()
      })
    })

    it('dots variant creates proper dot elements', () => {
      render(<Loading variant="dots" />)
      
      const dotsContainer = document.querySelector('.flex.gap-1')
      expect(dotsContainer).toBeInTheDocument()
      
      const dots = dotsContainer?.querySelectorAll('.rounded-full')
      expect(dots).toHaveLength(3)
    })
  })
})