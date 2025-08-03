import React from 'react'
import { cn } from '@/utils'
import { ChevronDown, AlertCircle } from 'lucide-react'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  helpText?: string
  containerClassName?: string
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      className,
      containerClassName,
      label,
      error,
      helpText,
      id,
      children,
      ...props
    },
    ref
  ) => {
    const selectId = id || `select-${Date.now()}`
    const hasError = Boolean(error)

    const baseClasses = [
      'block w-full rounded-lg border-0 py-2.5 px-3 pr-10',
      'text-neutral-900 shadow-sm ring-1 ring-inset',
      'focus:ring-2 focus:ring-inset',
      'transition-all duration-200',
      'disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:text-neutral-500',
      'appearance-none bg-white'
    ].join(' ')

    const stateClasses = hasError
      ? 'ring-danger-300 focus:ring-danger-500'
      : 'ring-neutral-300 focus:ring-primary-500'

    return (
      <div className={cn('space-y-1', containerClassName)}>
        {label && (
          <label 
            htmlFor={selectId}
            className="block text-sm font-medium text-neutral-700"
          >
            {label}
          </label>
        )}
        
        <div className="relative">
          <select
            id={selectId}
            className={cn(
              baseClasses,
              stateClasses,
              className
            )}
            ref={ref}
            aria-invalid={hasError}
            aria-describedby={
              error ? `${selectId}-error` : 
              helpText ? `${selectId}-help` : undefined
            }
            {...props}
          >
            {children}
          </select>
          
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <ChevronDown className="w-5 h-5 text-neutral-400" aria-hidden="true" />
          </div>
        </div>
        
        {error && (
          <div 
            id={`${selectId}-error`}
            className="flex items-center gap-1.5 text-sm text-danger-600"
            role="alert"
          >
            <AlertCircle className="w-4 h-4" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}
        
        {helpText && !error && (
          <p 
            id={`${selectId}-help`}
            className="text-sm text-neutral-500"
          >
            {helpText}
          </p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'

export default Select