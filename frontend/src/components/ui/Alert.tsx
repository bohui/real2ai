import React from 'react'
import { motion } from 'framer-motion'
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Info, 
  X,
  Shield,
  AlertCircle
} from 'lucide-react'
import { cn } from '@/utils'
import Button from './Button'

export type AlertType = 'success' | 'warning' | 'danger' | 'info' | 'legal' | 'compliance'

interface AlertProps {
  type?: AlertType
  variant?: 'filled' | 'outlined' | 'subtle' | 'minimal'
  title?: string
  description?: string
  dismissible?: boolean
  onDismiss?: () => void
  icon?: React.ReactNode
  actions?: React.ReactNode
  className?: string
  animated?: boolean
  children?: React.ReactNode
}

const Alert: React.FC<AlertProps> = ({
  type = 'info',
  variant = 'subtle',
  title,
  description,
  dismissible = false,
  onDismiss,
  icon,
  actions,
  className,
  animated = true,
  children
}) => {
  const getAlertConfig = (type: AlertType) => {
    const configs = {
      success: {
        icon: CheckCircle,
        colors: {
          filled: 'bg-success-500 text-white border-success-500',
          outlined: 'bg-white text-success-700 border-success-500 border-2',
          subtle: 'bg-success-50 text-success-800 border-success-200',
          minimal: 'bg-transparent text-success-700'
        },
        iconColor: {
          filled: 'text-white',
          outlined: 'text-success-500',
          subtle: 'text-success-600',
          minimal: 'text-success-500'
        }
      },
      warning: {
        icon: AlertTriangle,
        colors: {
          filled: 'bg-warning-500 text-white border-warning-500',
          outlined: 'bg-white text-warning-700 border-warning-500 border-2',
          subtle: 'bg-warning-50 text-warning-800 border-warning-200',
          minimal: 'bg-transparent text-warning-700'
        },
        iconColor: {
          filled: 'text-white',
          outlined: 'text-warning-500',
          subtle: 'text-warning-600',
          minimal: 'text-warning-500'
        }
      },
      danger: {
        icon: XCircle,
        colors: {
          filled: 'bg-danger-500 text-white border-danger-500',
          outlined: 'bg-white text-danger-700 border-danger-500 border-2',
          subtle: 'bg-danger-50 text-danger-800 border-danger-200',
          minimal: 'bg-transparent text-danger-700'
        },
        iconColor: {
          filled: 'text-white',
          outlined: 'text-danger-500',
          subtle: 'text-danger-600',
          minimal: 'text-danger-500'
        }
      },
      info: {
        icon: Info,
        colors: {
          filled: 'bg-primary-500 text-white border-primary-500',
          outlined: 'bg-white text-primary-700 border-primary-500 border-2',
          subtle: 'bg-primary-50 text-primary-800 border-primary-200',
          minimal: 'bg-transparent text-primary-700'
        },
        iconColor: {
          filled: 'text-white',
          outlined: 'text-primary-500',
          subtle: 'text-primary-600',
          minimal: 'text-primary-500'
        }
      },
      legal: {
        icon: Shield,
        colors: {
          filled: 'bg-trust-500 text-white border-trust-500',
          outlined: 'bg-white text-trust-700 border-trust-500 border-2',
          subtle: 'bg-trust-50 text-trust-800 border-trust-200',
          minimal: 'bg-transparent text-trust-700'
        },
        iconColor: {
          filled: 'text-white',
          outlined: 'text-trust-500',
          subtle: 'text-trust-600',
          minimal: 'text-trust-500'
        }
      },
      compliance: {
        icon: AlertCircle,
        colors: {
          filled: 'bg-compliant-500 text-white border-compliant-500',
          outlined: 'bg-white text-compliant-700 border-compliant-500 border-2',
          subtle: 'bg-compliant-50 text-compliant-800 border-compliant-200',
          minimal: 'bg-transparent text-compliant-700'
        },
        iconColor: {
          filled: 'text-white',
          outlined: 'text-compliant-500',
          subtle: 'text-compliant-600',
          minimal: 'text-compliant-500'
        }
      }
    }
    return configs[type]
  }

  const config = getAlertConfig(type)
  const IconComponent = icon ? () => icon : config.icon

  const baseClasses = [
    'rounded-lg border transition-all duration-200',
    variant !== 'minimal' && 'p-4',
    variant === 'minimal' && 'p-2'
  ].join(' ')

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: -10 } : undefined}
      animate={animated ? { opacity: 1, y: 0 } : undefined}
      exit={animated ? { opacity: 0, y: -10 } : undefined}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={cn(
        baseClasses,
        config.colors[variant],
        className
      )}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <IconComponent 
            className={cn(
              'w-5 h-5',
              config.iconColor[variant]
            )} 
          />
        </div>
        
        <div className="flex-1 min-w-0">
          {title && (
            <h4 className="font-semibold mb-1 text-sm leading-tight">
              {title}
            </h4>
          )}
          
          {description && (
            <p className="text-sm leading-relaxed opacity-90">
              {description}
            </p>
          )}
          
          {children && (
            <div className="mt-2">
              {children}
            </div>
          )}
          
          {actions && (
            <div className="mt-3 flex items-center gap-2">
              {actions}
            </div>
          )}
        </div>
        
        {dismissible && onDismiss && (
          <div className="flex-shrink-0">
            <Button
              variant="ghost"
              size="xs"
              onClick={onDismiss}
              className={cn(
                'p-1 rounded-md hover:bg-black/10',
                variant === 'filled' && 'text-white hover:bg-white/20',
                variant !== 'filled' && 'text-current'
              )}
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Dismiss</span>
            </Button>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default Alert