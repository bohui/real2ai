import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertCircle, CheckCircle } from "lucide-react";
import { ContractAnalysisProgress } from "./ContractAnalysisProgress";

export interface ContractAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  contract: {
    id: string;
    name: string;
    type:
      | "purchase-agreement"
      | "lease"
      | "employment"
      | "nda"
      | "service-agreement";
    size: number;
    uploadedAt: string;
  };
  onAnalysisComplete: (results: any) => void;
}

type ModalState = "analyzing" | "completed" | "error" | "cancelled";

export const ContractAnalysisModal: React.FC<ContractAnalysisModalProps> = ({
  isOpen,
  onClose,
  contract,
  onAnalysisComplete,
}) => {
  const [modalState, setModalState] = useState<ModalState>("analyzing");
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);

  const handleCancel = () => {
    setModalState("cancelled");
    setTimeout(() => {
      onClose();
      setModalState("analyzing");
      setError(null);
      setResults(null);
    }, 500);
  };

  const handleComplete = (analysisResults: any) => {
    setResults(analysisResults);
    setModalState("completed");
    onAnalysisComplete(analysisResults);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    setModalState("error");
  };

  const handleRetry = () => {
    setModalState("analyzing");
    setError(null);
    setResults(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
            onClick={handleCancel}
          />

          {/* Modal Container */}
          <div className="flex min-h-full items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-2xl"
            >
              {modalState === "analyzing" && (
                <ContractAnalysisProgress
                  contractId={contract.id}
                  contractType={contract.type}
                  contractName={contract.name}
                  onCancel={handleCancel}
                  onComplete={handleComplete}
                  onError={handleError}
                />
              )}

              {modalState === "completed" && (
                <div className="bg-white rounded-xl shadow-lg border border-gray-200">
                  {/* Header */}
                  <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                          <CheckCircle className="w-6 h-6 text-green-600" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">
                            Analysis Complete
                          </h3>
                          <p className="text-sm text-gray-600">
                            {contract.name} • {formatFileSize(contract.size)}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  {/* Results Summary */}
                  <div className="px-6 py-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                        <div className="text-2xl font-bold text-blue-900">
                          {results?.overallScore || 85}
                        </div>
                        <div className="text-sm text-blue-700">
                          Overall Score
                        </div>
                      </div>
                      <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
                        <div className="text-2xl font-bold text-amber-900">
                          {results?.riskCount || 3}
                        </div>
                        <div className="text-sm text-amber-700">
                          Risk Issues
                        </div>
                      </div>
                      <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                        <div className="text-2xl font-bold text-green-900">
                          {results?.complianceScore || 92}%
                        </div>
                        <div className="text-sm text-green-700">Compliance</div>
                      </div>
                    </div>

                    <div className="flex space-x-3">
                      <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                      >
                        View Detailed Report
                      </button>
                      <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {modalState === "error" && (
                <div className="bg-white rounded-xl shadow-lg border border-gray-200">
                  {/* Header */}
                  <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                          <AlertCircle className="w-6 h-6 text-red-600" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">
                            Analysis Failed
                          </h3>
                          <p className="text-sm text-gray-600">
                            {contract.name}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  {/* Error Content */}
                  <div className="px-6 py-6">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                      <p className="text-red-800 text-sm">
                        {error ||
                          "An unexpected error occurred during analysis."}
                      </p>
                    </div>

                    <div className="flex space-x-3">
                      <button
                        onClick={handleRetry}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                      >
                        Retry Analysis
                      </button>
                      <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {modalState === "cancelled" && (
                <div className="bg-white rounded-xl shadow-lg border border-gray-200">
                  <div className="px-6 py-8 text-center">
                    <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <X className="w-6 h-6 text-gray-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Analysis Cancelled
                    </h3>
                    <p className="text-gray-600">
                      The contract analysis has been cancelled.
                    </p>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default ContractAnalysisModal;
