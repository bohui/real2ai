import React from "react";
import { Link, Navigate } from "react-router-dom";
import { motion } from "framer-motion";

import RegisterForm from "@/components/forms/RegisterForm";
import { useAuthStore } from "@/store/authStore";
import { usePageSEO } from "@/contexts/SEOContext";

const RegisterPage: React.FC = () => {
  const { isAuthenticated } = useAuthStore();

  // SEO for Register page
  usePageSEO({
    title: "Register - Real2AI",
    description:
      "Create your Real2AI account and start analyzing real estate contracts with AI technology. Join thousands of Australian property professionals.",
    keywords: [
      "Real2AI register",
      "sign up",
      "create account",
      "real estate AI",
    ],
    canonical: "/auth/register",
    ogTitle: "Join Real2AI - Start Your AI-Powered Real Estate Journey",
    ogDescription:
      "Create your account and access advanced real estate analysis tools trusted by Australian professionals.",
  });

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full space-y-8"
      >
        {/* Header */}
        <div className="text-center">
          <div className="flex justify-center">
            <img
              src="/logo.svg"
              alt="Real2.AI logo"
              className="w-16 h-16 mb-6"
            />
          </div>
          <h2 className="text-3xl font-bold text-neutral-900">Join Real2.AI</h2>
          <p className="mt-2 text-neutral-600">
            Create your account to start analyzing contracts
          </p>
        </div>

        {/* Register Form */}
        <RegisterForm />

        {/* Footer */}
        <div className="text-center">
          <p className="text-sm text-neutral-600">
            Already have an account?{" "}
            <Link
              to="/auth/login"
              className="font-medium text-primary-600 hover:text-primary-500 transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>

        {/* Features */}
        <div className="mt-8 space-y-4">
          <h3 className="text-sm font-semibold text-neutral-900 text-center">
            What you'll get:
          </h3>
          <div className="space-y-2">
            {[
              "AI-powered contract analysis",
              "Australian legal compliance checks",
              "Risk assessment and recommendations",
              "Secure document processing",
              "Professional reporting",
            ].map((feature, index) => (
              <div
                key={index}
                className="flex items-center text-sm text-neutral-600"
              >
                <div className="w-2 h-2 bg-primary-600 rounded-full mr-3" />
                {feature}
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default RegisterPage;
