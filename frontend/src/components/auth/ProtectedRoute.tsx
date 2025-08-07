import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
  fallbackPath?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  fallbackPath = "/auth/login",
}) => {
  const { isAuthenticated, user } = useAuthStore();
  const { showOnboarding } = useUIStore();
  const location = useLocation();

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return (
      <Navigate to={fallbackPath} state={{ from: location.pathname }} replace />
    );
  }

  // Check role-based access if required
  if (requiredRole && user.user_type !== requiredRole) {
    return <Navigate to="/app/dashboard" replace />;
  }

  // If onboarding is required and user is trying to access dashboard,
  // let the onboarding wizard handle the flow
  if (showOnboarding && location.pathname === "/app/dashboard") {
    return <>{children}</>;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
