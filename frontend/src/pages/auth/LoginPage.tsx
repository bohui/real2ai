import React from 'react'
import { Link, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'

import LoginForm from '@/components/forms/LoginForm'
import { useAuthStore } from '@/store/authStore'
import { usePageSEO } from '@/contexts/SEOContext'

const LoginPage: React.FC = () => {
  const { isAuthenticated } = useAuthStore()

  // SEO for Login page
  usePageSEO({
    title: 'Login - Real2AI',
    description: 'Sign in to your Real2AI account to access powerful AI-driven real estate analysis tools and property intelligence.',
    keywords: ['Real2AI login', 'sign in', 'real estate platform', 'user authentication'],
    canonical: '/auth/login',
    noIndex: true,
    ogTitle: 'Login to Real2AI - Access Your Real Estate AI Tools',
    ogDescription: 'Sign in to analyze contracts, get property intelligence, and make informed real estate decisions with AI.'
  })

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
            Welcome back to Real2.AI
          </h2>
          <p className="mt-2 text-neutral-600">
            Sign in to your account to continue
          </p>
        </div>

        {/* Login Form */}
        <LoginForm />

        {/* Footer */}
        <div className="text-center">
          <p className="text-sm text-neutral-600">
            Don't have an account?{' '}
            <Link
              to="/auth/register"
              className="font-medium text-primary-600 hover:text-primary-500 transition-colors"
            >
              Sign up
            </Link>
          </p>
        </div>

        {/* Demo Notice */}
        <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="text-center">
            <h3 className="text-sm font-medium text-amber-800 mb-2">
              Demo Account Available
            </h3>
            <p className="text-xs text-amber-700">
              Use the demo login button to explore Real2.AI with sample data
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default LoginPage