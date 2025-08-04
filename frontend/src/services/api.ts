import axios, { AxiosInstance, AxiosError } from "axios";
import {
  User,
  UserRegistrationRequest,
  UserLoginRequest,
  AuthResponse,
  DocumentUploadResponse,
  DocumentDetails,
  ContractAnalysisRequest,
  ContractAnalysisResponse,
  ContractAnalysisResult,
  UsageStats,
} from "@/types";

// API Configuration
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiService {
  private client: AxiosInstance;
  private token: string | null = null;

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
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          // Redirect to login or emit event for auth state update
          window.dispatchEvent(new CustomEvent("auth:unauthorized"));
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage
    this.loadToken();
  }

  // Token management
  setToken(token: string): void {
    this.token = token;
    localStorage.setItem("auth_token", token);
  }

  clearToken(): void {
    this.token = null;
    localStorage.removeItem("auth_token");
  }

  private loadToken(): void {
    const token = localStorage.getItem("auth_token");
    if (token) {
      this.token = token;
    }
  }

  // Authentication endpoints
  async register(data: UserRegistrationRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>(
      "/api/auth/register",
      data
    );
    return response.data;
  }

  async login(data: UserLoginRequest): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>(
      "/api/auth/login",
      data
    );
    if (response.data.access_token) {
      this.setToken(response.data.access_token);
    }
    return response.data;
  }

  async logout(): Promise<void> {
    this.clearToken();
    // Could call logout endpoint if it exists
  }

  // User endpoints
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>("/api/users/profile");
    return response.data;
  }

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>(
      "/api/users/profile",
      userData
    );
    return response.data;
  }

  async updateUserPreferences(preferences: Record<string, any>): Promise<void> {
    await this.client.put("/api/users/preferences", preferences);
  }

  async getUserStats(): Promise<UsageStats> {
    const response = await this.client.get<UsageStats>(
      "/api/users/usage-stats"
    );
    return response.data;
  }

  // Document endpoints
  async uploadDocument(
    file: File,
    contractType: string = "purchase_agreement",
    australianState: string = "NSW"
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
            (progressEvent.loaded * 100) / (progressEvent.total || 1)
          );
          // Emit progress event
          window.dispatchEvent(
            new CustomEvent("upload:progress", {
              detail: { progress: percentCompleted },
            })
          );
        },
      }
    );
    return response.data;
  }

  async getDocument(documentId: string): Promise<DocumentDetails> {
    const response = await this.client.get<DocumentDetails>(
      `/api/documents/${documentId}`
    );
    return response.data;
  }

  // Contract analysis endpoints
  async startAnalysis(
    data: ContractAnalysisRequest
  ): Promise<ContractAnalysisResponse> {
    const response = await this.client.post<ContractAnalysisResponse>(
      "/api/contracts/analyze",
      data
    );
    return response.data;
  }

  async getAnalysisResult(contractId: string): Promise<ContractAnalysisResult> {
    const response = await this.client.get<ContractAnalysisResult>(
      `/api/contracts/${contractId}/analysis`
    );
    return response.data;
  }

  async deleteAnalysis(contractId: string): Promise<void> {
    await this.client.delete(`/api/contracts/${contractId}`);
  }

  async downloadReport(
    contractId: string,
    format: string = "pdf"
  ): Promise<string> {
    const response = await this.client.get(
      `/api/contracts/${contractId}/report?format=${format}`
    );
    return response.data.download_url;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }

  // Generic error handler
  handleError(error: AxiosError): string {
    if (error.response) {
      // Server responded with error status
      const data = error.response.data as any;
      return data?.detail || data?.message || "Server error occurred";
    } else if (error.request) {
      // Request made but no response received
      return "Network error - please check your connection";
    } else {
      // Something else happened
      return error.message || "An unexpected error occurred";
    }
  }
}

// WebSocket Service for real-time updates
export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(contractId: string) {
    const wsUrl = API_BASE_URL.replace("http", "ws");
    this.url = `${wsUrl}/ws/contracts/${contractId}/progress`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log("WebSocket connected");
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            // Emit custom event for components to listen to
            window.dispatchEvent(
              new CustomEvent("analysis:update", {
                detail: data,
              })
            );
          } catch (error) {
            console.error("Error parsing WebSocket message:", error);
          }
        };

        this.ws.onclose = (event) => {
          console.log("WebSocket disconnected:", event.code, event.reason);
          if (
            event.code !== 1000 &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            this.reconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private reconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(
        `Attempting to reconnect WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
      );
      this.connect().catch(console.error);
    }, delay);
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
