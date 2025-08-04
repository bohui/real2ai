import React from 'react'
import { cn } from '@/utils'

interface TypographyProps extends React.HTMLAttributes<HTMLElement> {
  variant?: 
    | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
    | 'body1' | 'body2' | 'subtitle1' | 'subtitle2'
    | 'caption' | 'overline' | 'legal' | 'code'
  color?: 'primary' | 'secondary' | 'muted' | 'accent' | 'success' | 'warning' | 'danger' | 'trust'
  weight?: 'light' | 'normal' | 'medium' | 'semibold' | 'bold'
  align?: 'left' | 'center' | 'right' | 'justify'
  as?: React.ElementType
  gradient?: boolean
}

const Typography = React.forwardRef<HTMLElement, TypographyProps>(
  (
    {
      className,
      variant = 'body1',
      color = 'primary',
      weight,
      align = 'left',
      as,
      gradient = false,
      children,
      ...props
    },
    ref
  ) => {
    const variantStyles = {
      h1: 'text-4xl md:text-5xl lg:text-6xl font-heading font-bold leading-tight tracking-tight',
      h2: 'text-3xl md:text-4xl lg:text-5xl font-heading font-bold leading-tight tracking-tight',
      h3: 'text-2xl md:text-3xl lg:text-4xl font-heading font-semibold leading-tight',
      h4: 'text-xl md:text-2xl lg:text-3xl font-heading font-semibold leading-snug',
      h5: 'text-lg md:text-xl lg:text-2xl font-heading font-medium leading-snug',
      h6: 'text-base md:text-lg lg:text-xl font-heading font-medium leading-normal',
      body1: 'text-base leading-relaxed font-normal',
      body2: 'text-sm leading-relaxed font-normal',
      subtitle1: 'text-lg font-medium leading-normal',
      subtitle2: 'text-base font-medium leading-normal',
      caption: 'text-xs leading-normal font-normal',
      overline: 'text-xs leading-normal font-medium uppercase tracking-wider',
      legal: 'text-sm leading-relaxed font-normal font-mono',
      code: 'text-sm font-mono leading-normal bg-neutral-100 px-1.5 py-0.5 rounded'
    }

    const colorStyles = {
      primary: gradient 
        ? 'bg-gradient-to-r from-primary-600 to-primary-700 bg-clip-text text-transparent'
        : 'text-neutral-900',
      secondary: gradient
        ? 'bg-gradient-to-r from-secondary-500 to-secondary-600 bg-clip-text text-transparent'
        : 'text-neutral-700',
      muted: 'text-neutral-500',
      accent: gradient
        ? 'bg-gradient-to-r from-accent-500 to-accent-600 bg-clip-text text-transparent'
        : 'text-accent-600',
      success: gradient
        ? 'bg-gradient-to-r from-success-500 to-success-600 bg-clip-text text-transparent'
        : 'text-success-600',
      warning: gradient
        ? 'bg-gradient-to-r from-warning-500 to-warning-600 bg-clip-text text-transparent'
        : 'text-warning-600',
      danger: gradient
        ? 'bg-gradient-to-r from-danger-500 to-danger-600 bg-clip-text text-transparent'
        : 'text-danger-600',
      trust: gradient
        ? 'bg-gradient-to-r from-trust-500 to-trust-600 bg-clip-text text-transparent'
        : 'text-trust-600'
    }

    const weightStyles = weight ? {
      light: 'font-light',
      normal: 'font-normal',
      medium: 'font-medium',
      semibold: 'font-semibold',
      bold: 'font-bold'
    }[weight] : ''

    const alignStyles = {
      left: 'text-left',
      center: 'text-center',
      right: 'text-right',
      justify: 'text-justify'
    }

    const defaultElements = {
      h1: 'h1',
      h2: 'h2',
      h3: 'h3',
      h4: 'h4',
      h5: 'h5',
      h6: 'h6',
      body1: 'p',
      body2: 'p',
      subtitle1: 'p',
      subtitle2: 'p',
      caption: 'span',
      overline: 'span',
      legal: 'p',
      code: 'code'
    }

    const Component = as || defaultElements[variant] || 'p'

    return (
      <Component
        className={cn(
          variantStyles[variant],
          colorStyles[color],
          weightStyles,
          alignStyles[align],
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Typography.displayName = 'Typography'

export default Typography