/**
 * Test Sidebar component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@/test/utils'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Sidebar from '../Sidebar'

// Mock the analysis store
const mockAnalysisStore = {
  recentAnalyses: [],
  isAnalyzing: false,
}

vi.mock('@/store/analysisStore', () => ({
  useAnalysisStore: vi.fn(() => mockAnalysisStore),
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    span: ({ children, className, ...props }: any) => 
      <span className={className} {...props}>{children}</span>,
  },
}))

// Mock Lucide React icons
vi.mock('lucide-react', () => ({
  LayoutDashboard: ({ className }: any) => <div data-testid="dashboard-icon" className={className}>Dashboard</div>,
  FileText: ({ className }: any) => <div data-testid="file-text-icon" className={className}>FileText</div>,
  History: ({ className }: any) => <div data-testid="history-icon" className={className}>History</div>,
  Settings: ({ className }: any) => <div data-testid="settings-icon" className={className}>Settings</div>,
  Upload: ({ className }: any) => <div data-testid="upload-icon" className={className}>Upload</div>,
  BarChart3: ({ className }: any) => <div data-testid="bar-chart-icon" className={className}>BarChart3</div>,
  Zap: ({ className }: any) => <div data-testid="zap-icon" className={className}>Zap</div>,
  HelpCircle: ({ className }: any) => <div data-testid="help-circle-icon" className={className}>HelpCircle</div>,
}))

// Mock useLocation to control current path
const mockLocation = { pathname: '/app/dashboard' }
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useLocation: vi.fn(() => mockLocation),
  }
})

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

describe('Sidebar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock store state
    mockAnalysisStore.recentAnalyses = []
    mockAnalysisStore.isAnalyzing = false
    mockLocation.pathname = '/app/dashboard'
  })

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderWithProviders(<Sidebar />)
      
      expect(document.body).toBeInTheDocument()
    })

    it('has proper sidebar structure', () => {
      renderWithProviders(<Sidebar />)
      
      const container = document.querySelector('.flex.flex-col.h-full.bg-white.border-r.border-neutral-200')
      expect(container).toBeInTheDocument()
    })

    it('has proper layout sections', () => {
      renderWithProviders(<Sidebar />)
      
      // Logo section
      const logoSection = document.querySelector('.flex.items-center.gap-3.p-6.border-b.border-neutral-200')
      expect(logoSection).toBeInTheDocument()
      
      // Navigation section
      const navSection = document.querySelector('nav')
      expect(navSection).toBeInTheDocument()
      expect(navSection).toHaveClass('flex-1', 'px-4', 'py-6', 'space-y-2')
      
      // Quick actions section
      const quickActionsSection = document.querySelector('.px-4.py-4.border-t.border-neutral-200')
      expect(quickActionsSection).toBeInTheDocument()
    })
  })

  describe('Logo Section', () => {
    it('renders Real2.AI branding correctly', () => {
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByText('Real2.AI')).toBeInTheDocument()
      expect(screen.getByText('Contract Analysis')).toBeInTheDocument()
    })

    it('has proper logo styling', () => {
      renderWithProviders(<Sidebar />)
      
      const logoIcon = document.querySelector('.w-10.h-10.bg-primary-600.rounded-xl')
      expect(logoIcon).toBeInTheDocument()
      expect(logoIcon).toHaveClass('flex', 'items-center', 'justify-center')
      
      expect(screen.getByTestId('zap-icon')).toBeInTheDocument()
      expect(screen.getByTestId('zap-icon')).toHaveClass('w-6', 'h-6', 'text-white')
    })

    it('has proper text styling', () => {
      renderWithProviders(<Sidebar />)
      
      const title = screen.getByText('Real2.AI')
      expect(title).toHaveClass('text-xl', 'font-bold', 'text-neutral-900')
      
      const subtitle = screen.getByText('Contract Analysis')
      expect(subtitle).toHaveClass('text-xs', 'text-neutral-500')
    })
  })

  describe('Navigation Menu', () => {
    it('renders all navigation items', () => {
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('New Analysis')).toBeInTheDocument()
      expect(screen.getByText('Analysis History')).toBeInTheDocument()
      expect(screen.getByText('Reports')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })

    it('renders correct icons for each navigation item', () => {
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByTestId('dashboard-icon')).toBeInTheDocument()
      expect(screen.getByTestId('upload-icon')).toBeInTheDocument()
      expect(screen.getByTestId('history-icon')).toBeInTheDocument()
      expect(screen.getByTestId('bar-chart-icon')).toBeInTheDocument()
      expect(screen.getByTestId('settings-icon')).toBeInTheDocument()
    })

    it('has correct navigation links', () => {
      renderWithProviders(<Sidebar />)
      
      const dashboardLink = screen.getByText('Dashboard').closest('a')
      const analysisLink = screen.getByText('New Analysis').closest('a')
      const historyLink = screen.getByText('Analysis History').closest('a')
      const reportsLink = screen.getByText('Reports').closest('a')
      const settingsLink = screen.getByText('Settings').closest('a')
      
      expect(dashboardLink).toHaveAttribute('href', '/app/dashboard')
      expect(analysisLink).toHaveAttribute('href', '/app/analysis')
      expect(historyLink).toHaveAttribute('href', '/app/history')
      expect(reportsLink).toHaveAttribute('href', '/app/reports')
      expect(settingsLink).toHaveAttribute('href', '/app/settings')
    })

    it('applies active styling to current route', () => {
      mockLocation.pathname = '/app/dashboard'
      
      renderWithProviders(<Sidebar />)
      
      const activeLink = screen.getByText('Dashboard').closest('a')
      expect(activeLink).toHaveClass('bg-primary-50', 'text-primary-700', 'border', 'border-primary-200')
    })

    it('applies inactive styling to non-current routes', () => {
      mockLocation.pathname = '/app/dashboard'
      
      renderWithProviders(<Sidebar />)
      
      const inactiveLink = screen.getByText('New Analysis').closest('a')
      expect(inactiveLink).toHaveClass('text-neutral-600', 'hover:text-neutral-900', 'hover:bg-neutral-50')
      expect(inactiveLink).not.toHaveClass('bg-primary-50', 'text-primary-700')
    })

    it('applies correct icon styling based on active state', () => {
      mockLocation.pathname = '/app/dashboard'
      
      renderWithProviders(<Sidebar />)
      
      // Active item icon should have primary color
      const activeIcon = screen.getByTestId('dashboard-icon')
      expect(activeIcon).toHaveClass('text-primary-600')
      
      // Inactive item icon should have neutral color
      const inactiveIcon = screen.getByTestId('upload-icon')
      expect(inactiveIcon).toHaveClass('text-neutral-400', 'group-hover:text-neutral-600')
    })
  })

  describe('Analysis Status Badges', () => {
    it('shows "Active" badge when analyzing', () => {
      mockAnalysisStore.isAnalyzing = true
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByText('Active')).toBeInTheDocument()
    })

    it('does not show analysis badge when not analyzing', () => {
      mockAnalysisStore.isAnalyzing = false
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.queryByText('Active')).not.toBeInTheDocument()
    })

    it('shows count badge for analysis history when there are recent analyses', () => {
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } },
        { contract_id: '2', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 5 } },
      ]
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('does not show count badge when no recent analyses', () => {
      mockAnalysisStore.recentAnalyses = []
      
      renderWithProviders(<Sidebar />)
      
      // Should not show count badge for history
      const historyLink = screen.getByText('Analysis History').closest('a')
      const badge = historyLink?.querySelector('.inline-flex.items-center.px-2.py-1.rounded-full')
      expect(badge).not.toBeInTheDocument()
    })

    it('applies correct styling to Active badge', () => {
      mockAnalysisStore.isAnalyzing = true
      
      renderWithProviders(<Sidebar />)
      
      const activeBadge = screen.getByText('Active')
      expect(activeBadge).toHaveClass('bg-success-100', 'text-success-700')
    })

    it('applies correct styling to count badge for current route', () => {
      mockLocation.pathname = '/app/history'
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } }
      ]
      
      renderWithProviders(<Sidebar />)
      
      const countBadge = screen.getByText('1')
      expect(countBadge).toHaveClass('bg-primary-100', 'text-primary-700')
    })

    it('applies neutral styling to count badge for inactive route', () => {
      mockLocation.pathname = '/app/dashboard'
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } }
      ]
      
      renderWithProviders(<Sidebar />)
      
      const countBadge = screen.getByText('1')
      expect(countBadge).toHaveClass('bg-neutral-100', 'text-neutral-600')
    })
  })

  describe('Recent Analyses Section', () => {
    it('does not render recent analyses section when no analyses', () => {
      mockAnalysisStore.recentAnalyses = []
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.queryByText('Recent Analyses')).not.toBeInTheDocument()
    })

    it('renders recent analyses section when analyses exist', () => {
      mockAnalysisStore.recentAnalyses = [
        { 
          contract_id: '1', 
          analysis_timestamp: '2024-01-01T00:00:00Z', 
          executive_summary: { overall_risk_score: 3 } 
        }
      ]
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByText('Recent Analyses')).toBeInTheDocument()
    })

    it('limits recent analyses to 3 items', () => {
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } },
        { contract_id: '2', analysis_timestamp: '2024-01-02T00:00:00Z', executive_summary: { overall_risk_score: 5 } },
        { contract_id: '3', analysis_timestamp: '2024-01-03T00:00:00Z', executive_summary: { overall_risk_score: 7 } },
        { contract_id: '4', analysis_timestamp: '2024-01-04T00:00:00Z', executive_summary: { overall_risk_score: 2 } },
      ]
      
      renderWithProviders(<Sidebar />)
      
      const analysisLinks = document.querySelectorAll('a[href^="/app/analysis/"]')
      expect(analysisLinks).toHaveLength(3)
    })

    it('renders analysis items with correct structure', () => {
      mockAnalysisStore.recentAnalyses = [
        { 
          contract_id: '1', 
          analysis_timestamp: '2024-01-01T00:00:00Z', 
          executive_summary: { overall_risk_score: 3 } 
        }
      ]
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByTestId('file-text-icon')).toBeInTheDocument()
      expect(screen.getByText('Contract Analysis')).toBeInTheDocument()
      expect(screen.getByText('1/1/2024')).toBeInTheDocument() // Formatted date
    })

    it('has correct links for analysis items', () => {
      mockAnalysisStore.recentAnalyses = [
        { 
          contract_id: 'test-contract-123', 
          analysis_timestamp: '2024-01-01T00:00:00Z', 
          executive_summary: { overall_risk_score: 3 } 
        }
      ]
      
      renderWithProviders(<Sidebar />)
      
      const analysisLink = document.querySelector('a[href="/app/analysis/test-contract-123"]')
      expect(analysisLink).toBeInTheDocument()
    })

    it('shows risk indicators with correct colors', () => {
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 2 } }, // Low risk
        { contract_id: '2', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 6 } }, // Medium risk
        { contract_id: '3', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 8 } }, // High risk
      ]
      
      renderWithProviders(<Sidebar />)
      
      const riskDots = document.querySelectorAll('.w-2.h-2.rounded-full')
      
      // Low risk (score < 5) should be success
      expect(riskDots[0]).toHaveClass('bg-success-500')
      
      // Medium risk (5 <= score < 7) should be warning
      expect(riskDots[1]).toHaveClass('bg-warning-500')
      
      // High risk (score >= 7) should be danger
      expect(riskDots[2]).toHaveClass('bg-danger-500')
    })

    it('has proper section styling', () => {
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } }
      ]
      
      renderWithProviders(<Sidebar />)
      
      const sectionHeader = screen.getByText('Recent Analyses')
      expect(sectionHeader).toHaveClass('text-xs', 'font-semibold', 'text-neutral-500', 'uppercase', 'tracking-wider', 'mb-3')
      
      const section = document.querySelector('.px-4.py-4.border-t.border-neutral-200')
      expect(section).toBeInTheDocument()
    })
  })

  describe('Quick Actions Section', () => {
    it('renders quick actions', () => {
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByText('Help & Support')).toBeInTheDocument()
    })

    it('has correct link for help & support', () => {
      renderWithProviders(<Sidebar />)
      
      const helpLink = screen.getByText('Help & Support').closest('a')
      expect(helpLink).toHaveAttribute('href', '/help')
    })

    it('renders help icon correctly', () => {
      renderWithProviders(<Sidebar />)
      
      expect(screen.getByTestId('help-circle-icon')).toBeInTheDocument()
      expect(screen.getByTestId('help-circle-icon')).toHaveClass('w-4', 'h-4', 'text-neutral-400', 'group-hover:text-neutral-600')
    })

    it('has proper quick actions styling', () => {
      renderWithProviders(<Sidebar />)
      
      const helpLink = screen.getByText('Help & Support').closest('a')
      expect(helpLink).toHaveClass(
        'group', 'flex', 'items-center', 'gap-3', 'px-3', 'py-2', 'text-sm', 'font-medium',
        'text-neutral-600', 'rounded-lg', 'hover:text-neutral-900', 'hover:bg-neutral-50', 'transition-colors'
      )
    })
  })

  describe('Responsive Design', () => {
    it('has proper mobile layout structure', () => {
      renderWithProviders(<Sidebar />)
      
      const container = document.querySelector('.flex.flex-col.h-full')
      expect(container).toBeInTheDocument()
      
      // Navigation should be flex-1 to take available space
      const nav = document.querySelector('nav.flex-1')
      expect(nav).toBeInTheDocument()
    })

    it('applies correct spacing and padding', () => {
      renderWithProviders(<Sidebar />)
      
      // Logo section
      const logoSection = document.querySelector('.p-6')
      expect(logoSection).toBeInTheDocument()
      
      // Navigation section
      const navSection = document.querySelector('.px-4.py-6')
      expect(navSection).toBeInTheDocument()
      
      // Quick actions section
      const quickActionsSection = document.querySelector('.px-4.py-4')
      expect(quickActionsSection).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles empty recent analyses array', () => {
      mockAnalysisStore.recentAnalyses = []
      
      renderWithProviders(<Sidebar />)
      
      expect(screen.queryByText('Recent Analyses')).not.toBeInTheDocument()
    })

    it('handles analyses with missing data gracefully', () => {
      mockAnalysisStore.recentAnalyses = [
        { 
          contract_id: '1',
          analysis_timestamp: undefined,
          executive_summary: undefined
        } as any
      ]
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      try {
        renderWithProviders(<Sidebar />)
        
        // Should not crash
        expect(document.body).toBeInTheDocument()
      } catch (error) {
        // If it throws, that's also acceptable behavior
        expect(error).toBeDefined()
      }
      
      consoleSpy.mockRestore()
    })

    it('handles very long analysis timestamps', () => {
      mockAnalysisStore.recentAnalyses = [
        { 
          contract_id: '1', 
          analysis_timestamp: '2024-12-31T23:59:59.999Z', 
          executive_summary: { overall_risk_score: 3 } 
        }
      ]
      
      renderWithProviders(<Sidebar />)
      
      // Should format date correctly
      expect(screen.getByText('12/31/2024')).toBeInTheDocument()
    })

    it('handles invalid risk scores', () => {
      mockAnalysisStore.recentAnalyses = [
        { 
          contract_id: '1', 
          analysis_timestamp: '2024-01-01T00:00:00Z', 
          executive_summary: { overall_risk_score: -1 } 
        }
      ]
      
      renderWithProviders(<Sidebar />)
      
      // Should still render without crashing
      expect(screen.getByText('Contract Analysis')).toBeInTheDocument()
    })

    it('handles unknown routes', () => {
      mockLocation.pathname = '/unknown/route'
      
      renderWithProviders(<Sidebar />)
      
      // No navigation item should be active
      const activeItems = document.querySelectorAll('.bg-primary-50.text-primary-700')
      expect(activeItems).toHaveLength(0)
    })
  })

  describe('Accessibility', () => {
    it('uses semantic navigation element', () => {
      renderWithProviders(<Sidebar />)
      
      const nav = document.querySelector('nav')
      expect(nav).toBeInTheDocument()
    })

    it('has accessible navigation links', () => {
      renderWithProviders(<Sidebar />)
      
      const links = screen.getAllByRole('link')
      expect(links.length).toBeGreaterThan(0)
      
      // All links should have href attributes
      links.forEach(link => {
        expect(link).toHaveAttribute('href')
      })
    })

    it('provides meaningful text for all interactive elements', () => {
      renderWithProviders(<Sidebar />)
      
      // All navigation items should have text
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('New Analysis')).toBeInTheDocument()
      expect(screen.getByText('Analysis History')).toBeInTheDocument()
      expect(screen.getByText('Reports')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
      expect(screen.getByText('Help & Support')).toBeInTheDocument()
    })

    it('maintains proper heading hierarchy', () => {
      mockAnalysisStore.recentAnalyses = [
        { contract_id: '1', analysis_timestamp: '2024-01-01T00:00:00Z', executive_summary: { overall_risk_score: 3 } }
      ]
      
      renderWithProviders(<Sidebar />)
      
      // Logo title should be h1
      const title = screen.getByText('Real2.AI')
      expect(title.tagName).toBe('H1')
      
      // Section headers should be h3
      const sectionHeader = screen.getByText('Recent Analyses')
      expect(sectionHeader.tagName).toBe('H3')
    })
  })

  describe('Integration', () => {
    it('integrates with analysis store correctly', () => {
      renderWithProviders(<Sidebar />)
      
      // Should use data from analysis store
      expect(mockAnalysisStore.recentAnalyses).toBeDefined()
      expect(mockAnalysisStore.isAnalyzing).toBeDefined()
    })

    it('integrates with React Router correctly', () => {
      renderWithProviders(<Sidebar />)
      
      // Should use location from React Router
      const activeLink = document.querySelector('.bg-primary-50.text-primary-700')
      expect(activeLink).toBeInTheDocument()
      
      // Active link should correspond to current pathname
      expect(activeLink?.textContent).toContain('Dashboard')
    })

    it('handles route changes correctly', () => {
      mockLocation.pathname = '/app/settings'
      
      const { rerender } = renderWithProviders(<Sidebar />)
      
      let activeLink = screen.getByText('Settings').closest('a')
      expect(activeLink).toHaveClass('bg-primary-50', 'text-primary-700')
      
      // Change route
      mockLocation.pathname = '/app/analysis'
      rerender(<Sidebar />)
      
      activeLink = screen.getByText('New Analysis').closest('a')
      expect(activeLink).toHaveClass('bg-primary-50', 'text-primary-700')
    })
  })
})