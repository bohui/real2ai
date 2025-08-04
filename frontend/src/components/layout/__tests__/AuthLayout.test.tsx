/**
 * Test AuthLayout component
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@/test/utils'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom'
import AuthLayout from '../AuthLayout'

// Custom render function with required providers
const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={ui}>
            <Route index element={<div data-testid="auth-child">Auth Child Content</div>} />
            <Route path="login" element={<div data-testid="login-form">Login Form</div>} />
            <Route path="register" element={<div data-testid="register-form">Register Form</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('AuthLayout Component', () => {
  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderWithProviders(<AuthLayout />)
      
      expect(document.body).toBeInTheDocument()
    })

    it('renders the main container with correct classes', () => {
      renderWithProviders(<AuthLayout />)
      
      const container = document.querySelector('.min-h-screen')
      expect(container).toBeInTheDocument()
      expect(container).toHaveClass(
        'min-h-screen',
        'bg-gradient-to-br',
        'from-primary-50',
        'via-white',
        'to-secondary-50'
      )
    })

    it('includes background pattern element', () => {
      renderWithProviders(<AuthLayout />)
      
      const backgroundPattern = document.querySelector('.bg-grid-pattern')
      expect(backgroundPattern).toBeInTheDocument()
      expect(backgroundPattern).toHaveClass(
        'absolute',
        'inset-0',
        'bg-grid-pattern',
        'opacity-5'
      )
    })

    it('has proper content wrapper structure', () => {
      renderWithProviders(<AuthLayout />)
      
      const contentWrapper = document.querySelector('.relative')
      expect(contentWrapper).toBeInTheDocument()
      expect(contentWrapper).toHaveClass('relative')
    })
  })

  describe('Layout Structure', () => {
    it('has correct CSS layout hierarchy', () => {
      renderWithProviders(<AuthLayout />)
      
      // Main container
      const mainContainer = document.querySelector('.min-h-screen')
      expect(mainContainer).toBeInTheDocument()
      
      // Background pattern (absolute positioned)
      const backgroundPattern = mainContainer?.querySelector('.absolute.inset-0')
      expect(backgroundPattern).toBeInTheDocument()
      
      // Content wrapper (relative positioned)
      const contentWrapper = mainContainer?.querySelector('.relative')
      expect(contentWrapper).toBeInTheDocument()
    })

    it('maintains proper z-index stacking', () => {
      renderWithProviders(<AuthLayout />)
      
      const backgroundPattern = document.querySelector('.bg-grid-pattern')
      const contentWrapper = document.querySelector('.relative')
      
      expect(backgroundPattern).toHaveClass('absolute', 'inset-0')
      expect(contentWrapper).toHaveClass('relative')
      // Relative positioned content should be above absolute positioned background
    })
  })

  describe('Child Route Rendering', () => {
    it('renders child routes through Outlet', () => {
      renderWithProviders(<AuthLayout />)
      
      expect(screen.getByTestId('auth-child')).toBeInTheDocument()
    })

    it('properly integrates with React Router', () => {
      // Test that the layout works with different child routes
      const TestLayout = () => (
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AuthLayout />}>
              <Route path="test" element={<div data-testid="test-route">Test Route</div>} />
            </Route>
          </Routes>
        </BrowserRouter>
      )

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: 0, gcTime: 0 },
        },
      })

      render(
        <QueryClientProvider client={queryClient}>
          <TestLayout />
        </QueryClientProvider>
      )

      // The layout should be present even without a matching child route
      expect(document.querySelector('.min-h-screen')).toBeInTheDocument()
    })
  })

  describe('Responsive Design', () => {
    it('applies responsive gradient background', () => {
      renderWithProviders(<AuthLayout />)
      
      const container = document.querySelector('.min-h-screen')
      expect(container).toHaveClass('bg-gradient-to-br')
      expect(container).toHaveClass('from-primary-50')
      expect(container).toHaveClass('via-white')
      expect(container).toHaveClass('to-secondary-50')
    })

    it('uses full viewport height', () => {
      renderWithProviders(<AuthLayout />)
      
      const container = document.querySelector('.min-h-screen')
      expect(container).toHaveClass('min-h-screen')
    })
  })

  describe('Visual Design Elements', () => {
    it('applies correct opacity to background pattern', () => {
      renderWithProviders(<AuthLayout />)
      
      const backgroundPattern = document.querySelector('.bg-grid-pattern')
      expect(backgroundPattern).toHaveClass('opacity-5')
    })

    it('positions background pattern correctly', () => {
      renderWithProviders(<AuthLayout />)
      
      const backgroundPattern = document.querySelector('.bg-grid-pattern')
      expect(backgroundPattern).toHaveClass('absolute', 'inset-0')
    })
  })

  describe('Accessibility', () => {
    it('provides proper document structure', () => {
      renderWithProviders(<AuthLayout />)
      
      // Should have a main container
      const container = document.querySelector('.min-h-screen')
      expect(container).toBeInTheDocument()
      
      // Should have content area
      const contentArea = document.querySelector('.relative')
      expect(contentArea).toBeInTheDocument()
    })

    it('does not interfere with child component accessibility', () => {
      renderWithProviders(<AuthLayout />)
      
      // Child content should be accessible
      expect(screen.getByTestId('auth-child')).toBeInTheDocument()
    })
  })

  describe('CSS Classes Validation', () => {
    it('applies all required Tailwind classes correctly', () => {
      renderWithProviders(<AuthLayout />)
      
      const container = document.querySelector('.min-h-screen')
      const backgroundPattern = document.querySelector('.bg-grid-pattern')
      const contentWrapper = document.querySelector('.relative')
      
      // Container classes
      expect(container).toHaveClass(
        'min-h-screen',
        'bg-gradient-to-br',
        'from-primary-50',
        'via-white',
        'to-secondary-50'
      )
      
      // Background pattern classes
      expect(backgroundPattern).toHaveClass(
        'absolute',
        'inset-0',
        'bg-grid-pattern',
        'opacity-5'
      )
      
      // Content wrapper classes
      expect(contentWrapper).toHaveClass('relative')
    })
  })

  describe('Layout Behavior', () => {
    it('maintains layout with different content sizes', () => {
      const LargeContentLayout = () => (
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AuthLayout />}>
              <Route index element={
                <div data-testid="large-content" style={{ height: '2000px' }}>
                  Large Content
                </div>
              } />
            </Route>
          </Routes>
        </BrowserRouter>
      )

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: 0, gcTime: 0 },
        },
      })

      render(
        <QueryClientProvider client={queryClient}>
          <LargeContentLayout />
        </QueryClientProvider>
      )

      expect(screen.getByTestId('large-content')).toBeInTheDocument()
      expect(document.querySelector('.min-h-screen')).toBeInTheDocument()
    })

    it('handles empty content gracefully', () => {
      const EmptyContentLayout = () => (
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AuthLayout />}>
              <Route index element={<div data-testid="empty-content"></div>} />
            </Route>
          </Routes>
        </BrowserRouter>
      )

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: 0, gcTime: 0 },
        },
      })

      render(
        <QueryClientProvider client={queryClient}>
          <EmptyContentLayout />
        </QueryClientProvider>
      )

      expect(screen.getByTestId('empty-content')).toBeInTheDocument()
      expect(document.querySelector('.min-h-screen')).toBeInTheDocument()
    })
  })

  describe('Integration Tests', () => {
    it('works correctly with typical auth forms', () => {
      const AuthFormsLayout = () => (
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AuthLayout />}>
              <Route path="login" element={
                <form data-testid="login-form">
                  <input type="email" placeholder="Email" />
                  <input type="password" placeholder="Password" />
                  <button type="submit">Login</button>
                </form>
              } />
            </Route>
          </Routes>
        </BrowserRouter>
      )

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: 0, gcTime: 0 },
        },
      })

      // Navigate to login route
      window.history.pushState({}, '', '/login')

      render(
        <QueryClientProvider client={queryClient}>
          <AuthFormsLayout />
        </QueryClientProvider>
      )

      expect(screen.getByTestId('login-form')).toBeInTheDocument()
      expect(document.querySelector('.min-h-screen')).toBeInTheDocument()
    })
  })
})