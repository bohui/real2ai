/**
 * Test Typography component
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@/test/utils'
import { render } from '@testing-library/react'
import Typography from '../Typography'

// Mock utils
vi.mock('@/utils', () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(' '),
}))

describe('Typography Component', () => {
  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<Typography>Test content</Typography>)
      
      expect(screen.getByText('Test content')).toBeInTheDocument()
    })

    it('renders with default props', () => {
      render(<Typography>Default typography</Typography>)
      
      const element = screen.getByText('Default typography')
      expect(element).toBeInTheDocument()
      expect(element.tagName).toBe('P') // Default variant is body1 which maps to p
    })

    it('applies default classes correctly', () => {
      render(<Typography>Test</Typography>)
      
      const element = screen.getByText('Test')
      expect(element).toHaveClass('text-base', 'leading-relaxed', 'font-normal') // body1 variant
      expect(element).toHaveClass('text-neutral-900') // primary color
      expect(element).toHaveClass('text-left') // default alignment
    })
  })

  describe('Variant Prop', () => {
    it('renders heading variants correctly', () => {
      const headingVariants = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] as const
      
      headingVariants.forEach((variant, index) => {
        const { unmount } = render(<Typography variant={variant}>Heading {index + 1}</Typography>)
        
        const element = screen.getByText(`Heading ${index + 1}`)
        expect(element.tagName).toBe(variant.toUpperCase())
        expect(element).toHaveClass('font-heading')
        
        unmount()
      })
    })

    it('applies h1 variant classes correctly', () => {
      render(<Typography variant="h1">H1 Title</Typography>)
      
      const element = screen.getByText('H1 Title')
      expect(element).toHaveClass(
        'text-4xl', 'md:text-5xl', 'lg:text-6xl', 
        'font-heading', 'font-bold', 'leading-tight', 'tracking-tight'
      )
    })

    it('applies h2 variant classes correctly', () => {
      render(<Typography variant="h2">H2 Title</Typography>)
      
      const element = screen.getByText('H2 Title')
      expect(element).toHaveClass(
        'text-3xl', 'md:text-4xl', 'lg:text-5xl',
        'font-heading', 'font-bold', 'leading-tight', 'tracking-tight'
      )
    })

    it('applies h3 variant classes correctly', () => {
      render(<Typography variant="h3">H3 Title</Typography>)
      
      const element = screen.getByText('H3 Title')
      expect(element).toHaveClass(
        'text-2xl', 'md:text-3xl', 'lg:text-4xl',
        'font-heading', 'font-semibold', 'leading-tight'
      )
    })

    it('renders body variants correctly', () => {
      const { rerender } = render(<Typography variant="body1">Body 1</Typography>)
      
      let element = screen.getByText('Body 1')
      expect(element.tagName).toBe('P')
      expect(element).toHaveClass('text-base', 'leading-relaxed', 'font-normal')
      
      rerender(<Typography variant="body2">Body 2</Typography>)
      
      element = screen.getByText('Body 2')
      expect(element.tagName).toBe('P')
      expect(element).toHaveClass('text-sm', 'leading-relaxed', 'font-normal')
    })

    it('renders subtitle variants correctly', () => {
      const { rerender } = render(<Typography variant="subtitle1">Subtitle 1</Typography>)
      
      let element = screen.getByText('Subtitle 1')
      expect(element.tagName).toBe('P')
      expect(element).toHaveClass('text-lg', 'font-medium', 'leading-normal')
      
      rerender(<Typography variant="subtitle2">Subtitle 2</Typography>)
      
      element = screen.getByText('Subtitle 2')
      expect(element.tagName).toBe('P')
      expect(element).toHaveClass('text-base', 'font-medium', 'leading-normal')
    })

    it('renders small text variants correctly', () => {
      const { rerender } = render(<Typography variant="caption">Caption text</Typography>)
      
      let element = screen.getByText('Caption text')
      expect(element.tagName).toBe('SPAN')
      expect(element).toHaveClass('text-xs', 'leading-normal', 'font-normal')
      
      rerender(<Typography variant="overline">Overline text</Typography>)
      
      element = screen.getByText('Overline text')
      expect(element.tagName).toBe('SPAN')
      expect(element).toHaveClass('text-xs', 'leading-normal', 'font-medium', 'uppercase', 'tracking-wider')
    })

    it('renders special variants correctly', () => {
      const { rerender } = render(<Typography variant="legal">Legal text</Typography>)
      
      let element = screen.getByText('Legal text')
      expect(element.tagName).toBe('P')
      expect(element).toHaveClass('text-sm', 'leading-relaxed', 'font-normal', 'font-mono')
      
      rerender(<Typography variant="code">Code text</Typography>)
      
      element = screen.getByText('Code text')
      expect(element.tagName).toBe('CODE')
      expect(element).toHaveClass('text-sm', 'font-mono', 'leading-normal', 'bg-neutral-100', 'px-1.5', 'py-0.5', 'rounded')
    })
  })

  describe('Color Prop', () => {
    it('applies primary color correctly', () => {
      render(<Typography color="primary">Primary text</Typography>)
      
      const element = screen.getByText('Primary text')
      expect(element).toHaveClass('text-neutral-900')
    })

    it('applies secondary color correctly', () => {
      render(<Typography color="secondary">Secondary text</Typography>)
      
      const element = screen.getByText('Secondary text')
      expect(element).toHaveClass('text-neutral-700')
    })

    it('applies muted color correctly', () => {
      render(<Typography color="muted">Muted text</Typography>)
      
      const element = screen.getByText('Muted text')
      expect(element).toHaveClass('text-neutral-500')
    })

    it('applies semantic colors correctly', () => {
      const colors = ['accent', 'success', 'warning', 'danger', 'trust'] as const
      
      colors.forEach(color => {
        const { unmount } = render(<Typography color={color}>{color} text</Typography>)
        
        const element = screen.getByText(`${color} text`)
        expect(element).toHaveClass(`text-${color}-600`)
        
        unmount()
      })
    })
  })

  describe('Gradient Color', () => {
    it('applies gradient for primary color', () => {
      render(<Typography color="primary" gradient>Gradient primary</Typography>)
      
      const element = screen.getByText('Gradient primary')
      expect(element).toHaveClass(
        'bg-gradient-to-r', 'from-primary-600', 'to-primary-700', 
        'bg-clip-text', 'text-transparent'
      )
    })

    it('applies gradient for secondary color', () => {
      render(<Typography color="secondary" gradient>Gradient secondary</Typography>)
      
      const element = screen.getByText('Gradient secondary')
      expect(element).toHaveClass(
        'bg-gradient-to-r', 'from-secondary-500', 'to-secondary-600',
        'bg-clip-text', 'text-transparent'
      )
    })

    it('applies gradient for semantic colors', () => {
      const colors = ['accent', 'success', 'warning', 'danger', 'trust'] as const
      
      colors.forEach(color => {
        const { unmount } = render(<Typography color={color} gradient>Gradient {color}</Typography>)
        
        const element = screen.getByText(`Gradient ${color}`)
        expect(element).toHaveClass(
          'bg-gradient-to-r', `from-${color}-500`, `to-${color}-600`,
          'bg-clip-text', 'text-transparent'
        )
        
        unmount()
      })
    })

    it('ignores gradient for muted color', () => {
      render(<Typography color="muted" gradient>Muted gradient</Typography>)
      
      const element = screen.getByText('Muted gradient')
      expect(element).toHaveClass('text-neutral-500')
      expect(element).not.toHaveClass('bg-gradient-to-r')
    })

    it('uses regular color when gradient is false', () => {
      render(<Typography color="primary" gradient={false}>No gradient</Typography>)
      
      const element = screen.getByText('No gradient')
      expect(element).toHaveClass('text-neutral-900')
      expect(element).not.toHaveClass('bg-gradient-to-r')
    })
  })

  describe('Weight Prop', () => {
    it('applies different font weights correctly', () => {
      const weights = ['light', 'normal', 'medium', 'semibold', 'bold'] as const
      
      weights.forEach(weight => {
        const { unmount } = render(<Typography weight={weight}>{weight} weight</Typography>)
        
        const element = screen.getByText(`${weight} weight`)
        expect(element).toHaveClass(`font-${weight}`)
        
        unmount()
      })
    })

    it('does not apply weight class when weight is undefined', () => {
      render(<Typography>No weight</Typography>)
      
      const element = screen.getByText('No weight')
      expect(element).not.toHaveClass('font-light', 'font-normal', 'font-medium', 'font-semibold', 'font-bold')
    })

    it('overrides variant font weight with explicit weight', () => {
      render(<Typography variant="h1" weight="light">Light H1</Typography>)
      
      const element = screen.getByText('Light H1')
      expect(element).toHaveClass('font-light')
      expect(element).toHaveClass('font-bold') // From h1 variant
    })
  })

  describe('Align Prop', () => {
    it('applies text alignment correctly', () => {
      const alignments = ['left', 'center', 'right', 'justify'] as const
      
      alignments.forEach(align => {
        const { unmount } = render(<Typography align={align}>{align} aligned</Typography>)
        
        const element = screen.getByText(`${align} aligned`)
        expect(element).toHaveClass(`text-${align}`)
        
        unmount()
      })
    })

    it('applies default left alignment', () => {
      render(<Typography>Default alignment</Typography>)
      
      const element = screen.getByText('Default alignment')
      expect(element).toHaveClass('text-left')
    })
  })

  describe('As Prop (Polymorphic)', () => {
    it('renders as custom element when as prop is provided', () => {
      render(<Typography as="span">Span element</Typography>)
      
      const element = screen.getByText('Span element')
      expect(element.tagName).toBe('SPAN')
    })

    it('overrides default element mapping', () => {
      render(<Typography variant="h1" as="div">Div with h1 styling</Typography>)
      
      const element = screen.getByText('Div with h1 styling')
      expect(element.tagName).toBe('DIV')
      expect(element).toHaveClass('text-4xl', 'md:text-5xl', 'lg:text-6xl', 'font-heading', 'font-bold')
    })

    it('works with complex component types', () => {
      const CustomComponent = ({ children, className, ...props }: any) => (
        <article className={`custom-article ${className}`} {...props}>
          {children}
        </article>
      )
      
      render(<Typography as={CustomComponent}>Custom component</Typography>)
      
      const element = screen.getByText('Custom component')
      expect(element.tagName).toBe('ARTICLE')
      expect(element).toHaveClass('custom-article')
    })
  })

  describe('Custom Props and Ref', () => {
    it('applies custom className', () => {
      render(<Typography className="custom-class">Custom styled</Typography>)
      
      const element = screen.getByText('Custom styled')
      expect(element).toHaveClass('custom-class')
    })

    it('combines custom className with component classes', () => {
      render(<Typography variant="h2" color="success" className="custom-class">Combined classes</Typography>)
      
      const element = screen.getByText('Combined classes')
      expect(element).toHaveClass('custom-class')
      expect(element).toHaveClass('text-3xl', 'md:text-4xl', 'lg:text-5xl', 'font-heading')
      expect(element).toHaveClass('text-success-600')
    })

    it('forwards additional HTML attributes', () => {
      render(<Typography id="test-id" data-testid="typography-element">With attributes</Typography>)
      
      const element = screen.getByText('With attributes')
      expect(element).toHaveAttribute('id', 'test-id')
      expect(element).toHaveAttribute('data-testid', 'typography-element')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      
      render(<Typography ref={ref}>Ref test</Typography>)
      
      expect(ref.current).not.toBeNull()
    })

    it('passes through event handlers', () => {
      const handleClick = vi.fn()
      
      render(<Typography onClick={handleClick}>Clickable text</Typography>)
      
      const element = screen.getByText('Clickable text')
      element.click()
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Default Element Mapping', () => {
    it('maps variants to correct default elements', () => {
      const variantElementMapping = [
        { variant: 'h1', expectedTag: 'H1' },
        { variant: 'h2', expectedTag: 'H2' },
        { variant: 'h3', expectedTag: 'H3' },
        { variant: 'h4', expectedTag: 'H4' },
        { variant: 'h5', expectedTag: 'H5' },
        { variant: 'h6', expectedTag: 'H6' },
        { variant: 'body1', expectedTag: 'P' },
        { variant: 'body2', expectedTag: 'P' },
        { variant: 'subtitle1', expectedTag: 'P' },
        { variant: 'subtitle2', expectedTag: 'P' },
        { variant: 'caption', expectedTag: 'SPAN' },
        { variant: 'overline', expectedTag: 'SPAN' },
        { variant: 'legal', expectedTag: 'P' },
        { variant: 'code', expectedTag: 'CODE' },
      ] as const
      
      variantElementMapping.forEach(({ variant, expectedTag }) => {
        const { unmount } = render(<Typography variant={variant}>Test {variant}</Typography>)
        
        const element = screen.getByText(`Test ${variant}`)
        expect(element.tagName).toBe(expectedTag)
        
        unmount()
      })
    })

    it('falls back to p element for unknown variants', () => {
      // This tests the internal fallback mechanism
      const { container } = render(<Typography variant={'unknown' as any}>Unknown variant</Typography>)
      
      const element = container.querySelector('p')
      expect(element).toBeInTheDocument()
      expect(element).toHaveTextContent('Unknown variant')
    })
  })

  describe('Complex Combinations', () => {
    it('handles all props together correctly', () => {
      render(
        <Typography
          variant="h2"
          color="success"
          weight="medium"
          align="center"
          gradient
          className="custom-class"
          as="div"
        >
          Complex typography
        </Typography>
      )
      
      const element = screen.getByText('Complex typography')
      
      // Element type
      expect(element.tagName).toBe('DIV')
      
      // Variant classes
      expect(element).toHaveClass('text-3xl', 'md:text-4xl', 'lg:text-5xl', 'font-heading')
      
      // Color with gradient
      expect(element).toHaveClass('bg-gradient-to-r', 'from-success-500', 'to-success-600', 'bg-clip-text', 'text-transparent')
      
      // Weight
      expect(element).toHaveClass('font-medium')
      
      // Alignment
      expect(element).toHaveClass('text-center')
      
      // Custom class
      expect(element).toHaveClass('custom-class')
    })

    it('handles edge case with empty children', () => {
      render(<Typography></Typography>)
      
      const element = document.querySelector('p')
      expect(element).toBeInTheDocument()
      expect(element).toBeEmptyDOMElement()
    })

    it('handles multiple children correctly', () => {
      render(
        <Typography>
          Text content
          <span>Inline span</span>
          More text
        </Typography>
      )
      
      const element = screen.getByText('Text content')
      expect(element).toBeInTheDocument()
      expect(screen.getByText('Inline span')).toBeInTheDocument()
      expect(screen.getByText('More text')).toBeInTheDocument()
    })
  })

  describe('Responsive Classes', () => {
    it('applies responsive typography classes for headings', () => {
      render(<Typography variant="h1">Responsive heading</Typography>)
      
      const element = screen.getByText('Responsive heading')
      expect(element).toHaveClass('text-4xl', 'md:text-5xl', 'lg:text-6xl')
    })

    it('applies consistent responsive scaling across heading variants', () => {
      const headingVariants = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] as const
      
      headingVariants.forEach(variant => {
        const { unmount } = render(<Typography variant={variant}>Responsive {variant}</Typography>)
        
        const element = screen.getByText(`Responsive ${variant}`)
        
        // Should have responsive classes
        const classes = element.className
        expect(classes).toMatch(/md:text-/)
        expect(classes).toMatch(/lg:text-/)
        
        unmount()
      })
    })
  })

  describe('Accessibility', () => {
    it('maintains semantic HTML structure', () => {
      render(
        <div>
          <Typography variant="h1">Main Title</Typography>
          <Typography variant="h2">Section Title</Typography>
          <Typography variant="body1">Body content</Typography>
        </div>
      )
      
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Main Title')
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Section Title')
    })

    it('preserves ARIA attributes when passed', () => {
      render(
        <Typography 
          variant="h2" 
          role="banner" 
          aria-label="Custom label"
          aria-describedby="description"
        >
          Accessible heading
        </Typography>
      )
      
      const element = screen.getByText('Accessible heading')
      expect(element).toHaveAttribute('role', 'banner')
      expect(element).toHaveAttribute('aria-label', 'Custom label')
      expect(element).toHaveAttribute('aria-describedby', 'description')
    })

    it('supports keyboard navigation when interactive', () => {
      const handleKeyDown = vi.fn()
      
      render(
        <Typography 
          variant="button" 
          tabIndex={0}
          onKeyDown={handleKeyDown}
        >
          Interactive text
        </Typography>
      )
      
      const element = screen.getByText('Interactive text')
      expect(element).toHaveAttribute('tabIndex', '0')
    })
  })

  describe('Display Name', () => {
    it('has correct display name for debugging', () => {
      expect(Typography.displayName).toBe('Typography')
    })
  })
})