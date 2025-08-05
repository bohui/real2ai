import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  Play,
  MoreVertical,
  Download,
  Eye
} from 'lucide-react';
import { ContractAnalysisModal } from './ContractAnalysisModal';

export interface Contract {
  id: string;
  name: string;
  type: 'purchase-agreement' | 'lease' | 'employment' | 'nda' | 'service-agreement';
  size: number;
  uploadedAt: string;
  status: 'pending' | 'analyzing' | 'completed' | 'error';
  analysisResults?: {
    overallScore: number;
    riskCount: number;
    complianceScore: number;
    completedAt: string;
  };
}

export interface ContractAnalysisCardProps {
  contract: Contract;
  onAnalysisStart: (contractId: string) => void;
  onViewResults: (contractId: string) => void;
  className?: string;
}

const CONTRACT_TYPE_LABELS = {
  'purchase-agreement': 'Purchase Agreement',
  'lease': 'Lease Agreement', 
  'employment': 'Employment Contract',
  'nda': 'Non-Disclosure Agreement',
  'service-agreement': 'Service Agreement'
};

const CONTRACT_TYPE_COLORS = {
  'purchase-agreement': 'bg-blue-100 text-blue-800',
  'lease': 'bg-green-100 text-green-800',
  'employment': 'bg-purple-100 text-purple-800',
  'nda': 'bg-orange-100 text-orange-800',
  'service-agreement': 'bg-indigo-100 text-indigo-800'
};

export const ContractAnalysisCard: React.FC<ContractAnalysisCardProps> = ({
  contract,
  onAnalysisStart,
  onViewResults,
  className = ''
}) => {
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusIcon = () => {
    switch (contract.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'analyzing':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"
          />
        );
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-red-600" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (contract.status) {
      case 'completed':
        return 'Analysis Complete';
      case 'analyzing':
        return 'Analyzing...';
      case 'error':
        return 'Analysis Failed';
      default:
        return 'Pending Analysis';
    }
  };

  const getStatusColor = () => {
    switch (contract.status) {
      case 'completed':
        return 'text-green-600';
      case 'analyzing':
        return 'text-blue-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-500';
    }
  };

  const handleStartAnalysis = () => {
    if (contract.status === 'analyzing') {
      setShowModal(true);
    } else {
      onAnalysisStart(contract.id);
      setShowModal(true);
    }
  };

  const handleAnalysisComplete = (results: any) => {
    // This would typically update the contract status and results
    console.log('Analysis completed:', results);
    setShowModal(false);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-all duration-200 ${className}`}
      >
        {/* Card Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-gray-600" />
              </div>
              
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-gray-900 truncate">
                  {contract.name}
                </h3>
                <div className="flex items-center space-x-2 mt-1">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${CONTRACT_TYPE_COLORS[contract.type]}`}>
                    {CONTRACT_TYPE_LABELS[contract.type]}
                  </span>
                  <span className="text-sm text-gray-500">
                    {formatFileSize(contract.size)}
                  </span>
                </div>
              </div>
            </div>

            {/* Menu Button */}
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <MoreVertical className="w-4 h-4" />
              </button>

              {showMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setShowMenu(false);
                        // Handle view action
                      }}
                      className="flex items-center space-x-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      <span>View Document</span>
                    </button>
                    <button
                      onClick={() => {
                        setShowMenu(false);
                        // Handle download action
                      }}
                      className="flex items-center space-x-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Card Content */}
        <div className="p-6">
          {/* Status */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              {getStatusIcon()}
              <span className={`text-sm font-medium ${getStatusColor()}`}>
                {getStatusText()}
              </span>
            </div>
            
            <span className="text-sm text-gray-500">
              Uploaded {formatDate(contract.uploadedAt)}
            </span>
          </div>

          {/* Analysis Results */}
          {contract.status === 'completed' && contract.analysisResults && (
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {contract.analysisResults.overallScore}
                </div>
                <div className="text-xs text-gray-500">Overall Score</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-amber-600">
                  {contract.analysisResults.riskCount}
                </div>
                <div className="text-xs text-gray-500">Risk Issues</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {contract.analysisResults.complianceScore}%
                </div>
                <div className="text-xs text-gray-500">Compliance</div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-3">
            {contract.status === 'completed' ? (
              <>
                <button
                  onClick={() => onViewResults(contract.id)}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
                >
                  View Report
                </button>
                <button
                  onClick={handleStartAnalysis}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm"
                >
                  Re-analyze
                </button>
              </>
            ) : contract.status === 'analyzing' ? (
              <button
                onClick={handleStartAnalysis}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
              >
                View Progress
              </button>
            ) : (
              <button
                onClick={handleStartAnalysis}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm flex items-center justify-center space-x-2"
              >
                <Play className="w-4 h-4" />
                <span>Start Analysis</span>
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {/* Analysis Modal */}
      <ContractAnalysisModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        contract={contract}
        onAnalysisComplete={handleAnalysisComplete}
      />
    </>
  );
};