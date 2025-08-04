import React from 'react'
import { cn } from '@/utils'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outlined' | 'elevated' | 'flat' | 'glass' | 'premium' | 'legal'
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl'
  interactive?: boolean
  status?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  gradient?: boolean
}

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl'
}

interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl'
}

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl'
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = 'default',
      padding = 'md',
      interactive = false,
      status = 'default',
      gradient = false,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      'rounded-xl transition-all duration-300 ease-in-out',
      'relative overflow-hidden'
    ].join(' ')

    const variantClasses = {
      default: 'bg-white shadow-card border border-neutral-100/50',
      outlined: 'bg-white border-2 border-neutral-200 hover:border-primary-300',
      elevated: 'bg-white shadow-large hover:shadow-xl',
      flat: 'bg-neutral-50 hover:bg-neutral-100',
      glass: 'bg-white/80 backdrop-blur-sm border border-white/20 shadow-large',
      premium: gradient 
        ? 'bg-gradient-to-br from-white via-primary-50/30 to-accent-50/30 shadow-xl border border-primary-100'
        : 'bg-white shadow-xl border border-primary-100',
      legal: 'bg-white shadow-card border-l-4 border-l-trust-500 border-r border-t border-b border-neutral-100'
    }

    const paddingClasses = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
      xl: 'p-8'
    }

    const interactiveClasses = interactive
      ? 'cursor-pointer hover:shadow-card-hover hover:-translate-y-1 active:translate-y-0 transform hover:scale-[1.02] active:scale-100'
      : ''

    const statusClasses = {
      default: '',
      success: 'ring-1 ring-success-200 bg-success-50/30',
      warning: 'ring-1 ring-warning-200 bg-warning-50/30',
      danger: 'ring-1 ring-danger-200 bg-danger-50/30',
      info: 'ring-1 ring-primary-200 bg-primary-50/30'
    }

    return (
      <div
        className={cn(
          baseClasses,
          variantClasses[variant],
          paddingClasses[padding],
          interactiveClasses,
          status !== 'default' && statusClasses[status],
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </div>
    )
  }
)

const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, padding = 'none', children, ...props }, ref) => {
    const paddingClasses = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
      xl: 'p-8'
    }

    return (
      <div
        className={cn(
          'flex flex-col space-y-1.5',
          paddingClasses[padding],
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </div>
    )
  }
)

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, children, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      'text-lg font-semibold leading-none tracking-tight text-neutral-900',
      className
    )}
    {...props}
  >
    {children}
  </h3>
))

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-neutral-500', className)}
    {...props}
  >
    {children}
  </p>
))

const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, padding = 'none', children, ...props }, ref) => {
    const paddingClasses = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
      xl: 'p-8'
    }

    return (
      <div
        className={cn(paddingClasses[padding], className)}
        ref={ref}
        {...props}
      >
        {children}
      </div>
    )
  }
)

const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, padding = 'none', children, ...props }, ref) => {
    const paddingClasses = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
      xl: 'p-8'
    }

    return (
      <div
        className={cn(
          'flex items-center',
          paddingClasses[padding],
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'
CardHeader.displayName = 'CardHeader'
CardTitle.displayName = 'CardTitle'
CardDescription.displayName = 'CardDescription'
CardContent.displayName = 'CardContent'
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }