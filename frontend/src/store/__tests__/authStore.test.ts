import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useAuthStore } from "../authStore";
import { apiService } from "@/services/api";
import type {
  AuthResponse,
  User,
  UserLoginRequest,
  UserRegistrationRequest,
} from "@/types";

// Mock API service
vi.mock("@/services/api", () => ({
  apiService: {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    updateProfile: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
  },
}));

const mockApiService = vi.mocked(apiService);

describe("AuthStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state before each test
    useAuthStore.getState().logout();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Initial State", () => {
    it("should have correct initial state", () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe("Login", () => {
    it("should login successfully", async () => {
      const mockUser: User = {
        id: "1",
        email: "test@example.com",
        australian_state: "NSW",
        user_type: "buyer",
        subscription_status: "premium",
        credits_remaining: 100,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      };

      const mockAuthResponse: AuthResponse = {
        access_token: "mock-jwt-token",
        refresh_token: "mock-refresh-token",
        user_profile: mockUser,
      };

      mockApiService.login.mockResolvedValueOnce(mockAuthResponse);

      const { result } = renderHook(() => useAuthStore());

      const loginData: UserLoginRequest = {
        email: "test@example.com",
        password: "password123",
      };

      await act(async () => {
        await result.current.login(loginData);
      });

      expect(mockApiService.login).toHaveBeenCalledWith(loginData);
      expect(mockApiService.setToken).toHaveBeenCalledWith("mock-jwt-token");
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should handle login error", async () => {
      const errorMessage = "Invalid credentials";
      const loginPromise = Promise.reject(new Error(errorMessage));
      mockApiService.login.mockReturnValueOnce(loginPromise);

      const { result } = renderHook(() => useAuthStore());

      const loginData: UserLoginRequest = {
        email: "test@example.com",
        password: "wrongpassword",
      };

      await act(async () => {
        try {
          await result.current.login(loginData);
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeTruthy();
    });
  });

  describe("Register", () => {
    it("should register successfully", async () => {
      const mockUser: User = {
        id: "1",
        email: "test@example.com",
        australian_state: "NSW",
        user_type: "buyer",
        subscription_status: "free",
        credits_remaining: 1,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      };

      const mockAuthResponse: AuthResponse = {
        access_token: "mock-jwt-token",
        refresh_token: "mock-refresh-token",
        user_profile: mockUser,
      };

      mockApiService.register.mockResolvedValueOnce(mockAuthResponse);

      const { result } = renderHook(() => useAuthStore());

      const registerData: UserRegistrationRequest = {
        email: "test@example.com",
        password: "password123",
        australian_state: "NSW",
        user_type: "buyer",
      };

      await act(async () => {
        await result.current.register(registerData);
      });

      expect(mockApiService.register).toHaveBeenCalledWith(registerData);
      expect(mockApiService.setToken).toHaveBeenCalledWith("mock-jwt-token");
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should handle registration error", async () => {
      const errorMessage = "Email already exists";
      mockApiService.register.mockRejectedValueOnce(new Error(errorMessage));

      const { result } = renderHook(() => useAuthStore());

      const registerData: UserRegistrationRequest = {
        email: "existing@example.com",
        password: "password123",
        australian_state: "NSW",
        user_type: "buyer",
      };

      await act(async () => {
        try {
          await result.current.register(registerData);
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeTruthy();
    });
  });

  describe("Logout", () => {
    it("should logout successfully", () => {
      const { result } = renderHook(() => useAuthStore());

      // First, set up a logged-in state
      act(() => {
        result.current.updateUser({
          id: "1",
          email: "test@example.com",
          australian_state: "NSW",
          user_type: "buyer",
          subscription_status: "premium",
          credits_remaining: 100,
          preferences: {},
          onboarding_completed: false,
        });
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Then logout
      act(() => {
        result.current.logout();
      });

      expect(mockApiService.clearToken).toHaveBeenCalled();
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe("Update Profile", () => {
    it("should update profile successfully", async () => {
      const mockUser: User = {
        id: "1",
        email: "test@example.com",
        australian_state: "NSW",
        user_type: "buyer",
        subscription_status: "premium",
        credits_remaining: 100,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      };

      const mockUpdatedUser: User = {
        ...mockUser,
        full_name: "John Doe",
        phone_number: "1234567890",
      };

      mockApiService.updateProfile.mockResolvedValueOnce(mockUpdatedUser);

      const { result } = renderHook(() => useAuthStore());

      // Set up initial user state
      act(() => {
        result.current.updateUser(mockUser);
      });

      const updateData = {
        full_name: "John Doe",
        phone_number: "1234567890",
      };

      await act(async () => {
        await result.current.updateProfile(updateData);
      });

      expect(mockApiService.updateProfile).toHaveBeenCalledWith(updateData);
      expect(result.current.user).toEqual(mockUpdatedUser);
    });

    it("should handle profile update error", async () => {
      const errorMessage = "Failed to update profile";
      mockApiService.updateProfile.mockRejectedValueOnce(
        new Error(errorMessage),
      );

      const { result } = renderHook(() => useAuthStore());

      // Set up initial user state
      act(() => {
        result.current.updateUser({
          id: "1",
          email: "test@example.com",
          australian_state: "NSW",
          user_type: "buyer",
          subscription_status: "premium",
          credits_remaining: 100,
          preferences: {},
          onboarding_completed: false,
        });
      });

      const updateData = {
        full_name: "John Doe",
      };

      await act(async () => {
        try {
          await result.current.updateProfile(updateData);
        } catch (error) {
          // Expected to throw
        }
      });

      expect(mockApiService.updateProfile).toHaveBeenCalledWith(updateData);
      // User should remain unchanged on error
      expect(result.current.user?.full_name).toBeUndefined();
    });
  });

  describe("Clear Error", () => {
    it("should clear error", () => {
      const { result } = renderHook(() => useAuthStore());

      // Set an error first
      act(() => {
        result.current.updateUser({
          id: "1",
          email: "test@example.com",
          australian_state: "NSW",
          user_type: "buyer",
          subscription_status: "premium",
          credits_remaining: 100,
          preferences: {},
          onboarding_completed: false,
        });
      });

      // Simulate an error state
      act(() => {
        // This would normally be set by a failed login/register
        useAuthStore.setState({ error: "Test error" });
      });

      expect(result.current.error).toBe("Test error");

      // Clear the error
      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("Refresh User", () => {
    it("should refresh user successfully", async () => {
      const mockUser: User = {
        id: "1",
        email: "test@example.com",
        australian_state: "NSW",
        user_type: "buyer",
        subscription_status: "premium",
        credits_remaining: 100,
        preferences: {},
        onboarding_completed: false,
        onboarding_preferences: {}
      };

      mockApiService.getCurrentUser.mockResolvedValueOnce(mockUser);

      const { result } = renderHook(() => useAuthStore());

      // Set up authenticated state
      act(() => {
        useAuthStore.setState({
          user: mockUser,
          isAuthenticated: true,
        });
      });

      await act(async () => {
        await result.current.refreshUser();
      });

      expect(mockApiService.getCurrentUser).toHaveBeenCalled();
      expect(result.current.user).toEqual(mockUser);
    });
  });
});
