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
import { apiService } from "@/services/api";

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
    const method = (options.method || "GET").toUpperCase();
    const payload = options.body
      ? JSON.parse(options.body as string)
      : undefined;

    // Delegate to centralized API service (handles auth + token refresh)
    switch (method) {
      case "GET": {
        const { data } = await apiService.get<T>(endpoint);
        return data;
      }
      case "POST": {
        const { data } = await apiService.post<T>(endpoint, payload);
        return data;
      }
      case "PUT": {
        const { data } = await apiService.put<T>(endpoint, payload);
        return data;
      }
      case "DELETE": {
        const { data } = await apiService.delete<T>(endpoint);
        return data;
      }
      default: {
        // Fallback to GET if method unsupported here
        const { data } = await apiService.get<T>(endpoint);
        return data;
      }
    }
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
    // Ensure limit is at least 1 to prevent 422 validation errors
    const validLimit = Math.max(1, limit);
    return this.makeRequest(
      `/api/cache/property/history?limit=${validLimit}&offset=${offset}`,
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
    // Ensure limit is at least 1 to prevent 422 validation errors
    const validLimit = Math.max(1, limit);
    // Route unified under contracts API
    return this.makeRequest(
      `/api/contracts/history?limit=${validLimit}&offset=${offset}`,
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

      // Extract stats with safety guards
      const totalContracts = stats?.data?.contracts?.total_cached ?? 0;
      const totalProperties = stats?.data?.properties?.total_cached ?? 0;
      const avgContractAccess = stats?.data?.contracts?.average_access ?? 0;
      const avgPropertyAccess = stats?.data?.properties?.average_access ?? 0;

      // Safe ratio for hit rate estimation
      const ratio = (x: number) => (x && x > 1 ? (x - 1) / x : 0);
      const estimatedCacheHitRate = Math.min(
        ((ratio(avgContractAccess) + ratio(avgPropertyAccess)) / 2) * 100,
        100,
      );

      // Estimate token savings (assuming 1000 tokens per analysis)
      const estimatedTokenSavings = (totalContracts * (avgContractAccess || 0) +
        totalProperties * (avgPropertyAccess || 0)) * 1000;

      // Response time improvement can be adjusted based on health (keep constant for now)
      const responseTimeImprovement = 95;

      // Rough estimate of recent cache hits
      const recentCacheHits = Math.round(
        (totalContracts * (avgContractAccess || 0) +
          totalProperties * (avgPropertyAccess || 0)) / 7,
      );

      return {
        cache_hit_rate: Math.round(estimatedCacheHitRate),
        token_savings: estimatedTokenSavings,
        response_time_improvement: responseTimeImprovement,
        recent_cache_hits: recentCacheHits,
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
