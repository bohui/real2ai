/**
 * Test OnboardingWizard component
 */

import { describe, it, expect, vi } from 'vitest'
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
    expect(screen.getByText(/let's get you set up/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument()
  })

  it('navigates through onboarding steps', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Step 1: Welcome
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    // Step 2: Practice Area
    await waitFor(() => {
      expect(screen.getByText(/what's your practice area/i)).toBeInTheDocument()
    })
    
    fireEvent.click(screen.getByLabelText(/property law/i))
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    
    // Step 3: Jurisdiction
    await waitFor(() => {
      expect(screen.getByText(/which jurisdiction/i)).toBeInTheDocument()
    })
    
    fireEvent.click(screen.getByLabelText(/nsw/i))
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    
    // Step 4: Firm Size
    await waitFor(() => {
      expect(screen.getByText(/firm size/i)).toBeInTheDocument()
    })
    
    fireEvent.click(screen.getByLabelText(/small firm/i))
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    
    // Step 5: Contract Types
    await waitFor(() => {
      expect(screen.getByText(/contract types/i)).toBeInTheDocument()
    })
    
    fireEvent.click(screen.getByLabelText(/purchase agreements/i))
    fireEvent.click(screen.getByLabelText(/lease agreements/i))
    fireEvent.click(screen.getByRole('button', { name: /complete setup/i }))
    
    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith({
        practiceArea: 'property',
        jurisdiction: 'nsw',
        firmSize: 'small',
        primaryContractTypes: ['Purchase Agreements', 'Lease Agreements'],
      })
    })
  })

  it('can navigate backwards through steps', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Go to step 2
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/what's your practice area/i)).toBeInTheDocument()
    })
    
    // Go back to step 1
    fireEvent.click(screen.getByRole('button', { name: /back/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/welcome to real2\.ai/i)).toBeInTheDocument()
    })
  })

  it('shows progress indicator', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Navigate to second step
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    const progressIndicator = screen.getByRole('progressbar')
    expect(progressIndicator).toBeInTheDocument()
  })

  it('validates required fields before proceeding', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Navigate to practice area step
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/what's your practice area/i)).toBeInTheDocument()
    })
    
    // Try to proceed without selection
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    
    await waitFor(() => {
      expect(screen.getByText(/please select a practice area/i)).toBeInTheDocument()
    })
  })

  it('handles skip functionality', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    fireEvent.click(screen.getByRole('button', { name: /skip/i }))
    
    expect(mockOnSkip).toHaveBeenCalledTimes(1)
  })

  it('shows practice area options', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    await waitFor(() => {
      expect(screen.getByLabelText(/property law/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/commercial law/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/employment law/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/corporate law/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/litigation/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/family law/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/other/i)).toBeInTheDocument()
    })
  })

  it('shows jurisdiction options', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Navigate to jurisdiction step
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    await waitFor(() => {
      fireEvent.click(screen.getByLabelText(/property law/i))
      fireEvent.click(screen.getByRole('button', { name: /next/i }))
    })
    
    await waitFor(() => {
      expect(screen.getByLabelText(/nsw/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/vic/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/qld/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/wa/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/sa/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/tas/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/act/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/nt/i)).toBeInTheDocument()
    })
  })

  it('shows firm size options', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Navigate to firm size step
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    await waitFor(() => {
      fireEvent.click(screen.getByLabelText(/property law/i))
      fireEvent.click(screen.getByRole('button', { name: /next/i }))
    })
    
    await waitFor(() => {
      fireEvent.click(screen.getByLabelText(/nsw/i))
      fireEvent.click(screen.getByRole('button', { name: /next/i }))
    })
    
    await waitFor(() => {
      expect(screen.getByLabelText(/solo practice/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/small firm/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/medium firm/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/large firm/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/in-house/i)).toBeInTheDocument()
    })
  })

  it('allows multiple contract type selections', async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    // Navigate to contract types step
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))
    
    await waitFor(() => {
      fireEvent.click(screen.getByLabelText(/property law/i))
      fireEvent.click(screen.getByRole('button', { name: /next/i }))
    })
    
    await waitFor(() => {
      fireEvent.click(screen.getByLabelText(/nsw/i))
      fireEvent.click(screen.getByRole('button', { name: /next/i }))
    })
    
    await waitFor(() => {
      fireEvent.click(screen.getByLabelText(/small firm/i))
      fireEvent.click(screen.getByRole('button', { name: /next/i }))
    })
    
    await waitFor(() => {
      const purchaseCheckbox = screen.getByLabelText(/purchase agreements/i)
      const leaseCheckbox = screen.getByLabelText(/lease agreements/i)
      const employmentCheckbox = screen.getByLabelText(/employment contracts/i)
      
      fireEvent.click(purchaseCheckbox)
      fireEvent.click(leaseCheckbox)
      fireEvent.click(employmentCheckbox)
      
      expect(purchaseCheckbox).toBeChecked()
      expect(leaseCheckbox).toBeChecked()
      expect(employmentCheckbox).toBeChecked()
    })
  })

  it('can close the wizard', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    const closeButton = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeButton)
    
    expect(mockOnSkip).toHaveBeenCalledTimes(1)
  })

  it('has proper accessibility attributes', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby')
    
    const progressBar = screen.getByRole('progressbar')
    expect(progressBar).toHaveAttribute('aria-valuenow')
    expect(progressBar).toHaveAttribute('aria-valuemax')
  })

  it('focuses first focusable element when opened', () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSkip={mockOnSkip} />)
    
    const getStartedButton = screen.getByRole('button', { name: /get started/i })
    expect(document.activeElement).toBe(getStartedButton)
  })
})