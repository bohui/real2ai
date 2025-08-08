import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  History,
  Settings,
  Upload,
  BarChart3,
  Zap,
  HelpCircle,
  Building,
  TrendingUp,
  Calculator,
} from "lucide-react";
import { motion } from "framer-motion";

import { useAnalysisStore } from "@/store/analysisStore";
import { cn } from "@/utils";

const Sidebar: React.FC = () => {
  const location = useLocation();
  const { recentAnalyses, isAnalyzing } = useAnalysisStore();

  const navigation = [
    {
      name: "Dashboard",
      href: "/app/dashboard",
      icon: LayoutDashboard,
      current: location.pathname === "/app/dashboard",
    },
    {
      name: "New Analysis",
      href: "/app/analysis",
      icon: Upload,
      current: location.pathname === "/app/analysis",
      badge: isAnalyzing ? "Active" : null,
    },
    {
      name: "Analysis History",
      href: "/app/history",
      icon: History,
      current: location.pathname === "/app/history",
      badge: recentAnalyses.length > 0 ? recentAnalyses.length : null,
    },
    {
      name: "Reports",
      href: "/app/reports",
      icon: BarChart3,
      current: location.pathname === "/app/reports",
    },
    {
      name: "Property Intelligence",
      href: "/app/property-intelligence",
      icon: Building,
      current: location.pathname === "/app/property-intelligence",
      badge: "NEW",
    },
    {
      name: "Market Analysis",
      href: "/app/market-analysis",
      icon: TrendingUp,
      current: location.pathname === "/app/market-analysis",
      badge: "NEW",
    },
    {
      name: "Financial Analysis",
      href: "/app/financial-analysis",
      icon: Calculator,
      current: location.pathname === "/app/financial-analysis",
      badge: "NEW",
    },
    {
      name: "Settings",
      href: "/app/settings",
      icon: Settings,
      current: location.pathname === "/app/settings",
    },
  ];

  const quickActions = [
    {
      name: "Help & Support",
      href: "/help",
      icon: HelpCircle,
    },
  ];

  return (
    <div className="flex flex-col h-full bg-white border-r border-neutral-200">
      {/* Logo */}
      <div className="flex items-center gap-3 p-6 border-b border-neutral-200">
        <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center">
          <Zap className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-neutral-900">Real2.AI</h1>
          <p className="text-xs text-neutral-500">Property & Contract AI</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        {navigation.map((item) => {
          const IconComponent = item.icon;

          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                "group flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200",
                item.current
                  ? "bg-primary-50 text-primary-700 border border-primary-200"
                  : "text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50"
              )}
              aria-current={item.current ? "page" : undefined}
            >
              <div className="flex items-center gap-3">
                <IconComponent
                  className={cn(
                    "w-5 h-5",
                    item.current
                      ? "text-primary-600"
                      : "text-neutral-400 group-hover:text-neutral-600"
                  )}
                />
                <span>{item.name}</span>
              </div>

              {item.badge && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className={cn(
                    "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
                    item.name === "New Analysis" && isAnalyzing
                      ? "bg-success-100 text-success-700"
                      : item.badge === "NEW"
                      ? "bg-accent-100 text-accent-700"
                      : item.current
                      ? "bg-primary-100 text-primary-700"
                      : "bg-neutral-100 text-neutral-600"
                  )}
                >
                  {item.badge}
                </motion.span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Recent Analyses */}
      {recentAnalyses.length > 0 && (
        <div className="px-4 py-4 border-t border-neutral-200">
          <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">
            Recent Analyses
          </h3>
          <div className="space-y-2">
            {recentAnalyses.slice(0, 3).map((analysis) => {
              // Safely get risk score from either executive_summary or risk_assessment
              const riskScore =
                analysis.executive_summary?.overall_risk_score ??
                analysis.risk_assessment?.overall_risk_score ??
                0;

              return (
                <Link
                  key={analysis.contract_id}
                  to={`/app/analysis/${analysis.contract_id}`}
                  className="block p-2 rounded-lg hover:bg-neutral-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-neutral-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-neutral-900 truncate">
                        Contract Analysis
                      </p>
                      <p className="text-xs text-neutral-500">
                        {new Date(
                          analysis.analysis_timestamp
                        ).toLocaleDateString()}
                      </p>
                    </div>
                    <div
                      className={cn(
                        "w-2 h-2 rounded-full",
                        riskScore >= 7
                          ? "bg-danger-500"
                          : riskScore >= 5
                          ? "bg-warning-500"
                          : "bg-success-500"
                      )}
                    />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="px-4 py-4 border-t border-neutral-200">
        <div className="space-y-2">
          {quickActions.map((item) => {
            const IconComponent = item.icon;

            return (
              <Link
                key={item.name}
                to={item.href}
                className="group flex items-center gap-3 px-3 py-2 text-sm font-medium text-neutral-600 rounded-lg hover:text-neutral-900 hover:bg-neutral-50 transition-colors"
              >
                <IconComponent className="w-4 h-4 text-neutral-400 group-hover:text-neutral-600" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
