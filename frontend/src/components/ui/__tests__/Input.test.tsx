/**
 * Test Input component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@/test/utils'
import { Input } from '../Input'

describe('Input Component', () => {
  it('renders basic input', () => {
    render(<Input placeholder="Enter text" />)
    const input = screen.getByPlaceholderText('Enter text')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'text')
  })

  it('renders with label', () => {
    render(<Input label="Username" />)
    const label = screen.getByText('Username')
    const input = screen.getByLabelText('Username')
    
    expect(label).toBeInTheDocument()
    expect(input).toBeInTheDocument()
  })

  it('shows error state', () => {
    render(<Input label="Email" error="Invalid email" />)
    const input = screen.getByLabelText('Email')
    const errorMessage = screen.getByText('Invalid email')
    
    expect(input).toHaveClass('border-red-500')
    expect(errorMessage).toBeInTheDocument()
    expect(errorMessage).toHaveClass('text-red-600')
  })

  it('shows required indicator', () => {
    render(<Input label="Required Field" required />)
    const label = screen.getByText(/required field/i)
    
    expect(label.textContent).toContain('*')
  })

  it('handles different input types', () => {
    const { rerender } = render(<Input type="email" />)
    expect(screen.getByDisplayValue('')).toHaveAttribute('type', 'email')
    
    rerender(<Input type="password" />)
    expect(screen.getByDisplayValue('')).toHaveAttribute('type', 'password')
    
    rerender(<Input type="number" />)
    expect(screen.getByDisplayValue('')).toHaveAttribute('type', 'number')
  })

  it('handles value changes', () => {
    const handleChange = vi.fn()
    render(<Input onChange={handleChange} />)
    
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'test value' } })
    
    expect(handleChange).toHaveBeenCalledTimes(1)
    expect(handleChange).toHaveBeenCalledWith(expect.objectContaining({
      target: expect.objectContaining({ value: 'test value' })
    }))
  })

  it('can be disabled', () => {
    render(<Input disabled placeholder="Disabled input" />)
    const input = screen.getByPlaceholderText('Disabled input')
    
    expect(input).toBeDisabled()
    expect(input).toHaveClass('cursor-not-allowed', 'opacity-50')
  })

  it('shows help text', () => {
    render(<Input label="Password" helpText="Must be at least 8 characters" />)
    const helpText = screen.getByText('Must be at least 8 characters')
    
    expect(helpText).toBeInTheDocument()
    expect(helpText).toHaveClass('text-neutral-600')
  })

  it('applies custom className', () => {
    render(<Input className="custom-input-class" />)
    const input = screen.getByRole('textbox')
    
    expect(input).toHaveClass('custom-input-class')
  })

  it('handles controlled input', () => {
    const handleChange = vi.fn()
    const { rerender } = render(<Input value="initial" onChange={handleChange} />)
    
    expect(screen.getByDisplayValue('initial')).toBeInTheDocument()
    
    rerender(<Input value="updated" onChange={handleChange} />)
    expect(screen.getByDisplayValue('updated')).toBeInTheDocument()
  })

  it('shows different sizes', () => {
    const { rerender } = render(<Input size="sm" />)
    expect(screen.getByRole('textbox')).toHaveClass('h-8')
    
    rerender(<Input size="md" />)
    expect(screen.getByRole('textbox')).toHaveClass('h-10')
    
    rerender(<Input size="lg" />)
    expect(screen.getByRole('textbox')).toHaveClass('h-12')
  })

  it('has proper accessibility attributes', () => {
    render(
      <Input 
        label="Email" 
        required 
        error="Invalid email"
        helpText="Enter your email address"
        aria-describedby="custom-description"
      />
    )
    
    const input = screen.getByLabelText('Email *')
    
    expect(input).toHaveAttribute('required')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby')
  })

  it('supports ref forwarding', () => {
    let inputRef: HTMLInputElement | null = null
    
    render(<Input ref={(ref) => { inputRef = ref }} />)
    
    expect(inputRef).toBeInstanceOf(HTMLInputElement)
  })
})