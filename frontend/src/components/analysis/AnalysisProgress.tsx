import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  Clock,
  AlertCircle,
  FileText,
  Search,
  Shield,
  TrendingUp,
  FileCheck,
  Zap,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useAnalysisStore } from "@/store/analysisStore";
import { cn, formatRelativeTime } from "@/utils";
import { Button } from "@/components/ui/Button";

interface AnalysisProgressProps {
  className?: string;
}

// Define step mappings to match actual WebSocket messages from backend
const stepDefinitions: Record<
  string,
  { icon: any; title: string; description: string }
> = {
  document_uploaded: {
    icon: CheckCircle,
    title: "Upload document",
    description: "Document uploaded successfully",
  },
  queued: {
    icon: Clock,
    title: "Queued for analysis",
    description: "Queued for AI contract analysis...",
  },
  contract_analysis: {
    icon: FileText,
    title: "Initialize analysis",
    description: "Starting AI contract analysis...",
  },
  mark_processing_started: {
    icon: CheckCircle,
    title: "Processing started",
    description: "Processing started",
  },
  extract_text: {
    icon: FileText,
    title: "Extract text & diagrams",
    description: "Reading contract content using OCR technology",
  },
  save_diagrams: {
    icon: FileCheck,
    title: "Save diagrams",
    description: "Saving contract diagrams and charts",
  },
  update_metrics: {
    icon: TrendingUp,
    title: "Update metrics",
    description: "Updating analysis metrics",
  },
  mark_basic_complete: {
    icon: CheckCircle,
    title: "Basic processing complete",
    description: "Basic processing complete",
  },
  build_summary: {
    icon: FileCheck,
    title: "Build summary",
    description: "Building contract summary",
  },
  extract_terms: {
    icon: Search,
    title: "Extract contract terms",
    description: "Performing section-by-section analysis",
  },
  analyze_financial_terms: {
    icon: TrendingUp,
    title: "Analyze financial terms",
    description: "Financial terms analysis",
  },
  analyze_warranties: {
    icon: Shield,
    title: "Analyze warranties",
    description: "Warranties analysis",
  },
  analyze_default_termination: {
    icon: AlertCircle,
    title: "Analyze default & termination",
    description: "Default and termination analysis",
  },
  calculate_adjustments_outgoings: {
    icon: TrendingUp,
    title: "Calculate adjustments",
    description: "Adjustments and outgoings calculation",
  },
  check_disclosure_compliance: {
    icon: Shield,
    title: "Check compliance",
    description: "Disclosure compliance check",
  },
  validate_cross_sections: {
    icon: CheckCircle,
    title: "Validate cross-sections",
    description: "Cross-section validation",
  },
  finalize_results: {
    icon: FileCheck,
    title: "Finalize results",
    description: "Finalizing analysis results",
  },
};

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ className }) => {
  // Use specific selectors to ensure proper re-rendering
  const isAnalyzing = useAnalysisStore((state) => state.isAnalyzing);
  const analysisProgress = useAnalysisStore((state) => state.analysisProgress);
  const currentAnalysis = useAnalysisStore((state) => state.currentAnalysis);
  const wsService = useAnalysisStore((state) => state.wsService);
  const analysisError = useAnalysisStore((state) => state.analysisError);
  const triggerAnalysisRetry = useAnalysisStore(
    (state) => state.triggerAnalysisRetry
  );

  // Track completed steps from WebSocket messages
  const [completedSteps, setCompletedSteps] = React.useState<Set<string>>(
    new Set()
  );
  const [stepHistory, setStepHistory] = React.useState<
    Array<{ key: string; progress: number }>
  >([]);

  // Update step history when progress changes
  React.useEffect(() => {
    if (
      analysisProgress?.current_step &&
      analysisProgress?.progress_percent !== undefined
    ) {
      const currentStep = analysisProgress.current_step;
      const currentProgress = analysisProgress.progress_percent;

      setStepHistory((prev) => {
        // Add current step if not already in history
        const existingIndex = prev.findIndex((s) => s.key === currentStep);
        if (existingIndex === -1) {
          return [...prev, { key: currentStep, progress: currentProgress }];
        } else {
          // Update progress for existing step
          const updated = [...prev];
          updated[existingIndex] = {
            key: currentStep,
            progress: currentProgress,
          };
          return updated;
        }
      });

      // Mark previous steps as completed based on progress
      setCompletedSteps((prev) => {
        const newCompleted = new Set(prev);
        stepHistory.forEach((step) => {
          if (step.progress < currentProgress) {
            newCompleted.add(step.key);
          }
        });
        return newCompleted;
      });
    }
  }, [analysisProgress, stepHistory]);

  // Debug logging
  console.log("🔍 AnalysisProgress component state:", {
    isAnalyzing,
    analysisProgress,
    currentAnalysis: !!currentAnalysis,
    wsService: !!wsService,
    analysisError,
    hasProgress: !!analysisProgress,
    progressPercent: analysisProgress?.progress_percent,
  });

  // Get cache status to handle completion loading state
  const cacheStatus = useAnalysisStore((state) => state.cacheStatus);

  // Show a default state when no analysis is in progress or completed
  if (!isAnalyzing && !currentAnalysis) {
    // If cache shows complete but no analysis yet, show loading state
    if (cacheStatus === "complete") {
      console.log(
        "⏳ AnalysisProgress: Analysis complete but results loading..."
      );
      return (
        <Card
          className={cn(
            "w-full shadow-sm border-0 bg-gradient-to-br from-white to-neutral-50/50",
            className
          )}
        >
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-3 text-lg">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <div>
                <span>Contract Analysis</span>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-4 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">
              Loading Results
            </h3>
            <p className="text-neutral-500">
              Analysis complete, preparing results...
            </p>
          </CardContent>
        </Card>
      );
    }

    console.log(
      "🚫 AnalysisProgress: Showing default state - no analysis in progress or completed"
    );
    return (
      <Card
        className={cn(
          "w-full shadow-sm border-0 bg-gradient-to-br from-white to-neutral-50/50",
          className
        )}
      >
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <span>Contract Analysis</span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center py-8">
          <FileText className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-900 mb-2">
            Ready for Analysis
          </h3>
          <p className="text-neutral-500">
            Upload a document to begin contract analysis.
          </p>
        </CardContent>
      </Card>
    );
  }

  console.log("✅ AnalysisProgress: Rendering component");

  const progress = analysisProgress?.progress_percent || 0;

  // Create dynamic steps list based on actual WebSocket messages
  const visibleSteps = React.useMemo(() => {
    const steps: Array<{
      key: string;
      icon: any;
      title: string;
      description: string;
    }> = [];

    // Add steps from history in order they appeared
    stepHistory.forEach(({ key }) => {
      if (stepDefinitions[key] && !steps.find((s) => s.key === key)) {
        steps.push({
          key,
          ...stepDefinitions[key],
        });
      }
    });

    // If we have a current step that's not in history yet, add it
    if (
      analysisProgress?.current_step &&
      !steps.find((s) => s.key === analysisProgress.current_step)
    ) {
      const currentStepDef = stepDefinitions[analysisProgress.current_step];
      if (currentStepDef) {
        steps.push({
          key: analysisProgress.current_step,
          ...currentStepDef,
        });
      }
    }

    return steps;
  }, [stepHistory, analysisProgress?.current_step]);

  const currentStepIndex = analysisProgress
    ? visibleSteps.findIndex(
        (step) => step.key === analysisProgress.current_step
      )
    : -1;
  const isConnected = wsService?.isWebSocketConnected() || false;

  return (
    <Card
      className={cn(
        "w-full shadow-sm border-0 bg-gradient-to-br from-white to-neutral-50/50",
        className
      )}
    >
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span>Contract Analysis</span>
                {isAnalyzing && !analysisError && (
                  <span className="text-sm font-normal text-neutral-500">
                    - In Progress
                  </span>
                )}
              </div>
              {/* Connection Status Indicator */}
              {isAnalyzing && !analysisError && (
                <div className="flex items-center gap-1 mt-1">
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full",
                      isConnected ? "bg-green-500" : "bg-red-500"
                    )}
                    title={isConnected ? "Connected" : "Disconnected"}
                  />
                  <span className="text-xs text-neutral-500">
                    {isConnected ? "Connected" : "Disconnected"}
                  </span>
                </div>
              )}
            </div>
          </CardTitle>

          <div className="flex items-center gap-3">
            {analysisProgress && (
              <div className="text-right">
                <div className="text-2xl font-bold text-primary-600">
                  {progress}%
                </div>
                <div className="text-xs text-neutral-500">Complete</div>
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-0">
        {/* Overall Progress Bar */}
        {isAnalyzing && !analysisError && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-600 font-medium">
                Overall Progress
              </span>
              <span className="font-bold text-primary-600">{progress}%</span>
            </div>
            <div className="w-full bg-neutral-200 rounded-full h-2 overflow-hidden">
              <motion.div
                className="bg-gradient-to-r from-primary-500 to-primary-600 h-2 rounded-full shadow-sm"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </div>
        )}

        {/* Removed inline current-step banner to avoid duplication with step list */}

        {/* Step List */}
        <div className="space-y-3">
          {visibleSteps.map((step, index) => {
            // Use WebSocket-based completion tracking
            const isCompleted =
              completedSteps.has(step.key) || (!isAnalyzing && currentAnalysis);
            const isCurrent = currentStepIndex === index && isAnalyzing;
            const isPending = isAnalyzing && !isCompleted && !isCurrent;
            const failureContext = !!analysisError && !isAnalyzing;
            const isFailedStep = failureContext && currentStepIndex === index;

            const IconComponent = step.icon;

            return (
              <motion.div
                key={step.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={cn(
                  "flex items-start gap-3 p-3 rounded-xl transition-all duration-200 shadow-sm",
                  isCompleted &&
                    "bg-gradient-to-r from-green-50 to-green-100/50 border border-green-200",
                  isCurrent &&
                    "bg-gradient-to-r from-primary-50 to-primary-100/50 border border-primary-200 shadow-md",
                  isPending && "bg-neutral-50 border border-neutral-200"
                )}
              >
                <div
                  className={cn(
                    "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 shadow-sm",
                    isCompleted &&
                      "bg-gradient-to-br from-green-500 to-green-600 text-white",
                    isCurrent &&
                      "bg-gradient-to-br from-primary-500 to-primary-600 text-white",
                    isPending && "bg-neutral-300 text-neutral-600"
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : isCurrent ? (
                    <IconComponent className="w-4 h-4 animate-pulse" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <h4
                    className={cn(
                      "font-semibold transition-colors duration-200",
                      isCompleted && "text-green-900",
                      isCurrent && "text-primary-900",
                      isPending && "text-neutral-600"
                    )}
                  >
                    {step.title}
                  </h4>
                  <p
                    className={cn(
                      "text-sm mt-1 transition-colors duration-200",
                      isCompleted && "text-green-700",
                      isCurrent && "text-primary-700",
                      isPending && "text-neutral-500"
                    )}
                  >
                    {/* Use real-time step description from WebSocket if current step, otherwise use default */}
                    {isCurrent && analysisProgress?.step_description
                      ? analysisProgress.step_description
                      : step.description}
                  </p>
                </div>

                <AnimatePresence>
                  {isCompleted && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="flex-shrink-0"
                    >
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Per-step retry action when failed */}
                {isFailedStep && (
                  <div className="flex-shrink-0 ml-3">
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() =>
                        triggerAnalysisRetry(step.key).catch(console.error)
                      }
                    >
                      Retry from here
                    </Button>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        {/* Completion Message */}
        {!isAnalyzing && currentAnalysis && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center p-6 bg-gradient-to-br from-success-50 to-success-100/50 rounded-xl border border-success-200 shadow-sm"
          >
            <div className="w-12 h-12 bg-gradient-to-br from-success-500 to-success-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
              <CheckCircle className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-bold text-success-900 mb-2">
              Analysis Complete!
            </h3>
            <p className="text-success-700 mb-4">
              Your contract has been successfully analyzed. Review the results
              below.
            </p>
            <div className="text-sm text-success-600 font-medium">
              Completed {formatRelativeTime(currentAnalysis.analysis_timestamp)}
            </div>
          </motion.div>
        )}

        {/* Error State */}
        {(analysisError || (!isAnalyzing && !currentAnalysis)) && (
          <div className="text-center p-6 bg-gradient-to-br from-danger-50 to-danger-100/50 rounded-xl border border-danger-200 shadow-sm">
            <div className="w-12 h-12 bg-gradient-to-br from-danger-500 to-danger-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
              <AlertCircle className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-bold text-danger-900 mb-2">
              Analysis Failed
            </h3>
            <p className="text-danger-700 mb-4">
              {analysisError ||
                "There was an issue analyzing your contract. Please try uploading again."}
            </p>

            {/* Retry CTA */}
            <Button
              variant="primary"
              onClick={() => triggerAnalysisRetry().catch(console.error)}
              className="shadow-sm hover:shadow-md transition-shadow"
            >
              Retry Analysis
            </Button>

            {/* Connection Status for Errors */}
            {!isConnected && isAnalyzing && (
              <div className="text-sm text-amber-700 bg-gradient-to-r from-amber-50 to-amber-100/50 p-3 rounded-lg border border-amber-200">
                <div className="flex items-center justify-center gap-2">
                  <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
                  Reconnecting to analysis service...
                </div>
              </div>
            )}
          </div>
        )}

        {/* Real-time Status Info */}
        {isAnalyzing && analysisProgress && (
          <div className="text-xs text-neutral-500 text-center">
            Last updated: {new Date().toLocaleTimeString()}
            {isConnected && <span className="ml-2 text-green-600">● Live</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AnalysisProgress;
