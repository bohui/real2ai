/**
 * Test utilities for React Testing Library
 */

import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'

// Mock store states for different test scenarios
export interface TestStoreConfig {
  auth?: {
    user?: any
    isAuthenticated?: boolean
    isLoading?: boolean
    error?: string | null
  }
  ui?: {
    showOnboarding?: boolean
    notifications?: any[]
    sidebarOpen?: boolean
    isMobile?: boolean
  }
  analysis?: {
    isUploading?: boolean
    uploadProgress?: number
    contracts?: any[]
    analyses?: Record<string, any>
    recentAnalyses?: any[]
    isAnalyzing?: boolean
  }
}

// Create context-specific providers
const createTestProviders = (includeRouter: boolean = true) => {
  const TestProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          staleTime: 0,
          gcTime: 0,
        },
      },
    })

    const content = includeRouter ? (
      <BrowserRouter>
        {children}
      </BrowserRouter>
    ) : children

    return (
      <QueryClientProvider client={queryClient}>
        {content}
      </QueryClientProvider>
    )
  }
  return TestProviders
}

// Default provider (with router for components that need it)
const AllTheProviders = createTestProviders(true)

// Provider for App component (no router since App includes its own)
const AppProvider = createTestProviders(false)

const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

// Special render function for App component
export const renderApp = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AppProvider, ...options })

// Helper functions to configure mock stores before rendering
export const configureAuthenticatedState = (userOverrides: Partial<typeof mockUser> = {}) => {
  mockAuthStore.user = { ...mockUser, ...userOverrides }
  mockAuthStore.isAuthenticated = true
  mockAuthStore.isLoading = false
  mockAuthStore.error = null
  mockUIStore.showOnboarding = false
  mockUIStore.notifications = []
}

export const configureUnauthenticatedState = () => {
  mockAuthStore.user = null
  mockAuthStore.isAuthenticated = false
  mockAuthStore.isLoading = false
  mockAuthStore.error = null
  mockUIStore.showOnboarding = false
  mockUIStore.notifications = []
}

export const configureOnboardingState = (userOverrides: Partial<typeof mockUser> = {}) => {
  mockAuthStore.user = { 
    ...mockUser, 
    onboarding_completed: false,
    onboarding_completed_at: null,
    ...userOverrides 
  }
  mockAuthStore.isAuthenticated = true
  mockAuthStore.isLoading = false
  mockAuthStore.error = null
  mockUIStore.showOnboarding = true
  mockUIStore.notifications = []
}

export const configureLoadingState = () => {
  mockAuthStore.user = null
  mockAuthStore.isAuthenticated = false
  mockAuthStore.isLoading = true
  mockAuthStore.error = null
}

export const configureErrorState = (error: string = 'Test error') => {
  mockAuthStore.user = null
  mockAuthStore.isAuthenticated = false
  mockAuthStore.isLoading = false
  mockAuthStore.error = error
}

// Specialized render functions for different app states
export const renderAuthenticated = (
  ui: React.ReactElement,
  userOverrides: Partial<typeof mockUser> = {},
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  configureAuthenticatedState(userOverrides)
  return customRender(ui, options)
}

export const renderUnauthenticated = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  configureUnauthenticatedState()
  return customRender(ui, options)
}

export const renderOnboarding = (
  ui: React.ReactElement,
  userOverrides: Partial<typeof mockUser> = {},
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  configureOnboardingState(userOverrides)
  return customRender(ui, options)
}

export const renderLoading = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  configureLoadingState()
  return customRender(ui, options)
}

export const renderWithError = (
  ui: React.ReactElement,
  error: string = 'Test error',
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  configureErrorState(error)
  return customRender(ui, options)
}

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
  startAnalysis: vi.fn(),
  getAnalysisResult: vi.fn(),
  deleteAnalysis: vi.fn(),
  downloadReport: vi.fn(),
  updateProfile: vi.fn(),
  updateUserPreferences: vi.fn(),
  getUserStats: vi.fn(),
  healthCheck: vi.fn(),
  handleError: vi.fn((error) => error.message || 'Unknown error'),
  setToken: vi.fn(),
  clearToken: vi.fn(),
}

// Mock auth store
export const mockAuthStore = {
  user: null,
  isAuthenticated: false,
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

// Mock analysis store
export const mockAnalysisStore = {
  isUploading: false,
  uploadProgress: 0,
  uploadDocument: vi.fn(),
  contracts: [],
  analyses: {},
  recentAnalyses: [],
  isAnalyzing: false,
  getContract: vi.fn(),
  getAnalysis: vi.fn(),
  startAnalysis: vi.fn(),
  clearContracts: vi.fn(),
  setAnalysisProgress: vi.fn(),
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