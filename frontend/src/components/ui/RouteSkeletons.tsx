import React from "react";
import Loading from "@/components/ui/Loading";

export const DashboardSkeleton: React.FC = () => (
  <div className="p-6">
    <Loading variant="skeleton" className="mb-4" />
    <Loading variant="skeleton" className="mb-4" />
    <Loading variant="skeleton" className="mb-4" />
  </div>
);

export const AnalysisSkeleton: React.FC = () => (
  <div className="p-6">
    <Loading variant="analysis" text="Preparing analysis UI" />
  </div>
);

export const IntelligenceSkeleton: React.FC = () => (
  <div className="p-6">
    <Loading variant="skeleton" className="mb-4" />
    <Loading variant="skeleton" className="mb-4" />
  </div>
);

export const FinancialSkeleton: React.FC = () => (
  <div className="p-6">
    <Loading variant="skeleton" className="mb-4" />
    <Loading variant="skeleton" className="mb-4" />
    <Loading variant="skeleton" />
  </div>
);
