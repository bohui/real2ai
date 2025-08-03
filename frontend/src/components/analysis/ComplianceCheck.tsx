import React from 'react'
import { motion } from 'framer-motion'
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Info,
  DollarSign,
  Calendar,
  FileText,
  ExternalLink
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { ContractAnalysisResult } from '@/types'
import { formatCurrency, getStateFullName, cn } from '@/utils'

interface ComplianceCheckProps {
  analysis: ContractAnalysisResult
  className?: string
}

const ComplianceCheck: React.FC<ComplianceCheckProps> = ({ analysis, className }) => {
  const compliance = analysis.compliance_check
  const stampDuty = compliance?.stamp_duty_calculation
  
  const complianceItems = [
    {
      key: 'state_compliance',
      title: 'State Law Compliance',
      description: `Compliance with ${getStateFullName(analysis.australian_state)} property laws`,
      status: compliance?.state_compliance,
      icon: CheckCircle
    },
    {
      key: 'cooling_off',
      title: 'Cooling-off Period',
      description: 'Statutory cooling-off period requirements',
      status: compliance?.cooling_off_compliance,
      icon: Calendar,
      details: compliance?.cooling_off_details
    },
    {
      key: 'disclosures',
      title: 'Mandatory Disclosures',
      description: 'Required vendor disclosures and statements',
      status: compliance?.mandatory_disclosures && compliance.mandatory_disclosures.length > 0,
      icon: FileText,
      details: compliance?.mandatory_disclosures
    }
  ]

  return (
    <div className={cn('space-y-6', className)}>
      {/* Overall Compliance Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-primary-600" />
            Compliance Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="text-center">
              <div className={cn(
                'inline-flex items-center justify-center w-20 h-20 rounded-full text-4xl mb-4',
                compliance?.state_compliance 
                  ? 'bg-success-100 text-success-600' 
                  : 'bg-danger-100 text-danger-600'
              )}>
                {compliance?.state_compliance ? '✅' : '❌'}
              </div>
              <h3 className={cn(
                'text-lg font-semibold mb-2',
                compliance?.state_compliance ? 'text-success-900' : 'text-danger-900'
              )}>
                {compliance?.state_compliance ? 'Compliant' : 'Non-Compliant'}
              </h3>
              <p className="text-sm text-neutral-500">
                Overall compliance status for {getStateFullName(analysis.australian_state)}
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-neutral-900 mb-2">
                  Analysis Details
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-600">State:</span>
                    <span className="font-medium">{getStateFullName(analysis.australian_state)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Analysis Date:</span>
                    <span className="font-medium">
                      {new Date(analysis.analysis_timestamp).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Confidence:</span>
                    <span className="font-medium">
                      {Math.round(analysis.overall_confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Compliance Items */}
      <Card>
        <CardHeader>
          <CardTitle>Compliance Checklist</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {complianceItems.map((item, index) => {
              const IconComponent = item.icon
              
              return (
                <motion.div
                  key={item.key}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={cn(
                    'flex items-start gap-4 p-4 rounded-lg border',
                    item.status 
                      ? 'bg-success-50 border-success-200' 
                      : 'bg-danger-50 border-danger-200'
                  )}
                >
                  <div className={cn(
                    'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
                    item.status 
                      ? 'bg-success-600 text-white' 
                      : 'bg-danger-600 text-white'
                  )}>
                    {item.status ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                  </div>

                  <div className="flex-1">
                    <h4 className={cn(
                      'font-medium mb-1',
                      item.status ? 'text-success-900' : 'text-danger-900'
                    )}>
                      {item.title}
                    </h4>
                    <p className={cn(
                      'text-sm',
                      item.status ? 'text-success-700' : 'text-danger-700'
                    )}>
                      {item.description}
                    </p>

                    {/* Additional Details */}
                    {item.details && (
                      <div className="mt-3 pt-3 border-t border-neutral-200">
                        {Array.isArray(item.details) ? (
                          <ul className="text-sm space-y-1">
                            {item.details.map((detail, idx) => (
                              <li key={idx} className="flex items-center gap-2">
                                <div className="w-1 h-1 bg-neutral-400 rounded-full" />
                                {detail}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-sm">
                            <pre className="whitespace-pre-wrap font-mono bg-neutral-100 p-2 rounded">
                              {JSON.stringify(item.details, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Stamp Duty Calculation */}
      {stampDuty && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-primary-600" />
              Stamp Duty Calculation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="text-center p-4 bg-primary-50 rounded-lg">
                  <div className="text-3xl font-bold text-primary-600 mb-2">
                    {formatCurrency(stampDuty.total_duty)}
                  </div>
                  <p className="text-sm text-primary-700">
                    Total Stamp Duty Payable
                  </p>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">Purchase Price:</span>
                    <span className="font-medium">
                      {formatCurrency(stampDuty.purchase_price)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">Base Duty:</span>
                    <span className="font-medium">
                      {formatCurrency(stampDuty.base_duty)}
                    </span>
                  </div>
                  {stampDuty.exemptions > 0 && (
                    <div className="flex justify-between text-sm text-success-600">
                      <span>Exemptions:</span>
                      <span className="font-medium">
                        -{formatCurrency(stampDuty.exemptions)}
                      </span>
                    </div>
                  )}
                  {stampDuty.surcharges > 0 && (
                    <div className="flex justify-between text-sm text-warning-600">
                      <span>Surcharges:</span>
                      <span className="font-medium">
                        +{formatCurrency(stampDuty.surcharges)}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-neutral-900">
                  Calculation Details
                </h4>
                
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-neutral-600">State:</span>
                    <span className="font-medium">{stampDuty.state}</span>
                  </div>
                  
                  {stampDuty.is_first_home_buyer && (
                    <div className="flex items-center gap-2 text-success-600">
                      <CheckCircle className="w-4 h-4" />
                      <span>First Home Buyer</span>
                    </div>
                  )}
                  
                  {stampDuty.is_foreign_buyer && (
                    <div className="flex items-center gap-2 text-warning-600">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Foreign Buyer Surcharge Applied</span>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-neutral-200">
                  <p className="text-xs text-neutral-500 mb-2">
                    💡 This is an estimate based on current rates. Consult your conveyancer for exact calculations.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    rightIcon={<ExternalLink className="w-4 h-4" />}
                    onClick={() => window.open(`https://www.revenue.${stampDuty.state.toLowerCase()}.gov.au`, '_blank')}
                  >
                    Official {stampDuty.state} Revenue Office
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Compliance Issues */}
      {compliance?.compliance_issues && compliance.compliance_issues.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-danger-600">
              <AlertTriangle className="w-5 h-5" />
              Compliance Issues ({compliance.compliance_issues.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {compliance.compliance_issues.map((issue, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start gap-3 p-3 bg-danger-50 rounded-lg border border-danger-200"
                >
                  <AlertTriangle className="w-5 h-5 text-danger-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-danger-900 font-medium">
                      {issue}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Warnings */}
      {compliance?.warnings && compliance.warnings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-warning-600">
              <Info className="w-5 h-5" />
              Warnings & Advisories ({compliance.warnings.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {compliance.warnings.map((warning, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start gap-3 p-3 bg-warning-50 rounded-lg border border-warning-200"
                >
                  <Info className="w-5 h-5 text-warning-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-warning-900">
                      {warning}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Legal References */}
      {compliance?.legal_references && compliance.legal_references.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary-600" />
              Legal References
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {compliance.legal_references.map((reference, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 text-sm text-neutral-700"
                >
                  <div className="w-1 h-1 bg-primary-600 rounded-full" />
                  {reference}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default ComplianceCheck