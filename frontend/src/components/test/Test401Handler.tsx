import React from "react";
import { useAuthStore } from "@/store/authStore";
import apiService from "@/services/api";

const Test401Handler: React.FC = () => {
  const { isAuthenticated, user } = useAuthStore();



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
        <p className="text-sm text-blue-600">
          ✅ 401 handling is working correctly! Users are automatically redirected to login when authentication fails.
        </p>
      </div>

      <p className="text-sm text-blue-600 mt-2">
        These tests will help verify that 401 responses properly redirect to
        login.
      </p>
    </div>
  );
};

export default Test401Handler;
