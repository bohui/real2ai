import React from 'react'
import { cn } from '@/utils'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  loading?: boolean
  loadingText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  fullWidth?: boolean
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
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      'inline-flex items-center justify-center',
      'font-medium transition-all duration-200',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'select-none'
    ].join(' ')

    const variantClasses = {
      primary: [
        'bg-primary-600 text-white shadow-sm',
        'hover:bg-primary-700 focus:ring-primary-500',
        'active:bg-primary-800'
      ].join(' '),
      secondary: [
        'bg-secondary-600 text-white shadow-sm',
        'hover:bg-secondary-700 focus:ring-secondary-500',
        'active:bg-secondary-800'
      ].join(' '),
      outline: [
        'border border-neutral-300 bg-white text-neutral-700 shadow-sm',
        'hover:bg-neutral-50 focus:ring-primary-500',
        'active:bg-neutral-100'
      ].join(' '),
      ghost: [
        'text-neutral-700 bg-transparent',
        'hover:bg-neutral-100 focus:ring-primary-500',
        'active:bg-neutral-200'
      ].join(' '),
      danger: [
        'bg-danger-600 text-white shadow-sm',
        'hover:bg-danger-700 focus:ring-danger-500',
        'active:bg-danger-800'
      ].join(' ')
    }

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm rounded-md gap-1.5',
      md: 'px-4 py-2 text-sm rounded-lg gap-2',
      lg: 'px-6 py-2.5 text-base rounded-lg gap-2',
      xl: 'px-8 py-3 text-lg rounded-xl gap-3'
    }

    const isDisabled = disabled || loading

    return (
      <button
        className={cn(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && 'w-full',
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