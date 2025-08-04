import React from 'react'
import { motion } from 'framer-motion'
import { 
  AlertTriangle, 
  Shield, 
  TrendingUp, 
  Scale, 
  FileText,
  Info
} from 'lucide-react'

import { cn } from '@/utils'
import { RiskFactor, AustralianState } from '@/types'

interface RiskVisualizationProps {
  riskScore: number
  riskFactors: RiskFactor[]
  state: AustralianState
  complianceStatus: 'compliant' | 'non-compliant'
  industryBenchmark?: number
  className?: string
}

const RiskVisualization: React.FC<RiskVisualizationProps> = ({
  riskScore,
  riskFactors,
  state,
  complianceStatus,
  industryBenchmark = 5.8,
  className
}) => {
  const getRiskLevel = (score: number) => {
    if (score >= 7) return { level: 'High Risk', color: 'danger', icon: AlertTriangle }
    if (score >= 5) return { level: 'Medium Risk', color: 'warning', icon: TrendingUp }
    return { level: 'Low Risk', color: 'success', icon: Shield }
  }

  const getStateFullName = (state: AustralianState) => {
    const stateNames: Record<AustralianState, string> = {
      'NSW': 'New South Wales',
      'VIC': 'Victoria',
      'QLD': 'Queensland', 
      'SA': 'South Australia',
      'WA': 'Western Australia',
      'TAS': 'Tasmania',
      'NT': 'Northern Territory',
      'ACT': 'Australian Capital Territory'
    }
    return stateNames[state] || state
  }

  const risk = getRiskLevel(riskScore)
  const RiskIcon = risk.icon
  
  const highRiskFactors = riskFactors.filter(f => f.severity === 'high' || f.severity === 'critical')
  const mediumRiskFactors = riskFactors.filter(f => f.severity === 'medium')
  const lowRiskFactors = riskFactors.filter(f => f.severity === 'low')

  const riskComparison = riskScore - industryBenchmark
  const isAboveAverage = riskComparison > 0

  return (
    <div className={cn('space-y-6', className)}>
      {/* Main Risk Score Display */}
      <div className="bg-white rounded-lg border border-neutral-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-1">
              Overall Risk Assessment
            </h3>
            <p className="text-sm text-neutral-600">
              Analysis based on {getStateFullName(state)} legal requirements
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-neutral-900 mb-1">
              {riskScore.toFixed(1)}
            </div>
            <div className="text-sm text-neutral-500">out of 10</div>
          </div>
        </div>

        {/* Risk Level Indicator */}
        <div className="flex items-center gap-4 mb-6">
          <div className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg",
            risk.color === 'danger'
              ? "bg-danger-100 text-danger-700"
              : risk.color === 'warning'
              ? "bg-warning-100 text-warning-700"
              : "bg-success-100 text-success-700"
          )}>
            <RiskIcon className="w-5 h-5" />
            <span className="font-medium">{risk.level}</span>
          </div>
          
          <div className="flex items-center gap-2 text-sm text-neutral-600">
            <TrendingUp className="w-4 h-4" />
            <span>
              {isAboveAverage ? 'Above' : 'Below'} average by {Math.abs(riskComparison).toFixed(1)} points
            </span>
          </div>
        </div>

        {/* Risk Score Gauge */}
        <div className="mb-6">
          <div className="flex justify-between text-xs text-neutral-500 mb-2">
            <span>Low Risk</span>
            <span>Medium Risk</span>
            <span>High Risk</span>
          </div>
          <div className="relative h-3 bg-gradient-to-r from-success-200 via-warning-200 to-danger-200 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(riskScore / 10) * 100}%` }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="absolute left-0 top-0 h-full bg-gradient-to-r from-success-500 via-warning-500 to-danger-500 rounded-full"
            />
            {/* Industry benchmark marker */}
            <div 
              className="absolute top-0 w-0.5 h-full bg-neutral-700"
              style={{ left: `${(industryBenchmark / 10) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-neutral-400 mt-1">
            <span>0</span>
            <span className="text-neutral-700">Industry avg: {industryBenchmark}</span>
            <span>10</span>
          </div>
        </div>

        {/* Compliance Status */}
        <div className={cn(
          "flex items-center gap-3 p-4 rounded-lg",
          complianceStatus === 'compliant'
            ? "bg-success-50 border border-success-200"
            : "bg-danger-50 border border-danger-200"
        )}>
          <div className={cn(
            "w-3 h-3 rounded-full",
            complianceStatus === 'compliant' ? "bg-success-500" : "bg-danger-500"
          )} />
          <div className="flex-1">
            <div className={cn(
              "font-medium",
              complianceStatus === 'compliant' ? "text-success-800" : "text-danger-800"
            )}>
              {complianceStatus === 'compliant' 
                ? `Compliant with ${getStateFullName(state)} law`
                : 'Compliance issues identified'
              }
            </div>
            <div className={cn(
              "text-sm",
              complianceStatus === 'compliant' ? "text-success-700" : "text-danger-700"
            )}>
              {complianceStatus === 'compliant'
                ? 'Contract meets regulatory requirements'
                : 'Review required before proceeding'
              }
            </div>
          </div>
          <Scale className={cn(
            "w-5 h-5",
            complianceStatus === 'compliant' ? "text-success-600" : "text-danger-600"
          )} />
        </div>
      </div>

      {/* Risk Factor Breakdown */}
      <div className="bg-white rounded-lg border border-neutral-200 p-6">
        <h4 className="text-lg font-semibold text-neutral-900 mb-4">
          Risk Factor Analysis
        </h4>

        {/* High Risk Factors */}
        {highRiskFactors.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-danger-600" />
              <h5 className="font-medium text-danger-800">
                Critical Issues ({highRiskFactors.length})
              </h5>
            </div>
            <div className="space-y-3">
              {highRiskFactors.map((factor, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="p-4 bg-danger-50 border border-danger-200 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h6 className="font-medium text-danger-900">{factor.factor}</h6>
                    <div className="flex items-center gap-2">
                      {factor.australian_specific && (
                        <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs rounded-full">
                          AU Specific
                        </span>
                      )}
                      <span className="text-xs text-danger-600">
                        {(factor.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-danger-800 mb-2">{factor.description}</p>
                  <div className="text-sm text-danger-700">
                    <strong>Impact:</strong> {factor.impact}
                  </div>
                  <div className="text-sm text-danger-700 mt-1">
                    <strong>Recommended Action:</strong> {factor.mitigation}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Medium Risk Factors */}
        {mediumRiskFactors.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-warning-600" />
              <h5 className="font-medium text-warning-800">
                Areas for Review ({mediumRiskFactors.length})
              </h5>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {mediumRiskFactors.map((factor, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="p-3 bg-warning-50 border border-warning-200 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-1">
                    <h6 className="font-medium text-warning-900 text-sm">{factor.factor}</h6>
                    {factor.australian_specific && (
                      <span className="px-1.5 py-0.5 bg-primary-100 text-primary-700 text-xs rounded">
                        AU
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-warning-800">{factor.description}</p>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Low Risk Factors Summary */}
        {lowRiskFactors.length > 0 && (
          <div className="p-4 bg-success-50 border border-success-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-5 h-5 text-success-600" />
              <h5 className="font-medium text-success-800">
                Compliant Areas ({lowRiskFactors.length})
              </h5>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {lowRiskFactors.map((factor, index) => (
                <div key={index} className="text-sm text-success-700">
                  • {factor.factor}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Legal Context Information */}
      <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-primary-600 mt-0.5" />
          <div>
            <h5 className="font-medium text-primary-900 mb-1">
              Australian Legal Context
            </h5>
            <p className="text-sm text-primary-800">
              This analysis is based on current {getStateFullName(state)} legislation and case law. 
              Risk scores are compared against similar contracts in the Australian property market. 
              Always consult with a qualified legal professional before making final decisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default RiskVisualization