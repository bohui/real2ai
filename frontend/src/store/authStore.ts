import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, UserLoginRequest, UserRegistrationRequest } from '@/types'
import { apiService } from '@/services/api'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (credentials: UserLoginRequest) => Promise<void>
  register: (data: UserRegistrationRequest) => Promise<void>
  logout: () => void
  clearError: () => void
  updateUser: (user: Partial<User>) => void
  refreshUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials: UserLoginRequest) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await apiService.login(credentials)
          set({
            user: response.user_profile,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: apiService.handleError(error)
          })
          throw error
        }
      },

      register: async (data: UserRegistrationRequest) => {
        set({ isLoading: true, error: null })
        
        try {
          const response = await apiService.register(data)
          set({
            user: response.user_profile,
            isAuthenticated: true,
            isLoading: false,
            error: null
          })
        } catch (error: any) {
          set({
            isLoading: false,
            error: apiService.handleError(error)
          })
          throw error
        }
      },

      logout: () => {
        apiService.logout()
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        })
      },

      clearError: () => {
        set({ error: null })
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user
        if (currentUser) {
          set({
            user: { ...currentUser, ...userData }
          })
        }
      },

      refreshUser: async () => {
        if (!get().isAuthenticated) return
        
        try {
          const user = await apiService.getCurrentUser()
          set({ user })
        } catch (error: any) {
          console.error('Failed to refresh user:', error)
          // Don't set error for background refresh failures
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

// Listen for unauthorized events to auto-logout
window.addEventListener('auth:unauthorized', () => {
  useAuthStore.getState().logout()
})