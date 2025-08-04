/**
 * Test MobileOptimizedLoading component
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@/test/utils'
import { render } from '@testing-library/react'
import MobileOptimizedLoading from '../MobileOptimizedLoading'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }: any) => 
      <div className={className} {...props}>{children}</div>,
    circle: ({ className, cx, cy, r, stroke, strokeWidth, fill, strokeLinecap, strokeDasharray, ...props }: any) => 
      <circle 
        className={className} 
        cx={cx} 
        cy={cy} 
        r={r} 
        stroke={stroke} 
        strokeWidth={strokeWidth} 
        fill={fill} 
        strokeLinecap={strokeLinecap}
        strokeDasharray={strokeDasharray}
        {...props} 
      />,
  },
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  FileText: ({ className }: any) => <div data-testid="file-text-icon" className={className}>FileText</div>,
  Shield: ({ className }: any) => <div data-testid="shield-icon" className={className}>Shield</div>,
  TrendingUp: ({ className }: any) => <div data-testid="trending-up-icon" className={className}>TrendingUp</div>,
  CheckCircle: ({ className }: any) => <div data-testid="check-circle-icon" className={className}>CheckCircle</div>,
}))

describe('MobileOptimizedLoading Component', () => {
  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<MobileOptimizedLoading />)
      
      expect(document.body).toBeInTheDocument()
    })

    it('renders with default props', () => {
      render(<MobileOptimizedLoading />)
      
      expect(screen.getByText('Analyzing Contract')).toBeInTheDocument()
      expect(screen.getByText('Our AI is reviewing your document...')).toBeInTheDocument()
      expect(screen.getByText('Processing document')).toBeInTheDocument()
    })

    it('has proper mobile layout structure', () => {
      render(<MobileOptimizedLoading />)
      
      const container = document.querySelector('.min-h-screen.bg-neutral-50.flex.flex-col')
      expect(container).toBeInTheDocument()
    })
  })

  describe('Header Section', () => {
    it('renders header with default title and subtitle', () => {
      render(<MobileOptimizedLoading />)
      
      const header = document.querySelector('.bg-white.border-b.border-neutral-200')
      expect(header).toBeInTheDocument()
      
      expect(screen.getByText('Analyzing Contract')).toBeInTheDocument()
      expect(screen.getByText('Our AI is reviewing your document...')).toBeInTheDocument()
    })

    it('renders header with custom title and subtitle', () => {
      render(
        <MobileOptimizedLoading 
          title="Custom Analysis" 
          subtitle="Custom processing message"
        />
      )
      
      expect(screen.getByText('Custom Analysis')).toBeInTheDocument()
      expect(screen.getByText('Custom processing message')).toBeInTheDocument()
    })

    it('shows estimated time when provided', () => {
      render(<MobileOptimizedLoading estimatedTime={5} />)
      
      expect(screen.getByText('Estimated time: 5 minutes remaining')).toBeInTheDocument()
    })

    it('does not show estimated time when not provided', () => {
      render(<MobileOptimizedLoading />)
      
      expect(screen.queryByText(/Estimated time:/)).not.toBeInTheDocument()
    })

    it('applies proper header styling', () => {
      render(<MobileOptimizedLoading />)
      
      const header = document.querySelector('.bg-white.border-b.border-neutral-200.px-4.py-6')
      expect(header).toBeInTheDocument()
      
      const title = screen.getByText('Analyzing Contract')
      expect(title).toHaveClass('text-xl', 'font-semibold', 'text-neutral-900', 'mb-2')
      
      const subtitle = screen.getByText('Our AI is reviewing your document...')
      expect(subtitle).toHaveClass('text-neutral-600')
    })
  })

  describe('Progress Ring', () => {
    it('renders progress ring with correct structure', () => {
      render(<MobileOptimizedLoading progress={50} />)
      
      const svg = document.querySelector('svg')
      expect(svg).toBeInTheDocument()
      expect(svg).toHaveClass('w-32', 'h-32', 'transform', '-rotate-90')
      
      const circles = svg?.querySelectorAll('circle')
      expect(circles).toHaveLength(2) // Background and progress circles
    })

    it('displays correct progress percentage', () => {
      render(<MobileOptimizedLoading progress={75} />)
      
      expect(screen.getByText('75%')).toBeInTheDocument()
      expect(screen.getByText('Complete')).toBeInTheDocument()
    })

    it('rounds progress percentage correctly', () => {
      render(<MobileOptimizedLoading progress={33.7} />)
      
      expect(screen.getByText('34%')).toBeInTheDocument()
    })

    it('handles zero progress', () => {
      render(<MobileOptimizedLoading progress={0} />)
      
      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('handles 100% progress', () => {
      render(<MobileOptimizedLoading progress={100} />)
      
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('has proper SVG attributes', () => {
      render(<MobileOptimizedLoading progress={50} />)
      
      const svg = document.querySelector('svg')
      expect(svg).toHaveAttribute('viewBox', '0 0 100 100')
      
      const backgroundCircle = svg?.querySelector('circle:first-child')
      expect(backgroundCircle).toHaveAttribute('cx', '50')
      expect(backgroundCircle).toHaveAttribute('cy', '50')
      expect(backgroundCircle).toHaveAttribute('r', '45')
      expect(backgroundCircle).toHaveAttribute('stroke', '#e5e7eb')
      expect(backgroundCircle).toHaveAttribute('strokeWidth', '6')
      expect(backgroundCircle).toHaveAttribute('fill', 'none')
      
      const progressCircle = svg?.querySelector('circle:last-child')
      expect(progressCircle).toHaveAttribute('stroke', '#3b82f6')
      expect(progressCircle).toHaveAttribute('strokeLinecap', 'round')
      expect(progressCircle).toHaveAttribute('strokeDasharray', '283')
    })
  })

  describe('Current Step Display', () => {
    it('shows current step with correct styling', () => {
      render(<MobileOptimizedLoading currentStep="Analyzing document" />)
      
      const stepBadge = document.querySelector('.bg-primary-100.text-primary-800.rounded-full')
      expect(stepBadge).toBeInTheDocument()
      
      expect(screen.getByText('Analyzing document')).toBeInTheDocument()
    })

    it('shows correct step based on progress', () => {
      render(<MobileOptimizedLoading progress={0} />)
      
      expect(screen.getByTestId('file-text-icon')).toBeInTheDocument()
      expect(screen.getByText('Extracting text and structure')).toBeInTheDocument()
    })

    it('displays step description correctly', () => {
      render(<MobileOptimizedLoading progress={30} />)
      
      // Should show second step (Shield icon) at 30% progress
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      expect(screen.getByText('Identifying potential issues')).toBeInTheDocument()
    })

    it('calculates current step index correctly', () => {
      const { rerender } = render(<MobileOptimizedLoading progress={25} />)
      // 25% should be step 1 (index 1) - Shield
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      
      rerender(<MobileOptimizedLoading progress={75} />)
      // 75% should be step 3 (index 3) - TrendingUp
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument()
    })
  })

  describe('Step Indicators', () => {
    it('renders all four steps', () => {
      render(<MobileOptimizedLoading />)
      
      expect(screen.getByText('Document Processing')).toBeInTheDocument()
      expect(screen.getByText('Risk Assessment')).toBeInTheDocument()
      expect(screen.getByText('Compliance Check')).toBeInTheDocument()
      expect(screen.getByText('Final Analysis')).toBeInTheDocument()
    })

    it('shows step descriptions', () => {
      render(<MobileOptimizedLoading />)
      
      expect(screen.getByText('Extracting text and structure')).toBeInTheDocument()
      expect(screen.getByText('Identifying potential issues')).toBeInTheDocument()
      expect(screen.getByText('Verifying Australian law compliance')).toBeInTheDocument()
      expect(screen.getByText('Generating recommendations')).toBeInTheDocument()
    })

    it('applies correct styling to completed steps', () => {
      render(<MobileOptimizedLoading progress={75} />)
      
      // First steps should be completed (success styling)
      const completedSteps = document.querySelectorAll('.bg-success-50.border.border-success-200')
      expect(completedSteps.length).toBeGreaterThan(0)
    })

    it('applies correct styling to current step', () => {
      render(<MobileOptimizedLoading progress={50} />)
      
      // Current step should have primary styling
      const currentStep = document.querySelector('.bg-primary-50.border.border-primary-200')
      expect(currentStep).toBeInTheDocument()
    })

    it('applies correct styling to upcoming steps', () => {
      render(<MobileOptimizedLoading progress={25} />)
      
      // Future steps should have neutral styling
      const upcomingSteps = document.querySelectorAll('.bg-white.border.border-neutral-200')
      expect(upcomingSteps.length).toBeGreaterThan(0)
    })

    it('shows correct icons for each step', () => {
      render(<MobileOptimizedLoading />)
      
      expect(screen.getByTestId('file-text-icon')).toBeInTheDocument()
      expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument()
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument()
    })

    it('shows loading spinner for current step', () => {
      render(<MobileOptimizedLoading progress={25} />)
      
      // Should have a loading spinner for the current step
      const spinner = document.querySelector('.border-2.border-primary-600.border-t-transparent.rounded-full')
      expect(spinner).toBeInTheDocument()
    })

    it('shows check circle for completed steps', () => {
      render(<MobileOptimizedLoading progress={75} />)
      
      // Completed steps should show CheckCircle icon instead of original icon
      const checkIcons = screen.getAllByTestId('check-circle-icon')
      expect(checkIcons.length).toBeGreaterThan(1) // Multiple completed steps
    })
  })

  describe('Progress Bar', () => {
    it('renders progress bar at bottom', () => {
      render(<MobileOptimizedLoading progress={60} />)
      
      const progressBar = document.querySelector('.bg-gradient-to-r.from-primary-500.to-primary-600')
      expect(progressBar).toBeInTheDocument()
    })

    it('shows progress labels', () => {
      render(<MobileOptimizedLoading progress={45} />)
      
      expect(screen.getByText('Started')).toBeInTheDocument()
      expect(screen.getByText('45% Complete')).toBeInTheDocument()
      expect(screen.getByText('Finished')).toBeInTheDocument()
    })

    it('has proper progress bar structure', () => {
      render(<MobileOptimizedLoading progress={30} />)
      
      const progressContainer = document.querySelector('.bg-neutral-200.rounded-full.h-2.overflow-hidden')
      expect(progressContainer).toBeInTheDocument()
      
      const progressBar = progressContainer?.querySelector('.h-full.bg-gradient-to-r')
      expect(progressBar).toBeInTheDocument()
    })
  })

  describe('Footer Section', () => {
    it('renders footer with branding', () => {
      render(<MobileOptimizedLoading />)
      
      const footer = document.querySelector('.bg-white.border-t.border-neutral-200')
      expect(footer).toBeInTheDocument()
      
      expect(screen.getByText('Analysis powered by Real2.AI')).toBeInTheDocument()
      expect(screen.getByText('Tailored for Australian legal requirements')).toBeInTheDocument()
    })

    it('has proper footer styling', () => {
      render(<MobileOptimizedLoading />)
      
      const footerText = screen.getByText('Analysis powered by Real2.AI')
      expect(footerText).toHaveClass('text-sm', 'text-neutral-500')
    })
  })

  describe('Custom Props', () => {
    it('applies custom className', () => {
      render(<MobileOptimizedLoading className="custom-loading" />)
      
      const container = document.querySelector('.custom-loading')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass('min-h-screen', 'bg-neutral-50', 'flex', 'flex-col')
    })

    it('handles all custom props together', () => {
      render(
        <MobileOptimizedLoading
          title="Complete Analysis"
          subtitle="Comprehensive review in progress"
          progress={85}
          currentStep="Finalizing report"
          estimatedTime={2}
          className="custom-mobile-loader"
        />
      )
      
      expect(screen.getByText('Complete Analysis')).toBeInTheDocument()
      expect(screen.getByText('Comprehensive review in progress')).toBeInTheDocument()
      expect(screen.getByText('85%')).toBeInTheDocument()
      expect(screen.getByText('Finalizing report')).toBeInTheDocument()
      expect(screen.getByText('Estimated time: 2 minutes remaining')).toBeInTheDocument()
      
      const container = document.querySelector('.custom-mobile-loader')
      expect(container).toBeInTheDocument()
    })
  })

  describe('Responsive Design', () => {
    it('has proper mobile-first structure', () => {
      render(<MobileOptimizedLoading />)
      
      const container = document.querySelector('.min-h-screen')
      expect(container).toBeInTheDocument()
      
      // Header should be full width
      const header = document.querySelector('.px-4.py-6')
      expect(header).toBeInTheDocument()
      
      // Content should be flexible
      const content = document.querySelector('.flex-1.flex.flex-col.justify-center')
      expect(content).toBeInTheDocument()
    })

    it('maintains proper spacing on mobile', () => {
      render(<MobileOptimizedLoading />)
      
      // Progress section should have mobile-appropriate padding
      const progressSection = document.querySelector('.px-4.py-8')
      expect(progressSection).toBeInTheDocument()
      
      // Step indicators should have mobile spacing
      const stepContainer = document.querySelector('.px-4.mb-8')
      expect(stepContainer).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles progress over 100%', () => {
      render(<MobileOptimizedLoading progress={150} />)
      
      expect(screen.getByText('150%')).toBeInTheDocument()
    })

    it('handles negative progress', () => {
      render(<MobileOptimizedLoading progress={-10} />)
      
      expect(screen.getByText('-10%')).toBeInTheDocument()
    })

    it('handles very long text content', () => {
      const longTitle = 'This is a very long title that should wrap correctly on mobile devices'
      const longSubtitle = 'This is a very long subtitle that provides detailed information about the process'
      
      render(
        <MobileOptimizedLoading 
          title={longTitle}
          subtitle={longSubtitle}
        />
      )
      
      expect(screen.getByText(longTitle)).toBeInTheDocument()
      expect(screen.getByText(longSubtitle)).toBeInTheDocument()
    })

    it('handles zero estimated time', () => {
      render(<MobileOptimizedLoading estimatedTime={0} />)
      
      expect(screen.getByText('Estimated time: 0 minutes remaining')).toBeInTheDocument()
    })

    it('handles large estimated time', () => {
      render(<MobileOptimizedLoading estimatedTime={999} />)
      
      expect(screen.getByText('Estimated time: 999 minutes remaining')).toBeInTheDocument()
    })
  })

  describe('Animation and Interaction', () => {
    it('applies animation classes where expected', () => {
      render(<MobileOptimizedLoading progress={50} />)
      
      // Loading spinner should have animation
      const spinner = document.querySelector('.border-2.border-primary-600.border-t-transparent.rounded-full')
      expect(spinner).toBeInTheDocument()
    })

    it('maintains visual hierarchy', () => {
      render(<MobileOptimizedLoading />)
      
      // Title should be larger than subtitle
      const title = screen.getByText('Analyzing Contract')
      const subtitle = screen.getByText('Our AI is reviewing your document...')
      
      expect(title).toHaveClass('text-xl', 'font-semibold')
      expect(subtitle).toHaveClass('text-neutral-600')
      expect(subtitle).not.toHaveClass('text-xl')
    })
  })

  describe('Accessibility', () => {
    it('maintains proper heading hierarchy', () => {
      render(<MobileOptimizedLoading />)
      
      const title = screen.getByText('Analyzing Contract')
      expect(title.tagName).toBe('H1')
      
      const stepLabels = document.querySelectorAll('h4')
      expect(stepLabels.length).toBeGreaterThan(0)
    })

    it('provides meaningful text content', () => {
      render(<MobileOptimizedLoading />)
      
      // All step descriptions should be accessible
      expect(screen.getByText('Extracting text and structure')).toBeInTheDocument()
      expect(screen.getByText('Identifying potential issues')).toBeInTheDocument()
      expect(screen.getByText('Verifying Australian law compliance')).toBeInTheDocument()
      expect(screen.getByText('Generating recommendations')).toBeInTheDocument()
    })

    it('has proper contrast in different states', () => {
      render(<MobileOptimizedLoading progress={50} />)
      
      // Completed steps should have success colors
      const completedElements = document.querySelectorAll('.text-success-700, .text-success-900')
      expect(completedElements.length).toBeGreaterThan(0)
      
      // Current step should have primary colors
      const currentElements = document.querySelectorAll('.text-primary-700, .text-primary-900')
      expect(currentElements.length).toBeGreaterThan(0)
      
      // Future steps should have neutral colors
      const futureElements = document.querySelectorAll('.text-neutral-500, .text-neutral-400')
      expect(futureElements.length).toBeGreaterThan(0)
    })
  })
})