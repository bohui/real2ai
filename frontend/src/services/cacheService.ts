/**
 * Cache Service for Frontend
 * Handles cache-related API operations
 */

import {
  BulkAnalysisRequest,
  BulkAnalysisResponse,
  CacheEfficiencyMetrics,
  CacheHealthResponse,
  CacheHistoryResponse,
  CacheOperationResponse,
  CacheStatsResponse,
  ContractCacheCheckRequest,
  PropertySearchWithCacheRequest,
} from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

class CacheService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const token = localStorage.getItem("access_token");

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "Authorization": token ? `Bearer ${token}` : "",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `HTTP error! status: ${response.status}`,
      );
    }

    return response.json();
  }

  // =====================================================
  // PROPERTY CACHE OPERATIONS
  // =====================================================

  /**
   * Search property with cache-first strategy
   */
  async searchPropertyWithCache(
    request: PropertySearchWithCacheRequest,
  ): Promise<CacheOperationResponse> {
    return this.makeRequest<CacheOperationResponse>(
      "/api/cache/property/search",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    );
  }

  /**
   * Get user's property search history
   */
  async getPropertyHistory(
    limit: number = 50,
    offset: number = 0,
  ): Promise<CacheHistoryResponse> {
    return this.makeRequest(
      `/api/cache/property/history?limit=${limit}&offset=${offset}`,
    );
  }

  // =====================================================
  // CONTRACT CACHE OPERATIONS
  // =====================================================

  /**
   * Check if contract analysis exists in cache
   */
  async checkContractCache(
    request: ContractCacheCheckRequest,
  ): Promise<{
    status: string;
    data: {
      content_hash: string;
      cache_hit: boolean;
      cached_analysis?: any;
    };
  }> {
    // Route unified under contracts API
    return this.makeRequest("/api/contracts/check-cache", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  // Removed duplicate analyze-with-cache endpoint; use /api/contracts/analyze instead

  /**
   * Get user's contract analysis history
   */
  async getContractHistory(
    limit: number = 50,
    offset: number = 0,
  ): Promise<CacheHistoryResponse> {
    // Route unified under contracts API
    return this.makeRequest(
      `/api/contracts/history?limit=${limit}&offset=${offset}`,
    );
  }

  // =====================================================
  // ENHANCED CONTRACT OPERATIONS
  // =====================================================

  /**
   * Enhanced contract analysis with cache integration
   */
  async startEnhancedContractAnalysis(
    request: {
      document_id: string;
      check_cache?: boolean;
      content_hash?: string;
      analysis_options?: Record<string, any>;
    },
  ): Promise<{
    contract_id: string;
    analysis_id: string;
    status: string;
    task_id?: string;
    estimated_completion_minutes: number;
    cached?: boolean;
    cache_hit?: boolean;
  }> {
    return this.makeRequest("/api/contracts/analyze-enhanced", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Bulk contract analysis
   */
  async bulkContractAnalysis(
    request: BulkAnalysisRequest,
  ): Promise<{
    status: string;
    data: BulkAnalysisResponse;
  }> {
    return this.makeRequest("/api/contracts/bulk-analyze", {
      method: "POST",
      body: JSON.stringify(request.requests),
    });
  }

  // =====================================================
  // CACHE MANAGEMENT OPERATIONS
  // =====================================================

  /**
   * Get cache statistics
   */
  async getCacheStats(): Promise<CacheStatsResponse> {
    return this.makeRequest("/api/cache/stats");
  }

  /**
   * Trigger cache cleanup
   */
  async cleanupCache(): Promise<{
    status: string;
    message: string;
    data: {
      contracts: number;
      properties: number;
    };
  }> {
    return this.makeRequest("/api/cache/cleanup", {
      method: "POST",
    });
  }

  /**
   * Check cache health
   */
  async getCacheHealth(): Promise<CacheHealthResponse> {
    return this.makeRequest("/api/cache/health");
  }

  // =====================================================
  // UTILITY OPERATIONS
  // =====================================================

  /**
   * Generate content hash for file
   */
  async generateContentHash(
    fileContent: string,
  ): Promise<{
    status: string;
    data: {
      content_hash: string;
      algorithm: string;
      file_size: number;
    };
  }> {
    return this.makeRequest("/api/cache/hash/content", {
      method: "POST",
      body: JSON.stringify({ file_content: fileContent }),
    });
  }

  /**
   * Generate property hash for address
   */
  async generatePropertyHash(
    address: string,
  ): Promise<{
    status: string;
    data: {
      original_address: string;
      normalized_address: string;
      property_hash: string;
      algorithm: string;
    };
  }> {
    return this.makeRequest("/api/cache/hash/property", {
      method: "POST",
      body: JSON.stringify({ address }),
    });
  }

  // =====================================================
  // HELPER METHODS
  // =====================================================

  /**
   * Convert file to base64 for hashing
   */
  static async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        // Remove the data URL prefix (e.g., "data:application/pdf;base64,")
        const base64 = result.split(",")[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  /**
   * Check if a contract might be cached before full analysis
   */
  async quickCacheCheck(file: File): Promise<{
    likely_cached: boolean;
    content_hash?: string;
    error?: string;
  }> {
    try {
      const base64Content = await CacheService.fileToBase64(file);
      const result = await this.checkContractCache({
        file_content: base64Content,
      });

      return {
        likely_cached: result.data.cache_hit,
        content_hash: result.data.content_hash,
      };
    } catch (error) {
      return {
        likely_cached: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }

  /**
   * Get cache efficiency metrics for dashboard
   */
  async getCacheEfficiencyMetrics(): Promise<CacheEfficiencyMetrics> {
    try {
      const [stats] = await Promise.all([
        this.getCacheStats(),
        this.getCacheHealth(),
      ]);

      // Calculate cache efficiency metrics
      const totalContracts = stats.data.contracts.total_cached;
      const totalProperties = stats.data.properties.total_cached;
      const avgContractAccess = stats.data.contracts.average_access;
      const avgPropertyAccess = stats.data.properties.average_access;

      // Estimate cache hit rate based on access patterns
      const estimatedCacheHitRate = Math.min(
        ((avgContractAccess - 1) / avgContractAccess +
          (avgPropertyAccess - 1) / avgPropertyAccess) / 2 * 100,
        100,
      );

      // Estimate token savings (assuming 1000 tokens per analysis)
      const estimatedTokenSavings = (totalContracts * avgContractAccess +
        totalProperties * avgPropertyAccess) * 1000;

      return {
        cache_hit_rate: Math.round(estimatedCacheHitRate),
        token_savings: estimatedTokenSavings,
        response_time_improvement: 95, // Cache responses are ~95% faster
        recent_cache_hits: Math.round(
          (totalContracts * avgContractAccess +
            totalProperties * avgPropertyAccess) / 7,
        ), // Estimate daily cache hits
      };
    } catch (error) {
      console.error("Error calculating cache efficiency metrics:", error);
      return {
        cache_hit_rate: 0,
        token_savings: 0,
        response_time_improvement: 0,
        recent_cache_hits: 0,
      };
    }
  }
}

// Create and export a singleton instance
export const cacheService = new CacheService();
export default cacheService;
