import React from 'react'
import { motion } from 'framer-motion'
import { 
  AlertTriangle,
  Shield,
  TrendingUp,
  Info,
  ChevronRight,
  AlertCircle
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { ContractAnalysisResult, RiskLevel } from '@/types'
import { getRiskLevelColor, getRiskLevelIcon, cn } from '@/utils'

interface RiskAssessmentProps {
  analysis: ContractAnalysisResult
  className?: string
}

const RiskAssessment: React.FC<RiskAssessmentProps> = ({ analysis, className }) => {
  const [expandedRisk, setExpandedRisk] = React.useState<string | null>(null)
  
  const riskAssessment = analysis.risk_assessment
  const riskFactors = riskAssessment?.risk_factors || []
  
  // Group risks by severity
  const groupedRisks = riskFactors.reduce((groups, risk) => {
    const severity = risk.severity
    if (!groups[severity]) groups[severity] = []
    groups[severity].push(risk)
    return groups
  }, {} as Record<RiskLevel, typeof riskFactors>)

  const getRiskScoreColor = (score: number) => {
    if (score >= 8) return 'text-danger-600 bg-danger-100'
    if (score >= 6) return 'text-warning-600 bg-warning-100'
    if (score >= 4) return 'text-primary-600 bg-primary-100'
    return 'text-success-600 bg-success-100'
  }

  const getRiskScoreLabel = (score: number) => {
    if (score >= 8) return 'High Risk'
    if (score >= 6) return 'Moderate Risk'
    if (score >= 4) return 'Low-Moderate Risk'
    return 'Low Risk'
  }

  const overallRiskScore = riskAssessment?.overall_risk_score || 0

  return (
    <div className={cn('space-y-6', className)}>
      {/* Overall Risk Score */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-600" />
            Risk Assessment Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Risk Score */}
            <div className="text-center">
              <div className={cn(
                'inline-flex items-center justify-center w-20 h-20 rounded-full text-2xl font-bold mb-3',
                getRiskScoreColor(overallRiskScore)
              )}>
                {overallRiskScore.toFixed(1)}
              </div>
              <h3 className="font-semibold text-neutral-900">
                {getRiskScoreLabel(overallRiskScore)}
              </h3>
              <p className="text-sm text-neutral-500 mt-1">
                Overall Risk Score (0-10)
              </p>
            </div>

            {/* Risk Distribution */}
            <div className="md:col-span-2">
              <h4 className="font-medium text-neutral-900 mb-3">Risk Distribution</h4>
              <div className="space-y-2">
                {(['critical', 'high', 'medium', 'low'] as RiskLevel[]).map(severity => {
                  const count = groupedRisks[severity]?.length || 0
                  const percentage = riskFactors.length > 0 ? (count / riskFactors.length) * 100 : 0
                  
                  return (
                    <div key={severity} className="flex items-center gap-3">
                      <div className="w-20 text-sm capitalize font-medium">
                        {getRiskLevelIcon(severity)} {severity}
                      </div>
                      <div className="flex-1 bg-neutral-200 rounded-full h-2">
                        <div
                          className={cn(
                            'h-2 rounded-full transition-all duration-500',
                            severity === 'critical' && 'bg-danger-600',
                            severity === 'high' && 'bg-warning-600',
                            severity === 'medium' && 'bg-primary-600',
                            severity === 'low' && 'bg-success-600'
                          )}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <div className="w-12 text-sm text-neutral-600 text-right">
                        {count}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Factors by Severity */}
      {(['critical', 'high', 'medium', 'low'] as RiskLevel[]).map(severity => {
        const risks = groupedRisks[severity] || []
        if (risks.length === 0) return null

        return (
          <Card key={severity}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 capitalize">
                {severity === 'critical' && <AlertCircle className="w-5 h-5 text-danger-600" />}
                {severity === 'high' && <AlertTriangle className="w-5 h-5 text-warning-600" />}
                {severity === 'medium' && <Info className="w-5 h-5 text-primary-600" />}
                {severity === 'low' && <TrendingUp className="w-5 h-5 text-success-600" />}
                {severity} Risk Factors ({risks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {risks.map((risk, index) => (
                  <motion.div
                    key={`${severity}-${index}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={cn(
                      'border rounded-lg transition-all duration-200',
                      getRiskLevelColor(risk.severity)
                    )}
                  >
                    <div className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-semibold text-neutral-900">
                              {risk.factor}
                            </h4>
                            {risk.australian_specific && (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-secondary-100 text-secondary-800">
                                🇦🇺 AU Specific
                              </span>
                            )}
                            <span className="text-xs text-neutral-500">
                              {Math.round(risk.confidence * 100)}% confidence
                            </span>
                          </div>
                          <p className="text-sm text-neutral-700 mb-2">
                            {risk.description}
                          </p>
                          
                          {expandedRisk === `${severity}-${index}` && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              className="space-y-3 pt-3 border-t border-neutral-200"
                            >
                              <div>
                                <h5 className="font-medium text-neutral-900 mb-1">
                                  Potential Impact
                                </h5>
                                <p className="text-sm text-neutral-700">
                                  {risk.impact}
                                </p>
                              </div>
                              <div>
                                <h5 className="font-medium text-neutral-900 mb-1">
                                  Mitigation Strategy
                                </h5>
                                <p className="text-sm text-neutral-700">
                                  {risk.mitigation}
                                </p>
                              </div>
                            </motion.div>
                          )}
                        </div>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedRisk(
                            expandedRisk === `${severity}-${index}` 
                              ? null 
                              : `${severity}-${index}`
                          )}
                          rightIcon={
                            <ChevronRight className={cn(
                              'w-4 h-4 transition-transform duration-200',
                              expandedRisk === `${severity}-${index}` && 'rotate-90'
                            )} />
                          }
                        >
                          {expandedRisk === `${severity}-${index}` ? 'Less' : 'More'}
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}

      {/* No Risks Found */}
      {riskFactors.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Shield className="w-12 h-12 text-success-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">
              No Significant Risks Identified
            </h3>
            <p className="text-neutral-500">
              This contract appears to have minimal risk factors based on our analysis.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default RiskAssessment