/**
 * Main Evaluation Page Component
 *
 * Central hub for the LLM evaluation system with:
 * - Dashboard overview with key metrics
 * - Job management (create, view, monitor)
 * - Navigation between different evaluation features
 * - Real-time updates and notifications
 */

import React, { useState, useEffect } from "react";
import { Card } from "../components/ui/Card";
import Button from "../components/ui/Button";
import Loading from "../components/ui/Loading";
import Alert from "../components/ui/Alert";
import { EvaluationJobForm } from "../components/evaluation/EvaluationJobForm";
import { EvaluationJobsDashboard } from "../components/evaluation/EvaluationJobsDashboard";
import { EvaluationJobDetails } from "../components/evaluation/EvaluationJobDetails";
import {
  useEvaluationStore,
  useEvaluationAnalytics,
} from "../store/evaluationStore";
import type { EvaluationJob } from "../services/evaluationApi";

type ViewMode =
  | "dashboard"
  | "create-job"
  | "job-details"
  | "job-results"
  | "analytics";

const EvaluationPage: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>("dashboard");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const error = useEvaluationStore((s) => s.error);
  const clearError = useEvaluationStore((s) => s.actions.clearError);
  const fetchJobs = useEvaluationStore((s) => s.actions.fetchJobs);
  const { dashboardStats, fetchDashboardStats } = useEvaluationAnalytics();

  useEffect(() => {
    // Load initial data
    fetchDashboardStats();
    fetchJobs();
  }, [fetchDashboardStats, fetchJobs]);

  const handleCreateJob = () => {
    setCurrentView("create-job");
  };

  const handleJobCreated = (jobId: string) => {
    setSelectedJobId(jobId);
    setCurrentView("job-details");
    // Refresh jobs list
    fetchJobs();
  };

  const handleViewJob = (job: EvaluationJob) => {
    setSelectedJobId(job.id);
    setCurrentView("job-details");
  };

  const handleViewResults = (job: EvaluationJob) => {
    setSelectedJobId(job.id);
    setCurrentView("job-results");
  };

  const handleBackToDashboard = () => {
    setCurrentView("dashboard");
    setSelectedJobId(null);
  };

  const QuickStatsCard: React.FC = () => {
    if (!dashboardStats) {
      return (
        <Card className="p-6">
          <div className="flex justify-center">
            <Loading size="sm" />
          </div>
        </Card>
      );
    }

    const stats =
      dashboardStats?.stats ||
      ({
        total_prompts: 0,
        total_datasets: 0,
        total_jobs: 0,
        total_evaluations: 0,
        avg_overall_score: 0,
      } as any);

    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Stats</h3>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {stats.total_prompts}
            </div>
            <div className="text-sm text-gray-600">Prompt Templates</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {stats.total_datasets}
            </div>
            <div className="text-sm text-gray-600">Test Datasets</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {stats.total_jobs}
            </div>
            <div className="text-sm text-gray-600">Evaluation Jobs</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {stats.total_evaluations.toLocaleString()}
            </div>
            <div className="text-sm text-gray-600">Total Evaluations</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {(stats.avg_overall_score * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600">Avg Score</div>
          </div>
        </div>
      </Card>
    );
  };

  const RecentJobsCard: React.FC = () => {
    if (!dashboardStats) {
      return (
        <Card className="p-6">
          <div className="flex justify-center">
            <Loading size="sm" />
          </div>
        </Card>
      );
    }

    const recent_jobs = dashboardStats?.recent_jobs || [];

    const getStatusColor = (status: string) => {
      switch (status) {
        case "completed":
          return "text-green-600 bg-green-100";
        case "running":
          return "text-blue-600 bg-blue-100";
        case "failed":
          return "text-red-600 bg-red-100";
        case "cancelled":
          return "text-yellow-600 bg-yellow-100";
        default:
          return "text-gray-600 bg-gray-100";
      }
    };

    return (
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Jobs</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentView("dashboard")}
          >
            View All
          </Button>
        </div>

        {recent_jobs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p className="mb-4">No evaluation jobs yet</p>
            <Button onClick={handleCreateJob} size="sm">
              Create Your First Job
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {recent_jobs.slice(0, 5).map((job: any) => (
              <div
                key={job.id}
                className="flex items-center justify-between p-3 border rounded-md hover:bg-gray-50"
              >
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{job.name}</h4>
                  <div className="text-sm text-gray-600">
                    Created: {new Date(job.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                      job.status
                    )}`}
                  >
                    {job.status}
                  </span>
                  <div className="text-sm text-gray-600">
                    {Math.round(job.progress * 100)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    );
  };

  const NavigationHeader: React.FC = () => (
    <div className="flex items-center justify-between mb-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          LLM Evaluation System
        </h1>
        <p className="text-gray-600 mt-1">
          {currentView === "dashboard" &&
            "Overview of your evaluation activities"}
          {currentView === "create-job" && "Create a new evaluation job"}
          {currentView === "job-details" && "Job details and monitoring"}
          {currentView === "job-results" && "Evaluation results and analysis"}
          {currentView === "analytics" && "Analytics and performance insights"}
        </p>
      </div>

      <div className="flex items-center space-x-3">
        {currentView !== "dashboard" && (
          <Button variant="outline" onClick={handleBackToDashboard}>
            ← Dashboard
          </Button>
        )}
        {currentView === "dashboard" && (
          <>
            <Button
              variant="outline"
              onClick={() => setCurrentView("analytics")}
            >
              Analytics
            </Button>
            <Button onClick={handleCreateJob}>Create Job</Button>
          </>
        )}
      </div>
    </div>
  );

  const DashboardOverview: React.FC = () => (
    <div className="space-y-8">
      {/* Quick Stats */}
      <QuickStatsCard />

      {/* Recent Jobs */}
      <RecentJobsCard />

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card
          className="p-6 text-center hover:shadow-md transition-shadow cursor-pointer"
          onClick={handleCreateJob}
        >
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-blue-600 text-xl">+</span>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">
            Create Evaluation Job
          </h3>
          <p className="text-sm text-gray-600">
            Start a new evaluation with custom models and metrics
          </p>
        </Card>

        <Card
          className="p-6 text-center hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => setCurrentView("dashboard")}
        >
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-green-600 text-xl">📊</span>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">View All Jobs</h3>
          <p className="text-sm text-gray-600">
            Monitor and manage your evaluation jobs
          </p>
        </Card>

        <Card
          className="p-6 text-center hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => setCurrentView("analytics")}
        >
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-purple-600 text-xl">📈</span>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Analytics</h3>
          <p className="text-sm text-gray-600">
            Compare models and analyze performance trends
          </p>
        </Card>
      </div>

      {/* Jobs Dashboard */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          Recent Evaluation Jobs
        </h2>
        <EvaluationJobsDashboard
          onCreateJob={handleCreateJob}
          onViewJob={handleViewJob}
          onViewResults={handleViewResults}
        />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Header */}
        <NavigationHeader />

        {/* Error Alert */}
        {error && (
          <Alert type="danger" className="mb-6">
            {error}
            <Button
              variant="outline"
              size="sm"
              onClick={clearError}
              className="ml-4"
            >
              Dismiss
            </Button>
          </Alert>
        )}

        {/* Main Content */}
        <div className="space-y-8">
          {currentView === "dashboard" && <DashboardOverview />}

          {currentView === "create-job" && (
            <EvaluationJobForm
              onSuccess={handleJobCreated}
              onCancel={handleBackToDashboard}
            />
          )}

          {currentView === "job-details" && selectedJobId && (
            <EvaluationJobDetails
              jobId={selectedJobId}
              onBack={handleBackToDashboard}
              onViewResults={() => setCurrentView("job-results")}
            />
          )}

          {currentView === "job-results" && selectedJobId && (
            <div className="text-center py-12">
              <h2 className="text-xl font-semibold mb-4">Results Analysis</h2>
              <p className="text-gray-600 mb-6">
                Detailed results analysis component will be implemented in Phase
                3
              </p>
              <Button onClick={handleBackToDashboard}>Back to Dashboard</Button>
            </div>
          )}

          {currentView === "analytics" && (
            <div className="text-center py-12">
              <h2 className="text-xl font-semibold mb-4">
                Analytics Dashboard
              </h2>
              <p className="text-gray-600 mb-6">
                Advanced analytics and model comparison tools will be
                implemented in Phase 3
              </p>
              <Button onClick={handleBackToDashboard}>Back to Dashboard</Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EvaluationPage;
