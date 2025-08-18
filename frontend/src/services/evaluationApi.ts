/**
 * Evaluation API service for LLM evaluation system
 * 
 * Provides typed API calls for:
 * - Prompt template management
 * - Test dataset operations
 * - Evaluation job execution
 * - Results and analytics
 */

import apiService from './api';

// Type definitions
export interface PromptTemplate {
  id: string;
  name: string;
  version: string;
  template_content: string;
  variables?: Record<string, any>;
  description?: string;
  tags?: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface TestDataset {
  id: string;
  name: string;
  description?: string;
  domain?: string;
  size: number;
  metadata?: Record<string, any>;
  created_by: string;
  created_at: string;
  is_active: boolean;
}

export interface TestCase {
  id: string;
  dataset_id: string;
  input_data: Record<string, any>;
  expected_output?: string;
  metadata?: Record<string, any>;
  tags?: string[];
  created_at: string;
}

export interface ModelConfig {
  model_name: string;
  provider: 'openai' | 'gemini';
  parameters: Record<string, any>;
}

export interface MetricsConfig {
  bleu_enabled: boolean;
  rouge_enabled: boolean;
  semantic_similarity_enabled: boolean;
  faithfulness_enabled: boolean;
  relevance_enabled: boolean;
  coherence_enabled: boolean;
  custom_metrics: string[];
  metric_weights: Record<string, number>;
}

export interface EvaluationJob {
  id: string;
  name: string;
  description?: string;
  prompt_template_id: string;
  dataset_id: string;
  model_configs: Record<string, any>[];
  metrics_config: Record<string, any>;
  status: 'created' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  priority: number;
  estimated_duration?: number;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface EvaluationResult {
  id: string;
  job_id: string;
  test_case_id: string;
  model_name: string;
  prompt_used: string;
  generated_response: string;
  response_time_ms: number;
  token_usage: number;
  metrics_scores: Record<string, number>;
  langsmith_run_id?: string;
  error_message?: string;
  created_at: string;
}

export interface ModelComparison {
  model_name: string;
  total_evaluations: number;
  avg_overall_score: number;
  avg_response_time: number;
  total_tokens: number;
  first_evaluation: string;
  last_evaluation: string;
}

export interface JobSummary {
  job_id: string;
  total_evaluations: number;
  successful_evaluations: number;
  success_rate: number;
  avg_response_time?: number;
  total_tokens: number;
  avg_overall_score?: number;
  metrics_breakdown: Record<string, number>;
  generated_at: string;
}

export interface DashboardStats {
  stats: {
    total_prompts: number;
    total_datasets: number;
    total_jobs: number;
    total_evaluations: number;
    avg_overall_score: number;
  };
  recent_jobs: Array<{
    id: string;
    name: string;
    status: string;
    progress: number;
    created_at: string;
  }>;
  generated_at: string;
}

// Request types
export interface CreatePromptTemplateRequest {
  name: string;
  version?: string;
  template_content: string;
  variables?: Record<string, any>;
  description?: string;
  tags?: string[];
}

export interface UpdatePromptTemplateRequest {
  template_content?: string;
  variables?: Record<string, any>;
  description?: string;
  tags?: string[];
  is_active?: boolean;
}

export interface CreateTestDatasetRequest {
  name: string;
  description?: string;
  domain?: string;
  metadata?: Record<string, any>;
}

export interface CreateTestCaseRequest {
  input_data: Record<string, any>;
  expected_output?: string;
  metadata?: Record<string, any>;
  tags?: string[];
}

export interface CreateEvaluationJobRequest {
  name: string;
  description?: string;
  prompt_template_id: string;
  dataset_id: string;
  model_configs: ModelConfig[];
  metrics_config: MetricsConfig;
  priority?: number;
}

// API endpoints
const BASE_PATH = '/api/v1/evaluation';

export class EvaluationAPI {
  // Prompt Template endpoints
  static async createPromptTemplate(data: CreatePromptTemplateRequest): Promise<PromptTemplate> {
    const response = await apiService.post<PromptTemplate>(`${BASE_PATH}/prompts`, data);
    return response.data;
  }

  static async getPromptTemplates(params?: {
    skip?: number;
    limit?: number;
    search?: string;
    tag?: string;
    is_active?: boolean;
  }): Promise<PromptTemplate[]> {
    const response = await apiService.get<PromptTemplate[]>(`${BASE_PATH}/prompts`, { params });
    return response.data;
  }

  static async getPromptTemplate(id: string): Promise<PromptTemplate> {
    const response = await apiService.get<PromptTemplate>(`${BASE_PATH}/prompts/${id}`);
    return response.data;
  }

  static async updatePromptTemplate(id: string, data: UpdatePromptTemplateRequest): Promise<PromptTemplate> {
    const response = await apiService.put<PromptTemplate>(`${BASE_PATH}/prompts/${id}`, data);
    return response.data;
  }

  static async deletePromptTemplate(id: string): Promise<{ message: string }> {
    const response = await apiService.delete<{ message: string }>(`${BASE_PATH}/prompts/${id}`);
    return response.data;
  }

  // Test Dataset endpoints
  static async createTestDataset(data: CreateTestDatasetRequest): Promise<TestDataset> {
    const response = await apiService.post<TestDataset>(`${BASE_PATH}/datasets`, data);
    return response.data;
  }

  static async getTestDatasets(params?: {
    skip?: number;
    limit?: number;
    domain?: string;
  }): Promise<TestDataset[]> {
    const response = await apiService.get<TestDataset[]>(`${BASE_PATH}/datasets`, { params });
    return response.data;
  }

  static async addTestCase(datasetId: string, data: CreateTestCaseRequest): Promise<TestCase> {
    const response = await apiService.post<TestCase>(`${BASE_PATH}/datasets/${datasetId}/test-cases`, data);
    return response.data;
  }

  static async getTestCases(datasetId: string, params?: {
    skip?: number;
    limit?: number;
  }): Promise<TestCase[]> {
    const response = await apiService.get<TestCase[]>(`${BASE_PATH}/datasets/${datasetId}/test-cases`, { params });
    return response.data;
  }

  static async importDataset(
    datasetId: string, 
    file: File, 
    format: 'csv' | 'json' = 'csv'
  ): Promise<{ message: string; imported_count: number }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiService.post<{ message: string; imported_count: number }>(
      `${BASE_PATH}/datasets/${datasetId}/import?format=${format}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  // Evaluation Job endpoints
  static async createEvaluationJob(data: CreateEvaluationJobRequest): Promise<EvaluationJob> {
    const response = await apiService.post<EvaluationJob>(`${BASE_PATH}/jobs`, data);
    return response.data;
  }

  static async getEvaluationJobs(params?: {
    status?: string;
    skip?: number;
    limit?: number;
  }): Promise<EvaluationJob[]> {
    const response = await apiService.get<EvaluationJob[]>(`${BASE_PATH}/jobs`, { params });
    return response.data;
  }

  static async getEvaluationJob(jobId: string): Promise<EvaluationJob> {
    const response = await apiService.get<EvaluationJob>(`${BASE_PATH}/jobs/${jobId}`);
    return response.data;
  }

  static async getEvaluationResults(jobId: string, params?: {
    skip?: number;
    limit?: number;
    model_name?: string;
  }): Promise<EvaluationResult[]> {
    const response = await apiService.get<EvaluationResult[]>(`${BASE_PATH}/jobs/${jobId}/results`, { params });
    return response.data;
  }

  static async cancelEvaluationJob(jobId: string): Promise<{ message: string }> {
    const response = await apiService.post<{ message: string }>(`${BASE_PATH}/jobs/${jobId}/cancel`);
    return response.data;
  }

  // Analytics endpoints
  static async getModelComparison(params?: {
    dataset_id?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<ModelComparison[]> {
    const response = await apiService.get<ModelComparison[]>(`${BASE_PATH}/analytics/model-comparison`, { params });
    return response.data;
  }

  static async getJobSummary(jobId: string): Promise<JobSummary> {
    const response = await apiService.get<JobSummary>(`${BASE_PATH}/analytics/job-summary/${jobId}`);
    return response.data;
  }

  static async getDashboardStats(): Promise<DashboardStats> {
    const response = await apiService.get<DashboardStats>(`${BASE_PATH}/analytics/dashboard`);
    return response.data;
  }

  // Export endpoints
  static async exportResults(jobId: string, format: 'csv' | 'json' = 'csv'): Promise<Blob> {
    const response = await apiService.get<Blob>(`${BASE_PATH}/jobs/${jobId}/export?format=${format}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  static downloadExport(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
}