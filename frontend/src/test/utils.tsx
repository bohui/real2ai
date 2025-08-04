/**
 * Test utilities for React Testing Library
 */

import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'

// Create a custom render function that includes providers
const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

export * from '@testing-library/react'
export { customRender as render }

// Mock API service
export const mockApiService = {
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getCurrentUser: vi.fn(),
  getOnboardingStatus: vi.fn(),
  completeOnboarding: vi.fn(),
  updateOnboardingPreferences: vi.fn(),
  uploadDocument: vi.fn(),
  getDocument: vi.fn(),
  startContractAnalysis: vi.fn(),
  getContractAnalysis: vi.fn(),
  downloadReport: vi.fn(),
  getUserProfile: vi.fn(),
  updateUserPreferences: vi.fn(),
  getUsageStats: vi.fn(),
}

// Mock auth store
export const mockAuthStore = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  login: vi.fn(),
  logout: vi.fn(),
  initializeAuth: vi.fn(),
  setUser: vi.fn(),
}

// Mock UI store
export const mockUIStore = {
  showOnboarding: false,
  notifications: [],
  setShowOnboarding: vi.fn(),
  addNotification: vi.fn(),
  removeNotification: vi.fn(),
  clearNotifications: vi.fn(),
}

// Test data
export const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  australian_state: 'NSW',
  user_type: 'buyer',
  subscription_status: 'free',
  credits_remaining: 5,
  preferences: {},
  onboarding_completed: true,
  onboarding_completed_at: '2024-01-01T00:00:00Z',
  onboarding_preferences: {
    practice_area: 'property',
    jurisdiction: 'nsw',
    firm_size: 'small',
  },
  created_at: '2024-01-01T00:00:00Z',
}

export const mockDocument = {
  id: 'test-doc-id',
  user_id: 'test-user-id',
  filename: 'test-contract.pdf',
  file_type: 'pdf',
  file_size: 1024000,
  status: 'uploaded',
  storage_path: 'documents/test-user-id/test-doc-id.pdf',
  upload_timestamp: '2024-01-01T00:00:00Z',
  processing_results: {
    extracted_text: 'Sample contract text',
    extraction_confidence: 0.95,
    character_count: 1000,
    word_count: 200,
  },
}

export const mockContract = {
  id: 'test-contract-id',
  document_id: 'test-doc-id',
  contract_type: 'purchase_agreement',
  australian_state: 'NSW',
  user_id: 'test-user-id',
}

export const mockAnalysis = {
  contract_id: 'test-contract-id',
  analysis_status: 'completed',
  analysis_result: {
    contract_terms: {
      purchase_price: 500000,
      deposit: 50000,
      settlement_date: '2024-03-15',
    },
    risk_assessment: {
      overall_risk_score: 3,
      risk_factors: [
        {
          factor: 'Short settlement period',
          severity: 'medium',
          description: 'Settlement period is shorter than recommended',
          impact: 'Medium financial risk',
          mitigation: 'Arrange finance pre-approval',
          australian_specific: true,
          confidence: 0.85,
        },
      ],
    },
    compliance_check: {
      state_compliance: true,
      compliance_issues: [],
      cooling_off_compliance: true,
      cooling_off_details: {
        cooling_off_period: '5 business days',
        cooling_off_end_date: '2024-02-20',
      },
      mandatory_disclosures: [
        'Section 32 Statement',
        'Building and Pest Inspection Report',
      ],
      warnings: [],
      legal_references: ['Conveyancing Act 1919 (NSW)'],
    },
    recommendations: [
      {
        priority: 'high',
        category: 'legal',
        recommendation: 'Review settlement date with conveyancer',
        action_required: true,
        australian_context: 'NSW specific settlement requirements',
        confidence: 0.9,
      },
    ],
  },
  risk_score: 3,
  processing_time: 45.2,
  created_at: '2024-01-01T00:00:00Z',
}

// Helper function to create a file for upload testing
export const createMockFile = (
  name = 'test-contract.pdf',
  size = 1024000,
  type = 'application/pdf'
) => {
  const file = new File(['test content'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}