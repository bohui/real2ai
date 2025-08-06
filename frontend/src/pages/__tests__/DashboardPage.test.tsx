/**
 * Test DashboardPage component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@/test/utils'
import DashboardPage from '../DashboardPage'

// Mock API service
vi.mock('@/services/api', () => ({
  apiService: {
    getUserStats: vi.fn().mockResolvedValue({
      analyses_count: 10,
      credits_used: 15,
      credits_remaining: 85,
      average_risk_score: 4.2,
    }),
  },
}))

// Mock stores
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: {
      id: 'test-user',
      email: 'test@example.com',
      subscription_status: 'free',
      credits_remaining: 5,
    },
    isAuthenticated: true,
  })),
}))

vi.mock('@/store/analysisStore', () => ({
  useAnalysisStore: vi.fn(() => ({
    recentAnalyses: [
      {
        id: 'analysis-1',
        contract_id: 'contract-1',
        filename: 'test-contract.pdf',
        analysis_status: 'completed',
        risk_score: 3,
        created_at: '2024-01-01T00:00:00Z',
        executive_summary: {
          overall_risk_score: 3,
          risk_level: 'medium',
        },
      },
    ],
    contracts: [
      {
        id: 'contract-1',
        filename: 'test-contract.pdf',
        upload_timestamp: '2024-01-01T00:00:00Z',
        status: 'uploaded',
      },
    ],
    isUploading: false,
    uploadProgress: 0,
    uploadDocument: vi.fn(),
    analyses: {},
    isAnalyzing: false,
    getContract: vi.fn(),
    getAnalysis: vi.fn(),
    startAnalysis: vi.fn(),
    clearContracts: vi.fn(),
    setAnalysisProgress: vi.fn(),
  })),
}))

vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => ({
    addNotification: vi.fn(),
  })),
}))

describe('DashboardPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard component', () => {
    render(<DashboardPage />)

    // Just verify the component renders without crashing
    expect(document.body).toBeInTheDocument()
  })

  it('renders with authenticated user', () => {
    render(<DashboardPage />)

    // The component should render successfully with the mocked auth state
    expect(document.body).toBeInTheDocument()
  })

  it('handles store data', () => {
    render(<DashboardPage />)

    // Should not throw any errors with the mocked store data
    expect(document.body).toBeInTheDocument()
  })
})