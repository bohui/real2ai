import React from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  TrendingUp, 
  FileText,
  MapPin,
  Calendar,
  DollarSign,
  Users,
  ArrowRight
} from 'lucide-react'

import Button from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import StatusBadge from '@/components/ui/StatusBadge'
import RiskIndicator from '@/components/ui/RiskIndicator'
import { cn } from '@/utils'
import { ContractAnalysisResult, AustralianState } from '@/types'

interface EnhancedContractCardProps {
  analysis: ContractAnalysisResult
  showDetails?: boolean
  className?: string
}

const EnhancedContractCard: React.FC<EnhancedContractCardProps> = ({ 
  analysis, 
  showDetails = false,
  className 
}) => {
  // Extract contract information
  const getContractInfo = () => {
    const terms = analysis.contract_terms || {}
    
    return {
      title: getContractTitle(),
      subtitle: getContractSubtitle(),
      parties: terms.parties || {},
      propertyDetails: terms.property_details || {},
      financialDetails: terms.financial_details || {},
      keyDates: terms.key_dates || {}
    }
  }

  const getContractTitle = () => {
    const terms = analysis.contract_terms || {}
    
    if (terms.property_details?.address) {
      return terms.property_details.address
    }
    
    if (terms.contract_type) {
      const typeMap: Record<string, string> = {
        'purchase_agreement': 'Property Purchase Agreement',
        'lease_agreement': 'Lease Agreement',
        'off_plan': 'Off-Plan Purchase Contract',
        'auction': 'Auction Contract'
      }
      return typeMap[terms.contract_type] || 'Contract Document'
    }
    
    return 'Contract Analysis'
  }

  const getContractSubtitle = () => {
    const terms = analysis.contract_terms || {}
    
    if (terms.parties?.buyer && terms.parties?.seller) {
      return `${terms.parties.buyer} ← ${terms.parties.seller}`
    }
    
    if (terms.property_details?.property_type) {
      return `${terms.property_details.property_type} • ${getStateFullName(analysis.australian_state)}`
    }
    
    return getStateFullName(analysis.australian_state)
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

  const getRiskLevel = (score: number) => {
    if (score >= 7) return { level: 'High Risk', color: 'danger' }
    if (score >= 5) return { level: 'Medium Risk', color: 'warning' }
    return { level: 'Low Risk', color: 'success' }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount)
  }

  const contractInfo = getContractInfo()
  const risk = getRiskLevel(analysis.executive_summary.overall_risk_score)
  const isCompleted = analysis.analysis_status === 'completed'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={className}
    >
      <Card 
        variant={isCompleted ? 'legal' : 'default'} 
        interactive={true} 
        className="group"
      >
        <CardContent padding="lg">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-neutral-900 truncate mb-1">
                {contractInfo.title}
              </h3>
              <p className="text-sm text-neutral-600 mb-2">
                {contractInfo.subtitle}
              </p>
              
              {/* Status and Risk */}
              <div className="flex items-center gap-3">
                <StatusBadge 
                  status={analysis.analysis_status === 'completed' ? 'completed' : 'processing'} 
                  size="sm" 
                  variant="solid"
                />
                
                {isCompleted && (
                  <RiskIndicator 
                    level={analysis.executive_summary.overall_risk_score >= 7 ? 'high' : 
                           analysis.executive_summary.overall_risk_score >= 5 ? 'medium' : 'low'}
                    score={analysis.executive_summary.overall_risk_score}
                    variant="compact"
                    size="sm"
                  />
                )}
              </div>
            </div>
            
            {/* Analysis Date */}
            <div className="text-right">
              <div className="flex items-center text-sm text-neutral-500 mb-1">
                <Calendar className="w-4 h-4 mr-1" />
                {new Date(analysis.analysis_timestamp).toLocaleDateString('en-AU')}
              </div>
              {isCompleted && (
                <div className="text-lg font-bold text-neutral-900">
                  {analysis.executive_summary.overall_risk_score.toFixed(1)}/10
                </div>
              )}
            </div>
          </div>

        {/* Contract Details (if available and showDetails) */}
        {showDetails && isCompleted && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 p-4 bg-neutral-50 rounded-lg">
            {contractInfo.financialDetails.purchase_price && (
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-neutral-500" />
                <div>
                  <div className="text-xs text-neutral-500">Purchase Price</div>
                  <div className="font-medium text-neutral-900">
                    {formatCurrency(contractInfo.financialDetails.purchase_price)}
                  </div>
                </div>
              </div>
            )}
            
            {contractInfo.propertyDetails.property_type && (
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-neutral-500" />
                <div>
                  <div className="text-xs text-neutral-500">Property Type</div>
                  <div className="font-medium text-neutral-900">
                    {contractInfo.propertyDetails.property_type}
                  </div>
                </div>
              </div>
            )}
            
            {contractInfo.parties.buyer && (
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-neutral-500" />
                <div>
                  <div className="text-xs text-neutral-500">Parties</div>
                  <div className="font-medium text-neutral-900 truncate">
                    {contractInfo.parties.buyer}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Key Insights */}
        {isCompleted && analysis.executive_summary.critical_issues > 0 && (
          <div className="mb-4 p-3 bg-warning-50 border border-warning-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-warning-600" />
              <span className="text-sm font-medium text-warning-800">
                {analysis.executive_summary.critical_issues} Critical Issue{analysis.executive_summary.critical_issues !== 1 ? 's' : ''} Found
              </span>
            </div>
            <p className="text-xs text-warning-700">
              Requires immediate attention before proceeding with contract
            </p>
          </div>
        )}

          {/* Compliance Status */}
          {isCompleted && (
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <StatusBadge 
                  status={analysis.executive_summary.compliance_status === 'compliant' ? 'compliant' : 'warning'} 
                  size="sm" 
                  variant="dot"
                  label={analysis.executive_summary.compliance_status === 'compliant' 
                    ? `Compliant with ${getStateFullName(analysis.australian_state)} law`
                    : 'Compliance issues identified'
                  }
                />
              </div>
              <div className="text-sm text-neutral-500">
                {analysis.executive_summary.total_recommendations} recommendation{analysis.executive_summary.total_recommendations !== 1 ? 's' : ''}
              </div>
            </div>
          )}
        </CardContent>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100 flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm text-neutral-500">
            <div className="flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              <span>Confidence: {isCompleted ? `${analysis.overall_confidence}%` : 'Processing...'}</span>
            </div>
            {isCompleted && (
              <div className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                <span>{analysis.processing_time}s analysis</span>
              </div>
            )}
          </div>
          
          <Link to={`/app/analysis/${analysis.contract_id}`}>
            <Button variant="ghost" size="sm" className="group">
              {isCompleted ? 'View Results' : 'View Progress'}
              <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-0.5 transition-transform" />
            </Button>
          </Link>
        </div>
      </Card>
    </motion.div>
  )
}

export default EnhancedContractCard