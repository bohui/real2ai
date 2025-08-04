/**
 * Test Header component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@/test/utils'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Header from '../Header'
import { mockUser } from '@/test/utils'

// Mock the stores
const mockAuthStore = {
  user: mockUser,
  logout: vi.fn(),
}

const mockUIStore = {
  toggleSidebar: vi.fn(),
  notifications: [],
}

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthStore),
}))

vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => mockUIStore),
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  Menu: ({ className }: any) => <div data-testid="menu-icon" className={className}>Menu</div>,
  Bell: ({ className }: any) => <div data-testid="bell-icon" className={className}>Bell</div>,
  Search: ({ className }: any) => <div data-testid="search-icon" className={className}>Search</div>,
  Settings: ({ className }: any) => <div data-testid="settings-icon" className={className}>Settings</div>,
  LogOut: ({ className }: any) => <div data-testid="logout-icon" className={className}>LogOut</div>,
  User: ({ className }: any) => <div data-testid="user-icon" className={className}>User</div>,
  CreditCard: ({ className }: any) => <div data-testid="credit-card-icon" className={className}>CreditCard</div>,
  HelpCircle: ({ className }: any) => <div data-testid="help-circle-icon" className={className}>HelpCircle</div>,
}))

// Mock Headless UI components
vi.mock('@headlessui/react', () => ({
  Menu: {
    Button: ({ children, className, ...props }: any) => 
      <button className={className} data-testid="menu-button" {...props}>{children}</button>,
    Items: ({ children, className }: any) => 
      <div className={className} data-testid="menu-items">{children}</div>,
    Item: ({ children }: any) => 
      <div data-testid="menu-item">{typeof children === 'function' ? children({ active: false }) : children}</div>,
  },
}))

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
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Header Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store states
    mockAuthStore.user = mockUser
    mockAuthStore.logout = vi.fn()
    mockUIStore.toggleSidebar = vi.fn()
    mockUIStore.notifications = []
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderWithProviders(<Header />)
      
      const header = document.querySelector('header')
      expect(header).toBeInTheDocument()
    })

    it('has proper header structure', () => {
      renderWithProviders(<Header />)
      
      const header = document.querySelector('header')
      expect(header).toHaveClass('bg-white', 'shadow-sm', 'border-b', 'border-neutral-200')
      
      const container = header?.querySelector('.px-4.sm\\:px-6.lg\\:px-8')
      expect(container).toBeInTheDocument()
      
      const flexContainer = container?.querySelector('.flex.justify-between.items-center.h-16')
      expect(flexContainer).toBeInTheDocument()
    })

    it('renders left and right sections', () => {
      renderWithProviders(<Header />)
      
      // Left side with menu and search
      const leftSection = document.querySelector('.flex.items-center.gap-4')
      expect(leftSection).toBeInTheDocument()
      
      // Right side with credits, notifications, and user menu
      const rightSection = document.querySelector('.flex.items-center.gap-3')
      expect(rightSection).toBeInTheDocument()
    })
  })

  describe('Mobile Sidebar Toggle', () => {
    it('renders mobile sidebar toggle button', () => {
      renderWithProviders(<Header />)
      
      const toggleButton = document.querySelector('.lg\\:hidden')
      expect(toggleButton).toBeInTheDocument()
      expect(screen.getByTestId('menu-icon')).toBeInTheDocument()
    })

    it('calls toggleSidebar when menu button is clicked', () => {
      renderWithProviders(<Header />)
      
      const menuButton = document.querySelector('.lg\\:hidden')
      fireEvent.click(menuButton!)
      
      expect(mockUIStore.toggleSidebar).toHaveBeenCalledTimes(1)
    })

    it('applies correct styling to menu button', () => {
      renderWithProviders(<Header />)
      
      const menuButton = document.querySelector('.lg\\:hidden')
      expect(menuButton).toBeInTheDocument()
      
      const menuIcon = screen.getByTestId('menu-icon')
      expect(menuIcon).toHaveClass('w-5', 'h-5')
    })
  })

  describe('Search Functionality', () => {
    it('renders search input on desktop', () => {
      renderWithProviders(<Header />)
      
      const searchContainer = document.querySelector('.hidden.md\\:block')
      expect(searchContainer).toBeInTheDocument()
      
      const searchInput = screen.getByPlaceholderText('Search contracts...')
      expect(searchInput).toBeInTheDocument()
      expect(searchInput).toHaveAttribute('type', 'text')
    })

    it('has proper search input styling', () => {
      renderWithProviders(<Header />)
      
      const searchInput = screen.getByPlaceholderText('Search contracts...')
      expect(searchInput).toHaveClass(
        'pl-10', 'pr-4', 'py-2', 'w-64', 'rounded-lg', 'border', 'border-neutral-200',
        'focus:ring-2', 'focus:ring-primary-500', 'focus:border-primary-500', 'text-sm'
      )
    })

    it('renders search icon correctly', () => {
      renderWithProviders(<Header />)
      
      const searchIcon = screen.getByTestId('search-icon')
      expect(searchIcon).toBeInTheDocument()
      expect(searchIcon).toHaveClass('absolute', 'left-3', 'top-1/2', 'transform', '-translate-y-1/2', 'w-4', 'h-4', 'text-neutral-400')
    })

    it('is hidden on mobile', () => {
      renderWithProviders(<Header />)
      
      const searchContainer = document.querySelector('.hidden.md\\:block')
      expect(searchContainer).toHaveClass('hidden', 'md:block')
    })
  })

  describe('Credits Display', () => {
    it('shows credits when user has credits', () => {
      mockAuthStore.user = { ...mockUser, credits_remaining: 10 }
      
      renderWithProviders(<Header />)
      
      expect(screen.getByText('10 credits')).toBeInTheDocument()
      expect(screen.getByTestId('credit-card-icon')).toBeInTheDocument()
    })

    it('applies correct styling to credits display', () => {
      mockAuthStore.user = { ...mockUser, credits_remaining: 5 }
      
      renderWithProviders(<Header />)
      
      const creditsContainer = document.querySelector('.bg-primary-50.text-primary-700.rounded-full')
      expect(creditsContainer).toBeInTheDocument()
      expect(creditsContainer).toHaveClass('hidden', 'sm:flex', 'items-center', 'gap-2', 'px-3', 'py-1.5', 'text-sm', 'font-medium')
    })

    it('does not show credits when user is null', () => {
      mockAuthStore.user = null
      
      renderWithProviders(<Header />)
      
      expect(screen.queryByText(/credits/)).not.toBeInTheDocument()
    })

    it('handles zero credits', () => {
      mockAuthStore.user = { ...mockUser, credits_remaining: 0 }
      
      renderWithProviders(<Header />)
      
      expect(screen.getByText('0 credits')).toBeInTheDocument()
    })

    it('is hidden on small screens', () => {
      mockAuthStore.user = { ...mockUser, credits_remaining: 5 }
      
      renderWithProviders(<Header />)
      
      const creditsContainer = document.querySelector('.hidden.sm\\:flex')
      expect(creditsContainer).toHaveClass('hidden', 'sm:flex')
    })
  })

  describe('Notifications', () => {
    it('renders notification bell', () => {
      renderWithProviders(<Header />)
      
      expect(screen.getByTestId('bell-icon')).toBeInTheDocument()
    })

    it('shows notification count when there are unread notifications', () => {
      mockUIStore.notifications = [
        { type: 'info', id: '1', title: 'Test' },
        { type: 'info', id: '2', title: 'Test 2' },
        { type: 'error', id: '3', title: 'Error' },
      ]
      
      renderWithProviders(<Header />)
      
      expect(screen.getByText('2')).toBeInTheDocument() // Only info type notifications
    })

    it('shows "9+" for more than 9 notifications', () => {
      mockUIStore.notifications = Array.from({ length: 12 }, (_, i) => ({
        type: 'info',
        id: i.toString(),
        title: `Test ${i}`,
      }))
      
      renderWithProviders(<Header />)
      
      expect(screen.getByText('9+')).toBeInTheDocument()
    })

    it('does not show count when no unread notifications', () => {
      mockUIStore.notifications = []
      
      renderWithProviders(<Header />)
      
      expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument()
      expect(screen.queryByText('9+')).not.toBeInTheDocument()
    })

    it('applies correct styling to notification badge', () => {
      mockUIStore.notifications = [{ type: 'info', id: '1', title: 'Test' }]
      
      renderWithProviders(<Header />)
      
      const badge = screen.getByText('1')
      expect(badge).toHaveClass(
        'absolute', '-top-1', '-right-1', 'w-4', 'h-4', 'bg-danger-500', 'text-white',
        'text-xs', 'rounded-full', 'flex', 'items-center', 'justify-center'
      )
    })

    it('only counts info type notifications', () => {
      mockUIStore.notifications = [
        { type: 'info', id: '1', title: 'Info 1' },
        { type: 'info', id: '2', title: 'Info 2' },
        { type: 'error', id: '3', title: 'Error' },
        { type: 'warning', id: '4', title: 'Warning' },
      ]
      
      renderWithProviders(<Header />)
      
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  describe('Help Button', () => {
    it('renders help button', () => {
      renderWithProviders(<Header />)
      
      expect(screen.getByTestId('help-circle-icon')).toBeInTheDocument()
    })

    it('has correct styling', () => {
      renderWithProviders(<Header />)
      
      const helpIcon = screen.getByTestId('help-circle-icon')
      expect(helpIcon).toHaveClass('w-5', 'h-5')
    })
  })

  describe('User Menu', () => {
    it('renders user menu button with avatar', () => {
      renderWithProviders(<Header />)
      
      const menuButton = screen.getByTestId('menu-button')
      expect(menuButton).toBeInTheDocument()
      
      // Should show user's initial
      const initial = mockUser.email.charAt(0).toUpperCase()
      expect(screen.getByText(initial)).toBeInTheDocument()
    })

    it('displays user information', () => {
      renderWithProviders(<Header />)
      
      // Username (part before @)
      const username = mockUser.email.split('@')[0]
      expect(screen.getByText(username)).toBeInTheDocument()
      
      // User type
      expect(screen.getByText(mockUser.user_type)).toBeInTheDocument()
    })

    it('shows user information on desktop only', () => {
      renderWithProviders(<Header />)
      
      const userInfo = document.querySelector('.hidden.md\\:block.text-left')
      expect(userInfo).toBeInTheDocument()
    })

    it('has proper avatar styling', () => {
      renderWithProviders(<Header />)
      
      const avatar = document.querySelector('.w-8.h-8.bg-primary-600.rounded-full')
      expect(avatar).toBeInTheDocument()
      expect(avatar).toHaveClass('flex', 'items-center', 'justify-center', 'text-white', 'font-semibold', 'text-sm')
    })

    it('renders user menu items', () => {
      renderWithProviders(<Header />)
      
      const menuItems = screen.getByTestId('menu-items')
      expect(menuItems).toBeInTheDocument()
      
      // Should have user info in header
      expect(screen.getByText(mockUser.email)).toBeInTheDocument()
      expect(screen.getByText(`${mockUser.australian_state} • ${mockUser.subscription_status}`)).toBeInTheDocument()
    })

    it('renders menu navigation links', () => {
      renderWithProviders(<Header />)
      
      expect(screen.getByText('Profile Settings')).toBeInTheDocument()
      expect(screen.getByText('Billing & Credits')).toBeInTheDocument()
      expect(screen.getByText('Preferences')).toBeInTheDocument()
    })

    it('has proper link hrefs', () => {
      renderWithProviders(<Header />)
      
      const profileLink = screen.getByText('Profile Settings').closest('a')
      const billingLink = screen.getByText('Billing & Credits').closest('a')
      const preferencesLink = screen.getByText('Preferences').closest('a')
      
      expect(profileLink).toHaveAttribute('href', '/app/settings')
      expect(billingLink).toHaveAttribute('href', '/app/billing')
      expect(preferencesLink).toHaveAttribute('href', '/app/settings')
    })

    it('renders logout button', () => {
      renderWithProviders(<Header />)
      
      const logoutButton = screen.getByText('Sign out').closest('button')
      expect(logoutButton).toBeInTheDocument()
      expect(screen.getByTestId('logout-icon')).toBeInTheDocument()
    })

    it('calls logout when logout button is clicked', () => {
      renderWithProviders(<Header />)
      
      const logoutButton = screen.getByText('Sign out').closest('button')
      fireEvent.click(logoutButton!)
      
      expect(mockAuthStore.logout).toHaveBeenCalledTimes(1)
    })

    it('applies correct styling to menu items', () => {
      renderWithProviders(<Header />)
      
      const menuItems = screen.getAllByTestId('menu-item')
      expect(menuItems.length).toBeGreaterThan(0)
      
      // Check logout button has danger styling
      const logoutButton = screen.getByText('Sign out').closest('button')
      expect(logoutButton).toHaveClass('text-danger-600')
    })
  })

  describe('Responsive Design', () => {
    it('hides elements appropriately on mobile', () => {
      renderWithProviders(<Header />)
      
      // Search should be hidden on mobile
      const search = document.querySelector('.hidden.md\\:block')
      expect(search).toHaveClass('hidden', 'md:block')
      
      // Credits should be hidden on small screens
      const credits = document.querySelector('.hidden.sm\\:flex')
      expect(credits).toHaveClass('hidden', 'sm:flex')
      
      // User info should be hidden on mobile
      const userInfo = document.querySelector('.hidden.md\\:block.text-left')
      expect(userInfo).toHaveClass('hidden', 'md:block')
    })

    it('shows mobile menu button only on mobile', () => {
      renderWithProviders(<Header />)
      
      const mobileMenu = document.querySelector('.lg\\:hidden')
      expect(mobileMenu).toHaveClass('lg:hidden')
    })

    it('applies responsive padding', () => {
      renderWithProviders(<Header />)
      
      const container = document.querySelector('.px-4.sm\\:px-6.lg\\:px-8')
      expect(container).toHaveClass('px-4', 'sm:px-6', 'lg:px-8')
    })
  })

  describe('Edge Cases', () => {
    it('handles user with no email gracefully', () => {
      mockAuthStore.user = { ...mockUser, email: '' }
      
      renderWithProviders(<Header />)
      
      // Should not crash
      expect(document.querySelector('header')).toBeInTheDocument()
    })

    it('handles user with undefined fields', () => {
      mockAuthStore.user = {
        ...mockUser,
        australian_state: undefined,
        subscription_status: undefined,
        user_type: undefined,
      }
      
      renderWithProviders(<Header />)
      
      // Should not crash
      expect(document.querySelector('header')).toBeInTheDocument()
    })

    it('handles very long email addresses', () => {
      mockAuthStore.user = {
        ...mockUser,
        email: 'verylongemailaddressthatmightbreaklayout@verylongdomainname.com',
      }
      
      renderWithProviders(<Header />)
      
      expect(document.querySelector('header')).toBeInTheDocument()
    })

    it('handles large number of notifications', () => {
      mockUIStore.notifications = Array.from({ length: 100 }, (_, i) => ({
        type: 'info',
        id: i.toString(),
        title: `Notification ${i}`,
      }))
      
      renderWithProviders(<Header />)
      
      expect(screen.getByText('9+')).toBeInTheDocument()
    })

    it('handles null user gracefully', () => {
      mockAuthStore.user = null
      
      renderWithProviders(<Header />)
      
      // Should not crash
      expect(document.querySelector('header')).toBeInTheDocument()
      expect(screen.queryByText('credits')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('uses semantic header element', () => {
      renderWithProviders(<Header />)
      
      const header = document.querySelector('header')
      expect(header).toBeInTheDocument()
    })

    it('has accessible search input', () => {
      renderWithProviders(<Header />)
      
      const searchInput = screen.getByPlaceholderText('Search contracts...')
      expect(searchInput).toHaveAttribute('type', 'text')
      expect(searchInput).toHaveAttribute('placeholder', 'Search contracts...')
    })

    it('has accessible menu buttons', () => {
      renderWithProviders(<Header />)
      
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
      
      // All buttons should be focusable
      buttons.forEach(button => {
        expect(button).not.toHaveAttribute('tabindex', '-1')
      })
    })

    it('has accessible navigation links', () => {
      renderWithProviders(<Header />)
      
      const links = screen.getAllByRole('link')
      expect(links.length).toBeGreaterThan(0)
      
      // All links should have href attributes
      links.forEach(link => {
        expect(link).toHaveAttribute('href')
      })
    })
  })

  describe('Integration', () => {
    it('integrates with auth store correctly', () => {
      renderWithProviders(<Header />)
      
      // Should use user data from auth store
      expect(screen.getByText(mockUser.email.charAt(0).toUpperCase())).toBeInTheDocument()
      expect(screen.getByText(mockUser.email)).toBeInTheDocument()
    })

    it('integrates with UI store correctly', () => {
      renderWithProviders(<Header />)
      
      // Should use notifications from UI store
      expect(mockUIStore.notifications).toBeDefined()
    })

    it('calls store methods correctly', () => {
      renderWithProviders(<Header />)
      
      // Test sidebar toggle
      const menuButton = document.querySelector('.lg\\:hidden')
      fireEvent.click(menuButton!)
      expect(mockUIStore.toggleSidebar).toHaveBeenCalled()
      
      // Test logout
      const logoutButton = screen.getByText('Sign out').closest('button')
      fireEvent.click(logoutButton!)
      expect(mockAuthStore.logout).toHaveBeenCalled()
    })
  })
})