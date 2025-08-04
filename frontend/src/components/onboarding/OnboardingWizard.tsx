import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle, 
  FileText, 
  Shield, 
  TrendingUp,
  Scale,
  MapPin,
  Building2
} from 'lucide-react'

import Button from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import Select from '@/components/ui/Select'
import { cn } from '@/utils'

interface OnboardingStep {
  id: string
  title: string
  subtitle: string
  content: React.ReactNode
  icon: React.ComponentType<any>
}

interface OnboardingWizardProps {
  onComplete: (preferences: UserPreferences) => void
  onSkip: () => void
}

interface UserPreferences {
  practiceArea: string
  jurisdiction: string
  firmSize: string
  primaryContractTypes: string[]
}

const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete, onSkip }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [preferences, setPreferences] = useState<UserPreferences>({
    practiceArea: '',
    jurisdiction: '',
    firmSize: '',
    primaryContractTypes: []
  })

  const practiceAreas = [
    { value: 'property', label: 'Property Law' },
    { value: 'commercial', label: 'Commercial Law' },
    { value: 'employment', label: 'Employment Law' },
    { value: 'corporate', label: 'Corporate Law' },
    { value: 'litigation', label: 'Litigation' },
    { value: 'family', label: 'Family Law' },
    { value: 'other', label: 'Other' }
  ]

  const jurisdictions = [
    { value: 'nsw', label: 'New South Wales' },
    { value: 'vic', label: 'Victoria' },
    { value: 'qld', label: 'Queensland' },
    { value: 'wa', label: 'Western Australia' },
    { value: 'sa', label: 'South Australia' },
    { value: 'tas', label: 'Tasmania' },
    { value: 'act', label: 'ACT' },
    { value: 'nt', label: 'Northern Territory' }
  ]

  const firmSizes = [
    { value: 'solo', label: 'Solo Practice' },
    { value: 'small', label: 'Small Firm (2-10 lawyers)' },
    { value: 'medium', label: 'Medium Firm (11-50 lawyers)' },
    { value: 'large', label: 'Large Firm (50+ lawyers)' },
    { value: 'inhouse', label: 'In-house Legal Team' }
  ]

  const contractTypes = [
    'Purchase Agreements', 'Lease Agreements', 'Employment Contracts',
    'Service Agreements', 'Partnership Agreements', 'Licensing Agreements',
    'Construction Contracts', 'Supply Agreements'
  ]

  const steps: OnboardingStep[] = [
    {
      id: 'welcome',
      title: 'Welcome to Real2.AI',
      subtitle: 'AI-powered contract analysis for Australian legal professionals',
      icon: Shield,
      content: (
        <div className="text-center space-y-6">
          <div className="w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mx-auto">
            <Shield className="w-12 h-12 text-primary-600" />
          </div>
          <div className="space-y-4">
            <p className="text-lg text-neutral-700">
              Real2.AI uses advanced AI to analyse contracts against Australian law, 
              helping you identify risks and ensure compliance faster than ever.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              <div className="text-center p-4">
                <TrendingUp className="w-8 h-8 text-success-600 mx-auto mb-2" />
                <h4 className="font-medium text-neutral-900">2-3 Minutes</h4>
                <p className="text-sm text-neutral-600">Average analysis time</p>
              </div>
              <div className="text-center p-4">
                <Scale className="w-8 h-8 text-primary-600 mx-auto mb-2" />
                <h4 className="font-medium text-neutral-900">Australian Law</h4>
                <p className="text-sm text-neutral-600">Trained on local legislation</p>
              </div>
              <div className="text-center p-4">
                <CheckCircle className="w-8 h-8 text-warning-600 mx-auto mb-2" />
                <h4 className="font-medium text-neutral-900">95% Accuracy</h4>
                <p className="text-sm text-neutral-600">Validated by legal experts</p>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'practice-setup',
      title: 'Customize Your Experience',
      subtitle: 'Help us tailor analysis for your practice',
      icon: Building2,
      content: (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Primary Practice Area
              </label>
              <Select
                value={preferences.practiceArea}
                onChange={(e) => 
                  setPreferences(prev => ({ ...prev, practiceArea: e.target.value }))
                }
              >
                <option value="">Select your practice area</option>
                {practiceAreas.map(area => (
                  <option key={area.value} value={area.value}>
                    {area.label}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Primary Jurisdiction
              </label>
              <Select
                value={preferences.jurisdiction}
                onChange={(e) => 
                  setPreferences(prev => ({ ...prev, jurisdiction: e.target.value }))
                }
              >
                <option value="">Select your jurisdiction</option>
                {jurisdictions.map(jurisdiction => (
                  <option key={jurisdiction.value} value={jurisdiction.value}>
                    {jurisdiction.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Firm Size
            </label>
            <Select
              value={preferences.firmSize}
              onChange={(e) => 
                setPreferences(prev => ({ ...prev, firmSize: e.target.value }))
              }
            >
              <option value="">Select your firm size</option>
              {firmSizes.map(size => (
                <option key={size.value} value={size.value}>
                  {size.label}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-3">
              Common Contract Types (Select all that apply)
            </label>
            <div className="grid grid-cols-2 gap-3">
              {contractTypes.map(type => (
                <label key={type} className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={preferences.primaryContractTypes.includes(type)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setPreferences(prev => ({
                          ...prev,
                          primaryContractTypes: [...prev.primaryContractTypes, type]
                        }))
                      } else {
                        setPreferences(prev => ({
                          ...prev,
                          primaryContractTypes: prev.primaryContractTypes.filter(t => t !== type)
                        }))
                      }
                    }}
                    className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                  />
                  <span className="text-sm text-neutral-700">{type}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'risk-demo',
      title: 'Understanding Risk Analysis',
      subtitle: 'See how our AI evaluates contract risks',
      icon: TrendingUp,
      content: (
        <div className="space-y-6">
          <div className="bg-neutral-50 rounded-lg p-6">
            <h4 className="font-medium text-neutral-900 mb-4">Sample Risk Assessment</h4>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-white rounded-lg border">
                <div>
                  <h5 className="font-medium text-neutral-900">Overall Risk Score</h5>
                  <p className="text-sm text-neutral-600">Medium Risk - Above average for VIC property contracts</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-warning-600">6.2</div>
                  <div className="text-xs text-neutral-500">Industry avg: 5.8</div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-white rounded-lg border">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-danger-500 rounded-full"></div>
                    <span className="font-medium text-neutral-900">High Risk Areas</span>
                  </div>
                  <ul className="text-sm text-neutral-600 space-y-1">
                    <li>• Unusual settlement terms (Clause 14.3)</li>
                    <li>• Missing financing conditions</li>
                    <li>• Unclear dispute resolution</li>
                  </ul>
                </div>

                <div className="p-4 bg-white rounded-lg border">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-success-500 rounded-full"></div>
                    <span className="font-medium text-neutral-900">Compliant Areas</span>
                  </div>
                  <ul className="text-sm text-neutral-600 space-y-1">
                    <li>• Property disclosure requirements</li>
                    <li>• Consumer protection clauses</li>
                    <li>• Stamp duty obligations</li>
                  </ul>
                </div>
              </div>

              <div className="p-4 bg-primary-50 rounded-lg border border-primary-200">
                <h6 className="font-medium text-primary-900 mb-2">AI Recommendation</h6>
                <p className="text-sm text-primary-800">
                  Review settlement terms in clause 14.3 for compliance with Property Law Act 1958 (VIC). 
                  Consider adding standard financing conditions similar to precedent in Chen v Melbourne Property (2023).
                </p>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'ready',
      title: 'You\'re All Set!',
      subtitle: 'Ready to start analyzing contracts with confidence',
      icon: CheckCircle,
      content: (
        <div className="text-center space-y-6">
          <div className="w-24 h-24 bg-success-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-12 h-12 text-success-600" />
          </div>
          
          <div className="space-y-4">
            <p className="text-lg text-neutral-700">
              Your personalized Real2.AI workspace is ready. Upload your first contract 
              to see our AI analysis in action.
            </p>
            
            <div className="bg-neutral-50 rounded-lg p-6">
              <h4 className="font-medium text-neutral-900 mb-4">Your Settings Summary</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                <div>
                  <span className="text-sm text-neutral-600">Practice Area:</span>
                  <div className="font-medium text-neutral-900">
                    {practiceAreas.find(a => a.value === preferences.practiceArea)?.label || 'Not selected'}
                  </div>
                </div>
                <div>
                  <span className="text-sm text-neutral-600">Jurisdiction:</span>
                  <div className="font-medium text-neutral-900">
                    {jurisdictions.find(j => j.value === preferences.jurisdiction)?.label || 'Not selected'}
                  </div>
                </div>
                <div>
                  <span className="text-sm text-neutral-600">Firm Size:</span>
                  <div className="font-medium text-neutral-900">
                    {firmSizes.find(s => s.value === preferences.firmSize)?.label || 'Not selected'}
                  </div>
                </div>
                <div>
                  <span className="text-sm text-neutral-600">Contract Types:</span>
                  <div className="font-medium text-neutral-900">
                    {preferences.primaryContractTypes.length > 0 
                      ? `${preferences.primaryContractTypes.length} selected`
                      : 'None selected'
                    }
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }
  ]

  const currentStepData = steps[currentStep]
  const isLastStep = currentStep === steps.length - 1
  const canProceed = currentStep === 0 || 
    (currentStep === 1 && preferences.practiceArea && preferences.jurisdiction) ||
    currentStep > 1

  const handleNext = () => {
    if (isLastStep) {
      onComplete(preferences)
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handlePrevious = () => {
    setCurrentStep(prev => Math.max(0, prev - 1))
  }

  return (
    <div className="fixed inset-0 bg-neutral-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6 border-b border-neutral-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <motion.div
                className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center"
                whileHover={{ scale: 1.05 }}
              >
                <currentStepData.icon className="w-6 h-6 text-primary-600" />
              </motion.div>
              <div>
                <h2 className="text-xl font-bold text-neutral-900">
                  {currentStepData.title}
                </h2>
                <p className="text-neutral-600">{currentStepData.subtitle}</p>
              </div>
            </div>
            <button
              onClick={onSkip}
              className="text-neutral-500 hover:text-neutral-700 text-sm font-medium"
            >
              Skip Setup
            </button>
          </div>

          {/* Progress Bar */}
          <div className="mt-6">
            <div className="flex items-center gap-2">
              {steps.map((_, index) => (
                <div
                  key={index}
                  className={cn(
                    'h-2 flex-1 rounded-full transition-colors',
                    index <= currentStep ? 'bg-primary-600' : 'bg-neutral-200'
                  )}
                />
              ))}
            </div>
            <div className="flex justify-between mt-2 text-xs text-neutral-500">
              <span>Step {currentStep + 1} of {steps.length}</span>
              <span>{Math.round(((currentStep + 1) / steps.length) * 100)}% Complete</span>
            </div>
          </div>
        </div>

        <div className="p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              {currentStepData.content}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="px-8 py-6 border-t border-neutral-200 flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={handlePrevious}
            disabled={currentStep === 0}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Previous
          </Button>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={onSkip}
            >
              Skip for now
            </Button>
            <Button
              variant="primary"
              onClick={handleNext}
              disabled={!canProceed}
              className="min-w-32"
            >
              {isLastStep ? 'Get Started' : 'Next'}
              {!isLastStep && <ArrowRight className="w-4 h-4 ml-2" />}
            </Button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default OnboardingWizard