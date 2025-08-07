import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Search,
  Download,
  FileText,
  Calendar,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Trash2,
  Eye,
  Database,
} from "lucide-react";

import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAnalysisStore } from "@/store/analysisStore";
import { useUIStore } from "@/store/uiStore";
import { usePageSEO } from "@/contexts/SEOContext";
import { cn } from "@/utils";
import type { ContractAnalysis } from "@/types";

// Import cache components (keeping only what's needed for other tabs)
import CacheEfficiencyBadge from "@/components/cache/CacheEfficiencyBadge";
import ContractHistoryList from "@/components/cache/ContractHistoryList";
import PropertyHistoryList from "@/components/cache/PropertyHistoryList";

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { recentAnalyses, deleteAnalysis } = useAnalysisStore();
  const { addNotification } = useUIStore();

  // SEO for History page
  usePageSEO({
    title: 'Analysis History - Real2AI',
    description: 'View your complete contract analysis history. Track insights, compare properties, and review past AI-powered assessments.',
    keywords: [
      'analysis history',
      'contract history',
      'property analysis records',
      'Real2AI reports',
      'contract analysis dashboard'
    ],
    canonical: '/app/history',
    noIndex: true // Private history page
  });

  const [searchQuery, setSearchQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<
    "all" | "completed" | "processing" | "failed"
  >("all");
  const [riskFilter, setRiskFilter] = React.useState<
    "all" | "low" | "medium" | "high"
  >("all");
  const [activeTab, setActiveTab] = React.useState<
    "legacy" | "contracts" | "properties"
  >("contracts");

  // Filter analyses based on search and filters
  const filteredAnalyses = React.useMemo(() => {
    return recentAnalyses.filter((analysis) => {
      // Search filter
      const matchesSearch =
        searchQuery === "" ||
        analysis.contract_id.toLowerCase().includes(searchQuery.toLowerCase());

      // Status filter
      const matchesStatus =
        statusFilter === "all" || analysis.analysis_status === statusFilter;

      // Risk filter
      const matchesRisk =
        riskFilter === "all" ||
        (riskFilter === "low" &&
          analysis.executive_summary.overall_risk_score < 4) ||
        (riskFilter === "medium" &&
          analysis.executive_summary.overall_risk_score >= 4 &&
          analysis.executive_summary.overall_risk_score < 7) ||
        (riskFilter === "high" &&
          analysis.executive_summary.overall_risk_score >= 7);

      return matchesSearch && matchesStatus && matchesRisk;
    });
  }, [recentAnalyses, searchQuery, statusFilter, riskFilter]);

  // Handle analysis deletion
  const handleDeleteAnalysis = async (contractId: string) => {
    try {
      await deleteAnalysis(contractId);
      addNotification({
        type: "success",
        title: "Analysis deleted",
        message: "The analysis has been successfully deleted.",
      });
    } catch (error) {
      addNotification({
        type: "error",
        title: "Delete failed",
        message: "Unable to delete the analysis. Please try again.",
      });
    }
  };

  // Get status icon and color
  const getStatusDisplay = (analysis: ContractAnalysis) => {
    switch (analysis.analysis_status) {
      case "completed":
        return {
          icon: CheckCircle,
          color: "text-success-600",
          bg: "bg-success-100",
          label: "Completed",
        };
      case "processing":
        return {
          icon: Clock,
          color: "text-warning-600",
          bg: "bg-warning-100",
          label: "Processing",
        };
      default:
        return {
          icon: AlertTriangle,
          color: "text-danger-600",
          bg: "bg-danger-100",
          label: "Failed",
        };
    }
  };

  // Get risk level display
  const getRiskDisplay = (riskScore: number) => {
    if (riskScore >= 7) {
      return { level: "High", color: "text-danger-600", bg: "bg-danger-100" };
    } else if (riskScore >= 4) {
      return {
        level: "Medium",
        color: "text-warning-600",
        bg: "bg-warning-100",
      };
    } else {
      return { level: "Low", color: "text-success-600", bg: "bg-success-100" };
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Analysis History
          </h1>
          <p className="text-neutral-600 mt-1">
            View your contract analysis history and cache performance
          </p>
        </div>

        <div className="flex items-center gap-3">
          <CacheEfficiencyBadge className="hidden sm:inline-flex" />
          <Button variant="outline" leftIcon={<Download className="w-4 h-4" />}>
            Export All
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-neutral-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { key: "contracts", label: "Contract History", icon: FileText },
            { key: "properties", label: "Property History", icon: Database },
            { key: "legacy", label: "Legacy Analysis", icon: Clock },
          ].map((tab) => {
            const TabIcon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={cn(
                  "group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors",
                  activeTab === tab.key
                    ? "border-primary-500 text-primary-600"
                    : "border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300"
                )}
              >
                <TabIcon
                  className={cn(
                    "mr-2 w-5 h-5",
                    activeTab === tab.key
                      ? "text-primary-500"
                      : "text-neutral-400 group-hover:text-neutral-500"
                  )}
                />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-8">
        {activeTab === "contracts" && (
          <div className="space-y-6">
            <CacheEfficiencyBadge showDetails className="sm:hidden" />
            <ContractHistoryList
              onContractSelect={(contractView) => {
                if (contractView.analysis_id) {
                  addNotification({
                    type: "info",
                    title: "Opening Analysis",
                    message: "Loading contract analysis details...",
                  });
                  // Navigate to analysis page using the analysis_id
                  navigate(`/app/analysis/${contractView.analysis_id}`);
                } else {
                  addNotification({
                    type: "warning",
                    title: "Analysis Not Available",
                    message:
                      "This contract analysis is not available for viewing.",
                  });
                }
              }}
            />
          </div>
        )}

        {activeTab === "properties" && (
          <div className="space-y-6">
            <PropertyHistoryList
              onPropertySelect={(propertyView) => {
                if (propertyView.analysis_result) {
                  addNotification({
                    type: "info",
                    title: "Opening Property Analysis",
                    message: `Loading analysis for ${propertyView.property_address}`,
                  });
                  // Navigate to property analysis page or property details
                  // Assuming there's a property analysis or property details page
                  navigate(
                    `/app/property/${encodeURIComponent(
                      propertyView.property_address
                    )}`
                  );
                } else {
                  addNotification({
                    type: "info",
                    title: "Property Bookmarked",
                    message: `${propertyView.property_address} has been added to your interests.`,
                  });
                  // Could implement a bookmark/watchlist feature here
                  // For now, just show the notification
                }
              }}
            />
          </div>
        )}

        {activeTab === "legacy" && (
          <div className="space-y-8">
            {/* Legacy Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <Card>
                <CardContent padding="lg">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                      <FileText className="w-5 h-5 text-primary-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-neutral-900">
                        {recentAnalyses.length}
                      </div>
                      <div className="text-sm text-neutral-500">
                        Total Contract Analyses
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent padding="lg">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-success-100 rounded-lg flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-success-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-neutral-900">
                        {
                          recentAnalyses.filter(
                            (a) => a.analysis_status === "completed"
                          ).length
                        }
                      </div>
                      <div className="text-sm text-neutral-500">Completed</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent padding="lg">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-warning-100 rounded-lg flex items-center justify-center">
                      <TrendingUp className="w-5 h-5 text-warning-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-neutral-900">
                        {recentAnalyses.length > 0
                          ? (
                              recentAnalyses.reduce(
                                (sum, a) =>
                                  sum + a.executive_summary.overall_risk_score,
                                0
                              ) / recentAnalyses.length
                            ).toFixed(1)
                          : "0.0"}
                      </div>
                      <div className="text-sm text-neutral-500">
                        Avg Risk Score
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent padding="lg">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-danger-100 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-danger-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-neutral-900">
                        {
                          recentAnalyses.filter(
                            (a) => a.executive_summary.overall_risk_score >= 7
                          ).length
                        }
                      </div>
                      <div className="text-sm text-neutral-500">High Risk</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Legacy Filters */}
            <Card>
              <CardContent padding="lg">
                <div className="flex flex-col lg:flex-row gap-4">
                  <div className="flex-1">
                    <Input
                      type="text"
                      placeholder="Search analyses..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      leftIcon={<Search className="w-4 h-4" />}
                    />
                  </div>

                  <div className="flex gap-3">
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value as any)}
                      className="px-3 py-2 rounded-lg border border-neutral-200 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                    >
                      <option value="all">All Status</option>
                      <option value="completed">Completed</option>
                      <option value="processing">Processing</option>
                      <option value="failed">Failed</option>
                    </select>

                    <select
                      value={riskFilter}
                      onChange={(e) => setRiskFilter(e.target.value as any)}
                      className="px-3 py-2 rounded-lg border border-neutral-200 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                    >
                      <option value="all">All Risk Levels</option>
                      <option value="low">Low Risk</option>
                      <option value="medium">Medium Risk</option>
                      <option value="high">High Risk</option>
                    </select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Legacy Analysis List */}
            <Card>
              <CardHeader>
                <CardTitle>
                  {filteredAnalyses.length}{" "}
                  {filteredAnalyses.length === 1 ? "Analysis" : "Analyses"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {filteredAnalyses.length > 0 ? (
                  <div className="space-y-4">
                    {filteredAnalyses.map((analysis, index) => {
                      const statusDisplay = getStatusDisplay(analysis);
                      const riskDisplay = getRiskDisplay(
                        analysis.executive_summary.overall_risk_score
                      );
                      const StatusIcon = statusDisplay.icon;

                      return (
                        <motion.div
                          key={analysis.contract_id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3, delay: index * 0.05 }}
                          className="p-6 border border-neutral-200 rounded-lg hover:border-primary-300 hover:bg-primary-50/30 transition-all duration-200"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div
                                className={cn(
                                  "w-12 h-12 rounded-lg flex items-center justify-center",
                                  statusDisplay.bg
                                )}
                              >
                                <StatusIcon
                                  className={cn("w-6 h-6", statusDisplay.color)}
                                />
                              </div>

                              <div className="flex-1">
                                <div className="flex items-center gap-3 mb-1">
                                  <h3 className="font-semibold text-neutral-900">
                                    Contract Analysis
                                  </h3>
                                  <span
                                    className={cn(
                                      "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                                      statusDisplay.bg,
                                      statusDisplay.color
                                    )}
                                  >
                                    {statusDisplay.label}
                                  </span>

                                  {analysis.analysis_status === "completed" && (
                                    <span
                                      className={cn(
                                        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                                        riskDisplay.bg,
                                        riskDisplay.color
                                      )}
                                    >
                                      {riskDisplay.level} Risk
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center gap-4 text-sm text-neutral-500">
                                  <div className="flex items-center gap-1">
                                    <Calendar className="w-4 h-4" />
                                    {new Date(
                                      analysis.analysis_timestamp
                                    ).toLocaleDateString()}
                                  </div>

                                  {analysis.analysis_status === "completed" && (
                                    <div className="flex items-center gap-1">
                                      <TrendingUp className="w-4 h-4" />
                                      Risk Score:{" "}
                                      {analysis.executive_summary.overall_risk_score.toFixed(
                                        1
                                      )}
                                    </div>
                                  )}

                                  <div>
                                    ID: {analysis.contract_id.slice(0, 8)}...
                                  </div>
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <Link
                                to={`/app/analysis/${analysis.contract_id}`}
                              >
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  leftIcon={<Eye className="w-4 h-4" />}
                                >
                                  View
                                </Button>
                              </Link>

                              {analysis.analysis_status === "completed" && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  leftIcon={<Download className="w-4 h-4" />}
                                  onClick={() =>
                                    addNotification({
                                      type: "info",
                                      title: "Download started",
                                      message: "Your report is being prepared.",
                                    })
                                  }
                                >
                                  Export
                                </Button>
                              )}

                              <Button
                                variant="ghost"
                                size="sm"
                                leftIcon={<Trash2 className="w-4 h-4" />}
                                onClick={() =>
                                  handleDeleteAnalysis(analysis.contract_id)
                                }
                                className="text-danger-600 hover:text-danger-700 hover:bg-danger-50"
                              >
                                Delete
                              </Button>
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <FileText className="w-16 h-16 text-neutral-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-neutral-900 mb-2">
                      No analyses found
                    </h3>
                    <p className="text-neutral-500 mb-6">
                      {searchQuery ||
                      statusFilter !== "all" ||
                      riskFilter !== "all"
                        ? "Try adjusting your search or filter criteria"
                        : "Upload your first contract to get started with analysis"}
                    </p>

                    {!searchQuery &&
                      statusFilter === "all" &&
                      riskFilter === "all" && (
                        <Link to="/app/analysis">
                          <Button variant="primary">Start New Analysis</Button>
                        </Link>
                      )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};
export default HistoryPage;
