import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle, 
  Clock, 
  AlertCircle,
  FileText,
  Search,
  Shield,
  TrendingUp,
  FileCheck,
  Zap
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useAnalysisStore } from '@/store/analysisStore'
import { cn, formatRelativeTime } from '@/utils'
import { Button } from '@/components/ui/Button'

interface AnalysisProgressProps {
  className?: string
}

const steps = [
  {
    key: 'validating_input',
    icon: CheckCircle,
    title: 'Validating Document',
    description: 'Checking file format and content quality'
  },
  {
    key: 'processing_document',
    icon: FileText,
    title: 'Extracting Text',
    description: 'Reading contract content using OCR technology'
  },
  {
    key: 'extracting_terms',
    icon: Search,
    title: 'Identifying Terms',
    description: 'Finding key contract clauses and conditions'
  },
  {
    key: 'analyzing_compliance',
    icon: Shield,
    title: 'Checking Compliance',
    description: 'Verifying Australian legal requirements'
  },
  {
    key: 'assessing_risks',
    icon: AlertCircle,
    title: 'Assessing Risks',
    description: 'Evaluating potential issues and concerns'
  },
  {
    key: 'generating_recommendations',
    icon: TrendingUp,
    title: 'Creating Recommendations',
    description: 'Generating actionable advice'
  },
  {
    key: 'compiling_report',
    icon: FileCheck,
    title: 'Finalizing Report',
    description: 'Preparing comprehensive analysis'
  }
]

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ className }) => {
  const { 
    isAnalyzing, 
    analysisProgress, 
    currentAnalysis, 
    wsService, 
    analysisError 
  } = useAnalysisStore()

  if (!isAnalyzing && !currentAnalysis) {
    return null
  }

  const currentStepIndex = analysisProgress 
    ? steps.findIndex(step => step.key === analysisProgress.current_step)
    : -1

  const progress = analysisProgress?.progress_percent || 0
  const isConnected = wsService?.isWebSocketConnected() || false
  
  const handleCancelAnalysis = () => {
    if (wsService && isAnalyzing) {
      if (confirm('Are you sure you want to cancel this analysis? This action cannot be undone.')) {
        wsService.cancelAnalysis();
      }
    }
  }

  return (
    <Card className={cn('w-full shadow-sm border-0 bg-gradient-to-br from-white to-neutral-50/50', className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span>Contract Analysis</span>
                {isAnalyzing && (
                  <span className="text-sm font-normal text-neutral-500">
                    - In Progress
                  </span>
                )}
              </div>
              {/* Connection Status Indicator */}
              {isAnalyzing && (
                <div className="flex items-center gap-1 mt-1">
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    isConnected ? "bg-green-500" : "bg-red-500"
                  )} 
                  title={isConnected ? "Connected" : "Disconnected"}
                  />
                  <span className="text-xs text-neutral-500">
                    {isConnected ? "Connected" : "Disconnected"}
                  </span>
                </div>
              )}
            </div>
          </CardTitle>
          
          <div className="flex items-center gap-3">
            {analysisProgress && (
              <div className="text-right">
                <div className="text-2xl font-bold text-primary-600">
                  {progress}%
                </div>
                <div className="text-xs text-neutral-500">
                  Complete
                </div>
              </div>
            )}
            
            {/* Cancel Button */}
            {isAnalyzing && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancelAnalysis}
                className="text-red-600 border-red-200 hover:bg-red-50 shadow-sm"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Overall Progress Bar */}
        {isAnalyzing && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-600 font-medium">Overall Progress</span>
              <span className="font-bold text-primary-600">{progress}%</span>
            </div>
            <div className="w-full bg-neutral-200 rounded-full h-2 overflow-hidden">
              <motion.div
                className="bg-gradient-to-r from-primary-500 to-primary-600 h-2 rounded-full shadow-sm"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>
        )}

        {/* Current Step Description */}
        {analysisProgress && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 bg-gradient-to-r from-primary-50 to-primary-100/50 rounded-xl border border-primary-200 shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center shadow-sm">
                <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
              </div>
              <div>
                <p className="font-semibold text-primary-900">
                  {analysisProgress.step_description || 'Processing...'}
                </p>
                <p className="text-sm text-primary-700">
                  This may take a few moments
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Step List */}
        <div className="space-y-3">
          {steps.map((step, index) => {
            const isCompleted = currentStepIndex > index || (!isAnalyzing && currentAnalysis)
            const isCurrent = currentStepIndex === index && isAnalyzing
            const isPending = currentStepIndex < index && isAnalyzing
            
            const IconComponent = step.icon

            return (
              <motion.div
                key={step.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={cn(
                  'flex items-start gap-3 p-3 rounded-xl transition-all duration-200 shadow-sm',
                  isCompleted && 'bg-gradient-to-r from-success-50 to-success-100/50 border border-success-200',
                  isCurrent && 'bg-gradient-to-r from-primary-50 to-primary-100/50 border border-primary-200 shadow-md',
                  isPending && 'bg-neutral-50 border border-neutral-200'
                )}
              >
                <div className={cn(
                  'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 shadow-sm',
                  isCompleted && 'bg-gradient-to-br from-success-500 to-success-600 text-white',
                  isCurrent && 'bg-gradient-to-br from-primary-500 to-primary-600 text-white',
                  isPending && 'bg-neutral-300 text-neutral-600'
                )}>
                  {isCompleted ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : isCurrent ? (
                    <IconComponent className="w-4 h-4 animate-pulse" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <h4 className={cn(
                    'font-semibold transition-colors duration-200',
                    isCompleted && 'text-success-900',
                    isCurrent && 'text-primary-900',
                    isPending && 'text-neutral-600'
                  )}>
                    {step.title}
                  </h4>
                  <p className={cn(
                    'text-sm mt-1 transition-colors duration-200',
                    isCompleted && 'text-success-700',
                    isCurrent && 'text-primary-700',
                    isPending && 'text-neutral-500'
                  )}>
                    {step.description}
                  </p>
                </div>

                <AnimatePresence>
                  {isCompleted && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="flex-shrink-0"
                    >
                      <CheckCircle className="w-5 h-5 text-success-600" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
        </div>

        {/* Completion Message */}
        {!isAnalyzing && currentAnalysis && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center p-6 bg-gradient-to-br from-success-50 to-success-100/50 rounded-xl border border-success-200 shadow-sm"
          >
            <div className="w-12 h-12 bg-gradient-to-br from-success-500 to-success-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
              <CheckCircle className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-bold text-success-900 mb-2">
              Analysis Complete!
            </h3>
            <p className="text-success-700 mb-4">
              Your contract has been successfully analyzed. Review the results below.
            </p>
            <div className="text-sm text-success-600 font-medium">
              Completed {formatRelativeTime(currentAnalysis.analysis_timestamp)}
            </div>
          </motion.div>
        )}

        {/* Error State */}
        {(analysisError || (!isAnalyzing && !currentAnalysis)) && (
          <div className="text-center p-6 bg-gradient-to-br from-danger-50 to-danger-100/50 rounded-xl border border-danger-200 shadow-sm">
            <div className="w-12 h-12 bg-gradient-to-br from-danger-500 to-danger-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
              <AlertCircle className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-bold text-danger-900 mb-2">
              Analysis Failed
            </h3>
            <p className="text-danger-700 mb-4">
              {analysisError || "There was an issue analyzing your contract. Please try uploading again."}
            </p>
            
            {/* Connection Status for Errors */}
            {!isConnected && isAnalyzing && (
              <div className="text-sm text-amber-700 bg-gradient-to-r from-amber-50 to-amber-100/50 p-3 rounded-lg border border-amber-200">
                <div className="flex items-center justify-center gap-2">
                  <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
                  Reconnecting to analysis service...
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Real-time Status Info */}
        {isAnalyzing && analysisProgress && (
          <div className="text-xs text-neutral-500 text-center">
            Last updated: {new Date().toLocaleTimeString()}
            {isConnected && (
              <span className="ml-2 text-green-600">● Live</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AnalysisProgress