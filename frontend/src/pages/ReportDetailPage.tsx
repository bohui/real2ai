import React from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ExternalLink } from "lucide-react";
import apiService from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import { cn } from "@/utils";

const ReportDetailPage: React.FC = () => {
  const { contractId } = useParams();
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [report, setReport] = React.useState<any | null>(null);

  React.useEffect(() => {
    let mounted = true;
    const fetchReport = async () => {
      if (!contractId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await apiService.getReportJson(contractId);
        if (!mounted) return;
        setReport(data);
      } catch (e: any) {
        if (!mounted) return;
        setError(
          apiService.handleError?.(e) || e?.message || "Failed to load report"
        );
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchReport();
    return () => {
      mounted = false;
    };
  }, [contractId]);

  const analysisResult = report?.analysis_result || {};
  const buyerReport = analysisResult?.buyer_report || {};

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <Link
            to="/app/reports"
            className="inline-flex items-center text-sm text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Reports
          </Link>
          {contractId && (
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  const url = await apiService.downloadReport(
                    contractId,
                    "pdf"
                  );
                  window.open(url, "_blank");
                } catch (e) {
                  console.error("Failed to download PDF", e);
                }
              }}
            >
              <ExternalLink className="w-4 h-4 mr-2" /> Download PDF
            </Button>
          )}
        </div>

        {loading && (
          <div className="p-8 text-center text-neutral-600">
            Loading report…
          </div>
        )}
        {error && (
          <div className="p-4 bg-red-50 text-red-700 rounded">{error}</div>
        )}

        {!loading && !error && (
          <div className="space-y-8">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Executive Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-neutral-800 whitespace-pre-wrap">
                    {buyerReport?.executive_summary || "No summary available."}
                  </p>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-neutral-500">Recommendation</span>
                      <div className="font-medium">
                        {buyerReport?.overall_recommendation || "-"}
                      </div>
                    </div>
                    <div>
                      <span className="text-neutral-500">Confidence</span>
                      <div className="font-medium">
                        {buyerReport?.confidence_level
                          ? Math.round(
                              (buyerReport.confidence_level as number) * 100
                            ) + "%"
                          : "-"}
                      </div>
                    </div>
                    <div>
                      <span className="text-neutral-500">Evidence refs</span>
                      <div className="font-medium">
                        {Array.isArray(buyerReport?.evidence_refs)
                          ? buyerReport.evidence_refs.length
                          : 0}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Key Risks</CardTitle>
                </CardHeader>
                <CardContent>
                  {Array.isArray(buyerReport?.key_risks) &&
                  buyerReport.key_risks.length > 0 ? (
                    <div className="space-y-3">
                      {buyerReport.key_risks.map((risk: any, idx: number) => (
                        <div
                          key={idx}
                          className={cn(
                            "p-3 rounded border",
                            risk.severity === "critical"
                              ? "border-red-300 bg-red-50"
                              : risk.severity === "high"
                              ? "border-orange-300 bg-orange-50"
                              : risk.severity === "medium"
                              ? "border-yellow-300 bg-yellow-50"
                              : "border-neutral-200 bg-white"
                          )}
                        >
                          <div className="flex items-center justify-between">
                            <div className="font-medium">{risk.title}</div>
                            <span className="text-xs uppercase tracking-wide text-neutral-600">
                              {risk.severity}
                            </span>
                          </div>
                          <div className="text-sm text-neutral-700 mt-1">
                            {risk.description}
                          </div>
                          <div className="text-sm text-neutral-600 mt-1">
                            Impact: {risk.impact_summary}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-neutral-600">No key risks found.</div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Action Plan</CardTitle>
                </CardHeader>
                <CardContent>
                  {Array.isArray(buyerReport?.action_plan_overview) &&
                  buyerReport.action_plan_overview.length > 0 ? (
                    <div className="space-y-3">
                      {buyerReport.action_plan_overview.map(
                        (action: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-3 rounded border border-neutral-200 bg-white"
                          >
                            <div className="flex items-center justify-between">
                              <div className="font-medium">{action.title}</div>
                              <span className="text-xs uppercase tracking-wide text-neutral-600">
                                {action.urgency}
                              </span>
                            </div>
                            <div className="text-sm text-neutral-700 mt-1">
                              Owner: {action.owner}
                            </div>
                            {action.timeline && (
                              <div className="text-sm text-neutral-600 mt-1">
                                Timeline: {action.timeline}
                              </div>
                            )}
                          </div>
                        )
                      )}
                    </div>
                  ) : (
                    <div className="text-neutral-600">No action items.</div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Section Summaries</CardTitle>
                </CardHeader>
                <CardContent>
                  {Array.isArray(buyerReport?.section_summaries) &&
                  buyerReport.section_summaries.length > 0 ? (
                    <div className="space-y-3">
                      {buyerReport.section_summaries.map(
                        (sec: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-3 rounded border border-neutral-200 bg-white"
                          >
                            <div className="flex items-center justify-between">
                              <div className="font-medium">{sec.name}</div>
                              <span className="text-xs uppercase tracking-wide text-neutral-600">
                                {sec.status}
                              </span>
                            </div>
                            <div className="text-sm text-neutral-700 mt-1">
                              {sec.summary}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  ) : (
                    <div className="text-neutral-600">
                      No section summaries.
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportDetailPage;

