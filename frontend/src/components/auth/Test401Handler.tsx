import React from "react";
import { apiService } from "@/services/api";

const Test401Handler: React.FC = () => {
  const test401Response = async () => {
    try {
      console.log("🧪 Testing 401 response...");
      // Make a call to a non-existent endpoint to trigger 401
      await apiService.client.get("/api/non-existent-endpoint");
    } catch (error: any) {
      console.log("🧪 401 test result:", error.response?.status, error.message);
    }
  };

  const testBackendTokenExpiry = async () => {
    try {
      console.log("🧪 Testing backend token expiry...");
      // Clear tokens to simulate expiry
      apiService.clearTokens();
      await apiService.getOnboardingStatus();
    } catch (error: any) {
      console.log(
        "🧪 Token expiry test result:",
        error.response?.status,
        error.message
      );
    }
  };

  const test403Response = async () => {
    try {
      console.log("🧪 Testing 403 response...");
      // Make a call to an endpoint that might return 403
      await apiService.client.get("/api/users/onboarding/status");
    } catch (error: any) {
      console.log("🧪 403 test result:", error.response?.status, error.message);
      if (error.response?.status === 403) {
        console.log("🚨 403 detected - should redirect to login");
      }
    }
  };

  const test401HandlingDirectly = () => {
    console.log("🧪 Testing 401 handling directly...");
    // @ts-ignore - accessing private method for testing
    apiService.handleUnauthorized();
  };

  const testInterceptors = async () => {
    try {
      console.log("🧪 Testing interceptors...");
      const token = localStorage.getItem("auth_token");
      console.log(
        "🧪 Current token:",
        token ? `${token.substring(0, 20)}...` : "None"
      );

      // Test if interceptors are working
      await apiService.client.get("/api/test-interceptor");
    } catch (error: any) {
      console.log(
        "🧪 Interceptor test result:",
        error.response?.status,
        error.message
      );
    }
  };

  return (
    <div className="p-4 border rounded-lg bg-gray-50">
      <h3 className="text-lg font-semibold mb-4">🔧 Auth Debug Tools</h3>
      <div className="space-y-2">
        <button
          onClick={test401Response}
          className="px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          Test 401 Response
        </button>
        <button
          onClick={testBackendTokenExpiry}
          className="px-3 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
        >
          Test Backend Token Expiry
        </button>
        <button
          onClick={test403Response}
          className="px-3 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
        >
          Test 403 Response
        </button>
        <button
          onClick={test401HandlingDirectly}
          className="px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Test 401 Handling Directly
        </button>
        <button
          onClick={testInterceptors}
          className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Test Interceptors
        </button>
      </div>
      <p className="text-sm text-gray-600 mt-4">
        Check browser console for test results. These tests help debug
        authentication issues.
      </p>
    </div>
  );
};

export default Test401Handler;
