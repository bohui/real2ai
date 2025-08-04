/**
 * Test OnboardingWizard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { OnboardingWizard } from '../OnboardingWizard'

describe('OnboardingWizard Component', () => {
  const mockOnComplete = vi.fn()
  const mockOnSkip = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders welcome step initially', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    expect(screen.getByText(/welcome to real2\.ai/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /skip for now/i })).toBeInTheDocument()
  })

  it('has navigation buttons', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /skip for now/i })).toBeInTheDocument()
  })

  it('can proceed to next step', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Click Next to go to step 2
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    
    // Should show step 2 content
    await waitFor(() => {
      expect(screen.getByText(/customize your experience/i)).toBeInTheDocument()
    })
  })

  it('calls onSkip when skip button is clicked', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    fireEvent.click(screen.getByRole('button', { name: /skip for now/i }))
    expect(mockOnSkip).toHaveBeenCalledTimes(1)
  })

  it('renders component structure correctly', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Basic structure should be present
    expect(screen.getByText(/welcome to real2\.ai/i)).toBeInTheDocument()
    expect(document.body).toBeInTheDocument()
  })
})