import React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { Mail, Lock, AlertCircle } from 'lucide-react'
import { motion } from 'framer-motion'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'
import { UserLoginRequest } from '@/types'

const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters')
})

type LoginFormData = z.infer<typeof loginSchema>

interface LoginFormProps {
  onSuccess?: () => void
  redirectTo?: string
}

const LoginForm: React.FC<LoginFormProps> = ({ onSuccess, redirectTo = '/dashboard' }) => {
  const { login, isLoading, error } = useAuthStore()
  const { addNotification } = useUIStore()
  
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur'
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data)
      
      addNotification({
        type: 'success',
        title: 'Welcome back!',
        message: 'You have been successfully logged in.'
      })
      
      if (onSuccess) {
        onSuccess()
      } else {
        window.location.href = redirectTo
      }
    } catch (err) {
      // Error is already handled in the store
      addNotification({
        type: 'error',
        title: 'Login failed',
        message: 'Please check your credentials and try again.'
      })
    }
  }

  const isProcessing = isLoading || isSubmitting

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-md mx-auto"
    >
      <Card variant="elevated" padding="none">
        <CardHeader padding="lg">
          <div className="text-center mb-2">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
              <span className="text-2xl font-bold text-primary-600">R2</span>
            </div>
          </div>
          <CardTitle className="text-center text-2xl">Welcome back</CardTitle>
          <CardDescription className="text-center">
            Sign in to your Real2.AI account to continue analyzing contracts
          </CardDescription>
        </CardHeader>

        <CardContent padding="lg">
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg"
            >
              <div className="flex items-center gap-2 text-danger-700">
                <AlertCircle className="w-5 h-5" />
                <span className="text-sm font-medium">{error}</span>
              </div>
            </motion.div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <Input
              label="Email address"
              type="email"
              autoComplete="email"
              placeholder="Enter your email"
              leftIcon={<Mail className="w-5 h-5" />}
              error={errors.email?.message}
              disabled={isProcessing}
              {...register('email')}
            />

            <Input
              label="Password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              leftIcon={<Lock className="w-5 h-5" />}
              showPasswordToggle
              error={errors.password?.message}
              disabled={isProcessing}
              {...register('password')}
            />

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-neutral-600">Remember me</span>
              </label>
              <Link
                to="/forgot-password"
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={isProcessing}
              loadingText="Signing in..."
            >
              Sign in
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-neutral-600">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-primary-600 hover:text-primary-700"
              >
                Sign up for free
              </Link>
            </p>
          </div>

          <div className="mt-6 pt-6 border-t border-neutral-200">
            <div className="text-center">
              <p className="text-xs text-neutral-500 mb-2">
                Try Real2.AI with our demo account
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleSubmit(onSubmit)({
                  email: 'demo@real2.ai',
                  password: 'demo123456'
                })}
                disabled={isProcessing}
              >
                Demo Login
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8 text-center text-xs text-neutral-500">
        <p>
          By signing in, you agree to our{' '}
          <Link to="/terms" className="text-primary-600 hover:text-primary-700">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="text-primary-600 hover:text-primary-700">
            Privacy Policy
          </Link>
        </p>
      </div>
    </motion.div>
  )
}

export default LoginForm