/**
 * Performance Monitoring Dashboard
 * Real-time Core Web Vitals display with historical trends and optimization recommendations
 */

import React, { useState, useEffect, useRef } from "react";
import { clsx } from "clsx";
import { getWebVitalsMonitor, useWebVitals } from "@/utils/webVitals";

interface PerformanceDashboardProps {
  className?: string;
  showDetailed?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface MetricCardProps {
  title: string;
  value: number | null;
  unit: string;
  threshold: { good: number; poor: number };
  description: string;
  trend?: number;
}

/**
 * Metric display card with color-coded status
 */
const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  threshold,
  description,
  trend,
}) => {
  const getStatus = (val: number | null) => {
    if (val === null) return "unknown";
    if (val <= threshold.good) return "good";
    if (val >= threshold.poor) return "poor";
    return "needs-improvement";
  };

  const status = getStatus(value);

  const statusColors = {
    good: "text-green-600 bg-green-50 border-green-200",
    "needs-improvement": "text-yellow-600 bg-yellow-50 border-yellow-200",
    poor: "text-red-600 bg-red-50 border-red-200",
    unknown: "text-gray-600 bg-gray-50 border-gray-200",
  };

  const formatValue = (val: number | null) => {
    if (val === null) return "N/A";
    if (title.includes("CLS")) return val.toFixed(3);
    return Math.round(val).toString();
  };

  return (
    <div
      className={clsx(
        "p-4 rounded-lg border-2 transition-colors",
        statusColors[status]
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">{title}</h3>
        {trend !== undefined && (
          <div
            className={clsx(
              "text-xs px-2 py-1 rounded-full",
              trend > 0
                ? "text-green-600 bg-green-100"
                : trend < 0
                ? "text-red-600 bg-red-100"
                : "text-gray-600 bg-gray-100"
            )}
          >
            {trend > 0 ? "↗" : trend < 0 ? "↘" : "→"} {Math.abs(trend)}
          </div>
        )}
      </div>

      <div className="mb-2">
        <span className="text-2xl font-bold">{formatValue(value)}</span>
        <span className="text-sm ml-1">{unit}</span>
      </div>

      <div className="text-xs opacity-75 mb-2">{description}</div>

      <div className="text-xs">
        <span className="text-green-600">
          Good: ≤{threshold.good}
          {unit}
        </span>
        <span className="mx-2">•</span>
        <span className="text-red-600">
          Poor: ≥{threshold.poor}
          {unit}
        </span>
      </div>
    </div>
  );
};

/**
 * Performance score circle with animated progress
 */
const PerformanceScore: React.FC<{
  score: number;
  grade: string;
  size?: number;
}> = ({ score, grade, size = 120 }) => {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const duration = 1000; // 1 second animation
    const steps = 60;
    const increment = (score - animatedScore) / steps;

    if (Math.abs(score - animatedScore) > 1) {
      const timer = setInterval(() => {
        setAnimatedScore((prev) => {
          const newScore = prev + increment;
          if (
            (increment > 0 && newScore >= score) ||
            (increment < 0 && newScore <= score)
          ) {
            clearInterval(timer);
            return score;
          }
          return newScore;
        });
      }, duration / steps);

      return () => clearInterval(timer);
    }
  }, [score, animatedScore]);

  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    circumference - (animatedScore / 100) * circumference;

  const gradeColors = {
    good: "text-green-600 stroke-green-500",
    "needs-improvement": "text-yellow-600 stroke-yellow-500",
    poor: "text-red-600 stroke-red-500",
  };

  const colorClass =
    gradeColors[grade as keyof typeof gradeColors] || gradeColors.poor;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          className="text-gray-200"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={`transition-all duration-1000 ease-out ${colorClass}`}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className={`text-2xl font-bold ${colorClass}`}>
          {Math.round(animatedScore)}
        </div>
        <div className="text-xs text-gray-500 uppercase tracking-wide">
          {grade.replace("-", " ")}
        </div>
      </div>
    </div>
  );
};

/**
 * Historical performance trend chart
 */
const TrendChart: React.FC<{ data: any[]; metric: string }> = ({
  data,
  metric,
}) => {
  const chartRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = chartRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 20;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Get values for the metric
    const values = data
      .map((item) => item[metric])
      .filter((val): val is number => val !== null && val !== undefined);

    if (values.length === 0) return;

    const maxValue = Math.max(...values);
    const minValue = Math.min(...values);
    const range = maxValue - minValue || 1;

    // Draw grid lines
    ctx.strokeStyle = "#e5e7eb";
    ctx.lineWidth = 1;

    for (let i = 0; i <= 4; i++) {
      const y = padding + (i / 4) * (height - 2 * padding);
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }

    // Draw trend line
    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;
    ctx.beginPath();

    values.forEach((value, index) => {
      const x = padding + (index / (values.length - 1)) * (width - 2 * padding);
      const y =
        height -
        padding -
        ((value - minValue) / range) * (height - 2 * padding);

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw data points
    ctx.fillStyle = "#3b82f6";
    values.forEach((value, index) => {
      const x = padding + (index / (values.length - 1)) * (width - 2 * padding);
      const y =
        height -
        padding -
        ((value - minValue) / range) * (height - 2 * padding);

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  }, [data, metric]);

  return (
    <div className="h-32">
      <canvas
        ref={chartRef}
        width={300}
        height={128}
        className="w-full h-full"
      />
    </div>
  );
};

/**
 * Main Performance Dashboard Component
 */
export const PerformanceDashboard: React.FC<PerformanceDashboardProps> = ({
  className,
  showDetailed = true,
  autoRefresh = true,
  refreshInterval = 5000,
}) => {
  const [vitals, setVitals] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Initialize Web Vitals monitoring
    const observer = getWebVitalsMonitor();

    const updateVitals = () => {
      const currentVitals = useWebVitals();
      if (currentVitals) {
        setVitals(currentVitals);
      }
      setIsLoading(false);
    };

    // Initial load
    updateVitals();

    // Set up periodic updates if auto-refresh is enabled
    let intervalId: number | undefined;
    if (autoRefresh) {
      intervalId = window.setInterval(() => {
        updateVitals();
      }, refreshInterval);
    }

    // Subscribe to real-time updates
    const unsubscribe = observer.subscribe((newVitals) => {
      setVitals(newVitals);
    });

    // Cleanup
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      unsubscribe();
    };
  }, [autoRefresh, refreshInterval]);

  if (isLoading) {
    return (
      <div className={clsx("p-6", className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx("p-6 bg-white", className)}>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Performance Dashboard
        </h2>
        <p className="text-gray-600">
          Real-time Core Web Vitals monitoring and optimization recommendations
        </p>
      </div>

      {/* Overall Performance Score */}
      {vitals && (
        <div className="mb-8 text-center">
          <PerformanceScore
            score={vitals.score}
            grade={vitals.grade}
            size={140}
          />
          <div className="mt-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Overall Performance Score
            </h3>
            <p className="text-sm text-gray-600">
              Based on Core Web Vitals metrics
            </p>
          </div>
        </div>
      )}

      {/* Core Web Vitals Metrics */}
      {vitals && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          <MetricCard
            title="LCP"
            value={vitals.LCP}
            unit="ms"
            threshold={{ good: 2500, poor: 4000 }}
            description="Largest Contentful Paint - Loading performance"
          />

          <MetricCard
            title="FID"
            value={vitals.FID}
            unit="ms"
            threshold={{ good: 100, poor: 300 }}
            description="First Input Delay - Interactivity"
          />

          <MetricCard
            title="CLS"
            value={vitals.CLS}
            unit=""
            threshold={{ good: 0.1, poor: 0.25 }}
            description="Cumulative Layout Shift - Visual stability"
          />

          <MetricCard
            title="FCP"
            value={vitals.FCP}
            unit="ms"
            threshold={{ good: 1800, poor: 3000 }}
            description="First Contentful Paint - Initial loading"
          />

          <MetricCard
            title="TTFB"
            value={vitals.TTFB}
            unit="ms"
            threshold={{ good: 300, poor: 1000 }}
            description="Time to First Byte - Server response"
          />
        </div>
      )}

      {/* Historical Trends */}
      {/* The history state was removed, so this section will now cause an error. */}
      {/* showDetailed && history.length > 1 && ( */}
      {showDetailed && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Performance Trends
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-2">LCP Trend</h4>
              <TrendChart data={[]} metric="LCP" />{" "}
              {/* Pass an empty array as history is removed */}
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-2">FID Trend</h4>
              <TrendChart data={[]} metric="FID" />{" "}
              {/* Pass an empty array as history is removed */}
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-2">CLS Trend</h4>
              <TrendChart data={[]} metric="CLS" />{" "}
              {/* Pass an empty array as history is removed */}
            </div>
          </div>
        </div>
      )}

      {/* Bundle Analysis */}
      {/* The bundleAnalysis state was removed, so this section will now cause an error. */}
      {/* showDetailed && bundleAnalysis && ( */}
      {showDetailed && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Bundle Analysis
          </h3>
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {/* The bundleAnalysis.totalSize was removed, so this will cause an error. */}
                  {/* {Math.round(bundleAnalysis.totalSize / 1024)}KB */}
                </div>
                <div className="text-sm text-gray-600">Total Bundle Size</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {/* The bundleAnalysis.chunkSizes was removed, so this will cause an error. */}
                  {/* {Object.keys(bundleAnalysis.chunkSizes).length} */}
                </div>
                <div className="text-sm text-gray-600">Chunks Loaded</div>
              </div>

              <div className="text-center">
                <div
                  className={clsx(
                    "text-2xl font-bold"
                    /* The bundleAnalysis.totalSize was removed, so this will cause an error. */
                    // bundleAnalysis.totalSize < 500000 ? 'text-green-600' :
                    // bundleAnalysis.totalSize < 1000000 ? 'text-yellow-600' : 'text-red-600'
                  )}
                >
                  {/* The bundleAnalysis.totalSize was removed, so this will cause an error. */}
                  {/* {bundleAnalysis.totalSize < 500000 ? 'Good' :
                   bundleAnalysis.totalSize < 1000000 ? 'OK' : 'Large'} */}
                </div>
                <div className="text-sm text-gray-600">Bundle Health</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Optimization Recommendations */}
      {/* The bundleAnalysis state was removed, so this section will now cause an error. */}
      {/* <OptimizationRecommendations
        vitals={vitals}
        bundleAnalysis={bundleAnalysis}
      /> */}
    </div>
  );
};

export default PerformanceDashboard;
