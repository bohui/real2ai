/**
 * Test RiskAssessment component
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'
import { RiskAssessment } from '../RiskAssessment'
import { mockAnalysis } from '@/test/utils'

describe('RiskAssessment Component', () => {
  const defaultProps = {
    riskAssessment: mockAnalysis.analysis_result.risk_assessment,
    loading: false,
  }

  it('renders risk assessment with overall score', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/risk assessment/i)).toBeInTheDocument()
    expect(screen.getByText(/overall risk score/i)).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument() // Risk score
  })

  it('displays risk factors', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/short settlement period/i)).toBeInTheDocument()
    expect(screen.getByText(/settlement period is shorter than recommended/i)).toBeInTheDocument()
  })

  it('shows risk severity levels', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    const riskFactor = screen.getByText(/short settlement period/i).closest('[data-testid="risk-factor"]')
    expect(riskFactor).toHaveClass('border-yellow-200') // Medium severity
  })

  it('displays risk mitigation suggestions', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/arrange finance pre-approval/i)).toBeInTheDocument()
  })

  it('shows confidence scores', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/85%/i)).toBeInTheDocument() // Confidence score
  })

  it('indicates Australian-specific risks', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    const australianBadge = screen.getByText(/australian specific/i)
    expect(australianBadge).toBeInTheDocument()
    expect(australianBadge).toHaveClass('bg-green-100')
  })

  it('handles loading state', () => {
    render(<RiskAssessment {...defaultProps} loading={true} />)
    
    expect(screen.getByText(/analyzing risks/i)).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
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
    
    let scoreElement = screen.getByText('1')
    expect(scoreElement.closest('[data-testid="risk-score"]')).toHaveClass('text-green-600')
    
    rerender(
      <RiskAssessment 
        riskAssessment={{ ...defaultProps.riskAssessment, overall_risk_score: 5 }}
        loading={false}
      />
    )
    
    scoreElement = screen.getByText('5')
    expect(scoreElement.closest('[data-testid="risk-score"]')).toHaveClass('text-yellow-600')
    
    rerender(
      <RiskAssessment 
        riskAssessment={{ ...defaultProps.riskAssessment, overall_risk_score: 8 }}
        loading={false}
      />
    )
    
    scoreElement = screen.getByText('8')
    expect(scoreElement.closest('[data-testid="risk-score"]')).toHaveClass('text-red-600')
  })

  it('shows impact information', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    expect(screen.getByText(/medium financial risk/i)).toBeInTheDocument()
  })

  it('groups risk factors by severity', () => {
    const riskAssessmentWithMultipleFactors = {
      overall_risk_score: 5,
      risk_factors: [
        {
          factor: 'High risk factor',
          severity: 'high',
          description: 'High risk description',
          impact: 'High impact',
          mitigation: 'High mitigation',
          australian_specific: true,
          confidence: 0.9,
        },
        {
          factor: 'Low risk factor',
          severity: 'low',
          description: 'Low risk description',
          impact: 'Low impact',
          mitigation: 'Low mitigation',
          australian_specific: false,
          confidence: 0.7,
        },
      ],
    }
    
    render(<RiskAssessment riskAssessment={riskAssessmentWithMultipleFactors} loading={false} />)
    
    const highRiskSection = screen.getByText(/high risk factors/i)
    const lowRiskSection = screen.getByText(/low risk factors/i)
    
    expect(highRiskSection).toBeInTheDocument()
    expect(lowRiskSection).toBeInTheDocument()
  })

  it('has expandable risk factor details', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    const riskFactor = screen.getByText(/short settlement period/i)
    fireEvent.click(riskFactor)
    
    // Should show additional details when expanded
    expect(screen.getByText(/medium financial risk/i)).toBeVisible()
    expect(screen.getByText(/arrange finance pre-approval/i)).toBeVisible()
  })

  it('has proper accessibility attributes', () => {
    render(<RiskAssessment {...defaultProps} />)
    
    const riskAssessment = screen.getByRole('region', { name: /risk assessment/i })
    expect(riskAssessment).toBeInTheDocument()
    
    const riskScore = screen.getByLabelText(/overall risk score/i)
    expect(riskScore).toBeInTheDocument()
    
    const riskFactors = screen.getAllByRole('button', { name: /risk factor/i })
    expect(riskFactors.length).toBeGreaterThan(0)
  })

  it('shows risk trend indicator', () => {
    const riskAssessmentWithTrend = {
      ...defaultProps.riskAssessment,
      risk_trend: 'increasing',
      historical_scores: [2, 2.5, 3],
    }
    
    render(<RiskAssessment riskAssessment={riskAssessmentWithTrend} loading={false} />)
    
    expect(screen.getByText(/risk trend/i)).toBeInTheDocument()
    expect(screen.getByText(/increasing/i)).toBeInTheDocument()
  })
})