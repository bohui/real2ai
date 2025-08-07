import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  TrendingUp,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle,
  DollarSign,
  Calendar,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import StatusBadge from "@/components/ui/StatusBadge";
import EnhancedContractCard from "@/components/analysis/EnhancedContractCard";
import { useAnalysisStore } from "@/store/analysisStore";
import { useAuthStore } from "@/store/authStore";
import { useUIStore } from "@/store/uiStore";
import { usePageSEO } from "@/contexts/SEOContext";
import { cn } from "@/utils";

const DashboardPage: React.FC = () => {
  const { recentAnalyses } = useAnalysisStore();
  const { user } = useAuthStore();
  const { showOnboarding } = useUIStore();

  // SEO for Dashboard page
  usePageSEO({
    title: 'Dashboard - Real2AI',
    description: 'Your Real2AI dashboard - manage contract analyses, view property intelligence reports, and track your real estate portfolio performance.',
    keywords: [
      'Real2AI dashboard',
      'contract analysis dashboard',
      'property reports',
      'AI insights',
      'real estate management'
    ],
    canonical: '/app/dashboard',
    noIndex: true // Private dashboard
  });

  // If onboarding is required, show a minimal loading state
  // The onboarding wizard will be rendered by the App component
  if (showOnboarding) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-neutral-600">Setting up your account...</p>
        </div>
      </div>
    );
  }

  // Calculate dashboard stats
  const totalAnalyses = recentAnalyses.length;
  const highRiskCount = recentAnalyses.filter(
    (a) => a.executive_summary.overall_risk_score >= 7
  ).length;

  // Calculate best value properties
  const bestValueProperties = recentAnalyses
    .filter((analysis) => {
      // Only include completed analyses with property data
      return (
        analysis.analysis_status === "completed" &&
        analysis.contract_terms?.property_address &&
        analysis.executive_summary?.overall_risk_score !== undefined
      );
    })
    .map((analysis) => {
      const riskScore = analysis.executive_summary.overall_risk_score;
      const propertyAddress = analysis.contract_terms.property_address;
      const purchasePrice =
        analysis.contract_terms?.financial_terms?.purchase_price;
      const marketValue =
        analysis.contract_terms?.property_details?.market_value;

      // Calculate value score (lower risk = better value, higher price-to-value ratio = better value)
      let valueScore = 0;

      // Risk factor (lower is better) - 40% weight
      const riskFactor = Math.max(0, 10 - riskScore) / 10;
      valueScore += riskFactor * 0.4;

      // Price-to-value ratio (if available) - 30% weight
      if (purchasePrice && marketValue && marketValue > 0) {
        const priceToValueRatio = purchasePrice / marketValue;
        const valueRatio = priceToValueRatio < 1 ? 1 - priceToValueRatio : 0; // Better if purchase price < market value
        valueScore += valueRatio * 0.3;
      }

      // Market trend factor (based on risk assessment) - 30% weight
      const marketTrendFactor = riskScore < 5 ? 1 : riskScore < 7 ? 0.5 : 0;
      valueScore += marketTrendFactor * 0.3;

      return {
        address: propertyAddress,
        riskScore,
        purchasePrice,
        marketValue,
        valueScore,
        analysis,
      };
    })
    .sort((a, b) => b.valueScore - a.valueScore)
    .slice(0, 3); // Top 3 best value properties

  // Calculate minimal risk properties (properties with lowest risk scores)
  const minimalRiskProperties = recentAnalyses
    .filter((analysis) => {
      return (
        analysis.analysis_status === "completed" &&
        analysis.contract_terms?.property_address &&
        analysis.executive_summary?.overall_risk_score !== undefined
      );
    })
    .map((analysis) => ({
      address: analysis.contract_terms.property_address,
      riskScore: analysis.executive_summary.overall_risk_score,
      analysis,
    }))
    .sort((a, b) => a.riskScore - b.riskScore) // Sort by lowest risk first
    .slice(0, 3);

  const minimalRiskCount = minimalRiskProperties.length;
  const averageMinimalRiskScore =
    minimalRiskProperties.length > 0
      ? minimalRiskProperties.reduce((sum, p) => sum + p.riskScore, 0) /
        minimalRiskProperties.length
      : 0;

  const stats = [
    {
      title: "Total Contract Analyses",
      value: totalAnalyses,
      change: "+12%",
      trend: "up",
      icon: FileText,
      color: "primary",
    },
    {
      title: "Minimal Risk Properties",
      value: minimalRiskCount,
      change:
        minimalRiskProperties.length > 0
          ? minimalRiskProperties[0].address.split(",")[0]
          : "0",
      trend:
        averageMinimalRiskScore < 3
          ? "up"
          : averageMinimalRiskScore < 5
          ? "neutral"
          : "down",
      icon: TrendingUp,
      color: "success",
      subtitle:
        minimalRiskProperties.length > 0
          ? `Avg Risk: ${averageMinimalRiskScore.toFixed(1)}/10`
          : "vs last month",
    },
    {
      title: "High Risk Contracts",
      value: highRiskCount,
      change: "-2",
      trend: "down",
      icon: AlertTriangle,
      color: "warning",
    },
    {
      title: "Credits Remaining",
      value: user?.credits_remaining || 0,
      change:
        user?.subscription_status === "premium" ||
        user?.subscription_status === "enterprise"
          ? "Unlimited"
          : "Limited",
      trend: "neutral",
      icon: DollarSign,
      color: "primary",
    },
  ];

  const quickActions = [
    {
      title: "New Analysis",
      description: "Upload and analyze a new contract",
      href: "/app/analysis",
      icon: FileText,
      color: "primary",
    },
    {
      title: "View History",
      description: "Browse your previous analyses",
      href: "/app/history",
      icon: Clock,
      color: "secondary",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Welcome Header */}
      <Card variant="premium" gradient className="mb-8">
        <CardContent padding="xl">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-heading font-bold text-neutral-900 mb-2">
                Welcome back, {user?.email.split("@")[0]}
              </h1>
              <p className="text-lg text-neutral-600 mb-4">
                Here's what's happening with your contract analyses
              </p>
              <div className="flex items-center gap-3">
                <StatusBadge
                  status={
                    user?.subscription_status === "premium"
                      ? "premium"
                      : "verified"
                  }
                  size="sm"
                  variant="outline"
                  label={
                    user?.subscription_status === "premium"
                      ? "Premium Account"
                      : "Standard Account"
                  }
                />
                <StatusBadge
                  status="verified"
                  size="sm"
                  variant="dot"
                  label="Australian Legal Compliance"
                />
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-6">
              <div className="text-right">
                <div className="text-sm text-neutral-500 mb-1">Last login</div>
                <div className="font-semibold text-neutral-900">
                  {new Date().toLocaleDateString("en-AU")}
                </div>
                <div className="text-xs text-neutral-500">
                  {new Date().toLocaleTimeString("en-AU", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-trust-500 rounded-full flex items-center justify-center text-white font-bold text-xl">
                {user?.email.charAt(0).toUpperCase()}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => {
          const IconComponent = stat.icon;

          return (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Card
                variant="elevated"
                interactive
                className="hover:shadow-xl group transition-all duration-300"
                title={
                  stat.title === "Best Value Properties" &&
                  bestValueProperties.length > 0
                    ? `Top properties: ${bestValueProperties
                        .map((p) => p.address.split(",")[0])
                        .join(", ")}`
                    : undefined
                }
              >
                <CardContent padding="lg">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-neutral-500 uppercase tracking-wide mb-2">
                        {stat.title}
                      </p>
                      <p className="text-3xl font-heading font-bold text-neutral-900 mb-3">
                        {stat.value}
                      </p>
                      <div className="flex items-center">
                        <span
                          className={cn(
                            "text-sm font-semibold px-2 py-1 rounded-full",
                            stat.trend === "up"
                              ? "text-success-700 bg-success-100"
                              : stat.trend === "down"
                              ? "text-danger-700 bg-danger-100"
                              : "text-neutral-700 bg-neutral-100"
                          )}
                        >
                          {stat.change}
                        </span>
                        <span className="text-neutral-500 text-xs ml-2">
                          {stat.subtitle || "vs last month"}
                        </span>
                      </div>
                    </div>
                    <div
                      className={cn(
                        "w-16 h-16 rounded-xl flex items-center justify-center shadow-soft group-hover:shadow-lg transition-all duration-300",
                        stat.color === "primary"
                          ? "bg-gradient-to-br from-primary-100 to-primary-200"
                          : stat.color === "success"
                          ? "bg-gradient-to-br from-success-100 to-success-200"
                          : stat.color === "warning"
                          ? "bg-gradient-to-br from-warning-100 to-warning-200"
                          : "bg-gradient-to-br from-secondary-100 to-secondary-200"
                      )}
                    >
                      <IconComponent
                        className={cn(
                          "w-8 h-8 group-hover:scale-110 transition-transform duration-300",
                          stat.color === "primary"
                            ? "text-primary-600"
                            : stat.color === "success"
                            ? "text-success-600"
                            : stat.color === "warning"
                            ? "text-warning-600"
                            : "text-secondary-600"
                        )}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Actions */}
        <div className="lg:col-span-1">
          <Card variant="elevated" className="h-fit">
            <CardHeader padding="lg">
              <CardTitle className="text-xl font-heading font-semibold">
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent padding="none">
              <div className="space-y-1">
                {quickActions.map((action) => {
                  const IconComponent = action.icon;

                  return (
                    <Link
                      key={action.title}
                      to={action.href}
                      className="block mx-6 mb-6 last:mb-0 p-4 rounded-xl border-2 border-neutral-100 hover:border-primary-300 hover:bg-gradient-to-r hover:from-primary-50 hover:to-transparent transition-all duration-200 group hover:shadow-soft"
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={cn(
                            "w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-200 shadow-soft",
                            action.color === "primary"
                              ? "bg-gradient-to-br from-primary-100 to-primary-200 text-primary-600 group-hover:from-primary-200 group-hover:to-primary-300"
                              : "bg-gradient-to-br from-secondary-100 to-secondary-200 text-secondary-600 group-hover:from-secondary-200 group-hover:to-secondary-300"
                          )}
                        >
                          <IconComponent className="w-6 h-6 group-hover:scale-110 transition-transform duration-200" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-neutral-900 group-hover:text-primary-700 transition-colors mb-1">
                            {action.title}
                          </h3>
                          <p className="text-sm text-neutral-600">
                            {action.description}
                          </p>
                        </div>
                        <ArrowRight className="w-5 h-5 text-neutral-400 group-hover:text-primary-600 group-hover:translate-x-1 transition-all duration-200" />
                      </div>
                    </Link>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Analyses */}
        <div className="lg:col-span-2">
          <Card variant="elevated">
            <CardHeader padding="lg">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl font-heading font-semibold">
                  Recent Contract Analyses
                </CardTitle>
                <Link to="/app/history">
                  <Button
                    variant="outline"
                    size="sm"
                    className="group flex items-center gap-2 whitespace-nowrap"
                  >
                    <span>View all analyses</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent padding="lg">
              {recentAnalyses.length > 0 ? (
                <div className="space-y-4">
                  {recentAnalyses.slice(0, 3).map((analysis) => (
                    <EnhancedContractCard
                      key={analysis.contract_id}
                      analysis={analysis}
                      showDetails={false}
                    />
                  ))}
                </div>
              ) : (
                <Card variant="glass" className="text-center py-16">
                  <div className="w-24 h-24 bg-gradient-to-br from-primary-100 to-trust-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-large">
                    <FileText className="w-12 h-12 text-primary-600" />
                  </div>
                  <h3 className="text-2xl font-heading font-bold text-neutral-900 mb-3">
                    Welcome to Real2.AI
                  </h3>
                  <p className="text-lg text-neutral-600 mb-8 max-w-lg mx-auto">
                    Upload your first contract to experience AI-powered analysis
                    tailored for Australian legal professionals
                  </p>
                  <div className="max-w-sm mx-auto">
                    <Link to="/app/analysis" className="block mb-4">
                      <Button
                        variant="primary"
                        size="lg"
                        gradient
                        elevated
                        fullWidth
                        className="group flex items-center gap-2"
                      >
                        <span>Upload Your First Contract</span>
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                      </Button>
                    </Link>
                    <div className="flex items-center justify-center gap-4 text-sm text-neutral-500">
                      <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        <span>2-3 minutes</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CheckCircle className="w-4 h-4" />
                        <span>Australian Law</span>
                      </div>
                    </div>
                  </div>
                </Card>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Australian Legal Market Insights */}
      <Card variant="premium" gradient className="overflow-hidden">
        <CardHeader padding="lg">
          <CardTitle className="flex items-center gap-3 text-xl font-heading font-semibold">
            <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <Calendar className="w-6 h-6 text-neutral-700" />
            </div>
            Australian Legal Market Insights
          </CardTitle>
        </CardHeader>
        <CardContent padding="lg">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <TrendingUp className="w-8 h-8 text-primary-600" />
              </div>
              <div className="text-3xl font-heading font-bold text-primary-600 mb-2">
                2.1%
              </div>
              <div className="font-medium text-neutral-700 mb-1">
                Interest Rate Change
              </div>
              <div className="text-xs text-neutral-500">RBA Cash Rate</div>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-success-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <DollarSign className="w-8 h-8 text-success-600" />
              </div>
              <div className="text-3xl font-heading font-bold text-success-600 mb-2">
                +5.2%
              </div>
              <div className="font-medium text-neutral-700 mb-1">
                Property Value Growth
              </div>
              <div className="text-xs text-neutral-500">National Average</div>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-warning-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <Calendar className="w-8 h-8 text-warning-600" />
              </div>
              <div className="text-3xl font-heading font-bold text-warning-600 mb-2">
                28 days
              </div>
              <div className="font-medium text-neutral-700 mb-1">
                Settlement Period
              </div>
              <div className="text-xs text-neutral-500">Average</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DashboardPage;
