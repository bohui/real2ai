import React from 'react'
import { motion } from 'framer-motion'
import { FileText, Shield, TrendingUp, CheckCircle } from 'lucide-react'

interface MobileOptimizedLoadingProps {
  title?: string
  subtitle?: string
  progress?: number
  currentStep?: string
  estimatedTime?: number
  className?: string
}

const MobileOptimizedLoading: React.FC<MobileOptimizedLoadingProps> = ({
  title = 'Analyzing Contract',
  subtitle = 'Our AI is reviewing your document...',
  progress = 0,
  currentStep = 'Processing document',
  estimatedTime,
  className = ''
}) => {
  const steps = [
    { icon: FileText, label: 'Document Processing', description: 'Extracting text and structure' },
    { icon: Shield, label: 'Risk Assessment', description: 'Identifying potential issues' },
    { icon: TrendingUp, label: 'Compliance Check', description: 'Verifying Australian law compliance' },
    { icon: CheckCircle, label: 'Final Analysis', description: 'Generating recommendations' }
  ]

  const currentStepIndex = Math.floor((progress / 100) * steps.length)

  return (
    <div className={`min-h-screen bg-neutral-50 flex flex-col ${className}`}>
      {/* Header */}
      <div className="bg-white border-b border-neutral-200 px-4 py-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-neutral-900 mb-2">{title}</h1>
          <p className="text-neutral-600">{subtitle}</p>
          {estimatedTime && (
            <p className="text-sm text-neutral-500 mt-2">
              Estimated time: {estimatedTime} minutes remaining
            </p>
          )}
        </div>
      </div>

      {/* Progress Section */}
      <div className="flex-1 flex flex-col justify-center px-4 py-8">
        {/* Animated Progress Ring */}
        <div className="flex justify-center mb-8">
          <div className="relative w-32 h-32">
            {/* Background circle */}
            <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="45"
                stroke="#e5e7eb"
                strokeWidth="6"
                fill="none"
              />
              {/* Progress circle */}
              <motion.circle
                cx="50"
                cy="50"
                r="45"
                stroke="#3b82f6"
                strokeWidth="6"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={283} // 2 * π * 45
                initial={{ strokeDashoffset: 283 }}
                animate={{ strokeDashoffset: 283 - (283 * progress) / 100 }}
                transition={{ duration: 0.5, ease: "easeInOut" }}
              />
            </svg>
            
            {/* Center content */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-2xl font-bold text-neutral-900">
                  {Math.round(progress)}%
                </div>
                <div className="text-xs text-neutral-500">Complete</div>
              </div>
            </div>
          </div>
        </div>

        {/* Current Step */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary-100 text-primary-800 rounded-full text-sm font-medium mb-3">
            {currentStepIndex < steps.length && (
              <>
                {React.createElement(steps[currentStepIndex].icon, { className: "w-4 h-4" })}
                {currentStep}
              </>
            )}
          </div>
          <p className="text-neutral-600 text-sm px-4">
            {currentStepIndex < steps.length && steps[currentStepIndex].description}
          </p>
        </div>

        {/* Step Indicators */}
        <div className="px-4 mb-8">
          <div className="space-y-4">
            {steps.map((step, index) => {
              const isCompleted = index < currentStepIndex
              const isCurrent = index === currentStepIndex

              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex items-center gap-4 p-3 rounded-lg transition-all duration-300 ${
                    isCurrent 
                      ? 'bg-primary-50 border border-primary-200'
                      : isCompleted
                      ? 'bg-success-50 border border-success-200'
                      : 'bg-white border border-neutral-200'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isCompleted
                      ? 'bg-success-500 text-white'
                      : isCurrent
                      ? 'bg-primary-500 text-white'
                      : 'bg-neutral-200 text-neutral-500'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      <step.icon className="w-5 h-5" />
                    )}
                  </div>
                  
                  <div className="flex-1">
                    <h4 className={`font-medium ${
                      isCurrent 
                        ? 'text-primary-900'
                        : isCompleted
                        ? 'text-success-900'
                        : 'text-neutral-500'
                    }`}>
                      {step.label}
                    </h4>
                    <p className={`text-sm ${
                      isCurrent
                        ? 'text-primary-700'
                        : isCompleted
                        ? 'text-success-700'
                        : 'text-neutral-400'
                    }`}>
                      {step.description}
                    </p>
                  </div>
                  
                  {isCurrent && (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                      className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full"
                    />
                  )}
                </motion.div>
              )
            })}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="px-4">
          <div className="bg-neutral-200 rounded-full h-2 overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary-500 to-primary-600 rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            />
          </div>
          <div className="flex justify-between text-xs text-neutral-500 mt-2">
            <span>Started</span>
            <span>{Math.round(progress)}% Complete</span>
            <span>Finished</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white border-t border-neutral-200 px-4 py-4">
        <div className="text-center text-sm text-neutral-500">
          <p>Analysis powered by Real2.AI</p>
          <p className="mt-1">Tailored for Australian legal requirements</p>
        </div>
      </div>
    </div>
  )
}

export default MobileOptimizedLoading