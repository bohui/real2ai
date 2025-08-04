import React from 'react'
import { cn } from '@/utils'
import { Card } from './Card'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circle' | 'rectangle'
  width?: string | number
  height?: string | number
  animated?: boolean
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'rectangle',
  width,
  height,
  animated = true
}) => {
  const baseClasses = [
    'bg-neutral-200',
    animated && 'animate-pulse',
    variant === 'text' && 'h-4 rounded',
    variant === 'circle' && 'rounded-full',
    variant === 'rectangle' && 'rounded-lg'
  ].filter(Boolean).join(' ')

  return (
    <div
      className={cn(baseClasses, className)}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height
      }}
    />
  )
}

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  variant?: 'primary' | 'secondary' | 'neutral'
  className?: string
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  variant = 'primary',
  className
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12'
  }

  const variantClasses = {
    primary: 'border-primary-600 border-t-transparent',
    secondary: 'border-secondary-600 border-t-transparent',
    neutral: 'border-neutral-400 border-t-transparent'
  }

  return (
    <div
      className={cn(
        'border-2 rounded-full animate-spin',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    />
  )
}

interface LoadingCardProps {
  showHeader?: boolean
  showContent?: boolean
  showFooter?: boolean
  lines?: number
  className?: string
}

export const LoadingCard: React.FC<LoadingCardProps> = ({
  showHeader = true,
  showContent = true,
  showFooter = false,
  lines = 3,
  className
}) => {
  return (
    <Card className={cn('p-6', className)}>
      {showHeader && (
        <div className="mb-4">
          <Skeleton className="h-6 w-3/4 mb-2" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      )}
      
      {showContent && (
        <div className="space-y-3 mb-4">
          {Array.from({ length: lines }).map((_, i) => (
            <Skeleton 
              key={i} 
              width={i === lines - 1 ? '60%' : '100%'} 
              className="h-4" 
            />
          ))}
        </div>
      )}
      
      {showFooter && (
        <div className="flex justify-between items-center pt-4 border-t border-neutral-100">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-8 w-24" />
        </div>
      )}
    </Card>
  )
}

interface LoadingStateProps {
  type?: 'cards' | 'table' | 'list' | 'dashboard'
  count?: number
  className?: string
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  type = 'cards',
  count = 3,
  className
}) => {
  if (type === 'cards') {
    return (
      <div className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6', className)}>
        {Array.from({ length: count }).map((_, i) => (
          <LoadingCard key={i} showFooter />
        ))}
      </div>
    )
  }

  if (type === 'table') {
    return (
      <Card className={cn('p-6', className)}>
        <div className="space-y-4">
          {/* Table header */}
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-4" />
            ))}
          </div>
          
          {/* Table rows */}
          {Array.from({ length: count }).map((_, i) => (
            <div key={i} className="grid grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, j) => (
                <Skeleton key={j} className="h-4" />
              ))}
            </div>
          ))}
        </div>
      </Card>
    )
  }

  if (type === 'list') {
    return (
      <div className={cn('space-y-4', className)}>
        {Array.from({ length: count }).map((_, i) => (
          <Card key={i} className="p-4">
            <div className="flex items-center gap-4">
              <Skeleton variant="circle" width={40} height={40} />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
              <Skeleton className="h-8 w-20" />
            </div>
          </Card>
        ))}
      </div>
    )
  }

  if (type === 'dashboard') {
    return (
      <div className={cn('space-y-8', className)}>
        {/* Stats grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="p-6">
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton variant="circle" width={48} height={48} />
              </div>
            </Card>
          ))}
        </div>
        
        {/* Main content grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <LoadingCard showFooter />
          <div className="lg:col-span-2">
            <LoadingCard lines={5} showFooter />
          </div>
        </div>
      </div>
    )
  }

  return null
}

interface ProcessingIndicatorProps {
  stage: string
  progress?: number
  stages?: string[]
  currentStage?: number
  className?: string
}

export const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({
  stage,
  progress,
  stages = [],
  currentStage = 0,
  className
}) => {
  return (
    <Card className={cn('p-6', className)}>
      <div className="text-center">
        <LoadingSpinner size="lg" className="mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-neutral-900 mb-2">
          Processing Contract Analysis
        </h3>
        <p className="text-sm text-neutral-600 mb-4">
          {stage}
        </p>
        
        {progress !== undefined && (
          <div className="w-full bg-neutral-200 rounded-full h-2 mb-4">
            <div 
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        
        {stages.length > 0 && (
          <div className="space-y-2">
            {stages.map((stageName, index) => (
              <div 
                key={index}
                className={cn(
                  'flex items-center gap-3 text-sm p-2 rounded-lg transition-colors',
                  index < currentStage 
                    ? 'text-success-700 bg-success-50' 
                    : index === currentStage 
                    ? 'text-primary-700 bg-primary-50' 
                    : 'text-neutral-500 bg-neutral-50'
                )}
              >
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  index < currentStage 
                    ? 'bg-success-500' 
                    : index === currentStage 
                    ? 'bg-primary-500 animate-pulse' 
                    : 'bg-neutral-300'
                )} />
                <span>{stageName}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

export default {
  Skeleton,
  LoadingSpinner,
  LoadingCard,
  LoadingState,
  ProcessingIndicator
}