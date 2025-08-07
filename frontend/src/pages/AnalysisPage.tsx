import React from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Download, Share, FileText } from "lucide-react";

import Button from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import DocumentUpload from "@/components/forms/DocumentUpload";
import AnalysisProgress from "@/components/analysis/AnalysisProgress";
import RiskAssessment from "@/components/analysis/RiskAssessment";
import ComplianceCheck from "@/components/analysis/ComplianceCheck";
import { useAnalysisStore } from "@/store/analysisStore";
import { useUIStore } from "@/store/uiStore";
import { usePageSEO } from "@/contexts/SEOContext";
import { cn } from "@/utils";

const AnalysisPage: React.FC = () => {
  const { contractId } = useParams();
  const {
    currentAnalysis,
    currentDocument,
    isAnalyzing,
    analysisError,
    cacheStatus,
    triggerAnalysisStart,
    triggerAnalysisRetry,
    clearCurrentAnalysis,
  } = useAnalysisStore();
  const { addNotification } = useUIStore();

  // Dynamic SEO based on current analysis
  const propertyAddress = currentAnalysis?.contract_terms?.property_address;
  const riskScore = currentAnalysis?.executive_summary?.overall_risk_score;
  
  usePageSEO(
    {
      title: propertyAddress 
        ? `Contract Analysis - ${propertyAddress} - Real2AI`
        : 'Contract Analysis - Real2AI',
      description: propertyAddress && riskScore !== undefined
        ? `Comprehensive AI analysis of ${propertyAddress} property contract. Risk level: ${riskScore >= 7 ? 'high' : riskScore >= 4 ? 'moderate' : 'low'}. Professional insights for Australian real estate transactions.`
        : 'AI-powered contract analysis for Australian real estate. Get comprehensive risk assessment, compliance checks, and professional insights.',
      keywords: [
        'contract analysis',
        'AI analysis',
        'real estate contracts',
        'risk assessment',
        'compliance check',
        'Australian property law',
        ...(typeof propertyAddress === 'string' ? [`${propertyAddress} contract`, `${propertyAddress} property analysis`] : [])
      ],
      canonical: contractId ? `/app/analysis/${contractId}` : '/app/analysis',
      noIndex: true, // Private analysis pages
      ogType: 'article',
      ...(typeof propertyAddress === 'string' && {
        publishedTime: new Date().toISOString(),
        section: 'Contract Analysis'
      })
    },
    (typeof propertyAddress === 'string') ? {
      address: propertyAddress,
      riskScore: riskScore,
      publishedTime: new Date().toISOString()
    } : undefined
  );

  const [activeTab, setActiveTab] = React.useState<
    "overview" | "risks" | "compliance"
  >("overview");

  // Handle document upload completion - now with smart cache handling
  const handleUploadComplete = async (_documentId: string) => {
    try {
      console.log('📡 Document uploaded, WebSocket should be connected');
      
      // The WebSocket connection is established during upload
      // Cache status will determine next steps automatically
      addNotification({
        type: "info",
        title: "Document uploaded",
        message: "Checking for existing analysis...",
      });
      
      // Wait for cache status to determine next steps
      // The WebSocket will handle cache status and trigger analysis if needed
      
    } catch (error) {
      console.error("Upload completion error:", error);
      addNotification({
        type: "error",
        title: "Upload error", 
        message: "Failed to process uploaded document.",
      });
    }
  };
  
  // Handle manual analysis start (for cache miss scenarios)
  const handleStartAnalysis = async () => {
    try {
      await triggerAnalysisStart();
      addNotification({
        type: "info",
        title: "Analysis started",
        message: "Your contract is being analyzed. This may take a few minutes.",
      });
    } catch (error) {
      console.error("Failed to start analysis:", error);
      addNotification({
        type: "error",
        title: "Analysis failed",
        message: "Could not start analysis. Please try again.",
      });
    }
  };
  
  // Handle analysis retry (for failed scenarios)
  const handleRetryAnalysis = async () => {
    try {
      await triggerAnalysisRetry();
      addNotification({
        type: "info",
        title: "Retrying analysis",
        message: "Retrying your contract analysis...",
      });
    } catch (error) {
      console.error("Failed to retry analysis:", error);
      addNotification({
        type: "error",
        title: "Retry failed",
        message: "Could not retry analysis. Please try again.",
      });
    }
  };

  // Handle report download
  const handleDownloadReport = async () => {
    if (!currentAnalysis) return;

    try {
      // Implementation would call API to generate and download report
      addNotification({
        type: "info",
        title: "Generating report",
        message: "Your analysis report is being prepared for download.",
      });
    } catch (error) {
      addNotification({
        type: "error",
        title: "Download failed",
        message: "Unable to generate report. Please try again.",
      });
    }
  };

  // Tab configuration
  const tabs = [
    { key: "overview", label: "Overview", count: null },
    {
      key: "risks",
      label: "Risk Assessment",
      count: currentAnalysis?.risk_assessment?.risk_factors?.length || 0,
    },
    {
      key: "compliance",
      label: "Compliance Check",
      count: currentAnalysis?.compliance_check?.compliance_issues?.length || 0,
    },
  ] as const;

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Contract Analysis
          </h1>
          <p className="text-neutral-600 mt-1">
            {currentDocument
              ? `Analyzing: ${currentDocument.filename}`
              : "Upload a contract document to get started"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {currentAnalysis && (
            <>
              <Button
                variant="outline"
                leftIcon={<Share className="w-4 h-4" />}
                onClick={() =>
                  addNotification({
                    type: "info",
                    title: "Share feature",
                    message: "Share functionality coming soon!",
                  })
                }
              >
                Share
              </Button>
              <Button
                variant="primary"
                leftIcon={<Download className="w-4 h-4" />}
                onClick={handleDownloadReport}
              >
                Download Report
              </Button>
            </>
          )}

          {(currentDocument || currentAnalysis) && (
            <Button
              variant="ghost"
              leftIcon={<ArrowLeft className="w-4 h-4" />}
              onClick={clearCurrentAnalysis}
            >
              Start New
            </Button>
          )}
        </div>
      </div>

      {/* Main Content */}
      {!currentDocument && !currentAnalysis ? (
        /* Upload Form */
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-2xl mx-auto"
        >
          <DocumentUpload onUploadComplete={handleUploadComplete} />
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Progress & Navigation */}
          <div className="space-y-6">
            {/* Cache Status & Action Panel */}
            {cacheStatus && (
              <Card className="border-l-4 border-l-primary-500">
                <CardContent padding="md">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-sm text-neutral-700 mb-1">
                        Document Status
                      </h3>
                      {cacheStatus === 'complete' && (
                        <p className="text-sm text-success-600">
                          ✅ Analysis complete - results ready!
                        </p>
                      )}
                      {cacheStatus === 'in_progress' && (
                        <p className="text-sm text-warning-600">
                          🔄 Analysis in progress - streaming updates...
                        </p>
                      )}
                      {cacheStatus === 'failed' && (
                        <p className="text-sm text-danger-600">
                          ❌ Previous analysis failed
                        </p>
                      )}
                      {cacheStatus === 'miss' && (
                        <p className="text-sm text-neutral-600">
                          🆕 New document - ready to analyze
                        </p>
                      )}
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex gap-2">
                      {cacheStatus === 'miss' && (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={handleStartAnalysis}
                          disabled={isAnalyzing}
                        >
                          Start Analysis
                        </Button>
                      )}
                      {cacheStatus === 'failed' && (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={handleRetryAnalysis}
                          disabled={isAnalyzing}
                        >
                          Retry Analysis
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            <AnalysisProgress />

            {/* Navigation Tabs (Mobile) */}
            {currentAnalysis && (
              <Card className="lg:hidden">
                <CardContent padding="sm">
                  <div className="flex space-x-1">
                    {tabs.map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        className={cn(
                          "flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                          activeTab === tab.key
                            ? "bg-primary-100 text-primary-700"
                            : "text-neutral-600 hover:text-neutral-900"
                        )}
                      >
                        {tab.label}
                        {tab.count !== null && tab.count > 0 && (
                          <span className="ml-1 px-1.5 py-0.5 text-xs bg-neutral-200 rounded-full">
                            {tab.count}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Analysis Results */}
          <div className="lg:col-span-2">
            {currentAnalysis ? (
              <div className="space-y-8">
                {/* Desktop Tab Navigation */}
                <div className="hidden lg:block">
                  <div className="border-b border-neutral-200">
                    <nav className="-mb-px flex space-x-8">
                      {tabs.map((tab) => (
                        <button
                          key={tab.key}
                          onClick={() => setActiveTab(tab.key)}
                          className={cn(
                            "whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors",
                            activeTab === tab.key
                              ? "border-primary-500 text-primary-600"
                              : "border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300"
                          )}
                        >
                          {tab.label}
                          {tab.count !== null && tab.count > 0 && (
                            <span className="ml-2 bg-neutral-100 text-neutral-900 py-0.5 px-2.5 rounded-full text-xs">
                              {tab.count}
                            </span>
                          )}
                        </button>
                      ))}
                    </nav>
                  </div>
                </div>

                {/* Tab Content */}
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  {activeTab === "overview" && (
                    <div className="space-y-6">
                      {/* Executive Summary */}
                      <Card>
                        <CardHeader>
                          <CardTitle>Executive Summary</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="text-center">
                              <div className="text-2xl font-bold text-primary-600">
                                {currentAnalysis.executive_summary.overall_risk_score.toFixed(
                                  1
                                )}
                              </div>
                              <div className="text-sm text-neutral-500">
                                Risk Score
                              </div>
                            </div>
                            <div className="text-center">
                              <div
                                className={cn(
                                  "text-2xl font-bold",
                                  currentAnalysis.executive_summary
                                    .compliance_status === "compliant"
                                    ? "text-success-600"
                                    : "text-danger-600"
                                )}
                              >
                                {currentAnalysis.executive_summary
                                  .compliance_status === "compliant"
                                  ? "✓"
                                  : "✗"}
                              </div>
                              <div className="text-sm text-neutral-500">
                                Compliance
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-warning-600">
                                {
                                  currentAnalysis.executive_summary
                                    .total_recommendations
                                }
                              </div>
                              <div className="text-sm text-neutral-500">
                                Recommendations
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-neutral-600">
                                {Math.round(
                                  currentAnalysis.executive_summary
                                    .confidence_level * 100
                                )}
                                %
                              </div>
                              <div className="text-sm text-neutral-500">
                                Confidence
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Key Recommendations */}
                      {currentAnalysis.recommendations.length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle>Key Recommendations</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="space-y-4">
                              {currentAnalysis.recommendations
                                .slice(0, 3)
                                .map((rec, index) => (
                                  <div
                                    key={index}
                                    className="flex items-start gap-3 p-3 bg-neutral-50 rounded-lg"
                                  >
                                    <div
                                      className={cn(
                                        "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                                        rec.priority === "critical"
                                          ? "bg-danger-100 text-danger-700"
                                          : rec.priority === "high"
                                          ? "bg-warning-100 text-warning-700"
                                          : "bg-primary-100 text-primary-700"
                                      )}
                                    >
                                      {index + 1}
                                    </div>
                                    <div className="flex-1">
                                      <p className="font-medium text-neutral-900">
                                        {rec.recommendation}
                                      </p>
                                      <p className="text-sm text-neutral-600 mt-1">
                                        {rec.australian_context}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  )}

                  {activeTab === "risks" && (
                    <RiskAssessment
                      riskAssessment={currentAnalysis?.risk_assessment}
                    />
                  )}

                  {activeTab === "compliance" && (
                    <ComplianceCheck analysis={currentAnalysis} />
                  )}
                </motion.div>
              </div>
            ) : isAnalyzing ? (
              <Card>
                <CardContent className="text-center py-12">
                  <FileText className="w-12 h-12 text-primary-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                    Analysis in Progress
                  </h3>
                  <p className="text-neutral-500">
                    Please wait while we analyze your contract. This typically
                    takes 2-3 minutes.
                  </p>
                  {analysisError && (
                    <div className="mt-4 p-3 bg-warning-50 border border-warning-200 rounded-lg">
                      <p className="text-warning-700 text-sm">
                        <strong>Notice:</strong> {analysisError}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : analysisError ? (
              <Card>
                <CardContent className="text-center py-12">
                  <div className="w-12 h-12 text-danger-600 mx-auto mb-4 flex items-center justify-center">
                    <svg
                      className="w-12 h-12"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                    Analysis Error
                  </h3>
                  <p className="text-neutral-500 mb-4">{analysisError}</p>
                  <Button
                    variant="primary"
                    onClick={() => {
                      if (currentDocument) {
                        handleUploadComplete(currentDocument.id);
                      }
                    }}
                  >
                    Retry Analysis
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="text-center py-12">
                  <FileText className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                    Ready for Analysis
                  </h3>
                  <p className="text-neutral-500">
                    Your document has been uploaded successfully. Analysis will
                    begin shortly.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
