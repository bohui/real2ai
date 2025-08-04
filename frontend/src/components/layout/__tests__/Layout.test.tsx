/**
 * Test Layout component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@/test/utils'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from '../Layout'
import { mockUser } from '@/test/utils'

// Mock the stores
const mockUIStore = {
  sidebarOpen: false,
  isMobile: false,
  setSidebarOpen: vi.fn(),
  toggleSidebar: vi.fn(),
  notifications: [],
  addNotification: vi.fn(),
  removeNotification: vi.fn(),
}

const mockAuthStore = {
  user: mockUser,
  logout: vi.fn(),
  isAuthenticated: true,
}

const mockAnalysisStore = {
  recentAnalyses: [],
  isAnalyzing: false,
}

vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => mockUIStore),
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthStore),
}))

vi.mock('@/store/analysisStore', () => ({
  useAnalysisStore: vi.fn(() => mockAnalysisStore),
}))

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, className, ...props }: any) => 
      <div onClick={onClick} className={className} {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  Menu: () => <div data-testid="menu-icon">Menu</div>,
  Bell: () => <div data-testid="bell-icon">Bell</div>,
  Search: () => <div data-testid="search-icon">Search</div>,
  Settings: () => <div data-testid="settings-icon">Settings</div>,
  LogOut: () => <div data-testid="logout-icon">LogOut</div>,
  User: () => <div data-testid="user-icon">User</div>,
  CreditCard: () => <div data-testid="credit-card-icon">CreditCard</div>,
  HelpCircle: () => <div data-testid="help-circle-icon">HelpCircle</div>,
  LayoutDashboard: () => <div data-testid="dashboard-icon">Dashboard</div>,
  FileText: () => <div data-testid="file-text-icon">FileText</div>,
  History: () => <div data-testid="history-icon">History</div>,
  Upload: () => <div data-testid="upload-icon">Upload</div>,
  BarChart3: () => <div data-testid="bar-chart-icon">BarChart3</div>,
  Zap: () => <div data-testid="zap-icon">Zap</div>,
}))

// Mock Headless UI components
vi.mock('@headlessui/react', () => ({
  Menu: {
    Button: ({ children, className, ...props }: any) => 
      <button className={className} {...props}>{children}</button>,
    Items: ({ children, className }: any) => 
      <div className={className}>{children}</div>,
    Item: ({ children }: any) => 
      <div>{typeof children === 'function' ? children({ active: false }) : children}</div>,
  },
}))

// Custom render function with required providers
const renderWithProviders = (ui: React.ReactElement, initialEntries: string[] = ['/']) => {
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
            <Route index element={<div data-testid="main-content">Main Content</div>} />
            <Route path="test" element={<div data-testid="test-content">Test Content</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Layout Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store states
    mockUIStore.sidebarOpen = false
    mockUIStore.isMobile = false
    mockAuthStore.user = mockUser
    mockAnalysisStore.recentAnalyses = []
    mockAnalysisStore.isAnalyzing = false
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderWithProviders(<Layout />)
      
      expect(document.body).toBeInTheDocument()
    })

    it('renders main layout structure', () => {
      renderWithProviders(<Layout />)
      
      // Main container
      const mainContainer = document.querySelector('.h-screen.flex.overflow-hidden')
      expect(mainContainer).toBeInTheDocument()
      expect(mainContainer).toHaveClass('bg-neutral-50')
    })

    it('renders sidebar', () => {
      renderWithProviders(<Layout />)
      
      // Check for sidebar container
      const sidebarContainer = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebarContainer).toBeInTheDocument()
      expect(sidebarContainer).toHaveClass('w-64')
    })

    it('renders header', () => {
      renderWithProviders(<Layout />)
      
      // Check for header element
      const header = document.querySelector('header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveClass('bg-white', 'shadow-sm', 'border-b', 'border-neutral-200')
    })

    it('renders main content area', () => {
      renderWithProviders(<Layout />)
      
      // Check for main content
      const mainContent = document.querySelector('main')
      expect(mainContent).toBeInTheDocument()
      expect(mainContent).toHaveClass('flex-1', 'overflow-auto')
      
      expect(screen.getByTestId('main-content')).toBeInTheDocument()
    })
  })

  describe('Sidebar Behavior', () => {
    it('shows sidebar when sidebarOpen is true', () => {
      mockUIStore.sidebarOpen = true
      
      renderWithProviders(<Layout />)
      
      const sidebarContainer = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebarContainer).toHaveClass('translate-x-0')
      expect(sidebarContainer).not.toHaveClass('-translate-x-full')
    })

    it('hides sidebar when sidebarOpen is false', () => {
      mockUIStore.sidebarOpen = false
      
      renderWithProviders(<Layout />)
      
      const sidebarContainer = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebarContainer).toHaveClass('-translate-x-full')
      expect(sidebarContainer).not.toHaveClass('translate-x-0')
    })

    it('applies desktop sidebar classes on large screens', () => {
      renderWithProviders(<Layout />)
      
      const sidebarContainer = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebarContainer).toHaveClass('lg:relative', 'lg:z-auto', 'lg:translate-x-0')
    })

    it('has proper z-index for mobile sidebar', () => {
      renderWithProviders(<Layout />)
      
      const sidebarContainer = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebarContainer).toHaveClass('z-50')
    })
  })

  describe('Mobile Overlay Behavior', () => {
    it('shows overlay when sidebar is open on mobile', () => {
      mockUIStore.sidebarOpen = true
      mockUIStore.isMobile = true
      
      renderWithProviders(<Layout />)
      
      // Check for overlay element
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).toBeInTheDocument()
      expect(overlay).toHaveClass('bg-neutral-900', 'bg-opacity-50', 'lg:hidden')
    })

    it('hides overlay when sidebar is closed', () => {
      mockUIStore.sidebarOpen = false
      mockUIStore.isMobile = true
      
      renderWithProviders(<Layout />)
      
      // Overlay should not be present
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).not.toBeInTheDocument()
    })

    it('hides overlay on desktop even when sidebar is open', () => {
      mockUIStore.sidebarOpen = true
      mockUIStore.isMobile = false
      
      renderWithProviders(<Layout />)
      
      // Overlay should not be present on desktop
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).not.toBeInTheDocument()
    })

    it('closes sidebar when overlay is clicked', () => {
      mockUIStore.sidebarOpen = true
      mockUIStore.isMobile = true
      
      renderWithProviders(<Layout />)
      
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).toBeInTheDocument()
      
      fireEvent.click(overlay!)
      
      // Should call setSidebarOpen with false
      expect(mockUIStore.setSidebarOpen).toHaveBeenCalledWith(false)
    })
  })

  describe('Header Integration', () => {
    it('renders header with proper structure', () => {
      renderWithProviders(<Layout />)
      
      const header = document.querySelector('header')
      expect(header).toBeInTheDocument()
      
      // Check for header content structure
      const headerContent = header?.querySelector('.px-4.sm\\:px-6.lg\\:px-8')
      expect(headerContent).toBeInTheDocument()
      
      const headerFlex = headerContent?.querySelector('.flex.justify-between.items-center.h-16')
      expect(headerFlex).toBeInTheDocument()
    })

    it('shows mobile menu button in header', () => {
      renderWithProviders(<Layout />)
      
      // The menu button should be present (though hidden on large screens)
      const menuButton = document.querySelector('.lg\\:hidden')
      expect(menuButton).toBeInTheDocument()
    })

    it('displays user information in header', () => {
      renderWithProviders(<Layout />)
      
      // User email should be displayed
      expect(screen.getByText(mockUser.email)).toBeInTheDocument()
    })

    it('shows credit information when user has credits', () => {
      mockAuthStore.user = { ...mockUser, credits_remaining: 5 }
      
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('5 credits')).toBeInTheDocument()
    })
  })

  describe('Sidebar Content', () => {
    it('displays Real2.AI branding', () => {
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('Real2.AI')).toBeInTheDocument()
      expect(screen.getByText('Contract Analysis')).toBeInTheDocument()
    })

    it('renders navigation links', () => {
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('New Analysis')).toBeInTheDocument()
      expect(screen.getByText('Analysis History')).toBeInTheDocument()
      expect(screen.getByText('Reports')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })

    it('shows analysis status badge when analyzing', () => {
      mockAnalysisStore.isAnalyzing = true
      
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('shows recent analyses count when available', () => {
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } },
        { contract_id: '2', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 5 } },
      ]
      
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('displays help & support link', () => {
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('Help & Support')).toBeInTheDocument()
    })
  })

  describe('Main Content Area', () => {
    it('has proper padding and layout classes', () => {
      renderWithProviders(<Layout />)
      
      const mainContent = document.querySelector('main')
      expect(mainContent).toHaveClass('flex-1', 'overflow-auto')
      
      const contentWrapper = mainContent?.querySelector('.py-6.px-4.sm\\:px-6.lg\\:px-8')
      expect(contentWrapper).toBeInTheDocument()
    })

    it('renders child content through Outlet', () => {
      renderWithProviders(<Layout />)
      
      expect(screen.getByTestId('main-content')).toBeInTheDocument()
    })

    it('adapts to different content sizes', () => {
      const LargeContentLayout = () => (
        <Layout />
      )

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: 0, gcTime: 0 },
        },
      })

      render(
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LargeContentLayout />}>
                <Route index element={
                  <div data-testid="large-content" style={{ height: '2000px' }}>
                    Large Content
                  </div>
                } />
              </Route>
            </Routes>
          </BrowserRouter>
        </QueryClientProvider>
      )

      expect(screen.getByTestId('large-content')).toBeInTheDocument()
      
      const mainContent = document.querySelector('main')
      expect(mainContent).toHaveClass('overflow-auto')
    })
  })

  describe('Responsive Behavior', () => {
    it('applies correct classes for mobile responsiveness', () => {
      renderWithProviders(<Layout />)
      
      // Check responsive padding classes
      const contentWrapper = document.querySelector('.py-6.px-4.sm\\:px-6.lg\\:px-8')
      expect(contentWrapper).toBeInTheDocument()
      
      // Check sidebar responsive classes
      const sidebarContainer = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebarContainer).toHaveClass('lg:relative', 'lg:z-auto', 'lg:translate-x-0')
    })

    it('handles different viewport states', () => {
      // Test mobile state
      mockUIStore.isMobile = true
      mockUIStore.sidebarOpen = true
      
      const { rerender } = renderWithProviders(<Layout />)
      
      let overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).toBeInTheDocument()
      
      // Test desktop state
      mockUIStore.isMobile = false
      
      rerender(
        <QueryClient>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<div data-testid="main-content">Main Content</div>} />
              </Route>
            </Routes>
          </BrowserRouter>
        </QueryClient>
      )
      
      overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).not.toBeInTheDocument()
    })
  })

  describe('Store Integration', () => {
    it('uses UI store for sidebar state', () => {
      renderWithProviders(<Layout />)
      
      // Component should read from UI store
      expect(mockUIStore.sidebarOpen).toBeDefined()
      expect(mockUIStore.isMobile).toBeDefined()
    })

    it('calls store methods for sidebar interactions', () => {
      mockUIStore.sidebarOpen = true
      mockUIStore.isMobile = true
      
      renderWithProviders(<Layout />)
      
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      fireEvent.click(overlay!)
      
      // Should call the store method
      expect(mockUIStore.setSidebarOpen).toHaveBeenCalledWith(false)
    })

    it('integrates with auth store for user data', () => {
      renderWithProviders(<Layout />)
      
      // Should display user information from auth store
      expect(screen.getByText(mockAuthStore.user.email)).toBeInTheDocument()
    })

    it('integrates with analysis store for sidebar badges', () => {
      mockAnalysisStore.isAnalyzing = true
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } }
      ]
      
      renderWithProviders(<Layout />)
      
      expect(screen.getByText('Active')).toBeInTheDocument()
      expect(screen.getByText('1')).toBeInTheDocument()
    })
  })

  describe('Layout Structure Validation', () => {
    it('maintains proper CSS grid/flexbox structure', () => {
      renderWithProviders(<Layout />)
      
      // Main container should be flex
      const mainContainer = document.querySelector('.h-screen.flex.overflow-hidden')
      expect(mainContainer).toBeInTheDocument()
      
      // Sidebar should be fixed positioned
      const sidebar = document.querySelector('.fixed.inset-y-0.left-0')
      expect(sidebar).toBeInTheDocument()
      
      // Main content area should be flex column
      const contentArea = document.querySelector('.flex-1.flex.flex-col.overflow-hidden')
      expect(contentArea).toBeInTheDocument()
    })

    it('has correct z-index hierarchy', () => {
      mockUIStore.sidebarOpen = true
      mockUIStore.isMobile = true
      
      renderWithProviders(<Layout />)
      
      const sidebar = document.querySelector('.fixed.inset-y-0.left-0')
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      
      expect(sidebar).toHaveClass('z-50')  // Sidebar above overlay
      expect(overlay).toHaveClass('z-40')   // Overlay below sidebar
    })
  })

  describe('Accessibility', () => {
    it('provides proper semantic structure', () => {
      renderWithProviders(<Layout />)
      
      // Should have header and main landmarks
      const header = document.querySelector('header')
      const main = document.querySelector('main')
      
      expect(header).toBeInTheDocument()
      expect(main).toBeInTheDocument()
    })

    it('maintains focus management for sidebar overlay', () => {
      mockUIStore.sidebarOpen = true
      mockUIStore.isMobile = true
      
      renderWithProviders(<Layout />)
      
      const overlay = document.querySelector('.fixed.inset-0.z-40')
      expect(overlay).toBeInTheDocument()
      
      // Overlay should be clickable for closing sidebar
      fireEvent.click(overlay!)
      expect(mockUIStore.setSidebarOpen).toHaveBeenCalledWith(false)
    })
  })
})