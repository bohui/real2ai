/**
 * Evaluation Jobs Dashboard Component
 * 
 * Main dashboard for managing evaluation jobs with:
 * - Job list with filtering and search
 * - Status indicators and progress tracking
 * - Quick actions (view, cancel, export)
 * - Real-time updates
 */

import React, { useState, useEffect, useMemo } from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Select from '../ui/Select';
import { Card } from '../ui/Card';
import Alert from '../ui/Alert';
import Loading from '../ui/Loading';
import StatusBadge from '../ui/StatusBadge';
import { useEvaluationJobs } from '../../store/evaluationStore';
import type { EvaluationJob } from '../../services/evaluationApi';
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

interface EvaluationJobsDashboardProps {
  onCreateJob?: () => void;
  onViewJob?: (job: EvaluationJob) => void;
  onViewResults?: (job: EvaluationJob) => void;
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Status' },
  { value: 'created', label: 'Created' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

// Removed STATUS_COLORS as we're using StatusBadge component instead

export const EvaluationJobsDashboard: React.FC<EvaluationJobsDashboardProps> = ({
  onCreateJob,
  onViewJob,
  onViewResults,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState<'created_at' | 'name' | 'status' | 'progress'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const {
    jobs,
    selectedJob,
    loading,
    error,
    actions,
  } = useEvaluationJobs();

  useEffect(() => {
    actions.fetchJobs({ status: statusFilter || undefined });
  }, [statusFilter, actions]);

  // Filter and sort jobs
  const filteredJobs = useMemo(() => {
    let filtered = jobs;

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(job =>
        job.name.toLowerCase().includes(query) ||
        (job.description?.toLowerCase().includes(query)) ||
        job.id.toLowerCase().includes(query)
      );
    }

    // Sort jobs
    filtered.sort((a, b) => {
      let aValue = a[sortBy];
      let bValue = b[sortBy];

      if (sortBy === 'created_at') {
        aValue = new Date(a.created_at).getTime();
        bValue = new Date(b.created_at).getTime();
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [jobs, searchQuery, sortBy, sortOrder]);

  const handleCancelJob = async (jobId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (window.confirm('Are you sure you want to cancel this job?')) {
      await actions.cancelJob(jobId);
    }
  };

  const handleJobClick = (job: EvaluationJob) => {
    actions.selectJob(job);
    onViewJob?.(job);
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

  const ProgressBar: React.FC<{ progress: number; status: string }> = ({ progress, status }) => (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-300 ${
          status === 'failed' ? 'bg-red-500' : 
          status === 'cancelled' ? 'bg-yellow-500' :
          status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
        }`}
        style={{ width: `${Math.max(0, Math.min(100, progress * 100))}%` }}
      />
    </div>
  );

  const JobCard: React.FC<{ job: EvaluationJob }> = ({ job }) => (
    <Card 
      className={`p-6 cursor-pointer hover:shadow-md transition-shadow ${
        selectedJob?.id === job.id ? 'ring-2 ring-blue-500' : ''
      }`}
      onClick={() => handleJobClick(job)}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{job.name}</h3>
          {job.description && (
            <p className="text-sm text-gray-600 mb-2">{job.description}</p>
          )}
          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <span>ID: {job.id.slice(0, 8)}...</span>
            <span>Priority: {job.priority}</span>
            <span>Models: {job.model_configs.length}</span>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <StatusBadge 
            status={mapJobStatusToStatusBadge(job.status)} 
          />
          {(job.status === 'running' || job.status === 'created') && (
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => handleCancelJob(job.id, e)}
              className="text-red-600 border-red-300 hover:bg-red-50"
            >
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Progress Section */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Progress</span>
          <span className="text-sm text-gray-600">{Math.round(job.progress * 100)}%</span>
        </div>
        <ProgressBar progress={job.progress} status={job.status} />
      </div>

      {/* Timestamps */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <div className="space-x-4">
          <span>Created: {formatDate(job.created_at)}</span>
          {job.started_at && (
            <span>Started: {formatDate(job.started_at)}</span>
          )}
        </div>
        <div>
          {job.completed_at ? (
            <span>Duration: {formatDuration(job.started_at, job.completed_at)}</span>
          ) : job.started_at ? (
            <span>Running: {formatDuration(job.started_at)}</span>
          ) : null}
        </div>
      </div>

      {/* Error Message */}
      {job.error_message && (
        <div className="mt-3 p-2 bg-red-50 border-l-4 border-red-400">
          <p className="text-sm text-red-700">{job.error_message}</p>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mt-4 flex justify-end space-x-2">
        {job.status === 'completed' && (
          <Button
            size="sm"
            variant="outline"
            onClick={(e) => {
              e.stopPropagation();
              onViewResults?.(job);
            }}
          >
            View Results
          </Button>
        )}
        <Button
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onViewJob?.(job);
          }}
        >
          View Details
        </Button>
      </div>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evaluation Jobs</h1>
          <p className="text-gray-600">
            Manage and monitor your LLM evaluation jobs
          </p>
        </div>
        {onCreateJob && (
          <Button onClick={onCreateJob}>
            Create New Job
          </Button>
        )}
      </div>

      {/* Filters and Search */}
      <Card className="p-4">
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <Input
              placeholder="Search jobs by name, description, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full"
            />
          </div>
          <div className="w-48">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="w-48">
            <Select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.target.value.split('-');
                setSortBy(field as typeof sortBy);
                setSortOrder(order as typeof sortOrder);
              }}
            >
              <option value="created_at-desc">Newest First</option>
              <option value="created_at-asc">Oldest First</option>
              <option value="name-asc">Name A-Z</option>
              <option value="name-desc">Name Z-A</option>
              <option value="progress-desc">Most Progress</option>
              <option value="progress-asc">Least Progress</option>
            </Select>
          </div>
        </div>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert type="danger">
          {error}
        </Alert>
      )}

      {/* Jobs List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loading size="lg" />
        </div>
      ) : filteredJobs.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-gray-500">
            {jobs.length === 0 ? (
              <div>
                <h3 className="text-lg font-medium mb-2">No evaluation jobs yet</h3>
                <p className="mb-4">Create your first evaluation job to get started.</p>
                {onCreateJob && (
                  <Button onClick={onCreateJob}>
                    Create Your First Job
                  </Button>
                )}
              </div>
            ) : (
              <div>
                <h3 className="text-lg font-medium mb-2">No jobs match your filters</h3>
                <p>Try adjusting your search or filter criteria.</p>
              </div>
            )}
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredJobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {/* Summary Stats */}
      {jobs.length > 0 && (
        <Card className="p-4">
          <div className="grid grid-cols-5 gap-4 text-center">
            {STATUS_OPTIONS.slice(1).map((status) => {
              const count = jobs.filter(job => job.status === status.value).length;
              return (
                <div key={status.value}>
                  <div className="text-2xl font-bold text-gray-900">{count}</div>
                  <div className="text-sm text-gray-600">{status.label}</div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
};