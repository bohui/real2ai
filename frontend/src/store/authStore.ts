import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User, UserLoginRequest, UserRegistrationRequest } from "@/types";
import { apiService } from "@/services/api";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: UserLoginRequest) => Promise<void>;
  register: (data: UserRegistrationRequest) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  updateUser: (user: Partial<User>) => void;
  updateProfile: (userData: Partial<User>) => Promise<void>;
  refreshUser: () => Promise<void>;
  initializeAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials: UserLoginRequest) => {
        set({ isLoading: true, error: null });

        try {
          const response = await apiService.login(credentials);
          set({
            user: response.user_profile,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: unknown) {
          set({
            isLoading: false,
            error: apiService.handleError(error as any),
          });
          throw error;
        }
      },

      register: async (data: UserRegistrationRequest) => {
        set({ isLoading: true, error: null });

        try {
          const response = await apiService.register(data);
          set({
            user: response.user_profile,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: unknown) {
          set({
            isLoading: false,
            error: apiService.handleError(error as any),
          });
          throw error;
        }
      },

      logout: () => {
        apiService.logout();
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });

        // Reset onboarding state on logout
        // Import is done dynamically to avoid circular dependency
        import("@/store/uiStore").then(({ useUIStore }) => {
          useUIStore.getState().resetOnboardingState();
        });
      },

      clearError: () => {
        set({ error: null });
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user;
        if (currentUser) {
          set({
            user: { ...currentUser, ...userData },
          });
        }
      },

      updateProfile: async (userData: Partial<User>) => {
        try {
          const updatedUser = await apiService.updateProfile(userData);
          set({ user: updatedUser });
        } catch (error: unknown) {
          console.error("Failed to update profile:", error);
          throw error;
        }
      },

      refreshUser: async () => {
        if (!get().isAuthenticated) return;

        try {
          const user = await apiService.getCurrentUser();
          set({ user });
        } catch (error: unknown) {
          console.error("Failed to refresh user:", error);
          // If it's an auth error (401), the interceptor will handle logout
          // Re-throw to allow callers to handle the error
          if ((error as any)?.response?.status === 401) {
            throw error;
          }
          // For other errors, don't set error for background refresh failures
        }
      },

      initializeAuth: async () => {
        set({ isLoading: true });

        // Check if user is already authenticated from persisted state
        const { user, isAuthenticated } = get();

        if (isAuthenticated && user) {
          try {
            // Only refresh user data if it's incomplete (missing required onboarding fields)
            // onboarding_completed_at is optional, so we don't check for it
            const hasCompleteData = user.onboarding_completed !== undefined &&
              user.onboarding_preferences !== undefined;

            if (!hasCompleteData) {
              // Validate token by attempting to refresh user data
              await get().refreshUser();
            }
            // If successful, user is still authenticated
            set({ isLoading: false });
          } catch (error) {
            // Token is likely expired, clear auth state
            console.log(
              "Token validation failed during initialization, logging out",
            );
            get().logout();
            set({ isLoading: false });
          }
        } else {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);

// Listen for unauthorized events to auto-logout
window.addEventListener("auth:unauthorized", () => {
  useAuthStore.getState().logout();
});
