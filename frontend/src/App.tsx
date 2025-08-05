import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

// Layout Components
import Layout from '@/components/layout/Layout'
import AuthLayout from '@/components/layout/AuthLayout'

// Pages
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import AnalysisPage from '@/pages/AnalysisPage'
import HistoryPage from '@/pages/HistoryPage'
import SettingsPage from '@/pages/SettingsPage'
import ReportsPage from '@/pages/ReportsPage'

// Components
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import NotificationSystem from '@/components/notifications/NotificationSystem'
import OnboardingWizard from '@/components/onboarding/OnboardingWizard'

// Hooks and stores
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'
import apiService from '@/services/api'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false
        }
        return failureCount < 3
      }
    }
  }
})

const App: React.FC = () => {
  const { initializeAuth, isLoading, user, isAuthenticated } = useAuthStore()
  const { showOnboarding, setShowOnboarding } = useUIStore()
  const [onboardingChecked, setOnboardingChecked] = React.useState(false)

  // Initialize authentication on app start
  React.useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  // Check onboarding status for authenticated users only
  React.useEffect(() => {
    const checkOnboardingStatus = async () => {
      // Only proceed if user is authenticated and we haven't checked yet
      if (user && isAuthenticated && !isLoading && !onboardingChecked) {
        try {
          const onboardingStatus = await apiService.getOnboardingStatus()
          
          // Double-check user is still authenticated after API call
          if (user && isAuthenticated) {
            if (!onboardingStatus.onboarding_completed) {
              setShowOnboarding(true)
            }
          }
          
          setOnboardingChecked(true)
        } catch (error) {
          console.error('Failed to check onboarding status:', error)
          // Don't show onboarding if API call fails - could indicate auth issues
          // If it's a legitimate API error, user can try again after refresh
          setOnboardingChecked(true)
        }
      } else if (!user || !isAuthenticated) {
        // Reset onboarding state when user logs out or becomes unauthenticated
        setOnboardingChecked(false)
        setShowOnboarding(false)
      }
    }

    checkOnboardingStatus()
  }, [user, isAuthenticated, isLoading, onboardingChecked, setShowOnboarding])

  const handleOnboardingComplete = async (preferences: any) => {
    try {
      const result = await apiService.completeOnboarding({
        practice_area: preferences.practiceArea,
        jurisdiction: preferences.jurisdiction,
        firm_size: preferences.firmSize,
        primary_contract_types: preferences.primaryContractTypes
      })
      
      console.log('Onboarding completed:', result.message)
      setShowOnboarding(false)
      
      // If user was already onboarded, don't show again
      if (result.skip_onboarding) {
        console.log('User already completed onboarding')
      }
    } catch (error) {
      console.error('Failed to complete onboarding:', error)
      // Still hide onboarding to prevent blocking the user
      setShowOnboarding(false)
    }
  }

  const handleOnboardingSkip = () => {
    setShowOnboarding(false)
  }

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-neutral-600">Loading Real2.AI...</p>
        </div>
      </div>
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="App">
          <Routes>
            {/* Auth routes */}
            <Route path="/auth" element={<AuthLayout />}>
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route index element={<Navigate to="/auth/login" replace />} />
            </Route>

            {/* Protected app routes */}
            <Route path="/app" element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }>
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="analysis" element={<AnalysisPage />} />
              <Route path="analysis/:contractId" element={<AnalysisPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route index element={<Navigate to="/app/dashboard" replace />} />
            </Route>

            {/* Root redirect */}
            <Route path="/" element={<Navigate to="/app/dashboard" replace />} />

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
          </Routes>

          {/* Global components */}
          <NotificationSystem />
          
          {/* Onboarding Wizard - Only show for fully authenticated users */}
          {showOnboarding && user && isAuthenticated && !isLoading && (
            <OnboardingWizard 
              onComplete={handleOnboardingComplete}
              onSkip={handleOnboardingSkip}
            />
          )}
        </div>
      </Router>

      {/* Development tools */}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  )
}

export default App