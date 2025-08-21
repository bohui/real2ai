import React from "react";
import { useAuthStore } from "@/store/authStore";
import apiService from "@/services/api";

const Test401Handler: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();

  const test401Response = async () => {
    try {
      // Make a request to an endpoint that will return 401
      // This simulates what happens when a token expires
      await apiService.client.get("/test-401-endpoint");
    } catch (error: any) {
      if (error.response?.status === 401) {
        console.log("✅ 401 response properly caught and handled");
      } else {
        console.log("❌ Unexpected error:", error);
      }
    }
  };

  const test401Handling = () => {
    // Test the 401 handling directly
    apiService.test401Handling();
  };

  const testInterceptors = () => {
    // Test if interceptors are working
    apiService.testInterceptors();
  };

  const testBackendTokenExpiry = () => {
    // Simulate backend token expiry by clearing tokens
    apiService.clearTokens();
    console.log("✅ Tokens cleared, should redirect to login");
  };

  if (!isAuthenticated) {
    return (
      <div className="p-4 bg-yellow-100 border border-yellow-400 rounded">
        <h3 className="font-bold text-yellow-800">Test 401 Handler</h3>
        <p className="text-yellow-700">
          Not authenticated - this component is working correctly!
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-blue-100 border border-blue-400 rounded">
      <h3 className="font-bold text-blue-800">Test 401 Handler</h3>
      <p className="text-blue-700 mb-4">
        Current user: {user?.email || "Unknown"}
      </p>

      <div className="space-y-2">
        <button
          onClick={test401Response}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
          Test 401 Response (API Call)
        </button>

        <button
          onClick={testBackendTokenExpiry}
          className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
        >
          Test Backend Token Expiry
        </button>

        <button
          onClick={test401Handling}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
        >
          Test 401 Handling Directly
        </button>

        <button
          onClick={testInterceptors}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Test Interceptors
        </button>
      </div>

      <p className="text-sm text-blue-600 mt-2">
        These tests will help verify that 401 responses properly redirect to
        login.
      </p>
    </div>
  );
};

export default Test401Handler;
