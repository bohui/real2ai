import React from 'react'
import { cn } from '@/utils'
import { Eye, EyeOff, Search, AlertCircle, CheckCircle } from 'lucide-react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  success?: string
  hint?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  variant?: 'default' | 'search' | 'legal'
  state?: 'default' | 'error' | 'success' | 'loading'
  showPasswordToggle?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type = 'text',
      label,
      error,
      success,
      hint,
      leftIcon,
      rightIcon,
      variant = 'default',
      state = 'default',
      showPasswordToggle = false,
      disabled,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = React.useState(false)
    const [isFocused, setIsFocused] = React.useState(false)
    
    const inputType = type === 'password' && showPassword ? 'text' : type
    
    const getStateClasses = () => {
      if (error || state === 'error') {
        return {
          container: 'border-danger-300 ring-danger-500/20 bg-danger-50/50',
          input: 'text-danger-900 placeholder-danger-400',
          icon: 'text-danger-500'
        }
      }
      
      if (success || state === 'success') {
        return {
          container: 'border-success-300 ring-success-500/20 bg-success-50/50',
          input: 'text-success-900 placeholder-success-400',
          icon: 'text-success-500'
        }
      }
      
      if (isFocused) {
        return {
          container: 'border-primary-300 ring-primary-500/20 bg-primary-50/30',
          input: 'text-neutral-900 placeholder-neutral-400',
          icon: 'text-primary-500'
        }
      }
      
      return {
        container: 'border-neutral-200 hover:border-neutral-300 bg-white',
        input: 'text-neutral-900 placeholder-neutral-500',
        icon: 'text-neutral-400'
      }
    }
    
    const stateClasses = getStateClasses()

    const variantClasses = {
      default: 'rounded-lg',
      search: 'rounded-full',
      legal: 'rounded-lg border-l-4 border-l-trust-500'
    }

    return (
      <div className="space-y-2">
        {/* Label */}
        {label && (
          <label className="block text-sm font-medium text-neutral-700">
            {label}
            {props.required && <span className="text-danger-500 ml-1">*</span>}
          </label>
        )}
        
        {/* Input Container */}
        <div className="relative">
          <div
            className={cn(
              'relative flex items-center border-2 transition-all duration-200',
              variantClasses[variant],
              stateClasses.container,
              disabled && 'opacity-50 cursor-not-allowed bg-neutral-100',
              isFocused && 'ring-4',
              className
            )}
          >
            {/* Left Icon */}
            {leftIcon && (
              <div className={cn('flex items-center justify-center w-10 h-10', stateClasses.icon)}>
                {leftIcon}
              </div>
            )}
            
            {/* Search Icon for search variant */}
            {variant === 'search' && !leftIcon && (
              <div className={cn('flex items-center justify-center w-10 h-10', stateClasses.icon)}>
                <Search className="w-4 h-4" />
              </div>
            )}
            
            {/* Input */}
            <input
              type={inputType}
              className={cn(
                'flex-1 min-w-0 px-3 py-2.5 bg-transparent border-0 focus:outline-none focus:ring-0',
                'text-sm font-medium',
                stateClasses.input,
                leftIcon || variant === 'search' ? 'pl-0' : 'pl-3',
                (rightIcon || showPasswordToggle || error || success) ? 'pr-0' : 'pr-3',
                disabled && 'cursor-not-allowed'
              )}
              ref={ref}
              disabled={disabled}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              {...props}
            />
            
            {/* Right Side Icons */}
            <div className="flex items-center gap-1 pr-3">
              {/* State Icons */}
              {(error || state === 'error') && (
                <AlertCircle className="w-4 h-4 text-danger-500" />
              )}
              {(success || state === 'success') && (
                <CheckCircle className="w-4 h-4 text-success-500" />
              )}
              
              {/* Password Toggle */}
              {showPasswordToggle && type === 'password' && (
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={cn(
                    'p-1 hover:bg-neutral-100 rounded transition-colors',
                    stateClasses.icon
                  )}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              )}
              
              {/* Custom Right Icon */}
              {rightIcon && (
                <div className={stateClasses.icon}>
                  {rightIcon}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Helper Text */}
        <div className="min-h-[1.25rem]">
          {error && (
            <p className="text-sm text-danger-600 flex items-center gap-1">
              <AlertCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
              {error}
            </p>
          )}
          {success && !error && (
            <p className="text-sm text-success-600 flex items-center gap-1">
              <CheckCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
              {success}
            </p>
          )}
          {hint && !error && !success && (
            <p className="text-sm text-neutral-500">{hint}</p>
          )}
        </div>
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input