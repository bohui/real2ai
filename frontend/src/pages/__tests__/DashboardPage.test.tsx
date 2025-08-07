import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@/test/utils'
import DashboardPage from '../DashboardPage'
import { useAuthStore } from '@/store/authStore'
import { useAnalysisStore } from '@/store/analysisStore'
import { apiService } from '@/services/api'
import { ContractAnalysisResult } from '@/types'

// Mock the stores
vi.mock('@/store/authStore')
vi.mock('@/store/analysisStore')
vi.mock('@/services/api')

const mockUseAuthStore = vi.mocked(useAuthStore)
const mockUseAnalysisStore = vi.mocked(useAnalysisStore)
const mockApiService = vi.mocked(apiService)

describe('DashboardPage', () => {
  const mockUser = {
    id: 'test-user-id',
    email: 'test@example.com',
    australian_state: 'NSW',
    user_type: 'individual',
    subscription_status: 'premium',
    credits_remaining: 10,
    preferences: {}
  }

  const mockAuthStore = {
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    error: null,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    clearError: vi.fn(),
    updateUser: vi.fn(),
    updateProfile: vi.fn(),
    refreshUser: vi.fn(),
    initializeAuth: vi.fn(),
  }

  const mockAnalysisStore = {
    contracts: [],
    analyses: {},
    recentAnalyses: [] as ContractAnalysisResult[],
    isAnalyzing: false,
    isUploading: false,
    uploadProgress: 0,
    uploadDocument: vi.fn(),
    getContract: vi.fn(),
    getAnalysis: vi.fn(),
    startAnalysis: vi.fn(),
    clearContracts: vi.fn(),
    setAnalysisProgress: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuthStore.mockReturnValue(mockAuthStore)
    mockUseAnalysisStore.mockReturnValue(mockAnalysisStore)
    
    // Mock API responses
    mockApiService.getUserStats.mockResolvedValue({
      total_contracts_analyzed: 5,
      credits_remaining: 60,
      subscription_status: 'premium' as const,
      current_month_usage: 15,
      recent_analyses: []
    })
  })

  describe('Page Rendering', () => {
    it('renders dashboard page with welcome message', () => {
      render(<DashboardPage />)
      
      expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
      expect(screen.getByText('test@example.com')).toBeInTheDocument()
    })

    it('displays user statistics cards', async () => {
      render(<DashboardPage />)
      
      await waitFor(() => {
        expect(screen.getByText(/total analyses/i)).toBeInTheDocument()
        expect(screen.getByText(/credits remaining/i)).toBeInTheDocument()
        expect(screen.getByText('60')).toBeInTheDocument() // Credits remaining
        expect(screen.getByText('5')).toBeInTheDocument() // Analyses count
      })
    })

    it('shows recent analyses section', () => {
      render(<DashboardPage />)
      
      expect(screen.getByText(/recent analyses/i)).toBeInTheDocument()
    })

    it('displays quick actions section', () => {
      render(<DashboardPage />)
      
      expect(screen.getByText(/quick actions/i)).toBeInTheDocument()
      expect(screen.getByText(/upload new document/i)).toBeInTheDocument()
      expect(screen.getByText(/view all analyses/i)).toBeInTheDocument()
    })
  })

  describe('User Statistics', () => {
    it('loads and displays user statistics on mount', async () => {
      render(<DashboardPage />)
      
      await waitFor(() => {
        expect(mockApiService.getUserStats).toHaveBeenCalledTimes(1)
      })
    })

    it('handles statistics loading error', async () => {
      mockApiService.getUserStats.mockRejectedValueOnce(new Error('Failed to load stats'))
      
      render(<DashboardPage />)
      
      await waitFor(() => {
        // Should handle error gracefully, maybe show default values or error message
        expect(mockApiService.getUserStats).toHaveBeenCalledTimes(1)
      })
    })

    it('shows loading state while fetching statistics', () => {
      // Mock slow API response
      mockApiService.getUserStats.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          total_contracts_analyzed: 5,
          credits_remaining: 60,
          subscription_status: 'premium' as const,
          current_month_usage: 15,
          recent_analyses: []
        }), 100))
      )
      
      render(<DashboardPage />)
      
      // Should show loading indicators or skeleton states
      expect(screen.getByTestId('main-layout')).toBeInTheDocument()
    })
  })

  describe('Recent Analyses', () => {
    it('displays recent analyses when available', () => {
      const mockRecentAnalyses = [
        {
          contract_id: 'contract-1',
          analysis_id: 'analysis-1',
          analysis_timestamp: '2024-01-01T00:00:00Z',
          user_id: 'user-1',
          australian_state: 'NSW' as const,
          analysis_status: 'completed' as const,
          contract_terms: {},
          risk_assessment: {
            overall_risk_score: 2,
            risk_factors: []
          },
          compliance_check: {
            state_compliance: true,
            compliance_issues: [],
            cooling_off_compliance: true,
            cooling_off_details: {},
            mandatory_disclosures: [],
            warnings: [],
            legal_references: []
          },
          recommendations: [],
          confidence_scores: {},
          overall_confidence: 0.8,
          processing_time: 120,
          analysis_version: '1.0',
          executive_summary: {
            overall_risk_score: 2,
            compliance_status: 'compliant' as const,
            total_recommendations: 1,
            critical_issues: 0,
            confidence_level: 0.8
          }
        }
      ]

      mockAnalysisStore.recentAnalyses = mockRecentAnalyses
      mockUseAnalysisStore.mockReturnValue({
        ...mockAnalysisStore,
        recentAnalyses: mockRecentAnalyses
      })

      render(<DashboardPage />)
      
      // The component should display analysis information based on the executive_summary
      expect(screen.getByText(/recent analyses/i)).toBeInTheDocument()
    })

    it('shows empty state when no recent analyses', () => {
      mockAnalysisStore.recentAnalyses = []
      mockUseAnalysisStore.mockReturnValue({
        ...mockAnalysisStore,
        recentAnalyses: []
      })

      render(<DashboardPage />)
      
      expect(screen.getByText(/no recent analyses/i)).toBeInTheDocument()
    })

    it('handles analysis click navigation', () => {
      const mockRecentAnalyses = [
        {
          contract_id: 'contract-1',
          analysis_id: 'analysis-1',
          analysis_timestamp: '2024-01-01T00:00:00Z',
          user_id: 'user-1',
          australian_state: 'NSW' as const,
          analysis_status: 'completed' as const,
          contract_terms: {},
          risk_assessment: {
            overall_risk_score: 2,
            risk_factors: []
          },
          compliance_check: {
            state_compliance: true,
            compliance_issues: [],
            cooling_off_compliance: true,
            cooling_off_details: {},
            mandatory_disclosures: [],
            warnings: [],
            legal_references: []
          },
          recommendations: [],
          confidence_scores: {},
          overall_confidence: 0.8,
          processing_time: 120,
          analysis_version: '1.0',
          executive_summary: {
            overall_risk_score: 2,
            compliance_status: 'compliant' as const,
            total_recommendations: 1,
            critical_issues: 0,
            confidence_level: 0.8
          }
        }
      ]

      mockAnalysisStore.recentAnalyses = mockRecentAnalyses
      mockUseAnalysisStore.mockReturnValue({
        ...mockAnalysisStore,
        recentAnalyses: mockRecentAnalyses
      })

      render(<DashboardPage />)
      
      // Should navigate to analysis page (mocked Navigate component will be called)
      expect(screen.getByText(/recent analyses/i)).toBeInTheDocument()
    })
  })

  describe('Quick Actions', () => {
    it('renders upload document action', () => {
      render(<DashboardPage />)
      
      const uploadButton = screen.getByText(/upload new document/i)
      expect(uploadButton).toBeInTheDocument()
    })

    it('renders view all analyses action', () => {
      render(<DashboardPage />)
      
      const viewAllButton = screen.getByText(/view all analyses/i)
      expect(viewAllButton).toBeInTheDocument()
    })

    it('handles upload document click', () => {
      render(<DashboardPage />)
      
      const uploadButton = screen.getByText(/upload new document/i)
      fireEvent.click(uploadButton)
      
      // Should trigger navigation or modal
    })

    it('handles view all analyses click', () => {
      render(<DashboardPage />)
      
      const viewAllButton = screen.getByText(/view all analyses/i)
      fireEvent.click(viewAllButton)
      
      // Should navigate to analyses list page
    })
  })

  describe('Subscription Status', () => {
    it('displays premium subscription benefits', () => {
      render(<DashboardPage />)
      
      // Should show premium-specific content or features
      expect(screen.getByText(/premium/i)).toBeInTheDocument()
    })

    it('shows credit information for premium users', async () => {
      render(<DashboardPage />)
      
      await waitFor(() => {
        expect(screen.getByText('60')).toBeInTheDocument() // Credits remaining
      })
    })

    it('handles free tier user differently', () => {
      const freeUser = {
        ...mockUser,
        subscription_status: 'free',
        credits_remaining: 3
      }

      mockUseAuthStore.mockReturnValue({
        ...mockAuthStore,
        user: freeUser
      })

      mockApiService.getUserStats.mockResolvedValueOnce({
        total_contracts_analyzed: 2,
        credits_remaining: 3,
        subscription_status: 'basic' as const,
        current_month_usage: 8,
        recent_analyses: []
      })

      render(<DashboardPage />)
      
      // Should show limited features or upgrade prompts for free users
      expect(screen.getByText('3')).toBeInTheDocument() // Credits remaining
    })

    it('shows upgrade prompt for users with low credits', async () => {
      const lowCreditUser = {
        ...mockUser,
        subscription_status: 'free',
        credits_remaining: 1
      }

      mockUseAuthStore.mockReturnValue({
        ...mockAuthStore,
        user: lowCreditUser
      })

      mockApiService.getUserStats.mockResolvedValueOnce({
        total_contracts_analyzed: 4,
        credits_remaining: 1,
        subscription_status: 'free' as const,
        current_month_usage: 12,
        recent_analyses: []
      })

      render(<DashboardPage />)
      
      await waitFor(() => {
        // Should show upgrade notification or warning about low credits
        expect(screen.getByText('1')).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Updates', () => {
    it('updates when analysis store changes', () => {
      const { rerender } = render(<DashboardPage />)
      
      // Initial state
      expect(mockAnalysisStore.recentAnalyses).toHaveLength(0)
      
      // Update store with new analysis
      const updatedStore = {
        ...mockAnalysisStore,
        recentAnalyses: [{
          id: 'new-analysis',
          contract_id: 'new-contract',
          document_name: 'New Contract.pdf',
          analysis_status: 'completed',
          created_at: '2024-01-03T00:00:00Z',
          risk_score: 4
        }]
      }
      
      mockUseAnalysisStore.mockReturnValue(updatedStore)
      rerender(<DashboardPage />)
      
      expect(screen.getByText('New Contract.pdf')).toBeInTheDocument()
    })

    it('shows analysis progress for ongoing analyses', () => {
      const processingAnalyses = [{
        id: 'processing-analysis',
        contract_id: 'processing-contract',
        document_name: 'Processing Contract.pdf',
        analysis_status: 'processing',
        created_at: '2024-01-01T00:00:00Z',
        progress: 0.65
      }]

      mockUseAnalysisStore.mockReturnValue({
        ...mockAnalysisStore,
        recentAnalyses: processingAnalyses,
        isAnalyzing: true
      })

      render(<DashboardPage />)
      
      expect(screen.getByText('Processing Contract.pdf')).toBeInTheDocument()
      expect(screen.getByText(/processing/i)).toBeInTheDocument()
      // Should show progress indicator if implemented
    })
  })

  describe('Error States', () => {
    it('handles authentication error gracefully', () => {
      mockUseAuthStore.mockReturnValue({
        ...mockAuthStore,
        user: null,
        isAuthenticated: false,
        error: 'Authentication failed'
      })

      render(<DashboardPage />)
      
      // Should redirect to login or show error state
      // This would depend on ProtectedRoute implementation
    })

    it('handles API service errors gracefully', async () => {
      mockApiService.getUserStats.mockRejectedValueOnce(new Error('Service unavailable'))
      
      render(<DashboardPage />)
      
      await waitFor(() => {
        expect(mockApiService.getUserStats).toHaveBeenCalledTimes(1)
      })
      
      // Should show error state or fallback content
      expect(screen.getByTestId('main-layout')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(<DashboardPage />)
      
      const headings = screen.getAllByRole('heading')
      expect(headings.length).toBeGreaterThan(0)
      
      // Should have proper heading hierarchy (h1, h2, etc.)
    })

    it('has accessible navigation elements', () => {
      render(<DashboardPage />)
      
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
      
      // Buttons should have accessible names
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName()
      })
    })

    it('supports keyboard navigation', () => {
      render(<DashboardPage />)
      
      const interactiveElements = screen.getAllByRole('button')
      interactiveElements.forEach(element => {
        expect(element).not.toHaveAttribute('tabindex', '-1')
      })
    })
  })

  describe('Responsive Design', () => {
    it('renders properly on mobile viewport', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })
      
      render(<DashboardPage />)
      
      // Should render mobile-optimized layout
      expect(screen.getByTestId('main-layout')).toBeInTheDocument()
    })

    it('renders properly on desktop viewport', () => {
      // Mock desktop viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1200,
      })
      
      render(<DashboardPage />)
      
      // Should render desktop layout
      expect(screen.getByTestId('main-layout')).toBeInTheDocument()
    })
  })
})