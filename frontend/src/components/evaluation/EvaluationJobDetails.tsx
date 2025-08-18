/**
 * Evaluation Job Details Component
 * 
 * Detailed view of an evaluation job with:
 * - Job configuration and status
 * - Real-time progress monitoring
 * - Model configurations
 * - Metrics configuration
 * - Recent results preview
 */

import React, { useState, useEffect } from 'react';
import Button from '../ui/Button';
import { Card } from '../ui/Card';
import Alert from '../ui/Alert';
import Loading from '../ui/Loading';
import StatusBadge from '../ui/StatusBadge';
// import { Tabs } from '../ui/Tabs';
import { useEvaluationStore } from '../../store/evaluationStore';
import type { EvaluationJob, EvaluationResult } from '../../services/evaluationApi';
import type { StatusType } from '../ui/StatusBadge';

// Map evaluation job status to StatusBadge status types
const mapJobStatusToStatusBadge = (status: EvaluationJob['status']): StatusType => {
  switch (status) {
    case 'created': return 'pending';
    case 'running': return 'processing';
    case 'completed': return 'completed';
    case 'failed': return 'failed';
    case 'cancelled': return 'warning';
    default: return 'pending';
  }
};

interface EvaluationJobDetailsProps {
  jobId: string;
  onBack?: () => void;
  onViewResults?: () => void;
  onExportResults?: () => void;
}

export const EvaluationJobDetails: React.FC<EvaluationJobDetailsProps> = ({
  jobId,
  onBack,
  onViewResults,
  // onExportResults,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'config' | 'progress' | 'results'>('overview');
  
  const {
    selectedJob,
    jobResults,
    loading,
    error,
    actions,
  } = useEvaluationStore();

  useEffect(() => {
    actions.fetchJobDetails(jobId);
    actions.fetchJobResults(jobId); // Preview results
  }, [jobId, actions]);

  useEffect(() => {
    // Set up polling for running jobs
    if (selectedJob?.status === 'running') {
      const interval = setInterval(() => {
        actions.fetchJobDetails(jobId);
      }, 5000); // Poll every 5 seconds

      return () => clearInterval(interval);
    }
  }, [selectedJob?.status, jobId, actions]);

  const handleCancel = async () => {
    if (selectedJob && window.confirm('Are you sure you want to cancel this job?')) {
      await actions.cancelJob(selectedJob.id);
    }
  };

  const handleExport = async (format: 'csv' | 'json') => {
    if (selectedJob) {
      await actions.exportJobResults(selectedJob.id, format);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (startDate?: string, endDate?: string) => {
    if (!startDate) return 'Not started';
    if (!endDate) return 'Running...';
    
    const start = new Date(startDate).getTime();
    const end = new Date(endDate).getTime();
    const duration = Math.round((end - start) / 1000);
    
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.round(duration / 60)}m`;
    return `${Math.round(duration / 3600)}h`;
  };

  const ProgressIndicator: React.FC<{ job: EvaluationJob }> = ({ job }) => (
    <div className="space-y-4">
      {/* Overall Progress */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Progress</span>
          <span className="text-sm text-gray-600">{Math.round(job.progress * 100)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${
              job.status === 'failed' ? 'bg-red-500' : 
              job.status === 'cancelled' ? 'bg-yellow-500' :
              job.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
            }`}
            style={{ width: `${Math.max(0, Math.min(100, job.progress * 100))}%` }}
          />
        </div>
      </div>

      {/* Status Timeline */}
      <div className="space-y-2">
        <div className="flex items-center space-x-3 text-sm">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span className="text-gray-600">Created: {formatDate(job.created_at)}</span>
        </div>
        {job.started_at && (
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-gray-600">Started: {formatDate(job.started_at)}</span>
          </div>
        )}
        {job.completed_at && (
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-gray-600">Completed: {formatDate(job.completed_at)}</span>
          </div>
        )}
      </div>

      {/* Estimated Time */}
      {job.estimated_duration && job.status === 'running' && (
        <div className="text-sm text-gray-600">
          Estimated duration: {Math.round(job.estimated_duration / 60)} minutes
        </div>
      )}
    </div>
  );

  const ModelConfigCard: React.FC<{ config: any; index: number }> = ({ config, index }) => (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-gray-900">
            {config.provider}/{config.model_name}
          </h4>
          <div className="mt-2 space-y-1 text-sm text-gray-600">
            {Object.entries(config.parameters).map(([key, value]) => (
              <div key={key}>
                <span className="font-medium">{key}:</span> {String(value)}
              </div>
            ))}
          </div>
        </div>
        <div className="text-sm text-gray-500">
          Model {index + 1}
        </div>
      </div>
    </Card>
  );

  const MetricsConfigCard: React.FC<{ config: any }> = ({ config }) => (
    <Card className="p-4">
      <h4 className="font-medium text-gray-900 mb-3">Enabled Metrics</h4>
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(config).map(([key, value]) => {
          if (key.endsWith('_enabled') && value) {
            const metricName = key.replace('_enabled', '').replace('_', ' ');
            return (
              <div key={key} className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm capitalize">{metricName}</span>
              </div>
            );
          }
          return null;
        })}
      </div>

      {config.metric_weights && (
        <div className="mt-4">
          <h5 className="font-medium text-gray-900 mb-2">Metric Weights</h5>
          <div className="space-y-1">
            {Object.entries(config.metric_weights).map(([metric, weight]) => (
              <div key={metric} className="flex justify-between text-sm">
                <span className="capitalize">{metric.replace('_', ' ')}</span>
                <span>{(weight as number).toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );

  const ResultsPreview: React.FC<{ results: EvaluationResult[] }> = ({ results }) => (
    <div className="space-y-4">
      {results.length === 0 ? (
        <Card className="p-8 text-center text-gray-500">
          No results available yet
        </Card>
      ) : (
        <>
          {results.map((result, index) => (
            <Card key={result.id} className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-medium text-gray-900">
                    Result {index + 1} - {result.model_name}
                  </h4>
                  <div className="text-sm text-gray-600">
                    Response time: {result.response_time_ms}ms | 
                    Tokens: {result.token_usage}
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {formatDate(result.created_at)}
                </div>
              </div>

              {/* Generated Response Preview */}
              <div className="mb-3">
                <h5 className="text-sm font-medium text-gray-700 mb-1">Generated Response</h5>
                <p className="text-sm text-gray-600 line-clamp-3">
                  {result.generated_response}
                </p>
              </div>

              {/* Metrics Scores */}
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(result.metrics_scores).slice(0, 6).map(([metric, score]) => (
                  <div key={metric} className="text-center">
                    <div className="text-lg font-semibold text-gray-900">
                      {(score as number).toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-600 capitalize">
                      {metric.replace('_', ' ')}
                    </div>
                  </div>
                ))}
              </div>

              {result.error_message && (
                <div className="mt-3 p-2 bg-red-50 border-l-4 border-red-400">
                  <p className="text-sm text-red-700">{result.error_message}</p>
                </div>
              )}
            </Card>
          ))}

          {results.length >= 10 && (
            <div className="text-center">
              <Button variant="outline" onClick={onViewResults}>
                View All Results
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );

  if (loading.jobDetails) {
    return (
      <div className="flex justify-center py-12">
        <Loading size="lg" />
      </div>
    );
  }

  if (!selectedJob) {
    return (
      <Card className="p-8 text-center">
        <div className="text-gray-500">Job not found</div>
        {onBack && (
          <Button variant="outline" onClick={onBack} className="mt-4">
            Go Back
          </Button>
        )}
      </Card>
    );
  }

  const results = jobResults[jobId] || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack} className="mb-3">
              ← Back to Jobs
            </Button>
          )}
          <div className="flex items-center space-x-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-900">{selectedJob.name}</h1>
            <StatusBadge status={mapJobStatusToStatusBadge(selectedJob.status)} />
          </div>
          {selectedJob.description && (
            <p className="text-gray-600">{selectedJob.description}</p>
          )}
          <div className="flex items-center space-x-4 text-sm text-gray-500 mt-2">
            <span>Job ID: {selectedJob.id}</span>
            <span>Priority: {selectedJob.priority}</span>
            <span>Models: {selectedJob.model_configs.length}</span>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {selectedJob.status === 'completed' && (
            <>
              <Button variant="outline" onClick={() => handleExport('csv')}>
                Export CSV
              </Button>
              <Button variant="outline" onClick={() => handleExport('json')}>
                Export JSON
              </Button>
              {onViewResults && (
                <Button onClick={onViewResults}>
                  View All Results
                </Button>
              )}
            </>
          )}
          {(selectedJob.status === 'running' || selectedJob.status === 'created') && (
            <Button variant="outline" onClick={handleCancel} className="text-red-600">
              Cancel Job
            </Button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert type="danger">
          {error}
        </Alert>
      )}

      {selectedJob.error_message && (
        <Alert type="danger">
          <strong>Job Error:</strong> {selectedJob.error_message}
        </Alert>
      )}

      {/* Tabs */}
      {/* Tabs - simplified for now */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'config', label: 'Configuration' },
            { id: 'progress', label: 'Progress' },
            { id: 'results', label: `Results (${results.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Job Status</h3>
              <ProgressIndicator job={selectedJob} />
            </Card>
            
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Quick Stats</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Status</span>
                  <StatusBadge status={mapJobStatusToStatusBadge(selectedJob.status)} />
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Progress</span>
                  <span className="font-medium">{Math.round(selectedJob.progress * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Duration</span>
                  <span className="font-medium">
                    {formatDuration(selectedJob.started_at, selectedJob.completed_at)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Results</span>
                  <span className="font-medium">{results.length}</span>
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'config' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-4">Model Configurations</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {selectedJob.model_configs.map((config, index) => (
                  <ModelConfigCard key={index} config={config} index={index} />
                ))}
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold mb-4">Metrics Configuration</h3>
              <MetricsConfigCard config={selectedJob.metrics_config} />
            </div>
          </div>
        )}

        {activeTab === 'progress' && (
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-6">Detailed Progress</h3>
            <ProgressIndicator job={selectedJob} />
            
            {selectedJob.status === 'running' && (
              <div className="mt-6">
                <Alert type="info">
                  This job is currently running. Progress updates automatically every 5 seconds.
                </Alert>
              </div>
            )}
          </Card>
        )}

        {activeTab === 'results' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Recent Results</h3>
              {loading.results && <Loading size="sm" />}
            </div>
            <ResultsPreview results={results} />
          </div>
        )}
      </div>
    </div>
  );
};