import React from 'react'
import { motion } from 'framer-motion'
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  XCircle, 
  Shield, 
  Crown,
  Verified
} from 'lucide-react'
import { cn } from '@/utils'

export type StatusType = 
  | 'compliant' 
  | 'processing' 
  | 'pending' 
  | 'failed' 
  | 'verified' 
  | 'premium' 
  | 'warning'
  | 'success'
  | 'completed'

interface StatusBadgeProps {
  status: StatusType
  variant?: 'dot' | 'outline' | 'solid' | 'subtle'
  size?: 'sm' | 'md' | 'lg'
  label?: string
  showIcon?: boolean
  animated?: boolean
  pulse?: boolean
  className?: string
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant = 'solid',
  size = 'md',
  label,
  showIcon = true,
  animated = false,
  pulse = false,
  className
}) => {
  const getStatusConfig = (status: StatusType) => {
    const configs = {
      compliant: {
        icon: Shield,
        label: 'Compliant',
        colors: {
          solid: 'bg-compliant-500 text-white',
          outline: 'border-compliant-500 text-compliant-700 bg-white',
          subtle: 'bg-compliant-50 text-compliant-700 border-compliant-200',
          dot: 'bg-compliant-500'
        },
        dotColor: 'bg-compliant-500'
      },
      processing: {
        icon: Clock,
        label: 'Processing',
        colors: {
          solid: 'bg-primary-500 text-white',
          outline: 'border-primary-500 text-primary-700 bg-white',
          subtle: 'bg-primary-50 text-primary-700 border-primary-200',
          dot: 'bg-primary-500'
        },
        dotColor: 'bg-primary-500'
      },
      pending: {
        icon: Clock,
        label: 'Pending',
        colors: {
          solid: 'bg-warning-500 text-white',
          outline: 'border-warning-500 text-warning-700 bg-white',
          subtle: 'bg-warning-50 text-warning-700 border-warning-200',
          dot: 'bg-warning-500'
        },
        dotColor: 'bg-warning-500'
      },
      failed: {
        icon: XCircle,
        label: 'Failed',
        colors: {
          solid: 'bg-danger-500 text-white',
          outline: 'border-danger-500 text-danger-700 bg-white',
          subtle: 'bg-danger-50 text-danger-700 border-danger-200',
          dot: 'bg-danger-500'
        },
        dotColor: 'bg-danger-500'
      },
      verified: {
        icon: Verified,
        label: 'Verified',
        colors: {
          solid: 'bg-verified-500 text-white',
          outline: 'border-verified-500 text-verified-700 bg-white',
          subtle: 'bg-verified-50 text-verified-700 border-verified-200',
          dot: 'bg-verified-500'
        },
        dotColor: 'bg-verified-500'
      },
      premium: {
        icon: Crown,
        label: 'Premium',
        colors: {
          solid: 'bg-gradient-to-r from-purple-600 to-blue-600 text-white',
          outline: 'border-purple-500 text-purple-700 bg-white',
          subtle: 'bg-purple-50 text-purple-700 border-purple-200',
          dot: 'bg-purple-500'
        },
        dotColor: 'bg-purple-500'
      },
      warning: {
        icon: AlertTriangle,
        label: 'Warning',
        colors: {
          solid: 'bg-warning-500 text-white',
          outline: 'border-warning-500 text-warning-700 bg-white',
          subtle: 'bg-warning-50 text-warning-700 border-warning-200',
          dot: 'bg-warning-500'
        },
        dotColor: 'bg-warning-500'
      },
      success: {
        icon: CheckCircle,
        label: 'Success',
        colors: {
          solid: 'bg-success-500 text-white',
          outline: 'border-success-500 text-success-700 bg-white',
          subtle: 'bg-success-50 text-success-700 border-success-200',
          dot: 'bg-success-500'
        },
        dotColor: 'bg-success-500'
      },
      completed: {
        icon: CheckCircle,
        label: 'Completed',
        colors: {
          solid: 'bg-success-500 text-white',
          outline: 'border-success-500 text-success-700 bg-white',
          subtle: 'bg-success-50 text-success-700 border-success-200',
          dot: 'bg-success-500'
        },
        dotColor: 'bg-success-500'
      }
    }
    return configs[status]
  }

  const config = getStatusConfig(status)
  const IconComponent = config.icon
  const displayLabel = label || config.label

  const sizeClasses = {
    sm: {
      container: 'text-xs px-2 py-1',
      icon: 'w-3 h-3',
      dot: 'w-1.5 h-1.5',
      gap: 'gap-1'
    },
    md: {
      container: 'text-sm px-2.5 py-1.5',
      icon: 'w-4 h-4',
      dot: 'w-2 h-2',
      gap: 'gap-1.5'
    },
    lg: {
      container: 'text-base px-3 py-2',
      icon: 'w-5 h-5',
      dot: 'w-2.5 h-2.5',
      gap: 'gap-2'
    }
  }

  const currentSize = sizeClasses[size]

  if (variant === 'dot') {
    return (
      <motion.div
        initial={animated ? { scale: 0 } : undefined}
        animate={animated ? { scale: 1 } : undefined}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={cn(
          'inline-flex items-center font-medium',
          currentSize.container,
          currentSize.gap,
          className
        )}
      >
        <div
          className={cn(
            'rounded-full',
            currentSize.dot,
            config.dotColor,
            pulse && 'animate-pulse'
          )}
        />
        <span className="text-neutral-700">{displayLabel}</span>
      </motion.div>
    )
  }

  const baseClasses = [
    'inline-flex items-center rounded-full font-medium',
    'transition-all duration-200',
    currentSize.container,
    currentSize.gap
  ].join(' ')

  const variantClasses = config.colors[variant]

  return (
    <motion.div
      initial={animated ? { scale: 0.8, opacity: 0 } : undefined}
      animate={animated ? { scale: 1, opacity: 1 } : undefined}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        baseClasses,
        variantClasses,
        variant === 'outline' && 'border',
        variant === 'subtle' && 'border',
        pulse && 'animate-pulse',
        status === 'processing' && 'animate-pulse',
        className
      )}
    >
      {showIcon && (
        <IconComponent 
          className={cn(
            currentSize.icon,
            status === 'processing' && 'animate-spin'
          )} 
        />
      )}
      <span>{displayLabel}</span>
    </motion.div>
  )
}

export default StatusBadge