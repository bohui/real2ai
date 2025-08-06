import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAuthStore } from '../authStore'
import { apiService } from '@/services/api'
import type { User, UserLoginRequest, UserRegistrationRequest } from '@/types'

// Mock API service
vi.mock('@/services/api', () => ({
  apiService: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateUserProfile: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
  }
}))

const mockApiService = vi.mocked(apiService)

describe('AuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset store state before each test
    useAuthStore.getState().logout()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useAuthStore())
      
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
    })
  })

  describe('Login', () => {
    it('should login successfully', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        australian_state: 'NSW',
        user_type: 'individual',
        subscription_status: 'premium',
        credits_remaining: 100,
        preferences: {}
      }

      const mockAuthResponse = {
        user: mockUser,
        token: 'mock-jwt-token'
      }

      mockApiService.login.mockResolvedValueOnce(mockAuthResponse)

      const { result } = renderHook(() => useAuthStore())

      const loginData: UserLoginRequest = {
        email: 'test@example.com',
        password: 'password123'
      }

      await act(async () => {
        await result.current.login(loginData)
      })

      expect(mockApiService.login).toHaveBeenCalledWith(loginData)
      expect(mockApiService.setToken).toHaveBeenCalledWith('mock-jwt-token')
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
    })

    it('should handle login error', async () => {
      const errorMessage = 'Invalid credentials'
      mockApiService.login.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHook(() => useAuthStore())

      const loginData: UserLoginRequest = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      await act(async () => {
        try {
          await result.current.login(loginData)
        } catch (error) {
          // Expected to throw
        }
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBe(errorMessage)
    })

    it('should set loading state during login', async () => {
      let resolveLogin: (value: any) => void
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve
      })
      mockApiService.login.mockReturnValueOnce(loginPromise)

      const { result } = renderHook(() => useAuthStore())

      const loginData: UserLoginRequest = {
        email: 'test@example.com',
        password: 'password123'
      }

      act(() => {
        result.current.login(loginData)
      })

      // Check loading state is true
      expect(result.current.isLoading).toBe(true)

      // Resolve the promise
      await act(async () => {
        resolveLogin!({
          user: { id: '1', email: 'test@example.com' },
          token: 'token'
        })
        await loginPromise
      })

      // Check loading state is false after completion
      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('Register', () => {
    it('should register successfully', async () => {
      const mockUser: User = {
        id: '1',
        email: 'newuser@example.com',
        australian_state: 'NSW',
        user_type: 'individual',
        subscription_status: 'free',
        credits_remaining: 10,
        preferences: {}
      }

      const mockAuthResponse = {
        user: mockUser,
        token: 'mock-jwt-token'
      }

      mockApiService.register.mockResolvedValueOnce(mockAuthResponse)

      const { result } = renderHook(() => useAuthStore())

      const registerData: UserRegistrationRequest = {
        email: 'newuser@example.com',
        password: 'password123',
        australian_state: 'NSW',
        user_type: 'individual'
      }

      await act(async () => {
        await result.current.register(registerData)
      })

      expect(mockApiService.register).toHaveBeenCalledWith(registerData)
      expect(mockApiService.setToken).toHaveBeenCalledWith('mock-jwt-token')
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.error).toBeNull()
    })

    it('should handle registration error', async () => {
      const errorMessage = 'Email already exists'
      mockApiService.register.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHook(() => useAuthStore())

      const registerData: UserRegistrationRequest = {
        email: 'existing@example.com',
        password: 'password123',
        australian_state: 'NSW',
        user_type: 'individual'
      }

      await act(async () => {
        try {
          await result.current.register(registerData)
        } catch (error) {
          // Expected to throw
        }
      })

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.error).toBe(errorMessage)
    })
  })

  describe('Logout', () => {
    it('should logout and clear user data', async () => {
      const { result } = renderHook(() => useAuthStore())

      // Set initial authenticated state
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            australian_state: 'NSW',
            user_type: 'individual',
            subscription_status: 'premium',
            credits_remaining: 100,
            preferences: {}
          },
          isAuthenticated: true
        })
      })

      act(() => {
        result.current.logout()
      })

      expect(mockApiService.clearToken).toHaveBeenCalled()
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.error).toBeNull()
    })
  })

  describe('Update User', () => {
    it('should update user data', () => {
      const { result } = renderHook(() => useAuthStore())

      // Set initial user
      const initialUser: User = {
        id: '1',
        email: 'test@example.com',
        australian_state: 'NSW',
        user_type: 'individual',
        subscription_status: 'free',
        credits_remaining: 10,
        preferences: {}
      }

      act(() => {
        useAuthStore.setState({ user: initialUser, isAuthenticated: true })
      })

      // Update user
      const updates = { 
        subscription_status: 'premium' as const, 
        credits_remaining: 100 
      }

      act(() => {
        result.current.updateUser(updates)
      })

      expect(result.current.user).toEqual({
        ...initialUser,
        ...updates
      })
    })

    it('should handle update when no user exists', () => {
      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.updateUser({ subscription_status: 'premium' })
      })

      expect(result.current.user).toBeNull()
    })
  })

  describe('Update Profile', () => {
    it('should update user profile successfully', async () => {
      const mockUpdatedUser: User = {
        id: '1',
        email: 'test@example.com',
        australian_state: 'VIC',
        user_type: 'individual',
        subscription_status: 'premium',
        credits_remaining: 100,
        preferences: { theme: 'dark' }
      }

      mockApiService.updateUserProfile.mockResolvedValueOnce(mockUpdatedUser)
      mockApiService.getCurrentUser.mockResolvedValueOnce(mockUpdatedUser)

      const { result } = renderHook(() => useAuthStore())

      // Set initial authenticated state
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            australian_state: 'NSW',
            user_type: 'individual',
            subscription_status: 'premium',
            credits_remaining: 100,
            preferences: {}
          },
          isAuthenticated: true
        })
      })

      const updateData = { 
        australian_state: 'VIC' as const, 
        preferences: { theme: 'dark' } 
      }

      await act(async () => {
        await result.current.updateProfile(updateData)
      })

      expect(mockApiService.updateUserProfile).toHaveBeenCalledWith(updateData)
      expect(mockApiService.getCurrentUser).toHaveBeenCalled()
      expect(result.current.user).toEqual(mockUpdatedUser)
    })

    it('should handle profile update error', async () => {
      const errorMessage = 'Update failed'
      mockApiService.updateUserProfile.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHook(() => useAuthStore())

      // Set initial authenticated state
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            australian_state: 'NSW',
            user_type: 'individual',
            subscription_status: 'premium',
            credits_remaining: 100,
            preferences: {}
          },
          isAuthenticated: true
        })
      })

      await act(async () => {
        try {
          await result.current.updateProfile({ australian_state: 'VIC' })
        } catch (error) {
          // Expected to throw
        }
      })

      expect(result.current.error).toBe(errorMessage)
    })
  })

  describe('Refresh User', () => {
    it('should refresh user data successfully', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        australian_state: 'NSW',
        user_type: 'individual',
        subscription_status: 'premium',
        credits_remaining: 90,
        preferences: {}
      }

      mockApiService.getCurrentUser.mockResolvedValueOnce(mockUser)

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        await result.current.refreshUser()
      })

      expect(mockApiService.getCurrentUser).toHaveBeenCalled()
      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })

    it('should handle refresh error', async () => {
      const errorMessage = 'Failed to refresh user'
      mockApiService.getCurrentUser.mockRejectedValueOnce(new Error(errorMessage))

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        try {
          await result.current.refreshUser()
        } catch (error) {
          // Expected to throw
        }
      })

      expect(result.current.error).toBe(errorMessage)
    })
  })

  describe('Clear Error', () => {
    it('should clear error state', () => {
      const { result } = renderHook(() => useAuthStore())

      // Set error state
      act(() => {
        useAuthStore.setState({ error: 'Some error' })
      })

      expect(result.current.error).toBe('Some error')

      // Clear error
      act(() => {
        result.current.clearError()
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('Initialize Auth', () => {
    it('should initialize auth and refresh user if token exists', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        australian_state: 'NSW',
        user_type: 'individual',
        subscription_status: 'premium',
        credits_remaining: 100,
        preferences: {}
      }

      // Mock token exists
      vi.stubGlobal('localStorage', {
        getItem: vi.fn().mockReturnValue('{"state":{"user":null,"token":"existing-token"}}'),
        setItem: vi.fn(),
        removeItem: vi.fn()
      })

      mockApiService.getCurrentUser.mockResolvedValueOnce(mockUser)

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        result.current.initializeAuth()
        // Allow any pending promises to resolve
        await new Promise(resolve => setTimeout(resolve, 0))
      })

      expect(result.current.user).toEqual(mockUser)
      expect(result.current.isAuthenticated).toBe(true)
    })
  })
})