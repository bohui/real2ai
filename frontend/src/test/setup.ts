/**
 * Test setup file for Vitest
 */

import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock fetch for API calls
global.fetch = vi.fn()

// Mock console methods to reduce noise in tests
vi.spyOn(console, 'warn').mockImplementation(() => {})
vi.spyOn(console, 'error').mockImplementation(() => {})

// Mock router
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: '/', search: '', hash: '', state: null }),
    useParams: () => ({}),
  }
})

// Mock stores
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
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
  }))
}))

vi.mock('@/store/uiStore', () => ({
  useUIStore: vi.fn(() => ({
    showOnboarding: false,
    notifications: [],
    setShowOnboarding: vi.fn(),
    addNotification: vi.fn(),
    removeNotification: vi.fn(),
    clearNotifications: vi.fn(),
  }))
}))

vi.mock('@/store/analysisStore', () => ({
  useAnalysisStore: vi.fn(() => ({
    isUploading: false,
    uploadProgress: 0,
    uploadDocument: vi.fn(),
    contracts: [],
    analyses: {},
    getContract: vi.fn(),
    getAnalysis: vi.fn(),
    startAnalysis: vi.fn(),
  }))
}))

// Mock API service
vi.mock('@/services/api', () => ({
  default: {
    uploadDocument: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    getOnboardingStatus: vi.fn(),
    completeOnboarding: vi.fn(),
    updateProfile: vi.fn(),
    startContractAnalysis: vi.fn(),
    getContractAnalysis: vi.fn(),
  },
  apiService: {
    uploadDocument: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    handleError: vi.fn((error) => error.message || 'Unknown error'),
  }
}))