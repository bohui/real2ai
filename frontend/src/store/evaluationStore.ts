/**
 * Evaluation store for state management
 *
 * Manages:
 * - Evaluation jobs state
 * - Prompt templates
 * - Test datasets
 * - Results and analytics
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import {
  CreateEvaluationJobRequest,
  CreatePromptTemplateRequest,
  CreateTestDatasetRequest,
  DashboardStats,
  EvaluationAPI,
  EvaluationJob,
  EvaluationResult,
  ModelComparison,
  PromptTemplate,
  TestDataset,
} from "../services/evaluationApi";

export interface EvaluationState {
  // Jobs
  jobs: EvaluationJob[];
  selectedJob: EvaluationJob | null;
  jobResults: Record<string, EvaluationResult[]>;
  loading: {
    jobs: boolean;
    jobDetails: boolean;
    results: boolean;
    creating: boolean;
  };

  // Prompt Templates
  promptTemplates: PromptTemplate[];
  selectedPromptTemplate: PromptTemplate | null;

  // Test Datasets
  testDatasets: TestDataset[];
  selectedDataset: TestDataset | null;

  // Analytics
  dashboardStats: DashboardStats | null;
  modelComparisons: ModelComparison[];

  // UI State
  filters: {
    status?: string;
    search?: string;
    dateFrom?: string;
    dateTo?: string;
  };
  pagination: {
    jobs: { page: number; limit: number; total: number };
    templates: { page: number; limit: number; total: number };
    datasets: { page: number; limit: number; total: number };
  };

  // Error handling
  error: string | null;

  // Actions
  actions: {
    // Job actions
    fetchJobs: (
      params?: { status?: string; skip?: number; limit?: number },
    ) => Promise<void>;
    fetchJobDetails: (jobId: string) => Promise<void>;
    fetchJobResults: (
      jobId: string,
      params?: { model_name?: string },
    ) => Promise<void>;
    createJob: (data: CreateEvaluationJobRequest) => Promise<EvaluationJob>;
    cancelJob: (jobId: string) => Promise<void>;
    selectJob: (job: EvaluationJob | null) => void;

    // Prompt template actions
    fetchPromptTemplates: (
      params?: { search?: string; tag?: string },
    ) => Promise<void>;
    createPromptTemplate: (
      data: CreatePromptTemplateRequest,
    ) => Promise<PromptTemplate>;
    selectPromptTemplate: (template: PromptTemplate | null) => void;

    // Dataset actions
    fetchTestDatasets: (params?: { domain?: string }) => Promise<void>;
    createTestDataset: (data: CreateTestDatasetRequest) => Promise<TestDataset>;
    selectDataset: (dataset: TestDataset | null) => void;
    importDataset: (
      datasetId: string,
      file: File,
      format?: "csv" | "json",
    ) => Promise<void>;

    // Analytics actions
    fetchDashboardStats: () => Promise<void>;
    fetchModelComparisons: (
      params?: { dataset_id?: string; date_from?: string; date_to?: string },
    ) => Promise<void>;

    // Export actions
    exportJobResults: (jobId: string, format?: "csv" | "json") => Promise<void>;

    // Filter and pagination
    setFilters: (filters: Partial<EvaluationState["filters"]>) => void;
    setPagination: (
      key: keyof EvaluationState["pagination"],
      data: Partial<{ page: number; limit: number; total: number }>,
    ) => void;

    // Real-time updates
    updateJobProgress: (
      jobId: string,
      progress: number,
      status?: string,
    ) => void;

    // Error handling
    setError: (error: string | null) => void;
    clearError: () => void;
  };
}

export const useEvaluationStore = create<EvaluationState>()(
  devtools(
    (set, get) => ({
      // Initial state
      jobs: [],
      selectedJob: null,
      jobResults: {},
      loading: {
        jobs: false,
        jobDetails: false,
        results: false,
        creating: false,
      },

      promptTemplates: [],
      selectedPromptTemplate: null,

      testDatasets: [],
      selectedDataset: null,

      dashboardStats: null,
      modelComparisons: [],

      filters: {},
      pagination: {
        jobs: { page: 1, limit: 20, total: 0 },
        templates: { page: 1, limit: 20, total: 0 },
        datasets: { page: 1, limit: 20, total: 0 },
      },

      error: null,

      actions: {
        // Job actions
        fetchJobs: async (params) => {
          set((state) => ({
            loading: { ...state.loading, jobs: true },
            error: null,
          }));
          try {
            const jobs = await EvaluationAPI.getEvaluationJobs(params);
            set({ jobs, loading: { ...get().loading, jobs: false } });
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch jobs",
              loading: { ...get().loading, jobs: false },
            });
          }
        },

        fetchJobDetails: async (jobId) => {
          set((state) => ({
            loading: { ...state.loading, jobDetails: true },
            error: null,
          }));
          try {
            const job = await EvaluationAPI.getEvaluationJob(jobId);
            set({
              selectedJob: job,
              loading: { ...get().loading, jobDetails: false },
            });
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch job details",
              loading: { ...get().loading, jobDetails: false },
            });
          }
        },

        fetchJobResults: async (jobId, params) => {
          set((state) => ({
            loading: { ...state.loading, results: true },
            error: null,
          }));
          try {
            const results = await EvaluationAPI.getEvaluationResults(
              jobId,
              params,
            );
            set((state) => ({
              jobResults: { ...state.jobResults, [jobId]: results },
              loading: { ...state.loading, results: false },
            }));
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch results",
              loading: { ...get().loading, results: false },
            });
          }
        },

        createJob: async (data) => {
          set((state) => ({
            loading: { ...state.loading, creating: true },
            error: null,
          }));
          try {
            const job = await EvaluationAPI.createEvaluationJob(data);
            set((state) => ({
              jobs: [job, ...state.jobs],
              loading: { ...state.loading, creating: false },
            }));
            return job;
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to create job",
              loading: { ...get().loading, creating: false },
            });
            throw error;
          }
        },

        cancelJob: async (jobId) => {
          try {
            await EvaluationAPI.cancelEvaluationJob(jobId);
            set((state) => ({
              jobs: state.jobs.map((job) =>
                job.id === jobId
                  ? { ...job, status: "cancelled" as const }
                  : job
              ),
            }));
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to cancel job",
            });
          }
        },

        selectJob: (job) => {
          set({ selectedJob: job });
        },

        // Prompt template actions
        fetchPromptTemplates: async (params) => {
          try {
            const templates = await EvaluationAPI.getPromptTemplates(params);
            set({ promptTemplates: templates });
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch prompt templates",
            });
          }
        },

        createPromptTemplate: async (data) => {
          try {
            const template = await EvaluationAPI.createPromptTemplate(data);
            set((state) => ({
              promptTemplates: [template, ...state.promptTemplates],
            }));
            return template;
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to create prompt template",
            });
            throw error;
          }
        },

        selectPromptTemplate: (template) => {
          set({ selectedPromptTemplate: template });
        },

        // Dataset actions
        fetchTestDatasets: async (params) => {
          try {
            const datasets = await EvaluationAPI.getTestDatasets(params);
            set({ testDatasets: datasets });
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch test datasets",
            });
          }
        },

        createTestDataset: async (data) => {
          try {
            const dataset = await EvaluationAPI.createTestDataset(data);
            set((state) => ({
              testDatasets: [dataset, ...state.testDatasets],
            }));
            return dataset;
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to create test dataset",
            });
            throw error;
          }
        },

        selectDataset: (dataset) => {
          set({ selectedDataset: dataset });
        },

        importDataset: async (datasetId, file, format = "csv") => {
          try {
            const result = await EvaluationAPI.importDataset(
              datasetId,
              file,
              format,
            );
            // Update dataset size if successful
            set((state) => ({
              testDatasets: state.testDatasets.map((dataset) =>
                dataset.id === datasetId
                  ? { ...dataset, size: dataset.size + result.imported_count }
                  : dataset
              ),
            }));
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to import dataset",
            });
            throw error;
          }
        },

        // Analytics actions
        fetchDashboardStats: async () => {
          try {
            const stats = await EvaluationAPI.getDashboardStats();
            set({ dashboardStats: stats });
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch dashboard stats",
            });
          }
        },

        fetchModelComparisons: async (params) => {
          try {
            const comparisons = await EvaluationAPI.getModelComparison(params);
            set({ modelComparisons: comparisons });
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to fetch model comparisons",
            });
          }
        },

        // Export actions
        exportJobResults: async (jobId, format = "csv") => {
          try {
            const blob = await EvaluationAPI.exportResults(jobId, format);
            const filename = `evaluation_results_${jobId}.${format}`;
            EvaluationAPI.downloadExport(blob, filename);
          } catch (error) {
            set({
              error: error instanceof Error
                ? error.message
                : "Failed to export results",
            });
          }
        },

        // Filter and pagination
        setFilters: (newFilters) => {
          set((state) => ({
            filters: { ...state.filters, ...newFilters },
          }));
        },

        setPagination: (key, data) => {
          set((state) => ({
            pagination: {
              ...state.pagination,
              [key]: { ...state.pagination[key], ...data },
            },
          }));
        },

        // Real-time updates
        updateJobProgress: (jobId, progress, status) => {
          set((state) => ({
            jobs: state.jobs.map((job) =>
              job.id === jobId
                ? { ...job, progress, ...(status && { status: status as any }) }
                : job
            ),
            selectedJob: state.selectedJob?.id === jobId
              ? {
                ...state.selectedJob,
                progress,
                ...(status && { status: status as any }),
              }
              : state.selectedJob,
          }));
        },

        // Error handling
        setError: (error) => {
          set({ error });
        },

        clearError: () => {
          set({ error: null });
        },
      },
    }),
    {
      name: "evaluation-store",
      partialize: (state: EvaluationState) => ({
        // Only persist filters and pagination
        filters: state.filters,
        pagination: state.pagination,
      }),
    },
  ),
);

// Selector hooks for better performance
export const useEvaluationJobs = () =>
  useEvaluationStore((state) => ({
    jobs: state.jobs,
    selectedJob: state.selectedJob,
    loading: state.loading.jobs,
    error: state.error,
    fetchJobs: state.actions.fetchJobs,
    selectJob: state.actions.selectJob,
    cancelJob: state.actions.cancelJob,
  }));

export const useJobCreation = () =>
  useEvaluationStore((state) => ({
    promptTemplates: state.promptTemplates,
    testDatasets: state.testDatasets,
    loading: state.loading.creating,
    error: state.error,
    createJob: state.actions.createJob,
    fetchPromptTemplates: state.actions.fetchPromptTemplates,
    fetchTestDatasets: state.actions.fetchTestDatasets,
  }));

export const useEvaluationAnalytics = () =>
  useEvaluationStore((state) => ({
    dashboardStats: state.dashboardStats,
    modelComparisons: state.modelComparisons,
    fetchDashboardStats: state.actions.fetchDashboardStats,
    fetchModelComparisons: state.actions.fetchModelComparisons,
  }));
