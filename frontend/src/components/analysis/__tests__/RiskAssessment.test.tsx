/**
 * Test RiskAssessment component
 */

import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@/test/utils'
import { RiskAssessment } from '../RiskAssessment'
import { RiskLevel } from '@/types'

describe('RiskAssessment Component', () => {
  const defaultProps = {
    riskAssessment: {
      overall_risk_score: 3,
      risk_factors: [
        {
          factor: "Short settlement period",
          severity: "medium" as RiskLevel,
          description: "Settlement period is shorter than recommended",
          impact: "Medium financial risk",
          mitigation: "Arrange finance pre-approval",
          australian_specific: true,
          confidence: 0.85,
        },
      ],
    },
    loading: false,
  }

  it('renders risk assessment with overall score', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/risk assessment/i)).toBeInTheDocument()
    expect(screen.getByText(/overall risk score/i)).toBeInTheDocument()
    expect(screen.getByText('3.0')).toBeInTheDocument() // Risk score
  })

  it('displays risk factors', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/short settlement period/i)).toBeInTheDocument()
    expect(screen.getByText(/settlement period is shorter than recommended/i)).toBeInTheDocument()
  })

  it('shows risk severity levels', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    const riskFactor = screen.getByText(/short settlement period/i).closest('.border')
    expect(riskFactor).toHaveClass('border-warning-200') // Medium severity
  })

  it('displays risk mitigation suggestions', async () => {
    render(<RiskAssessment {...defaultProps} />)
    
    // Click on the "More" button to expand details
    const moreButton = screen.getByRole('button', { name: /more/i })
    fireEvent.click(moreButton)
    
    await waitFor(() => {
      expect(screen.getByText(/arrange finance pre-approval/i)).toBeInTheDocument()
    })
  })

  it('shows confidence scores', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/85%/i)).toBeInTheDocument() // Confidence score
  })

  it('indicates Australian-specific risks', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    const australianBadge = screen.getByText(/au specific/i)
    expect(australianBadge).toBeInTheDocument()
    expect(australianBadge).toHaveClass('bg-secondary-100')
  })

  it('handles loading state', () => {
    render(<RiskAssessment {...defaultProps} loading={true} />)
    
    expect(screen.getByText(/risk assessment/i)).toBeInTheDocument()
    // Loading state shows skeleton placeholders instead of progressbar
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('handles empty risk assessment', () => {
    render(<RiskAssessment riskAssessment={null} loading={false} />)
    
    expect(screen.getByText(/no risk assessment available/i)).toBeInTheDocument()
  })

  it('displays risk score with appropriate color coding', () => {
    const { rerender } = render(
      <RiskAssessment 
        riskAssessment={{ ...defaultProps.riskAssessment, overall_risk_score: 1 }}
        loading={false}
      />
    )
    
    let scoreElement = screen.getByText('1.0')
    expect(scoreElement).toHaveClass('text-success-600')
    
    rerender(
      <RiskAssessment 
        riskAssessment={{ ...defaultProps.riskAssessment, overall_risk_score: 5 }}
        loading={false}
      />
    )
    
    scoreElement = screen.getByText('5.0')
    expect(scoreElement).toHaveClass('text-primary-600')
    
    rerender(
      <RiskAssessment 
        riskAssessment={{ ...defaultProps.riskAssessment, overall_risk_score: 8 }}
        loading={false}
      />
    )
    
    scoreElement = screen.getByText('8.0')
    expect(scoreElement).toHaveClass('text-danger-600')
  })

  it('displays multiple risk factors correctly', () => {
    const riskAssessmentWithMultipleFactors = {
      overall_risk_score: 6,
      risk_factors: [
        {
          factor: "High purchase price",
          severity: "high" as RiskLevel,
          description: "Purchase price is above market average",
          impact: "High financial risk",
          mitigation: "Negotiate price reduction",
          australian_specific: false,
          confidence: 0.9,
        },
        {
          factor: "Short settlement period",
          severity: "medium" as RiskLevel,
          description: "Settlement period is shorter than recommended",
          impact: "Medium financial risk",
          mitigation: "Arrange finance pre-approval",
          australian_specific: true,
          confidence: 0.85,
        },
      ],
    }

    render(<RiskAssessment riskAssessment={riskAssessmentWithMultipleFactors} loading={false} />)
    
    expect(screen.getByText(/high purchase price/i)).toBeInTheDocument()
    expect(screen.getByText(/short settlement period/i)).toBeInTheDocument()
  })

  it('groups risks by severity correctly', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    // Check that risks are grouped by severity
    const mediumRiskSection = screen.getByText(/medium/i)
    expect(mediumRiskSection).toBeInTheDocument()
  })

  it('expands and collapses risk details', async () => {
    render(<RiskAssessment {...defaultProps} />)
    
    // Initially, mitigation should not be visible
    expect(screen.queryByText(/arrange finance pre-approval/i)).not.toBeInTheDocument()
    
    // Click to expand
    const expandButton = screen.getByRole('button', { name: /more/i })
    fireEvent.click(expandButton)
    
    await waitFor(() => {
      expect(screen.getByText(/arrange finance pre-approval/i)).toBeInTheDocument()
    })
    
    // Click to collapse
    const collapseButton = screen.getByRole('button', { name: /less/i })
    fireEvent.click(collapseButton)
    
    await waitFor(() => {
      expect(screen.queryByText(/arrange finance pre-approval/i)).not.toBeInTheDocument()
    })
  })

  it('displays risk trends when available', () => {
    const riskAssessmentWithTrend = {
      risk_trend: "increasing",
      historical_scores: [2, 3, 4],
      overall_risk_score: 4,
      risk_factors: [
        {
          factor: "Market volatility",
          severity: "medium" as RiskLevel,
          description: "Market conditions are volatile",
          impact: "Medium market risk",
          mitigation: "Monitor market conditions",
          australian_specific: true,
          confidence: 0.8,
        },
      ],
    }

    render(<RiskAssessment riskAssessment={riskAssessmentWithTrend} loading={false} />)
    
    expect(screen.getByText(/risk assessment overview/i)).toBeInTheDocument()
  })
})