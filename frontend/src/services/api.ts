import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";
import {
  AuthResponse,
  ContractAnalysisRequest,
  ContractAnalysisResponse,
  ContractAnalysisResult,
  DocumentDetails,
  DocumentUploadResponse,
  OnboardingPreferences,
  UsageStats,
  User,
  UserLoginRequest,
  UserRegistrationRequest,
} from "@/types";
import { logger } from "@/utils/logger";

// Extended API types
interface AxiosRequestConfigExtended extends AxiosRequestConfig {
  _retry?: boolean;
}

interface RawAnalysisData {
  contract_id?: string;
  analysis_id?: string;
  created_at?: string;
  analysis_status?: string;
  risk_score?: number;
  [key: string]: any; // For backward compatibility with other fields
}

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

class ApiService {
  private client: AxiosInstance;
  private token: string | null = null; // can be backend token or supabase token
  private refreshToken: string | null = null; // only present for supabase token flows
  private isRefreshing = false;
  private failedQueue: Array<
    { resolve: (value?: any) => void; reject: (error?: any) => void }
  > = [];
  private tokenRefreshInterval: ReturnType<typeof setInterval> | null = null;
  private tokenExpiryTime: number | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response) => {
        // Check for new token in response headers (from backend coordination)
        const newToken = response.headers["x-new-token"];
        if (newToken) {
          logger.api("Received coordinated token refresh from backend");
          this.setToken(newToken);
          this.setupTokenRefreshInterval();
        }
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfigExtended;

        if (error.response?.status === 401 && !originalRequest._retry) {
          logger.api("auth:401-received", {
            url: originalRequest.url,
            method: originalRequest.method,
            retry: !!originalRequest._retry,
            hasRefreshToken: !!this.refreshToken,
            isBackendToken: this.isBackendToken(),
          });

          // Don't attempt token refresh for login/register endpoints
          const isAuthEndpoint = originalRequest.url?.includes("/auth/login") ||
            originalRequest.url?.includes("/auth/register");

          if (isAuthEndpoint) {
            logger.api("auth:401-on-auth-endpoint-skip-redirect", {
              url: originalRequest.url,
              method: originalRequest.method,
            });
            // For auth endpoints, just clear tokens and let the login form handle the error
            this.clearTokens();
            return Promise.reject(error);
          }

          // For backend tokens, we can't refresh them - user needs to log in again
          if (this.isBackendToken()) {
            logger.api("auth:backend-token-401-redirecting", {
              url: originalRequest.url,
              method: originalRequest.method,
            });
            this.clearTokens();
            this.handleUnauthorized();
            return Promise.reject(
              new Error("Session expired. Please log in again."),
            );
          }

          if (this.isRefreshing) {
            // If already refreshing, queue the request
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then((token) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              return this.client.request(originalRequest);
            }).catch((err) => {
              return Promise.reject(err);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            if (this.refreshToken) {
              const newTokens = await this.refreshTokens();
              this.processQueue(null, newTokens.access_token);

              // Retry the original request with new token
              if (originalRequest.headers) {
                originalRequest.headers.Authorization =
                  `Bearer ${newTokens.access_token}`;
              }
              return this.client.request(originalRequest);
            } else {
              // No refresh token available - user needs to log in again
              this.processQueue(
                new Error("Session expired. Please log in again."),
                null,
              );
              this.clearTokens();
              this.handleUnauthorized();
              return Promise.reject(
                new Error("Session expired. Please log in again."),
              );
            }
          } catch (refreshError) {
            this.processQueue(refreshError, null);
            this.clearTokens();
            this.handleUnauthorized();
            return Promise.reject(
              new Error("Session expired. Please log in again."),
            );
          } finally {
            this.isRefreshing = false;
          }
        }

        // Handle 401/403 responses and network errors
        if (error.response?.status === 401) {
          logger.api("auth:401-interceptor-redirect", {
            url: error.config?.url,
            method: error.config?.method,
          });
          this.handleUnauthorized();
        } else if (error.response?.status === 403) {
          logger.api("auth:403-detected-no-redirect", {
            url: error.config?.url,
            method: error.config?.method,
          });
        } else if (
          error.code === "ERR_NETWORK" || error.message === "Network Error"
        ) {
          // Network/CORS errors: surface to caller; do not auto-logout to avoid loops
          console.log("🚨 Network error detected:", {
            url: error.config?.url,
            method: error.config?.method,
            code: error.code,
            message: error.message,
          });
        }

        return Promise.reject(error);
      },
    );

    // Load tokens from localStorage
    this.loadTokens();
  }

  // Token management
  setTokens(accessToken: string, refreshToken?: string): void {
    this.token = accessToken;
    this.refreshToken = refreshToken || null;
    localStorage.setItem("auth_token", accessToken);
    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    } else {
      localStorage.removeItem("refresh_token");
    }
    // Setup proactive refresh for new tokens
    this.setupTokenRefreshInterval();
  }

  setToken(token: string): void {
    this.token = token;
    localStorage.setItem("auth_token", token);
    // Setup proactive refresh for new token
    this.setupTokenRefreshInterval();
  }

  clearTokens(): void {
    this.token = null;
    this.refreshToken = null;
    this.tokenExpiryTime = null;
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    // Clear refresh interval
    if (this.tokenRefreshInterval) {
      clearInterval(this.tokenRefreshInterval);
      this.tokenRefreshInterval = null;
    }
  }

  // Check if current token is a backend token
  private isBackendToken(): boolean {
    if (!this.token) return false;

    try {
      // Backend tokens are JWTs with a specific structure
      // We can check if it has the expected claims
      const payload = JSON.parse(atob(this.token.split(".")[1]));
      const isBackend = payload.type === "api";

      // Debug logging
      console.log("Token type check:", {
        tokenLength: this.token?.length,
        payloadType: payload.type,
        isBackend,
        payload: payload,
      });

      return isBackend;
    } catch (error) {
      // If we can't decode the token, assume it's not a backend token
      console.log("Failed to decode token:", error);
      return false;
    }
  }

  // Handle unauthorized access by redirecting to login
  private handleUnauthorized(): void {
    // Clear any existing auth state
    this.clearTokens();

    // Dispatch custom event for components to listen to
    window.dispatchEvent(
      new CustomEvent("auth:unauthorized", {
        detail: { message: "Session expired. Please log in again." },
      }),
    );

    // Force redirect to login page
    if (window.location.pathname !== "/auth/login") {
      logger.api("auth:redirect-login", { from: window.location.pathname });
      window.location.href = "/auth/login";
    }
  }

  clearToken(): void {
    this.clearTokens();
  }

  private loadTokens(): void {
    const token = localStorage.getItem("auth_token");
    const refreshToken = localStorage.getItem("refresh_token");
    if (token) {
      this.token = token;
      // Setup proactive refresh for loaded token
      this.setupTokenRefreshInterval();
    }
    if (refreshToken) {
      this.refreshToken = refreshToken;
    }
  }

  private extractTokenExpiry(token: string): number | null {
    try {
      // Decode JWT payload without verification
      const parts = token.split(".");
      if (parts.length !== 3) return null;

      const payload = JSON.parse(atob(parts[1]));

      // For backend tokens, check supa_exp first, then exp
      // This ensures we refresh before the underlying Supabase token expires
      const expiry = payload.supa_exp || payload.exp;

      if (expiry && typeof expiry === "number") {
        return expiry;
      }
    } catch (error) {
      console.warn("Failed to extract token expiry:", error);
    }
    return null;
  }

  private setupTokenRefreshInterval(): void {
    // Clear existing interval
    if (this.tokenRefreshInterval) {
      clearInterval(this.tokenRefreshInterval);
      this.tokenRefreshInterval = null;
    }

    if (!this.token) return;

    // Extract token expiry
    this.tokenExpiryTime = this.extractTokenExpiry(this.token);

    if (this.tokenExpiryTime) {
      // Check every minute if token needs refresh
      this.tokenRefreshInterval = setInterval(() => {
        this.checkAndRefreshToken();
      }, 60000); // Check every minute

      // Also do an immediate check
      this.checkAndRefreshToken();
    }
  }

  private async checkAndRefreshToken(): Promise<void> {
    if (!this.tokenExpiryTime) return;

    const now = Math.floor(Date.now() / 1000);
    const timeToExpiry = this.tokenExpiryTime - now;

    // Log for debugging
    console.debug(`Token expires in ${timeToExpiry}s`);

    // Refresh when 10 minutes or less remaining (configurable)
    const refreshThreshold = 600; // 10 minutes in seconds

    if (timeToExpiry <= refreshThreshold && timeToExpiry > 0) {
      logger.api(
        `Token expiring soon (${timeToExpiry}s remaining), initiating proactive refresh`,
      );

      try {
        // Only refresh if we have a refresh token or if backend supports token refresh
        if (this.refreshToken) {
          await this.refreshTokens();
          logger.api("Proactive token refresh successful");
        } else {
          // For backend tokens without refresh capability, we need to check if
          // the backend can provide a new token via the next API call
          logger.api(
            "Backend token near expiry, will receive new token on next API call",
          );
        }
      } catch (error) {
        console.warn("Proactive token refresh failed:", error);
        // The regular 401 interceptor will handle this on the next request
      }
    } else if (timeToExpiry <= 0) {
      // Token already expired
      console.warn("Token already expired, clearing tokens");
      this.clearTokens();
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
  }

  private processQueue(error: any, token: string | null = null): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  private async refreshTokens(): Promise<
    { access_token: string; refresh_token?: string }
  > {
    // If we have a Supabase refresh token, use the regular refresh endpoint
    if (this.refreshToken) {
      const response = await this.client.post("/api/auth/refresh", {}, {
        headers: {
          "X-Refresh-Token": this.refreshToken,
        },
      });

      const { access_token, refresh_token } = response.data;
      this.setTokens(access_token, refresh_token);
      return { access_token, refresh_token };
    }

    // No refresh token (likely backend token flow) → require login again
    throw new Error("Session expired. Please log in again.");
  }

  // Authentication endpoints
  async register(data: UserRegistrationRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>(
      "/api/auth/register",
      data,
    );
    if (response.data.access_token) {
      // Support both backend token flow (no refresh token) and supabase flow
      this.setTokens(response.data.access_token, response.data.refresh_token);
    }
    return response.data;
  }

  async login(data: UserLoginRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>(
      "/api/auth/login",
      data,
    );
    if (response.data.access_token) {
      // Support both backend token flow (no refresh token) and supabase flow
      this.setTokens(response.data.access_token, response.data.refresh_token);
    }
    return response.data;
  }

  async logout(): Promise<void> {
    this.clearTokens();
    // Could call logout endpoint if it exists
  }

  async changePassword(data: {
    current_password: string;
    new_password: string;
  }): Promise<{ message: string }> {
    const response = await this.client.post<{ message: string }>(
      "/api/auth/change-password",
      data,
    );
    return response.data;
  }

  // User endpoints
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>("/api/users/profile");
    return response.data;
  }

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>(
      "/api/users/profile",
      userData,
    );
    return response.data;
  }

  async updateUserPreferences(
    preferences: Record<string, unknown>,
  ): Promise<void> {
    await this.client.put("/api/users/preferences", preferences);
  }

  // Onboarding endpoints
  async getOnboardingStatus(): Promise<{
    onboarding_completed: boolean;
    onboarding_completed_at?: string;
    onboarding_preferences: OnboardingPreferences;
  }> {
    const response = await this.client.get("/api/users/onboarding/status");
    return response.data;
  }

  async completeOnboarding(preferences: {
    practice_area?: string;
    jurisdiction?: string;
    firm_size?: string;
    primary_contract_types?: string[];
  }): Promise<{
    message: string;
    skip_onboarding: boolean;
    preferences_saved?: boolean;
  }> {
    const response = await this.client.post("/api/users/onboarding/complete", {
      onboarding_preferences: preferences,
    });
    return response.data;
  }

  async updateOnboardingPreferences(preferences: {
    practice_area?: string;
    jurisdiction?: string;
    firm_size?: string;
    primary_contract_types?: string[];
  }): Promise<void> {
    await this.client.put("/api/users/onboarding/preferences", preferences);
  }

  async getUserStats(): Promise<UsageStats> {
    const response = await this.client.get<UsageStats>(
      "/api/users/usage-stats",
    );
    return response.data;
  }

  // Document endpoints
  async uploadDocument(
    file: File,
    contractType: string = "purchase_agreement",
    australianState: string = "NSW",
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("contract_type", contractType);
    formData.append("australian_state", australianState);

    const response = await this.client.post<DocumentUploadResponse>(
      "/api/documents/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        // Upload progress tracking
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || 1),
          );
          // Emit progress event
          window.dispatchEvent(
            new CustomEvent("upload:progress", {
              detail: { progress: percentCompleted },
            }),
          );
        },
      },
    );
    return response.data;
  }

  async getDocument(documentId: string): Promise<DocumentDetails> {
    const response = await this.client.get<DocumentDetails>(
      `/api/documents/${documentId}`,
    );
    return response.data;
  }

  // Contract analysis endpoints
  async prepareContract(
    data: {
      document_id: string;
      contract_type?: string;
      australian_state?: string;
    },
  ): Promise<{ contract_id: string; document_id: string }> {
    const response = await this.client.post<
      { contract_id: string; document_id: string }
    >(
      "/api/contracts/prepare",
      data,
    );
    return response.data;
  }

  async startAnalysis(
    data: ContractAnalysisRequest,
  ): Promise<ContractAnalysisResponse> {
    const response = await this.client.post<ContractAnalysisResponse>(
      "/api/contracts/analyze",
      data,
    );
    return response.data;
  }

  async getAnalysisResult(contractId: string): Promise<ContractAnalysisResult> {
    const response = await this.retryRequest(
      () => this.client.get<unknown>(`/api/contracts/${contractId}/analysis`),
      3, // max retries
      1000, // initial delay
    );

    // Transform API response to match frontend expectations
    const apiData = response.data as any;
    const analysisResult = apiData.analysis_result || {};

    // Transform to match ContractAnalysisResult interface
    const rawData = apiData as RawAnalysisData;
    const transformedResult: ContractAnalysisResult = {
      contract_id: rawData.contract_id || "",
      analysis_id: analysisResult.analysis_id || rawData.contract_id || "",
      analysis_timestamp: analysisResult.analysis_timestamp ||
        rawData.created_at || new Date().toISOString(),
      user_id: analysisResult.user_id || "",
      australian_state: analysisResult.australian_state || "NSW",
      analysis_status: (rawData.analysis_status as
        | "pending"
        | "processing"
        | "completed"
        | "failed") || "completed",
      contract_terms: analysisResult.contract_terms || {},
      risk_assessment: {
        overall_risk_score:
          analysisResult.risk_assessment?.overall_risk_score ||
          rawData.risk_score || 0,
        risk_factors: analysisResult.risk_assessment?.risk_factors || [],
      },
      compliance_check: analysisResult.compliance_check || {
        state_compliance: false,
        compliance_issues: [],
        cooling_off_compliance: false,
        cooling_off_details: {},
        mandatory_disclosures: [],
        warnings: [],
        legal_references: [],
      },
      recommendations: analysisResult.recommendations || [],
      confidence_scores: analysisResult.confidence_scores || {},
      overall_confidence: analysisResult.overall_confidence || 0.8,
      processing_time: (apiData as any).processing_time || 0,
      analysis_version: analysisResult.processing_summary?.analysis_version ||
        "1.0",
      executive_summary: {
        overall_risk_score:
          analysisResult.risk_assessment?.overall_risk_score || 0,
        compliance_status: analysisResult.compliance_check?.state_compliance
          ? "compliant"
          : "non-compliant",
        total_recommendations: analysisResult.recommendations?.length || 0,
        critical_issues:
          analysisResult.risk_assessment?.risk_factors?.filter((rf: any) =>
            rf.severity === "critical" || rf.severity === "high"
          ).length || 0,
        confidence_level: analysisResult.overall_confidence || 0.8,
      },
    };

    return transformedResult;
  }

  async removeFromWatchlist(watchlistItemId: string): Promise<void> {
    await this.client.delete(
      `/api/property-intelligence/watchlist/${watchlistItemId}`,
    );
  }

  async deleteAnalysis(contractId: string): Promise<void> {
    await this.retryRequest(
      () => this.client.delete(`/api/contracts/${contractId}`),
      2, // fewer retries for delete operations
      1000,
    );
  }

  async downloadReport(
    contractId: string,
    format: string = "pdf",
  ): Promise<string> {
    const response = await this.client.get(
      `/api/contracts/${contractId}/report?format=${format}`,
    );
    return response.data.download_url;
  }

  async getReportJson(contractId: string): Promise<any> {
    const response = await this.client.get(
      `/api/contracts/${contractId}/report?format=json`,
    );
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }

  // Generic HTTP methods for other services
  async get<T = unknown>(url: string, config?: any): Promise<{ data: T }> {
    const response = await this.client.get<T>(url, config);
    return { data: response.data };
  }

  async post<T = unknown>(
    url: string,
    data?: any,
    config?: any,
  ): Promise<{ data: T }> {
    const response = await this.client.post<T>(url, data, config);
    return { data: response.data };
  }

  async put<T = unknown>(
    url: string,
    data?: any,
    config?: any,
  ): Promise<{ data: T }> {
    const response = await this.client.put<T>(url, data, config);
    return { data: response.data };
  }

  async delete<T = unknown>(
    url: string,
    config?: any,
  ): Promise<{ data: T }> {
    const response = await this.client.delete<T>(url, config);
    return { data: response.data };
  }

  // Enhanced error handler with retry logic
  handleError(error: AxiosError): string {
    if (error.response) {
      // Server responded with error status
      const data = error.response.data as Record<string, unknown>;
      const status = error.response.status;

      // Handle specific status codes
      switch (status) {
        case 400:
          return (data?.detail as string) ||
            "Invalid request. Please check your input.";
        case 401:
          return "Authentication required. Please log in again.";
        case 403:
          return "Access denied. You don't have permission for this action.";
        case 404:
          return (data?.detail as string) ||
            "The requested resource was not found.";
        case 409:
          return (data?.detail as string) || "Conflict with existing data.";
        case 422:
          return (data?.detail as string) ||
            "Validation error. Please check your input.";
        case 429:
          return "Rate limit exceeded. Please try again later.";
        case 500:
          return "Server error. Please try again later.";
        case 502:
        case 503:
        case 504:
          return "Service temporarily unavailable. Please try again later.";
        default:
          return (data?.detail as string) || (data?.message as string) ||
            `Server error (${status})`;
      }
    } else if (error.request) {
      // Request made but no response received
      if (error.code === "ECONNABORTED") {
        return "Request timeout. Please try again.";
      }
      return "Network error - please check your connection";
    } else {
      // Something else happened
      return error.message || "An unexpected error occurred";
    }
  }

  // Add retry mechanism for failed requests
  private async retryRequest<T>(
    requestFn: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000,
  ): Promise<T> {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await requestFn();
      } catch (error) {
        if (attempt === maxRetries) {
          throw error;
        }

        // Check if error is retryable
        const axiosError = error as AxiosError;
        const shouldRetry = !axiosError.response ||
          axiosError.response.status >= 500 ||
          axiosError.response.status === 408 ||
          axiosError.response.status === 429;

        if (!shouldRetry) {
          throw error;
        }

        // Wait before retry with exponential backoff
        await new Promise((resolve) => setTimeout(resolve, delay * attempt));
      }
    }
    throw new Error("Max retries exceeded");
  }
}

// WebSocket Service for real-time updates
export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private isConnecting = false;
  private isConnected = false;
  private contractId: string;
  private messageQueue: unknown[] = [];
  private connectedAt: number | null = null;
  private closedAt: number | null = null;
  private lastMessageAt: number | null = null;
  private lastHeartbeatSentAt: number | null = null;
  private lastHeartbeatAckAt: number | null = null;
  private manualCloseOrigin: string | null = null;

  constructor(documentId: string) {
    logger.websocket("Creating WebSocket service for document", { documentId });

    // Fix URL construction for both HTTP and HTTPS
    const wsUrl = API_BASE_URL.replace(
      /^https?/,
      API_BASE_URL.startsWith("https") ? "wss" : "ws",
    );
    logger.debug("WebSocket URL configuration", { API_BASE_URL, wsUrl });

    const token = localStorage.getItem("auth_token");
    logger.debug("Auth token status", { hasToken: !!token });

    if (!token || token.trim() === "") {
      const error = "Authentication token not found. Please log in again.";
      console.error("❌ WebSocket creation failed:", error);
      throw new Error(error);
    }

    if (!documentId || documentId.trim() === "") {
      const error = "Document ID is required for WebSocket connection.";
      console.error("❌ WebSocket creation failed:", error);
      throw new Error(error);
    }

    this.contractId = documentId; // Store as contractId for backward compatibility in logs
    this.url = `${wsUrl}/ws/documents/${documentId}?token=${
      encodeURIComponent(token)
    }`;

    logger.websocket(`WebSocket service created for document ${documentId}`, {
      documentId,
      contractId: this.contractId,
      redactedUrl: this.url.replace(/token=[^&]+/, "token=[REDACTED]"),
      urlLength: this.url.length,
      hasToken: this.url.includes("token="),
      isWss: this.url.startsWith("wss://"),
      isWs: this.url.startsWith("ws://"),
    });
  }

  connect(): Promise<void> {
    // Prevent multiple connection attempts
    if (this.isConnecting || this.isConnected) {
      logger.websocket(`WebSocket already connecting/connected`, {
        contractId: this.contractId,
        isConnecting: this.isConnecting,
        isConnected: this.isConnected,
      });
      return Promise.resolve();
    }

    logger.websocket(`Attempting to connect WebSocket`, {
      contractId: this.contractId,
      redactedUrl: this.url.replace(/token=[^&]+/, "token=[REDACTED]"),
    });

    // Validate URL format
    if (!this.url.startsWith("ws://") && !this.url.startsWith("wss://")) {
      const error = new Error(`❌ Invalid WebSocket URL format: ${this.url}`);
      console.error(error.message);
      return Promise.reject(error);
    }

    return new Promise((resolve, reject) => {
      try {
        this.isConnecting = true;
        logger.websocket(`Starting WebSocket connection`, {
          contractId: this.contractId,
        });
        // Reset manual close origin when initiating a fresh connection
        this.manualCloseOrigin = null;

        // Close existing connection if any
        if (this.ws) {
          logger.websocket(`Closing existing WebSocket`, {
            contractId: this.contractId,
          });
          this.ws.close(1000, "Reconnecting");
          this.ws = null;
        }

        // Validate URL before creating WebSocket
        if (!this.url || !this.url.startsWith("ws")) {
          throw new Error(`Invalid WebSocket URL: ${this.url}`);
        }

        logger.websocket(`Creating new WebSocket connection`, {
          contractId: this.contractId,
          redactedUrl: this.url.replace(/token=[^&]+/, "token=[REDACTED]"),
        });
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          logger.websocket(`WebSocket connected successfully`, {
            contractId: this.contractId,
          });
          logger.websocket(`Connection state updated`, {
            connecting: false,
            connected: true,
          });
          this.reconnectAttempts = 0;
          this.isConnecting = false;
          this.isConnected = true;
          this.connectedAt = Date.now();
          this.closedAt = null;
          this.lastMessageAt = null;
          this.lastHeartbeatSentAt = null;
          this.lastHeartbeatAckAt = null;

          // Start heartbeat
          this.startHeartbeat();

          // Process queued messages
          this.processMessageQueue();

          // Request initial status after a brief delay to ensure connection is stable
          setTimeout(() => {
            if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
              logger.websocket("Requesting initial status via WebSocket");
              this.sendMessage({ type: "get_status" });
            }
          }, 1000);

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.lastMessageAt = Date.now();
          logger.websocket(`WebSocket message received`, {
            contractId: this.contractId,
            data: event.data,
          });
          try {
            const message = JSON.parse(event.data);
            logger.websocket(`Parsed WebSocket message`, { message });
            if (message?.event_type === "heartbeat") {
              this.lastHeartbeatAckAt = Date.now();
              logger.websocket("Heartbeat acknowledged", {
                contractId: this.contractId,
                sinceLastSendMs: this.lastHeartbeatSentAt
                  ? Date.now() - this.lastHeartbeatSentAt
                  : null,
              });
            }

            // Emit custom event for the store to handle
            const customEvent = new CustomEvent("analysis:update", {
              detail: message,
            });
            logger.websocket("Dispatching analysis:update event", {
              customEvent,
            });
            window.dispatchEvent(customEvent);
          } catch (error) {
            console.error(
              "❌ Failed to parse WebSocket message:",
              error,
              event.data,
            );
          }
        };

        this.ws.onerror = (error) => {
          console.error(`❌ WebSocket error for ${this.contractId}:`, error);
          this.isConnecting = false;
          reject(new Error(`WebSocket connection error: ${String(error)}`));
        };

        this.ws.onclose = (event) => {
          this.closedAt = Date.now();
          const durationMs = this.connectedAt
            ? this.closedAt - this.connectedAt
            : null;
          const heartbeatLagMs =
            this.lastHeartbeatSentAt && this.lastHeartbeatAckAt
              ? this.lastHeartbeatAckAt - this.lastHeartbeatSentAt
              : null;
          logger.websocket(`WebSocket closed`, {
            contractId: this.contractId,
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean,
            durationMs,
            lastMessageAt: this.lastMessageAt,
            lastHeartbeatSentAt: this.lastHeartbeatSentAt,
            lastHeartbeatAckAt: this.lastHeartbeatAckAt,
            heartbeatLagMs,
            manualCloseOrigin: this.manualCloseOrigin,
            reconnectAttempts: this.reconnectAttempts,
          });
          this.isConnected = false;
          this.isConnecting = false;

          if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
          }

          // Attempt reconnection if not manually closed
          if (
            event.code !== 1000 &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            logger.websocket(`Attempting to reconnect WebSocket`, {
              contractId: this.contractId,
            });
            this.reconnectAttempts++;
            setTimeout(() => {
              this.reconnect();
            }, this.reconnectDelay * this.reconnectAttempts);
          }
        };
      } catch (error) {
        console.error(
          `❌ Failed to create WebSocket for ${this.contractId}:`,
          error,
        );
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  private reconnect(): void {
    // Prevent multiple reconnection attempts
    if (this.isConnecting) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      logger.websocket(`Attempting to reconnect WebSocket`, {
        contractId: this.contractId,
        attempt: this.reconnectAttempts,
        maxAttempts: this.maxReconnectAttempts,
      });
      this.connect().catch(console.error);
    }, delay);
  }

  disconnect(origin?: string): void {
    this.manualCloseOrigin = origin || this.manualCloseOrigin || "unknown";
    logger.websocket(`Disconnecting WebSocket`, {
      contractId: this.contractId,
      origin: this.manualCloseOrigin,
    });

    this.isConnecting = false;
    this.isConnected = false;

    // Stop heartbeat first
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    // Close WebSocket connection
    if (this.ws) {
      try {
        this.ws.close(1000, "Client disconnect");
      } catch (error) {
        console.warn(
          `Error closing WebSocket for contract ${this.contractId}:`,
          error,
        );
      }
      this.ws = null;
    }

    // Clear message queue
    this.messageQueue = [];
  }

  private startHeartbeat(): void {
    // Clear existing heartbeat
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    // Send heartbeat every 30 seconds
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
        this.lastHeartbeatSentAt = Date.now();
        logger.websocket("Sending heartbeat", {
          contractId: this.contractId,
          sinceLastAckMs: this.lastHeartbeatAckAt
            ? Date.now() - this.lastHeartbeatAckAt
            : null,
        });
        this.sendMessage({ type: "heartbeat" });
      } else {
        // Connection lost, clear heartbeat
        if (this.heartbeatInterval) {
          clearInterval(this.heartbeatInterval);
          this.heartbeatInterval = null;
        }
      }
    }, 30000);
  }

  sendMessage(message: unknown): void {
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      try {
        const messageStr = JSON.stringify(message);
        logger.websocket(`Sending WebSocket message`, {
          contractId: this.contractId,
          messageType: (message as any)?.type || "unknown",
        });
        this.ws.send(messageStr);
      } catch (error) {
        console.error(
          `❌ Error sending WebSocket message for contract ${this.contractId}:`,
          error,
        );
        // Queue message for retry only if it's not a heartbeat
        if ((message as any)?.type !== "heartbeat") {
          this.messageQueue.push(message);
        }
      }
    } else {
      console.warn(
        `⚠️ WebSocket not connected for contract ${this.contractId} (state: ${this.getConnectionState()}), queueing message:`,
        (message as any)?.type || "unknown",
      );
      // Queue non-heartbeat messages for when connection is established
      if ((message as any)?.type !== "heartbeat") {
        this.messageQueue.push(message);
      }
    }
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendMessage(message);
      }
    }
  }

  requestStatus(): void {
    this.sendMessage({ type: "get_status" });
  }

  cancelAnalysis(): void {
    this.sendMessage({ type: "cancel_analysis" });
  }

  // New methods for document-based WebSocket flow
  startAnalysis(analysisOptions = {}): void {
    this.sendMessage({
      type: "start_analysis",
      analysis_options: analysisOptions,
    });
  }

  retryAnalysis(
    retryAttempt = 1,
    analysisOptions?: Record<string, unknown>,
  ): void {
    this.sendMessage({
      type: "retry_analysis",
      retry_attempt: retryAttempt,
      ...(analysisOptions ? { analysis_options: analysisOptions } : {}),
    });
  }

  isWebSocketConnected(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return "disconnected";
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return "connecting";
      case WebSocket.OPEN:
        return "open";
      case WebSocket.CLOSING:
        return "closing";
      case WebSocket.CLOSED:
        return "closed";
      default:
        return "unknown";
    }
  }
}

// WebSocket Connection Manager to prevent multiple connections
class WebSocketConnectionManager {
  private static instance: WebSocketConnectionManager;
  private connections: Map<string, WebSocketService> = new Map();

  static getInstance(): WebSocketConnectionManager {
    if (!WebSocketConnectionManager.instance) {
      WebSocketConnectionManager.instance = new WebSocketConnectionManager();
    }
    return WebSocketConnectionManager.instance;
  }

  getConnection(documentId: string): WebSocketService | null {
    return this.connections.get(documentId) || null;
  }

  createConnection(documentId: string): WebSocketService {
    logger.websocket(`Creating WebSocket connection for document`, {
      documentId,
    });

    // Close existing connection if any
    const existing = this.connections.get(documentId);
    if (existing) {
      logger.websocket(`Closing existing connection for document`, {
        documentId,
      });
      existing.disconnect("connectionManager.createConnection");
      this.connections.delete(documentId);
    }

    const connection = new WebSocketService(documentId);
    this.connections.set(documentId, connection);
    logger.websocket(`WebSocket connection created and registered`, {
      documentId,
    });
    return connection;
  }

  removeConnection(documentId: string): void {
    const connection = this.connections.get(documentId);
    if (connection) {
      connection.disconnect("connectionManager.removeConnection");
      this.connections.delete(documentId);
    }
  }

  disconnectAll(): void {
    for (const [, connection] of this.connections) {
      connection.disconnect("connectionManager.disconnectAll");
    }
    this.connections.clear();
  }

  getActiveConnections(): string[] {
    return Array.from(this.connections.keys()).filter((documentId) => {
      const connection = this.connections.get(documentId);
      return connection?.isWebSocketConnected();
    });
  }
}

// Export singleton instances
export const apiService = new ApiService();
export const wsConnectionManager = WebSocketConnectionManager.getInstance();
export default apiService;

// Cleanup connections on page unload
window.addEventListener("beforeunload", () => {
  logger.websocket("beforeunload: disconnecting all WebSocket connections");
  wsConnectionManager.disconnectAll();
});

// Optional: disconnect on page visibility hidden after a configurable delay
let __wsHiddenDisconnectTimer: ReturnType<typeof setTimeout> | null = null;
const WS_HIDDEN_DISCONNECT_MS = Number(
  (import.meta.env.VITE_WS_HIDDEN_DISCONNECT_MS as string) || 0,
);

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    logger.websocket("visibilitychange(hidden): page hidden");
    if (WS_HIDDEN_DISCONNECT_MS > 0) {
      if (__wsHiddenDisconnectTimer) {
        clearTimeout(__wsHiddenDisconnectTimer);
      }
      __wsHiddenDisconnectTimer = setTimeout(() => {
        logger.websocket(
          "visibility hidden timeout reached: disconnecting all WebSocket connections",
          { timeoutMs: WS_HIDDEN_DISCONNECT_MS },
        );
        wsConnectionManager.disconnectAll();
      }, WS_HIDDEN_DISCONNECT_MS);
    }
  } else {
    // Page visible again: cancel any pending hidden disconnect
    logger.websocket(
      "visibilitychange(visible): clearing hidden disconnect timer",
    );
    if (__wsHiddenDisconnectTimer) {
      clearTimeout(__wsHiddenDisconnectTimer);
      __wsHiddenDisconnectTimer = null;
    }
  }
});
