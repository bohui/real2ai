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

  // Onboarding endpoints
  async getOnboardingStatus(): Promise<{
    onboarding_completed: boolean;
    onboarding_completed_at?: string;
    onboarding_preferences: Record<string, any>;
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
      onboarding_preferences: preferences
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
    const response = await this.retryRequest(
      () => this.client.get<any>(`/api/contracts/${contractId}/analysis`),
      3, // max retries
      1000 // initial delay
    );
    
    // Transform API response to match frontend expectations
    const apiData = response.data;
    const analysisResult = apiData.analysis_result || {};
    
    // Create executive summary from available data
    const executiveSummary = {
      overall_risk_score: analysisResult.risk_assessment?.overall_risk_score || apiData.risk_score || 0,
      compliance_status: analysisResult.compliance_check?.state_compliance ? 'compliant' : 'non-compliant',
      total_recommendations: analysisResult.recommendations?.length || 0,
      critical_issues: analysisResult.recommendations?.filter((r: any) => r.priority === 'critical')?.length || 0,
      confidence_level: analysisResult.overall_confidence || 0.8
    };
    
    // Transform to match ContractAnalysisResult interface
    const transformedResult: ContractAnalysisResult = {
      contract_id: apiData.contract_id,
      analysis_id: analysisResult.analysis_id || apiData.contract_id,
      analysis_timestamp: analysisResult.analysis_timestamp || apiData.created_at,
      user_id: analysisResult.user_id || '',
      australian_state: analysisResult.australian_state || 'NSW',
      analysis_status: apiData.analysis_status || 'completed',
      contract_terms: analysisResult.contract_terms || {},
      risk_assessment: {
        overall_risk_score: analysisResult.risk_assessment?.overall_risk_score || apiData.risk_score || 0,
        risk_factors: analysisResult.risk_assessment?.risk_factors || []
      },
      compliance_check: analysisResult.compliance_check || {
        state_compliance: false,
        compliance_issues: [],
        cooling_off_compliance: false,
        cooling_off_details: {},
        mandatory_disclosures: [],
        warnings: [],
        legal_references: []
      },
      recommendations: analysisResult.recommendations || [],
      confidence_scores: analysisResult.confidence_scores || {},
      overall_confidence: analysisResult.overall_confidence || 0.8,
      processing_time: apiData.processing_time || 0,
      analysis_version: analysisResult.processing_summary?.analysis_version || '1.0',
      executive_summary: executiveSummary
    };
    
    return transformedResult;
  }

  async deleteAnalysis(contractId: string): Promise<void> {
    await this.retryRequest(
      () => this.client.delete(`/api/contracts/${contractId}`),
      2, // fewer retries for delete operations
      1000
    );
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

  // Enhanced error handler with retry logic
  handleError(error: AxiosError): string {
    if (error.response) {
      // Server responded with error status
      const data = error.response.data as any;
      const status = error.response.status;
      
      // Handle specific status codes
      switch (status) {
        case 400:
          return data?.detail || "Invalid request. Please check your input.";
        case 401:
          return "Authentication required. Please log in again.";
        case 403:
          return "Access denied. You don't have permission for this action.";
        case 404:
          return data?.detail || "The requested resource was not found.";
        case 409:
          return data?.detail || "Conflict with existing data.";
        case 422:
          return data?.detail || "Validation error. Please check your input.";
        case 429:
          return "Rate limit exceeded. Please try again later.";
        case 500:
          return "Server error. Please try again later.";
        case 502:
        case 503:
        case 504:
          return "Service temporarily unavailable. Please try again later.";
        default:
          return data?.detail || data?.message || `Server error (${status})`;
      }
    } else if (error.request) {
      // Request made but no response received
      if (error.code === 'ECONNABORTED') {
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
    delay: number = 1000
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
        const shouldRetry = 
          !axiosError.response || 
          axiosError.response.status >= 500 ||
          axiosError.response.status === 408 ||
          axiosError.response.status === 429;
          
        if (!shouldRetry) {
          throw error;
        }
        
        // Wait before retry with exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay * attempt));
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
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isConnected = false;
  private contractId: string;
  private messageQueue: any[] = [];

  constructor(contractId: string) {
    const wsUrl = API_BASE_URL.replace("http", "ws");
    const token = localStorage.getItem("auth_token");
    this.contractId = contractId;
    this.url = `${wsUrl}/ws/contracts/${contractId}?token=${encodeURIComponent(token || "")}`;
  }

  connect(): Promise<void> {
    // Prevent multiple connection attempts
    if (this.isConnecting || this.isConnected) {
      console.log(`WebSocket already connecting/connected for contract ${this.contractId}`);
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      try {
        this.isConnecting = true;
        
        // Close existing connection if any
        if (this.ws) {
          console.log(`Closing existing WebSocket for contract ${this.contractId}`);
          this.ws.close(1000, "Reconnecting");
          this.ws = null;
        }

        // Validate URL before creating WebSocket
        if (!this.url || !this.url.startsWith('ws')) {
          throw new Error(`Invalid WebSocket URL: ${this.url}`);
        }

        console.log(`Creating new WebSocket connection for contract ${this.contractId}: ${this.url}`);
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log(`WebSocket connected for contract ${this.contractId}`);
          this.reconnectAttempts = 0;
          this.isConnecting = false;
          this.isConnected = true;
          
          // Start heartbeat
          this.startHeartbeat();
          
          // Process queued messages
          this.processMessageQueue();
          
          // Request initial status after a brief delay to ensure connection is stable
          setTimeout(() => {
            if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
              this.sendMessage({ type: "get_status" });
            }
          }, 100);
          
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log(`WebSocket message received for contract ${this.contractId}:`, data.event_type);
            
            // Validate message structure
            if (!data.event_type) {
              console.warn(`Invalid WebSocket message format for contract ${this.contractId}:`, data);
              return;
            }
            
            // Emit custom event for components to listen to
            window.dispatchEvent(
              new CustomEvent("analysis:update", {
                detail: data,
              })
            );
          } catch (error) {
            console.error(`Error parsing WebSocket message for contract ${this.contractId}:`, error, event.data);
          }
        };

        this.ws.onclose = (event) => {
          console.log(`WebSocket disconnected for contract ${this.contractId}:`, event.code, event.reason);
          this.isConnecting = false;
          this.isConnected = false;
          
          // Only reconnect if it wasn't a clean disconnect (1000) and we haven't exceeded max attempts
          if (
            event.code !== 1000 &&
            event.code !== 1001 && // Going away
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            this.reconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error(`WebSocket error for contract ${this.contractId}:`, error);
          this.isConnecting = false;
          this.isConnected = false;
          reject(error);
        };
      } catch (error) {
        this.isConnecting = false;
        this.isConnected = false;
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
      console.log(
        `Attempting to reconnect WebSocket for contract ${this.contractId} (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
      );
      this.connect().catch(console.error);
    }, delay);
  }

  disconnect(): void {
    console.log(`Disconnecting WebSocket for contract ${this.contractId}`);
    
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
        console.warn(`Error closing WebSocket for contract ${this.contractId}:`, error);
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

  sendMessage(message: any): void {
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      try {
        const messageStr = JSON.stringify(message);
        console.log(`Sending WebSocket message for contract ${this.contractId}:`, message.type);
        this.ws.send(messageStr);
      } catch (error) {
        console.error(`Error sending WebSocket message for contract ${this.contractId}:`, error);
        // Queue message for retry only if it's not a heartbeat
        if (message.type !== 'heartbeat') {
          this.messageQueue.push(message);
        }
      }
    } else {
      console.warn(`WebSocket not connected for contract ${this.contractId} (state: ${this.getConnectionState()}), queueing message:`, message.type);
      // Queue non-heartbeat messages for when connection is established
      if (message.type !== 'heartbeat') {
        this.messageQueue.push(message);
      }
    }
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected) {
      const message = this.messageQueue.shift();
      this.sendMessage(message);
    }
  }

  requestStatus(): void {
    this.sendMessage({ type: "get_status" });
  }

  cancelAnalysis(): void {
    this.sendMessage({ type: "cancel_analysis" });
  }

  isWebSocketConnected(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected';
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'open';
      case WebSocket.CLOSING: return 'closing';
      case WebSocket.CLOSED: return 'closed';
      default: return 'unknown';
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

  getConnection(contractId: string): WebSocketService | null {
    return this.connections.get(contractId) || null;
  }

  createConnection(contractId: string): WebSocketService {
    console.log(`Creating WebSocket connection for contract ${contractId}`);
    
    // Close existing connection if any
    const existing = this.connections.get(contractId);
    if (existing) {
      console.log(`Closing existing connection for contract ${contractId}`);
      existing.disconnect();
      this.connections.delete(contractId);
    }

    const connection = new WebSocketService(contractId);
    this.connections.set(contractId, connection);
    console.log(`WebSocket connection created and registered for contract ${contractId}`);
    return connection;
  }

  removeConnection(contractId: string): void {
    const connection = this.connections.get(contractId);
    if (connection) {
      connection.disconnect();
      this.connections.delete(contractId);
    }
  }

  disconnectAll(): void {
    for (const [contractId, connection] of this.connections) {
      connection.disconnect();
    }
    this.connections.clear();
  }

  getActiveConnections(): string[] {
    return Array.from(this.connections.keys()).filter(contractId => {
      const connection = this.connections.get(contractId);
      return connection?.isWebSocketConnected();
    });
  }
}

// Export singleton instances
export const apiService = new ApiService();
export const wsConnectionManager = WebSocketConnectionManager.getInstance();
export default apiService;

// Cleanup connections on page unload
window.addEventListener('beforeunload', () => {
  wsConnectionManager.disconnectAll();
});

// Cleanup connections on page visibility change (mobile Safari)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    // Page is hidden, disconnect WebSockets to save resources
    wsConnectionManager.disconnectAll();
  }
});
