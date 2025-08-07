import React from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Shield, TrendingUp } from 'lucide-react'
import { cn } from '@/utils'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

interface RiskIndicatorProps {
  level: RiskLevel
  score?: number
  maxScore?: number
  variant?: 'compact' | 'detailed' | 'circular'
  showIcon?: boolean
  showLabel?: boolean
  showScore?: boolean
  className?: string
  animated?: boolean
  size?: 'sm' | 'md' | 'lg'
}

const RiskIndicator: React.FC<RiskIndicatorProps> = ({
  level,
  score,
  maxScore = 10,
  variant = 'compact',
  showIcon = true,
  showLabel = true,
  showScore = false,
  className,
  animated = false,
  size = 'md'
}) => {
  const getRiskConfig = (level: RiskLevel) => {
    const configs = {
      low: {
        icon: Shield,
        label: 'Low Risk',
        color: 'success',
        bgColor: 'bg-success-50',
        textColor: 'text-success-700',
        borderColor: 'border-success-200',
        iconColor: 'text-success-600',
        progressColor: 'bg-success-500'
      },
      medium: {
        icon: TrendingUp,
        label: 'Medium Risk',
        color: 'warning',
        bgColor: 'bg-warning-50',
        textColor: 'text-warning-700',
        borderColor: 'border-warning-200',
        iconColor: 'text-warning-600',
        progressColor: 'bg-warning-500'
      },
      high: {
        icon: AlertTriangle,
        label: 'High Risk',
        color: 'danger',
        bgColor: 'bg-danger-50',
        textColor: 'text-danger-700',
        borderColor: 'border-danger-200',
        iconColor: 'text-danger-600',
        progressColor: 'bg-danger-500'
      },
      critical: {
        icon: AlertTriangle,
        label: 'Critical Risk',
        color: 'danger',
        bgColor: 'bg-danger-100',
        textColor: 'text-danger-800',
        borderColor: 'border-danger-300',
        iconColor: 'text-danger-700',
        progressColor: 'bg-danger-600'
      }
    }
    return configs[level]
  }

  const config = getRiskConfig(level)
  const IconComponent = config.icon

  const sizeClasses = {
    sm: {
      container: 'text-xs',
      icon: 'w-3 h-3',
      padding: 'px-2 py-1',
      circular: 'w-6 h-6',
      circularIcon: 'w-3 h-3'
    },
    md: {
      container: 'text-sm',
      icon: 'w-4 h-4',
      padding: 'px-2.5 py-1.5',
      circular: 'w-8 h-8',
      circularIcon: 'w-4 h-4'
    },
    lg: {
      container: 'text-base',
      icon: 'w-5 h-5',
      padding: 'px-3 py-2',
      circular: 'w-10 h-10',
      circularIcon: 'w-5 h-5'
    }
  }

  const currentSize = sizeClasses[size]

  if (variant === 'circular') {
    return (
      <motion.div
        initial={animated ? { scale: 0 } : undefined}
        animate={animated ? { scale: 1 } : undefined}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={cn(
          'rounded-full flex items-center justify-center border',
          config.bgColor,
          config.borderColor,
          currentSize.circular,
          animated && level === 'critical' && 'animate-status-pulse',
          className
        )}
        title={showScore && score ? `${config.label}: ${score}/${maxScore}` : config.label}
      >
        {showIcon && (
          <IconComponent className={cn(currentSize.circularIcon, config.iconColor)} />
        )}
      </motion.div>
    )
  }

  if (variant === 'detailed') {
    const progressPercentage = score ? (score / maxScore) * 100 : 0

    return (
      <motion.div
        initial={animated ? { opacity: 0, y: 10 } : undefined}
        animate={animated ? { opacity: 1, y: 0 } : undefined}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={cn(
          'rounded-lg border p-4 space-y-3',
          config.bgColor,
          config.borderColor,
          animated && level === 'critical' && 'animate-status-pulse',
          className
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {showIcon && (
              <IconComponent className={cn(currentSize.icon, config.iconColor)} />
            )}
            {showLabel && (
              <span className={cn('font-medium', config.textColor, currentSize.container)}>
                {config.label}
              </span>
            )}
          </div>
          {showScore && score !== undefined && (
            <span className={cn('font-bold', config.textColor, currentSize.container)}>
              {score.toFixed(1)}/{maxScore}
            </span>
          )}
        </div>
        
        {score !== undefined && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-neutral-500">
              <span>Risk Level</span>
              <span>{progressPercentage.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-neutral-200 rounded-full h-2 overflow-hidden">
              <motion.div
                className={cn('h-full rounded-full', config.progressColor)}
                initial={{ width: 0 }}
                animate={{ width: `${progressPercentage}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            </div>
          </div>
        )}
      </motion.div>
    )
  }

  // Compact variant (default)
  return (
    <motion.div
      initial={animated ? { scale: 0.8, opacity: 0 } : undefined}
      animate={animated ? { scale: 1, opacity: 1 } : undefined}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        config.bgColor,
        config.textColor,
        config.borderColor,
        currentSize.padding,
        currentSize.container,
        animated && level === 'critical' && 'animate-status-pulse',
        className
      )}
    >
      {showIcon && (
        <IconComponent className={cn(currentSize.icon, config.iconColor)} />
      )}
      {showLabel && <span>{config.label}</span>}
      {showScore && score !== undefined && (
        <span className="font-bold">
          {score.toFixed(1)}
        </span>
      )}
    </motion.div>
  )
}

export default RiskIndicator