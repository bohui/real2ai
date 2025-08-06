import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Typography from '../Typography'

describe('Typography Component', () => {
  describe('Heading Variants', () => {
    it('should render h1 heading', () => {
      render(<Typography variant="h1">Main Heading</Typography>)
      
      const heading = screen.getByRole('heading', { level: 1 })
      expect(heading).toBeInTheDocument()
      expect(heading).toHaveTextContent('Main Heading')
      expect(heading.tagName).toBe('H1')
    })

    it('should render h2 heading', () => {
      render(<Typography variant="h2">Section Heading</Typography>)
      
      const heading = screen.getByRole('heading', { level: 2 })
      expect(heading).toBeInTheDocument()
      expect(heading).toHaveTextContent('Section Heading')
      expect(heading.tagName).toBe('H2')
    })

    it('should render h3 heading', () => {
      render(<Typography variant="h3">Subsection Heading</Typography>)
      
      const heading = screen.getByRole('heading', { level: 3 })
      expect(heading).toBeInTheDocument()
      expect(heading.tagName).toBe('H3')
    })

    it('should render h4 heading', () => {
      render(<Typography variant="h4">Small Heading</Typography>)
      
      const heading = screen.getByRole('heading', { level: 4 })
      expect(heading).toBeInTheDocument()
      expect(heading.tagName).toBe('H4')
    })
  })

  describe('Body Text Variants', () => {
    it('should render body text', () => {
      render(<Typography variant="body1">This is body text</Typography>)
      
      const text = screen.getByText('This is body text')
      expect(text).toBeInTheDocument()
      expect(text.tagName).toBe('P')
    })

    it('should render large body text', () => {
      render(<Typography variant="body1">This is large body text</Typography>)
      
      const text = screen.getByText('This is large body text')
      expect(text).toHaveClass('text-lg')
    })

    it('should render small body text', () => {
      render(<Typography variant="body2">This is small body text</Typography>)
      
      const text = screen.getByText('This is small body text')
      expect(text).toHaveClass('text-sm')
    })
  })

  describe('Special Variants', () => {
    it('should render caption text', () => {
      render(<Typography variant="caption">This is caption text</Typography>)
      
      const text = screen.getByText('This is caption text')
      expect(text).toHaveClass('text-xs')
      expect(text.tagName).toBe('SPAN')
    })

    it('should render subtitle text', () => {
      render(<Typography variant="subtitle1">This is subtitle text</Typography>)
      
      const text = screen.getByText('This is subtitle text')
      expect(text).toHaveClass('text-lg', 'font-medium')
    })

    it('should render overline text', () => {
      render(<Typography variant="overline">OVERLINE TEXT</Typography>)
      
      const text = screen.getByText('OVERLINE TEXT')
      expect(text).toHaveClass('text-xs', 'uppercase', 'tracking-wider')
    })
  })

  describe('Custom Element Types', () => {
    it('should render with custom element', () => {
      render(
        <Typography variant="body1" as="div">
          Div content
        </Typography>
      )
      
      const element = screen.getByText('Div content')
      expect(element.tagName).toBe('DIV')
    })

    it('should render span when specified', () => {
      render(
        <Typography variant="h2" as="span">
          Span heading
        </Typography>
      )
      
      const element = screen.getByText('Span heading')
      expect(element.tagName).toBe('SPAN')
    })
  })

  describe('Text Colors', () => {
    it('should render with primary color', () => {
      render(<Typography color="primary">Primary text</Typography>)
      
      const text = screen.getByText('Primary text')
      expect(text).toHaveClass('text-primary-600')
    })

    it('should render with secondary color', () => {
      render(<Typography color="secondary">Secondary text</Typography>)
      
      const text = screen.getByText('Secondary text')
      expect(text).toHaveClass('text-secondary-600')
    })

    it('should render with muted color', () => {
      render(<Typography color="muted">Muted text</Typography>)
      
      const text = screen.getByText('Muted text')
      expect(text).toHaveClass('text-gray-600')
    })

    it('should render with error color', () => {
      render(<Typography color="danger">Error text</Typography>)
      
      const text = screen.getByText('Error text')
      expect(text).toHaveClass('text-red-600')
    })

    it('should render with success color', () => {
      render(<Typography color="success">Success text</Typography>)
      
      const text = screen.getByText('Success text')
      expect(text).toHaveClass('text-green-600')
    })

    it('should render with warning color', () => {
      render(<Typography color="warning">Warning text</Typography>)
      
      const text = screen.getByText('Warning text')
      expect(text).toHaveClass('text-yellow-600')
    })
  })

  describe('Text Alignment', () => {
    it('should render with center alignment', () => {
      render(<Typography align="center">Centered text</Typography>)
      
      const text = screen.getByText('Centered text')
      expect(text).toHaveClass('text-center')
    })

    it('should render with right alignment', () => {
      render(<Typography align="right">Right aligned text</Typography>)
      
      const text = screen.getByText('Right aligned text')
      expect(text).toHaveClass('text-right')
    })

    it('should render with left alignment by default', () => {
      render(<Typography>Left aligned text</Typography>)
      
      const text = screen.getByText('Left aligned text')
      expect(text).toHaveClass('text-left')
    })

    it('should render with justify alignment', () => {
      render(<Typography align="justify">Justified text</Typography>)
      
      const text = screen.getByText('Justified text')
      expect(text).toHaveClass('text-justify')
    })
  })

  describe('Font Weight', () => {
    it('should render with light weight', () => {
      render(<Typography weight="light">Light text</Typography>)
      
      const text = screen.getByText('Light text')
      expect(text).toHaveClass('font-light')
    })

    it('should render with normal weight', () => {
      render(<Typography weight="normal">Normal text</Typography>)
      
      const text = screen.getByText('Normal text')
      expect(text).toHaveClass('font-normal')
    })

    it('should render with medium weight', () => {
      render(<Typography weight="medium">Medium text</Typography>)
      
      const text = screen.getByText('Medium text')
      expect(text).toHaveClass('font-medium')
    })

    it('should render with semibold weight', () => {
      render(<Typography weight="semibold">Semibold text</Typography>)
      
      const text = screen.getByText('Semibold text')
      expect(text).toHaveClass('font-semibold')
    })

    it('should render with bold weight', () => {
      render(<Typography weight="bold">Bold text</Typography>)
      
      const text = screen.getByText('Bold text')
      expect(text).toHaveClass('font-bold')
    })
  })

  describe('Additional Props', () => {
    it('should apply custom className', () => {
      render(<Typography className="custom-class">Custom class text</Typography>)
      
      const text = screen.getByText('Custom class text')
      expect(text).toHaveClass('custom-class')
    })

    it('should pass through data attributes', () => {
      render(<Typography data-testid="custom-typography">Test text</Typography>)
      
      const text = screen.getByTestId('custom-typography')
      expect(text).toBeInTheDocument()
    })

    it('should handle onClick events', () => {
      const handleClick = vi.fn()
      render(<Typography onClick={handleClick}>Clickable text</Typography>)
      
      const text = screen.getByText('Clickable text')
      text.click()
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('should render with truncation', () => {
      render(<Typography>This is very long text that should be truncated</Typography>)
      
      const text = screen.getByText('This is very long text that should be truncated')
      expect(text).toHaveClass('truncate')
    })

    it('should render with no wrap', () => {
      render(<Typography>This text should not wrap</Typography>)
      
      const text = screen.getByText('This text should not wrap')
      expect(text).toHaveClass('whitespace-nowrap')
    })
  })

  describe('Responsive Typography', () => {
    it('should handle responsive font sizes', () => {
      render(<Typography variant="h1">Responsive heading</Typography>)
      
      const text = screen.getByText('Responsive heading')
      expect(text).toHaveClass('text-2xl', 'md:text-4xl', 'lg:text-5xl')
    })
  })

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      render(
        <div>
          <Typography variant="h1">Main Title</Typography>
          <Typography variant="h2">Section</Typography>
          <Typography variant="h3">Subsection</Typography>
        </div>
      )
      
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 3 })).toBeInTheDocument()
    })

    it('should support screen readers with appropriate semantics', () => {
      render(<Typography variant="caption" role="note">Important note</Typography>)
      
      const text = screen.getByRole('note')
      expect(text).toHaveTextContent('Important note')
    })

    it('should handle aria-label for accessibility', () => {
      render(<Typography aria-label="Accessible label">Content</Typography>)
      
      const text = screen.getByLabelText('Accessible label')
      expect(text).toBeInTheDocument()
    })
  })
})