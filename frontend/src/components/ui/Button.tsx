import React from 'react'
import { cn } from '@/utils'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'warning' | 'premium'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  loading?: boolean
  loadingText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
  elevated?: boolean
  rounded?: boolean
  gradient?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      loadingText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      elevated = false,
      rounded = false,
      gradient = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      'inline-flex items-center justify-center',
      'font-medium transition-all duration-200 ease-in-out',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'select-none relative overflow-hidden',
      'transform active:scale-95 hover:scale-[1.02]'
    ].join(' ')

    const variantClasses = {
      primary: [
        gradient ? 'bg-gradient-to-r from-primary-600 to-primary-700' : 'bg-primary-600',
        'text-white shadow-soft',
        'hover:from-primary-700 hover:to-primary-800 hover:shadow-primary',
        'focus:ring-primary-500/50',
        'active:from-primary-800 active:to-primary-900'
      ].join(' '),
      secondary: [
        gradient ? 'bg-gradient-to-r from-secondary-500 to-secondary-600' : 'bg-secondary-500',
        'text-white shadow-soft',
        'hover:from-secondary-600 hover:to-secondary-700 hover:shadow-warning',
        'focus:ring-secondary-500/50',
        'active:from-secondary-700 active:to-secondary-800'
      ].join(' '),
      success: [
        gradient ? 'bg-gradient-to-r from-success-500 to-success-600' : 'bg-success-500',
        'text-white shadow-soft',
        'hover:from-success-600 hover:to-success-700 hover:shadow-success',
        'focus:ring-success-500/50',
        'active:from-success-700 active:to-success-800'
      ].join(' '),
      warning: [
        gradient ? 'bg-gradient-to-r from-warning-500 to-warning-600' : 'bg-warning-500',
        'text-white shadow-soft',
        'hover:from-warning-600 hover:to-warning-700 hover:shadow-warning',
        'focus:ring-warning-500/50',
        'active:from-warning-700 active:to-warning-800'
      ].join(' '),
      danger: [
        gradient ? 'bg-gradient-to-r from-danger-500 to-danger-600' : 'bg-danger-500',
        'text-white shadow-soft',
        'hover:from-danger-600 hover:to-danger-700 hover:shadow-danger',
        'focus:ring-danger-500/50',
        'active:from-danger-700 active:to-danger-800'
      ].join(' '),
      premium: [
        'bg-gradient-to-r from-accent-500 via-primary-600 to-accent-500',
        'text-white shadow-large',
        'hover:from-accent-600 hover:via-primary-700 hover:to-accent-600',
        'focus:ring-primary-500/50 animate-glow',
        'active:from-accent-700 active:via-primary-800 active:to-accent-700'
      ].join(' '),
      outline: [
        'border-2 border-neutral-300 bg-white text-neutral-700 shadow-soft',
        'hover:border-primary-400 hover:bg-primary-50 hover:text-primary-700',
        'focus:ring-primary-500/50 focus:border-primary-500',
        'active:bg-primary-100 active:border-primary-600'
      ].join(' '),
      ghost: [
        'text-neutral-700 bg-transparent',
        'hover:bg-neutral-100 hover:text-neutral-900',
        'focus:ring-primary-500/30 focus:bg-neutral-50',
        'active:bg-neutral-200'
      ].join(' ')
    }

    const sizeClasses = {
      xs: `px-2.5 py-1.5 text-xs gap-1 ${rounded ? 'rounded-full' : 'rounded-md'}`,
      sm: `px-3 py-2 text-sm gap-1.5 ${rounded ? 'rounded-full' : 'rounded-lg'}`,
      md: `px-4 py-2.5 text-sm gap-2 ${rounded ? 'rounded-full' : 'rounded-lg'}`,
      lg: `px-6 py-3 text-base gap-2.5 ${rounded ? 'rounded-full' : 'rounded-xl'}`,
      xl: `px-8 py-4 text-lg gap-3 ${rounded ? 'rounded-full' : 'rounded-xl'}`
    }

    const isDisabled = disabled || loading

    return (
      <button
        className={cn(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
          elevated && 'shadow-large hover:shadow-xl',
          className
        )}
        disabled={isDisabled}
        ref={ref}
        {...props}
      >
        {loading && (
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
        )}
        {!loading && leftIcon && (
          <span className="inline-flex" aria-hidden="true">
            {leftIcon}
          </span>
        )}
        <span>
          {loading && loadingText ? loadingText : children}
        </span>
        {!loading && rightIcon && (
          <span className="inline-flex" aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button