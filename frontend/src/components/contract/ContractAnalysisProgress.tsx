import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Brain, 
  Shield, 
  Clock,
  X,
  Pause,
  Play
} from 'lucide-react';

export interface AnalysisStage {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed' | 'error' | 'skipped';
  progress: number; // 0-100
  duration?: number; // in seconds
  error?: string;
  icon: React.ReactNode;
}

export interface ContractAnalysisProgressProps {
  contractId: string;
  contractType: 'purchase-agreement' | 'lease' | 'employment' | 'nda' | 'service-agreement';
  contractName: string;
  onCancel: () => void;
  onComplete: (results: any) => void;
  onError: (error: string) => void;
  className?: string;
}

const CONTRACT_TYPE_LABELS = {
  'purchase-agreement': 'Purchase Agreement',
  'lease': 'Lease Agreement',
  'employment': 'Employment Contract',
  'nda': 'Non-Disclosure Agreement',
  'service-agreement': 'Service Agreement'
};

const ANALYSIS_STAGES: Omit<AnalysisStage, 'status' | 'progress' | 'duration' | 'error'>[] = [
  {
    id: 'upload',
    name: 'Document Validation',
    description: 'Verifying document integrity and format',
    icon: <FileText className="w-5 h-5" />
  },
  {
    id: 'extraction',
    name: 'Text Extraction',
    description: 'Extracting text content with OCR fallback',
    icon: <FileText className="w-5 h-5" />
  },
  {
    id: 'analysis',
    name: 'AI Analysis',
    description: 'Analyzing contract clauses and terms',
    icon: <Brain className="w-5 h-5" />
  },
  {
    id: 'risk-assessment',
    name: 'Risk Assessment',
    description: 'Calculating risk scores and flagging issues',
    icon: <AlertTriangle className="w-5 h-5" />
  },
  {
    id: 'compliance',
    name: 'Compliance Check',
    description: 'Verifying regulatory and legal compliance',
    icon: <Shield className="w-5 h-5" />
  },
  {
    id: 'recommendations',
    name: 'Recommendations',
    description: 'Generating improvement suggestions',
    icon: <CheckCircle className="w-5 h-5" />
  },
  {
    id: 'completion',
    name: 'Analysis Complete',
    description: 'Finalizing results and preparing report',
    icon: <CheckCircle className="w-5 h-5" />
  }
];

export const ContractAnalysisProgress: React.FC<ContractAnalysisProgressProps> = ({
  contractId,
  contractType,
  contractName,
  onCancel,
  onComplete,
  onError,
  className = ''
}) => {
  const [stages, setStages] = useState<AnalysisStage[]>(() =>
    ANALYSIS_STAGES.map(stage => ({
      ...stage,
      status: 'pending' as const,
      progress: 0,
      duration: 0
    }))
  );
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [overallProgress, setOverallProgress] = useState(0);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [startTime] = useState(Date.now());
  const [ws, setWs] = useState<WebSocket | null>(null);

  // WebSocket connection management
  useEffect(() => {
    const websocket = new WebSocket(`${process.env.REACT_APP_WS_URL}/contract-analysis/${contractId}`);
    
    websocket.onopen = () => {
      console.log('WebSocket connected for contract analysis');
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleProgressUpdate(data);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      onError('Connection error occurred during analysis');
    };

    websocket.onclose = () => {
      console.log('WebSocket connection closed');
      setWs(null);
    };

    return () => {
      websocket.close();
    };
  }, [contractId]);

  const handleProgressUpdate = useCallback((data: any) => {
    const { stage, progress, status, error, estimatedTimeRemaining: etr, results } = data;

    if (results && status === 'completed') {
      onComplete(results);
      return;
    }

    if (error && status === 'error') {
      setStages(prev => prev.map((s, index) => 
        s.id === stage ? { ...s, status: 'error', error } : 
        index < currentStageIndex ? { ...s, status: 'completed' } : s
      ));
      onError(error);
      return;
    }

    setStages(prev => prev.map((s, index) => {
      if (s.id === stage) {
        return {
          ...s,
          status: status as AnalysisStage['status'],
          progress: progress || 0,
          duration: (Date.now() - startTime) / 1000
        };
      }
      
      // Mark previous stages as completed
      if (index < prev.findIndex(stage => stage.id === stage)) {
        return { ...s, status: 'completed' as const, progress: 100 };
      }
      
      return s;
    }));

    // Update current stage index
    const stageIndex = ANALYSIS_STAGES.findIndex(s => s.id === stage);
    if (stageIndex !== -1) {
      setCurrentStageIndex(stageIndex);
    }

    // Update overall progress
    const completedStages = stages.filter(s => s.status === 'completed').length;
    const currentProgress = progress || 0;
    const overall = ((completedStages * 100) + currentProgress) / (ANALYSIS_STAGES.length * 100) * 100;
    setOverallProgress(Math.min(overall, 100));

    // Update estimated time
    if (etr) {
      setEstimatedTimeRemaining(etr);
    }
  }, [stages, currentStageIndex, startTime, onComplete, onError]);

  const handleCancel = () => {
    if (ws) {
      ws.send(JSON.stringify({ action: 'cancel' }));
    }
    onCancel();
  };

  const handlePauseResume = () => {
    if (ws) {
      ws.send(JSON.stringify({ action: isPaused ? 'resume' : 'pause' }));
      setIsPaused(!isPaused);
    }
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getStageStatusIcon = (stage: AnalysisStage) => {
    switch (stage.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'in-progress':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"
          />
        );
      default:
        return <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />;
    }
  };

  return (
    <div className={`bg-white rounded-xl shadow-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">
              Analyzing Contract
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {CONTRACT_TYPE_LABELS[contractType]} • {contractName}
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={handlePauseResume}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              disabled={stages[currentStageIndex]?.status === 'completed'}
            >
              {isPaused ? <Play className="w-5 h-5" /> : <Pause className="w-5 h-5" />}
            </button>
            <button
              onClick={handleCancel}
              className="p-2 text-gray-400 hover:text-red-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Overall Progress Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
            <span>Overall Progress</span>
            <span>{Math.round(overallProgress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${overallProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          
          {estimatedTimeRemaining && (
            <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
              <div className="flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>Estimated time remaining: {formatTime(estimatedTimeRemaining)}</span>
              </div>
              {isPaused && (
                <span className="text-amber-600 font-medium">Analysis Paused</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Stages List */}
      <div className="px-6 py-4">
        <div className="space-y-4">
          {stages.map((stage, index) => (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`flex items-start space-x-4 p-4 rounded-lg transition-all ${
                stage.status === 'in-progress'
                  ? 'bg-blue-50 border border-blue-200'
                  : stage.status === 'completed'
                  ? 'bg-green-50 border border-green-200'
                  : stage.status === 'error'
                  ? 'bg-red-50 border border-red-200'
                  : 'bg-gray-50 border border-gray-200'
              }`}
            >
              {/* Stage Icon */}
              <div className="flex-shrink-0 mt-1">
                {getStageStatusIcon(stage)}
              </div>

              {/* Stage Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className={`text-sm font-medium ${
                    stage.status === 'error' ? 'text-red-900' :
                    stage.status === 'completed' ? 'text-green-900' :
                    stage.status === 'in-progress' ? 'text-blue-900' :
                    'text-gray-700'
                  }`}>
                    {stage.name}
                  </h4>
                  
                  {stage.status === 'in-progress' && (
                    <span className="text-xs text-blue-600 font-medium">
                      {stage.progress}%
                    </span>
                  )}
                </div>

                <p className={`text-xs mt-1 ${
                  stage.status === 'error' ? 'text-red-700' :
                  stage.status === 'completed' ? 'text-green-700' :
                  stage.status === 'in-progress' ? 'text-blue-700' :
                  'text-gray-500'
                }`}>
                  {stage.error || stage.description}
                </p>

                {/* Progress Bar for Current Stage */}
                {stage.status === 'in-progress' && (
                  <div className="mt-2">
                    <div className="w-full bg-blue-200 rounded-full h-1.5">
                      <motion.div
                        className="bg-blue-600 h-1.5 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${stage.progress}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                  </div>
                )}

                {/* Duration for Completed Stages */}
                {stage.status === 'completed' && stage.duration && (
                  <span className="text-xs text-green-600 mt-1 block">
                    Completed in {formatTime(stage.duration)}
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Footer Status */}
      <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2 text-gray-600">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span>Real-time analysis in progress</span>
          </div>
          
          <div className="text-gray-500">
            Contract ID: {contractId.slice(0, 8)}...
          </div>
        </div>
      </div>
    </div>
  );
};