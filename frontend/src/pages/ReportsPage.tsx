import React from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  TrendingUp,
  FileText,
  AlertTriangle,
  CheckCircle,
  Download,
  Filter,
} from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAnalysisStore } from "@/store/analysisStore";
import { cn } from "@/utils";

const ReportsPage: React.FC = () => {
  const { recentAnalyses } = useAnalysisStore();

  // Calculate summary statistics
  const totalAnalyses = recentAnalyses.length;
  const highRiskCount = recentAnalyses.filter((analysis) => {
    const riskScore =
      analysis.executive_summary?.overall_risk_score ??
      analysis.risk_assessment?.overall_risk_score ??
      0;
    return riskScore >= 7;
  }).length;

  const mediumRiskCount = recentAnalyses.filter((analysis) => {
    const riskScore =
      analysis.executive_summary?.overall_risk_score ??
      analysis.risk_assessment?.overall_risk_score ??
      0;
    return riskScore >= 5 && riskScore < 7;
  }).length;

  const lowRiskCount = totalAnalyses - highRiskCount - mediumRiskCount;

  const averageRiskScore =
    totalAnalyses > 0
      ? recentAnalyses.reduce((sum, analysis) => {
          const riskScore =
            analysis.executive_summary?.overall_risk_score ??
            analysis.risk_assessment?.overall_risk_score ??
            0;
          return sum + riskScore;
        }, 0) / totalAnalyses
      : 0;

  const summaryCards = [
    {
      title: "Total Contract Analyses",
      value: totalAnalyses.toString(),
      icon: FileText,
      color: "blue",
      change: null,
    },
    {
      title: "Average Risk Score",
      value: averageRiskScore.toFixed(1),
      icon: BarChart3,
      color:
        averageRiskScore >= 7
          ? "red"
          : averageRiskScore >= 5
          ? "yellow"
          : "green",
      change: null,
    },
    {
      title: "High Risk Contracts",
      value: highRiskCount.toString(),
      icon: AlertTriangle,
      color: "red",
      change: null,
    },
    {
      title: "Low Risk Contracts",
      value: lowRiskCount.toString(),
      icon: CheckCircle,
      color: "green",
      change: null,
    },
  ];

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between"
          >
            <div>
              <h1 className="text-3xl font-bold text-neutral-900">Reports</h1>
              <p className="text-neutral-600 mt-1">
                Analytics and insights from your contract analyses
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" size="sm">
                <Filter className="w-4 h-4 mr-2" />
                Filter
              </Button>
              <Button size="sm">
                <Download className="w-4 h-4 mr-2" />
                Export Report
              </Button>
            </div>
          </motion.div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {summaryCards.map((card, index) => {
            const IconComponent = card.icon;
            return (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-neutral-600">
                          {card.title}
                        </p>
                        <p className="text-3xl font-bold text-neutral-900 mt-2">
                          {card.value}
                        </p>
                      </div>
                      <div
                        className={cn(
                          "w-12 h-12 rounded-lg flex items-center justify-center",
                          card.color === "blue" && "bg-blue-100",
                          card.color === "green" && "bg-green-100",
                          card.color === "yellow" && "bg-yellow-100",
                          card.color === "red" && "bg-red-100"
                        )}
                      >
                        <IconComponent
                          className={cn(
                            "w-6 h-6",
                            card.color === "blue" && "text-blue-600",
                            card.color === "green" && "text-green-600",
                            card.color === "yellow" && "text-yellow-600",
                            card.color === "red" && "text-red-600"
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

        {/* Risk Distribution Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Risk Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-red-500 rounded-full" />
                      <span className="text-sm text-neutral-600">
                        High Risk
                      </span>
                    </div>
                    <span className="text-sm font-medium">{highRiskCount}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                      <span className="text-sm text-neutral-600">
                        Medium Risk
                      </span>
                    </div>
                    <span className="text-sm font-medium">
                      {mediumRiskCount}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full" />
                      <span className="text-sm text-neutral-600">Low Risk</span>
                    </div>
                    <span className="text-sm font-medium">{lowRiskCount}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Analysis Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentAnalyses.slice(0, 5).map((analysis) => (
                    <div
                      key={analysis.contract_id}
                      className="flex items-center gap-3"
                    >
                      <div className="w-2 h-2 bg-primary-500 rounded-full" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-neutral-900">
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
                          (() => {
                            const riskScore =
                              analysis.executive_summary?.overall_risk_score ??
                              analysis.risk_assessment?.overall_risk_score ??
                              0;
                            return riskScore >= 7
                              ? "bg-red-500"
                              : riskScore >= 5
                              ? "bg-yellow-500"
                              : "bg-green-500";
                          })()
                        )}
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Recent Analyses Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Recent Analyses</CardTitle>
            </CardHeader>
            <CardContent>
              {recentAnalyses.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600">No analyses available yet</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Start by uploading a contract for analysis
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-neutral-200">
                        <th className="text-left py-3 px-4 font-medium text-neutral-900">
                          Contract
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-neutral-900">
                          Date
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-neutral-900">
                          Risk Score
                        </th>
                        <th className="text-left py-3 px-4 font-medium text-neutral-900">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentAnalyses.map((analysis) => {
                        const riskScore =
                          analysis.executive_summary?.overall_risk_score ??
                          analysis.risk_assessment?.overall_risk_score ??
                          0;
                        const riskLevel =
                          riskScore >= 7
                            ? "High"
                            : riskScore >= 5
                            ? "Medium"
                            : "Low";

                        return (
                          <tr
                            key={analysis.contract_id}
                            className="border-b border-neutral-100"
                          >
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-neutral-400" />
                                <span className="font-medium text-neutral-900">
                                  Contract Analysis
                                </span>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-neutral-600">
                              {new Date(
                                analysis.analysis_timestamp
                              ).toLocaleDateString()}
                            </td>
                            <td className="py-3 px-4">
                              <span className="font-medium">
                                {riskScore.toFixed(1)}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={cn(
                                  "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
                                  riskLevel === "High" &&
                                    "bg-red-100 text-red-700",
                                  riskLevel === "Medium" &&
                                    "bg-yellow-100 text-yellow-700",
                                  riskLevel === "Low" &&
                                    "bg-green-100 text-green-700"
                                )}
                              >
                                {riskLevel} Risk
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default ReportsPage;
