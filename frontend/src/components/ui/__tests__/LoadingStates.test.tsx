/**
 * Test LoadingStates component
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@/test/utils'
import { render } from '@testing-library/react'
import LoadingStates, { 
  Skeleton, 
  LoadingSpinner, 
  LoadingCard, 
  LoadingState, 
  ProcessingIndicator 
} from '../LoadingStates'

// Mock utils
vi.mock('@/utils', () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}))

describe('Skeleton Component', () => {
  it('renders with default props', () => {
    render(<Skeleton />)
    
    const skeleton = document.querySelector('.bg-neutral-200')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('animate-pulse', 'rounded-lg')
  })

  it('renders different variants correctly', () => {
    const { rerender } = render(<Skeleton variant="text" />)
    expect(document.querySelector('.h-4.rounded')).toBeInTheDocument()
    
    rerender(<Skeleton variant="circle" />)
    expect(document.querySelector('.rounded-full')).toBeInTheDocument()
    
    rerender(<Skeleton variant="rectangle" />)
    expect(document.querySelector('.rounded-lg')).toBeInTheDocument()
  })

  it('applies custom dimensions', () => {
    render(<Skeleton width={100} height={50} />)
    
    const skeleton = document.querySelector('.bg-neutral-200')
    expect(skeleton).toHaveStyle({ width: '100px', height: '50px' })
  })

  it('applies string dimensions', () => {
    render(<Skeleton width="50%" height="2rem" />)
    
    const skeleton = document.querySelector('.bg-neutral-200')
    expect(skeleton).toHaveStyle({ width: '50%', height: '2rem' })
  })

  it('can disable animation', () => {
    render(<Skeleton animated={false} />)
    
    const skeleton = document.querySelector('.bg-neutral-200')
    expect(skeleton).not.toHaveClass('animate-pulse')
  })

  it('applies custom className', () => {
    render(<Skeleton className="custom-skeleton" />)
    
    const skeleton = document.querySelector('.custom-skeleton')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('bg-neutral-200')
  })
})

describe('LoadingSpinner Component', () => {
  it('renders with default props', () => {
    render(<LoadingSpinner />)
    
    const spinner = document.querySelector('.border-2.rounded-full.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('w-6', 'h-6', 'border-primary-600', 'border-t-transparent')
  })

  it('renders different sizes correctly', () => {
    const { rerender } = render(<LoadingSpinner size="sm" />)
    expect(document.querySelector('.w-4.h-4')).toBeInTheDocument()
    
    rerender(<LoadingSpinner size="md" />)
    expect(document.querySelector('.w-6.h-6')).toBeInTheDocument()
    
    rerender(<LoadingSpinner size="lg" />)
    expect(document.querySelector('.w-8.h-8')).toBeInTheDocument()
    
    rerender(<LoadingSpinner size="xl" />)
    expect(document.querySelector('.w-12.h-12')).toBeInTheDocument()
  })

  it('renders different variants correctly', () => {
    const { rerender } = render(<LoadingSpinner variant="primary" />)
    expect(document.querySelector('.border-primary-600')).toBeInTheDocument()
    
    rerender(<LoadingSpinner variant="secondary" />)
    expect(document.querySelector('.border-secondary-600')).toBeInTheDocument()
    
    rerender(<LoadingSpinner variant="neutral" />)
    expect(document.querySelector('.border-neutral-400')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(<LoadingSpinner className="custom-spinner" />)
    
    const spinner = document.querySelector('.custom-spinner')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('border-2', 'rounded-full', 'animate-spin')
  })
})

describe('LoadingCard Component', () => {
  it('renders with default props', () => {
    render(<LoadingCard />)
    
    // Should have header and content by default
    const headerSkeleton = document.querySelector('.h-6.w-3\\/4')
    const contentSkeletons = document.querySelectorAll('.h-4')
    
    expect(headerSkeleton).toBeInTheDocument()
    expect(contentSkeletons.length).toBeGreaterThanOrEqual(3)
  })

  it('conditionally renders sections', () => {
    render(<LoadingCard showHeader={false} showContent={false} showFooter={true} />)
    
    // Should not have header
    expect(document.querySelector('.h-6.w-3\\/4')).not.toBeInTheDocument()
    
    // Should have footer
    expect(document.querySelector('.border-t.border-neutral-100')).toBeInTheDocument()
  })

  it('renders custom number of content lines', () => {
    render(<LoadingCard lines={5} />)
    
    const contentSkeletons = document.querySelectorAll('.space-y-3 .h-4')
    expect(contentSkeletons).toHaveLength(5)
  })

  it('applies custom className', () => {
    render(<LoadingCard className="custom-card" />)
    
    const card = document.querySelector('.custom-card')
    expect(card).toBeInTheDocument()
  })

  it('renders footer when enabled', () => {
    render(<LoadingCard showFooter={true} />)
    
    const footer = document.querySelector('.border-t.border-neutral-100')
    expect(footer).toBeInTheDocument()
    
    // Footer should have two skeleton elements
    const footerSkeletons = footer?.querySelectorAll('.h-4, .h-8')
    expect(footerSkeletons).toHaveLength(2)
  })
})

describe('LoadingState Component', () => {
  it('renders cards type by default', () => {
    render(<LoadingState />)
    
    const grid = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3')
    expect(grid).toBeInTheDocument()
  })

  it('renders custom count of cards', () => {
    render(<LoadingState type="cards" count={5} />)
    
    const cards = document.querySelectorAll('.grid > *')
    expect(cards).toHaveLength(5)
  })

  it('renders table type correctly', () => {
    render(<LoadingState type="table" />)
    
    // Should have table header (4 columns)
    const headerCols = document.querySelectorAll('.grid.grid-cols-4:first-of-type .h-4')
    expect(headerCols).toHaveLength(4)
    
    // Should have table rows
    const rowGrids = document.querySelectorAll('.grid.grid-cols-4')
    expect(rowGrids.length).toBeGreaterThan(1) // Header + rows
  })

  it('renders list type correctly', () => {
    render(<LoadingState type="list" />)
    
    const listItems = document.querySelectorAll('.space-y-4 > *')
    expect(listItems).toHaveLength(3) // Default count
    
    // Each item should have circle and text skeletons
    listItems.forEach(item => {
      expect(item.querySelector('.rounded-full')).toBeInTheDocument()
      expect(item.querySelectorAll('.h-4, .h-3')).toHaveLength(2)
    })
  })

  it('renders dashboard type correctly', () => {
    render(<LoadingState type="dashboard" />)
    
    // Should have stats grid (4 items)
    const statsGrid = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4')
    expect(statsGrid).toBeInTheDocument()
    
    const statsCards = statsGrid?.querySelectorAll('> *')
    expect(statsCards).toHaveLength(4)
    
    // Should have main content grid
    const mainGrid = document.querySelector('.grid.grid-cols-1.lg\\:grid-cols-3')
    expect(mainGrid).toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(<LoadingState className="custom-loading-state" />)
    
    const container = document.querySelector('.custom-loading-state')
    expect(container).toBeInTheDocument()
  })

  it('returns null for invalid type', () => {
    const result = render(<LoadingState type={'invalid' as any} />)
    expect(result.container.firstChild).toBeNull()
  })
})

describe('ProcessingIndicator Component', () => {
  it('renders with basic props', () => {
    render(<ProcessingIndicator stage="Processing..." />)
    
    expect(screen.getByText('Processing Contract Analysis')).toBeInTheDocument()
    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })

  it('renders progress bar when progress is provided', () => {
    render(<ProcessingIndicator stage="Processing..." progress={75} />)
    
    const progressBar = document.querySelector('.bg-primary-600')
    expect(progressBar).toBeInTheDocument()
    expect(progressBar).toHaveStyle({ width: '75%' })
  })

  it('does not render progress bar when progress is undefined', () => {
    render(<ProcessingIndicator stage="Processing..." />)
    
    const progressContainer = document.querySelector('.bg-neutral-200.rounded-full.h-2')
    expect(progressContainer).not.toBeInTheDocument()
  })

  it('renders stages when provided', () => {
    const stages = ['Stage 1', 'Stage 2', 'Stage 3']
    
    render(
      <ProcessingIndicator 
        stage="Processing..." 
        stages={stages} 
        currentStage={1}
      />
    )
    
    stages.forEach(stage => {
      expect(screen.getByText(stage)).toBeInTheDocument()
    })
  })

  it('applies correct styling to current stage', () => {
    const stages = ['Stage 1', 'Stage 2', 'Stage 3']
    
    render(
      <ProcessingIndicator 
        stage="Processing..." 
        stages={stages} 
        currentStage={1}
      />
    )
    
    // Find stage containers
    const stageContainers = document.querySelectorAll('.flex.items-center.gap-3')
    
    // Current stage (index 1) should have primary colors
    const currentStage = stageContainers[1]
    expect(currentStage).toHaveClass('text-primary-700', 'bg-primary-50')
    
    // Previous stage (index 0) should have success colors
    const previousStage = stageContainers[0]
    expect(previousStage).toHaveClass('text-success-700', 'bg-success-50')
    
    // Future stage (index 2) should have neutral colors
    const futureStage = stageContainers[2]
    expect(futureStage).toHaveClass('text-neutral-500', 'bg-neutral-50')
  })

  it('applies correct dot styling to stages', () => {
    const stages = ['Stage 1', 'Stage 2', 'Stage 3']
    
    render(
      <ProcessingIndicator 
        stage="Processing..." 
        stages={stages} 
        currentStage={1}
      />
    )
    
    const dots = document.querySelectorAll('.w-2.h-2.rounded-full')
    
    // Previous stage dot should be success
    expect(dots[0]).toHaveClass('bg-success-500')
    
    // Current stage dot should be primary with animation
    expect(dots[1]).toHaveClass('bg-primary-500', 'animate-pulse')
    
    // Future stage dot should be neutral
    expect(dots[2]).toHaveClass('bg-neutral-300')
  })

  it('applies custom className', () => {
    render(<ProcessingIndicator stage="Test" className="custom-processing" />)
    
    const container = document.querySelector('.custom-processing')
    expect(container).toBeInTheDocument()
  })

  it('handles empty stages array', () => {
    render(<ProcessingIndicator stage="Processing..." stages={[]} />)
    
    // Should still render main content
    expect(screen.getByText('Processing Contract Analysis')).toBeInTheDocument()
    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })

  it('handles currentStage beyond stages length', () => {
    const stages = ['Stage 1', 'Stage 2']
    
    render(
      <ProcessingIndicator 
        stage="Processing..." 
        stages={stages} 
        currentStage={5}
      />
    )
    
    // Should not crash and still render stages
    expect(screen.getByText('Stage 1')).toBeInTheDocument()
    expect(screen.getByText('Stage 2')).toBeInTheDocument()
  })

  it('has proper structure and loading spinner', () => {
    render(<ProcessingIndicator stage="Test" />)
    
    // Should have loading spinner
    const spinner = document.querySelector('.border-2.rounded-full.animate-spin')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('w-8', 'h-8') // lg size
    
    // Should be centered
    const container = document.querySelector('.text-center')
    expect(container).toBeInTheDocument()
  })
})

describe('LoadingStates Default Export', () => {
  it('exports all components correctly', () => {
    expect(LoadingStates.Skeleton).toBeDefined()
    expect(LoadingStates.LoadingSpinner).toBeDefined()
    expect(LoadingStates.LoadingCard).toBeDefined()
    expect(LoadingStates.LoadingState).toBeDefined()
    expect(LoadingStates.ProcessingIndicator).toBeDefined()
  })

  it('components work when imported from default export', () => {
    render(<LoadingStates.Skeleton />)
    expect(document.querySelector('.bg-neutral-200')).toBeInTheDocument()
    
    render(<LoadingStates.LoadingSpinner />)
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })
})

describe('Integration Tests', () => {
  it('LoadingCard uses Skeleton components internally', () => {
    render(<LoadingCard />)
    
    // Should have skeleton elements
    const skeletons = document.querySelectorAll('.bg-neutral-200')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('LoadingState uses LoadingCard for cards type', () => {
    render(<LoadingState type="cards" count={2} />)
    
    // Should have card-like structure
    const cardContainers = document.querySelectorAll('.grid > *')
    expect(cardContainers).toHaveLength(2)
  })

  it('ProcessingIndicator uses LoadingSpinner', () => {
    render(<ProcessingIndicator stage="Test" />)
    
    // Should have spinner structure
    const spinner = document.querySelector('.border-2.rounded-full.animate-spin')
    expect(spinner).toBeInTheDocument()
  })
})

describe('Accessibility', () => {
  it('ProcessingIndicator has proper heading structure', () => {
    render(<ProcessingIndicator stage="Test stage" />)
    
    const heading = screen.getByText('Processing Contract Analysis')
    expect(heading.tagName).toBe('H3')
    expect(heading).toHaveClass('text-lg', 'font-semibold')
  })

  it('maintains semantic structure in LoadingState', () => {
    render(<LoadingState type="cards" />)
    
    // Should have proper grid structure
    const grid = document.querySelector('.grid')
    expect(grid).toBeInTheDocument()
  })

  it('Skeleton components have appropriate roles implicitly', () => {
    render(<Skeleton />)
    
    // Skeleton should be a div element that doesn't interfere with screen readers
    const skeleton = document.querySelector('.bg-neutral-200')
    expect(skeleton?.tagName).toBe('DIV')
  })
})

describe('Edge Cases', () => {
  it('handles zero count in LoadingState', () => {
    render(<LoadingState type="cards" count={0} />)
    
    const grid = document.querySelector('.grid')
    expect(grid).toBeInTheDocument()
    expect(grid?.children).toHaveLength(0)
  })

  it('handles negative progress in ProcessingIndicator', () => {
    render(<ProcessingIndicator stage="Test" progress={-10} />)
    
    const progressBar = document.querySelector('.bg-primary-600')
    expect(progressBar).toHaveStyle({ width: '-10%' })
  })

  it('handles progress over 100 in ProcessingIndicator', () => {
    render(<ProcessingIndicator stage="Test" progress={150} />)
    
    const progressBar = document.querySelector('.bg-primary-600')
    expect(progressBar).toHaveStyle({ width: '150%' })
  })

  it('handles very long text in ProcessingIndicator', () => {
    const longStage = 'This is a very long stage description that should wrap properly and not break the layout'
    
    render(<ProcessingIndicator stage={longStage} />)
    
    expect(screen.getByText(longStage)).toBeInTheDocument()
  })

  it('handles empty or undefined dimensions in Skeleton', () => {
    render(<Skeleton width={undefined} height={undefined} />)
    
    const skeleton = document.querySelector('.bg-neutral-200')
    expect(skeleton).toBeInTheDocument()
  })

  it('handles large count values in LoadingState', () => {
    render(<LoadingState type="cards" count={100} />)
    
    const grid = document.querySelector('.grid')
    expect(grid?.children).toHaveLength(100)
  })
})