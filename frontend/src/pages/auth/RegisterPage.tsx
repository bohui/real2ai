import React from 'react'
import { Link, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'

import RegisterForm from '@/components/forms/RegisterForm'
import { useAuthStore } from '@/store/authStore'

const RegisterPage: React.FC = () => {
  const { isAuthenticated } = useAuthStore()

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full space-y-8"
      >
        {/* Header */}
        <div className="text-center">
          <div className="flex justify-center">
            <div className="w-16 h-16 bg-primary-600 rounded-2xl flex items-center justify-center mb-6">
              <Zap className="w-8 h-8 text-white" />
            </div>
          </div>
          <h2 className="text-3xl font-bold text-neutral-900">
            Join Real2.AI
          </h2>
          <p className="mt-2 text-neutral-600">
            Create your account to start analyzing contracts
          </p>
        </div>

        {/* Register Form */}
        <RegisterForm />

        {/* Footer */}
        <div className="text-center">
          <p className="text-sm text-neutral-600">
            Already have an account?{' '}
            <Link
              to="/auth/login"
              className="font-medium text-primary-600 hover:text-primary-500 transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>

        {/* Features */}
        <div className="mt-8 space-y-4">
          <h3 className="text-sm font-semibold text-neutral-900 text-center">
            What you'll get:
          </h3>
          <div className="space-y-2">
            {[
              'AI-powered contract analysis',
              'Australian legal compliance checks',
              'Risk assessment and recommendations',
              'Secure document processing',
              'Professional reporting'
            ].map((feature, index) => (
              <div key={index} className="flex items-center text-sm text-neutral-600">
                <div className="w-2 h-2 bg-primary-600 rounded-full mr-3" />
                {feature}
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default RegisterPage