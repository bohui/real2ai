import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

// Layout Components
import Layout from "@/components/layout/Layout";
import AuthLayout from "@/components/layout/AuthLayout";

// Pages
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import DashboardPage from "@/pages/DashboardPage";
import AnalysisPage from "@/pages/AnalysisPage";
import HistoryPage from "@/pages/HistoryPage";
import SettingsPage from "@/pages/SettingsPage";
import ReportsPage from "@/pages/ReportsPage";
import PropertyIntelligencePage from "@/pages/PropertyIntelligencePage";
import MarketAnalysisPage from "@/pages/MarketAnalysisPage";
import FinancialAnalysisPage from "@/pages/FinancialAnalysisPage";

// Components
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import NotificationSystem from "@/components/notifications/NotificationSystem";
import OnboardingWizard from "@/components/onboarding/OnboardingWizard";
import SEOProvider from "@/contexts/SEOContext";
import RootSEO from "@/components/seo/RootSEO";
import SEOFloatingButton from "@/components/seo/SEOFloatingButton";

// Hooks and stores
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import apiService from "@/services/api";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
    },
  },
});

const App: React.FC = () => {
  const { initializeAuth, isLoading, user, isAuthenticated } = useAuthStore();
  const { showOnboarding, setShowOnboarding } = useUIStore();
  const hasCheckedOnboardingRef = React.useRef(false);

  // Initialize authentication on app start
  React.useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  // Check onboarding status for authenticated users only
  React.useEffect(() => {
    const checkOnboardingStatus = async () => {
      // Only proceed if user is authenticated and not loading, and we haven't checked yet
      if (
        user &&
        isAuthenticated &&
        !isLoading &&
        !hasCheckedOnboardingRef.current
      ) {
        try {
          // Mark as checked to prevent duplicate calls
          hasCheckedOnboardingRef.current = true;

          // Always check the backend for the most up-to-date onboarding status
          // This ensures we have the latest data even if the frontend state is stale
          const onboardingStatus = await apiService.getOnboardingStatus();

          // Double-check user is still authenticated after API call
          if (user && isAuthenticated) {
            if (!onboardingStatus.onboarding_completed) {
              setShowOnboarding(true);
            } else {
              // User has completed onboarding, ensure it's hidden
              setShowOnboarding(false);

              // Update the user's onboarding status in the auth store to keep it in sync
              if (
                user.onboarding_completed !==
                onboardingStatus.onboarding_completed
              ) {
                useAuthStore.getState().updateUser({
                  onboarding_completed: onboardingStatus.onboarding_completed,
                  onboarding_preferences:
                    onboardingStatus.onboarding_preferences || {},
                });
              }
            }
          }
        } catch (error) {
          console.error("Failed to check onboarding status:", error);
          // Fallback to frontend state if API call fails
          if (user.onboarding_completed !== undefined) {
            if (!user.onboarding_completed) {
              setShowOnboarding(true);
            } else {
              setShowOnboarding(false);
            }
          } else {
            // If we can't determine onboarding status, don't show onboarding to prevent blocking
            setShowOnboarding(false);
          }
        }
      } else if (!user || !isAuthenticated) {
        // Reset onboarding state when user logs out or becomes unauthenticated
        setShowOnboarding(false);
        hasCheckedOnboardingRef.current = false;
      }
    };

    checkOnboardingStatus();
  }, [user?.id, isAuthenticated, isLoading, setShowOnboarding]);

  // Reset onboarding check ref when user changes
  const prevUserIdRef = React.useRef<string | undefined>(undefined);

  React.useEffect(() => {
    const currentUserId = user?.id;
    const previousUserId = prevUserIdRef.current;

    // Only reset if we have a different user ID (not on initial load)
    if (currentUserId && previousUserId && currentUserId !== previousUserId) {
      hasCheckedOnboardingRef.current = false;
    }

    // Update the previous user ID reference
    if (currentUserId) {
      prevUserIdRef.current = currentUserId;
    }
  }, [user?.id]);

  const handleOnboardingComplete = async (preferences: any) => {
    try {
      const result = await apiService.completeOnboarding({
        practice_area: preferences.practiceArea,
        jurisdiction: preferences.jurisdiction,
        firm_size: preferences.firmSize,
        primary_contract_types: preferences.primaryContractTypes,
      });

      console.log("Onboarding completed:", result.message);
      setShowOnboarding(false);

      // Update the user's onboarding status in the auth store to keep it in sync with backend
      if (user) {
        useAuthStore.getState().updateUser({
          onboarding_completed: true,
          onboarding_preferences: preferences,
        });
      }

      // If user was already onboarded, don't show again
      if (result.skip_onboarding) {
        console.log("User already completed onboarding");
      }
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
      // Still hide onboarding to prevent blocking the user
      setShowOnboarding(false);
    }
  };

  const handleOnboardingSkip = async () => {
    try {
      // Treat skip as completion with default preferences
      const defaultPreferences = {
        practice_area: "property",
        jurisdiction: user?.australian_state?.toLowerCase() || "nsw",
        firm_size: "individual",
        primary_contract_types: ["purchase_agreement"],
      };

      const result = await apiService.completeOnboarding(defaultPreferences);

      console.log("Onboarding skipped:", result.message);
      setShowOnboarding(false);

      // Update the user's onboarding status in the auth store to keep it in sync with backend
      if (user) {
        useAuthStore.getState().updateUser({
          onboarding_completed: true,
          onboarding_preferences: defaultPreferences,
        });
      }
    } catch (error) {
      console.error("Failed to skip onboarding:", error);
      // Still hide onboarding to prevent blocking the user
      setShowOnboarding(false);
    }
  };

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-neutral-600">Loading Real2.AI...</p>
        </div>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <SEOProvider>
          <RootSEO />
          <div className="App">
            <Routes>
            {/* Auth routes */}
            <Route path="/auth" element={<AuthLayout />}>
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route index element={<Navigate to="/auth/login" replace />} />
            </Route>

            {/* Protected app routes */}
            <Route
              path="/app"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="analysis" element={<AnalysisPage />} />
              <Route path="analysis/:contractId" element={<AnalysisPage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route
                path="property-intelligence"
                element={<PropertyIntelligencePage />}
              />
              <Route path="market-analysis" element={<MarketAnalysisPage />} />
              <Route
                path="financial-analysis"
                element={<FinancialAnalysisPage />}
              />
              <Route path="settings" element={<SettingsPage />} />
              <Route index element={<Navigate to="/app/dashboard" replace />} />
            </Route>

            {/* Root redirect */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Navigate to="/app/dashboard" replace />
                </ProtectedRoute>
              }
            />

            {/* Catch-all redirect */}
            <Route
              path="*"
              element={
                <ProtectedRoute>
                  <Navigate to="/app/dashboard" replace />
                </ProtectedRoute>
              }
            />
          </Routes>

          {/* Global components */}
          <NotificationSystem />
          <SEOFloatingButton />

          {/* Onboarding Wizard - Only show for fully authenticated users */}
          {showOnboarding && user && isAuthenticated && !isLoading && (
            <OnboardingWizard
              onComplete={handleOnboardingComplete}
              onSkip={handleOnboardingSkip}
            />
          )}
          </div>
        </SEOProvider>
      </Router>

      {/* Development tools */}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
};

export default App;
