import { create } from "zustand";
import {
  AnalysisProgressUpdate,
  ContractAnalysisRequest,
  ContractAnalysisResult,
  DocumentDetails,
} from "@/types";
import {
  apiService,
  WebSocketService,
  wsConnectionManager,
} from "@/services/api";

interface AnalysisState {
  // Current analysis state
  currentDocument: DocumentDetails | null;
  currentAnalysis: ContractAnalysisResult | null;
  analysisProgress: AnalysisProgressUpdate | null;

  // Upload state
  isUploading: boolean;
  uploadProgress: number;

  // Analysis state
  isAnalyzing: boolean;
  analysisError: string | null;

  // WebSocket
  wsService: WebSocketService | null;
  wsEventListener: ((event: any) => void) | null;
  currentDocumentId: string | null;
  currentContractId: string | null;
  cacheStatus: "complete" | "in_progress" | "failed" | "miss" | null;

  // Recent analyses
  recentAnalyses: ContractAnalysisResult[];

  // Actions
  uploadDocument: (
    file: File,
    contractType: string,
    state: string,
  ) => Promise<string>;
  prepareContractAndConnect: (
    documentId: string,
    contractType: string,
    state: string,
  ) => Promise<string>;
  startAnalysis: (request: ContractAnalysisRequest) => Promise<void>;
  connectDocumentWebSocket: (documentId: string) => Promise<void>;
  connectWebSocket: (contractId: string) => Promise<void>;
  disconnectWebSocket: () => void;
  handleCacheStatus: (cacheData: any) => void;
  triggerAnalysisStart: () => Promise<void>;
  triggerAnalysisRetry: () => Promise<void>;
  updateProgress: (progress: AnalysisProgressUpdate) => void;
  setAnalysisResult: (result: ContractAnalysisResult) => void;
  clearCurrentAnalysis: () => void;
  addRecentAnalysis: (analysis: ContractAnalysisResult) => void;
  deleteAnalysis: (contractId: string) => Promise<void>;
  setError: (error: string | null) => void;
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  // Initial state
  currentDocument: null,
  currentAnalysis: null,
  analysisProgress: null,
  isUploading: false,
  uploadProgress: 0,
  isAnalyzing: false,
  analysisError: null,
  wsService: null,
  wsEventListener: null,
  currentDocumentId: null,
  currentContractId: null,
  cacheStatus: null,
  recentAnalyses: [],

  uploadDocument: async (file: File, contractType: string, state: string) => {
    console.log("🚀 Starting upload process...", {
      filename: file.name,
      contractType,
      state,
    });
    set({
      isUploading: true,
      uploadProgress: 0,
      analysisError: null,
      cacheStatus: null,
    });

    try {
      // Listen for upload progress
      const handleProgress = (event: any) => {
        console.log("📊 Upload progress:", event.detail.progress);
        set({ uploadProgress: event.detail.progress });
      };
      window.addEventListener(
        "upload:progress",
        handleProgress as EventListener,
      );

      console.log("📤 Uploading document...");
      const response = await apiService.uploadDocument(
        file,
        contractType,
        state,
      );
      console.log("✅ Upload API response:", response);

      // Get document details
      console.log("📄 Fetching document details...");
      const document = await apiService.getDocument(response.document_id);
      console.log("✅ Document details fetched:", document);

      set({
        currentDocument: document,
        isUploading: false,
        uploadProgress: 100,
      });

      window.removeEventListener(
        "upload:progress",
        handleProgress as EventListener,
      );

      // 🎆 KEY CHANGE: Connect WebSocket IMMEDIATELY after upload
      console.log("🔌 Connecting WebSocket immediately after upload...");
      console.log("📋 Document ID for WebSocket:", response.document_id);
      console.log("🔍 Current store state before WebSocket connection:", {
        currentDocumentId: get().currentDocumentId,
        wsService: get().wsService ? "exists" : "null",
        isConnected: get().wsService?.isWebSocketConnected() || false,
      });

      try {
        await get().connectDocumentWebSocket(response.document_id);
        console.log("✅ WebSocket connected successfully after upload");
        console.log("🔍 Store state after WebSocket connection:", {
          currentDocumentId: get().currentDocumentId,
          wsService: get().wsService ? "exists" : "null",
          isConnected: get().wsService?.isWebSocketConnected() || false,
        });
      } catch (wsError) {
        console.error("❌ WebSocket connection failed after upload:", wsError);
        console.error("🔍 WebSocket error details:", {
          error: wsError,
          message: wsError instanceof Error ? wsError.message : String(wsError),
          stack: wsError instanceof Error ? wsError.stack : undefined,
        });
        // Don't fail the upload, just show a warning
        set({
          analysisError:
            `Document uploaded but real-time updates unavailable: ${
              wsError instanceof Error
                ? wsError.message
                : "WebSocket connection failed"
            }`,
        });
      }

      return response.document_id;
    } catch (error: unknown) {
      console.error("❌ Upload process failed:", error);
      console.error("🔍 Upload error details:", {
        error,
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      set({
        isUploading: false,
        uploadProgress: 0,
        analysisError: apiService.handleError(error as any),
      });
      throw error;
    }
  },

  prepareContractAndConnect: async (
    documentId: string,
    contractType: string,
    state: string,
  ) => {
    console.log("🏠 Preparing contract and WebSocket connection...", {
      documentId,
      contractType,
      state,
    });

    try {
      // Call the prepare contract endpoint to get contract_id
      console.log("📄 Creating contract record...");
      const response = await apiService.prepareContract({
        document_id: documentId,
        contract_type: contractType,
        australian_state: state,
      });

      console.log("✅ Contract prepared successfully:", response);

      // Connect WebSocket immediately with the contract_id
      console.log("🔌 Connecting WebSocket for real-time updates...");
      await get().connectWebSocket(response.contract_id);

      console.log(
        `✅ Contract prepared and WebSocket connected for contract ${response.contract_id}`,
      );
      return response.contract_id;
    } catch (error: unknown) {
      console.error(
        "❌ Failed to prepare contract and connect WebSocket:",
        error,
      );
      set({
        analysisError: `Failed to prepare analysis: ${
          apiService.handleError(error as any)
        }`,
      });
      throw error;
    }
  },

  connectDocumentWebSocket: async (documentId: string) => {
    const state = get();

    console.log(
      `🔌 Attempting to connect WebSocket for document: ${documentId}`,
    );
    console.log("🔍 Initial state check:", {
      currentDocumentId: state.currentDocumentId,
      wsService: state.wsService ? "exists" : "null",
      isConnected: state.wsService?.isWebSocketConnected() || false,
    });

    // Validate document ID
    if (!documentId || documentId.trim() === "") {
      const error = "Document ID is required for WebSocket connection";
      console.error(`❌ ${error}`);
      throw new Error(error);
    }

    // Don't reconnect to the same document
    if (
      state.currentDocumentId === documentId &&
      state.wsService?.isWebSocketConnected()
    ) {
      console.log(`✅ Already connected to document ${documentId}`);
      return;
    }

    // Disconnect existing connection
    console.log("🧽 Disconnecting any existing WebSocket connection...");
    get().disconnectWebSocket();

    // Use connection manager to prevent duplicate connections
    console.log(
      "🏠 Creating new WebSocket connection via connection manager...",
    );
    console.log("🔍 Connection manager state before creation:", {
      activeConnections: wsConnectionManager.getActiveConnections(),
      existingConnection: wsConnectionManager.getConnection(documentId)
        ? "exists"
        : "null",
    });

    const wsService = wsConnectionManager.createConnection(documentId);
    console.log("✅ WebSocket service created:", {
      serviceExists: !!wsService,
      serviceState: wsService.getConnectionState(),
    });

    // Create event handler with proper cleanup
    const handleUpdate = (event: any) => {
      const data = event.detail;

      console.log(
        `📨 Processing WebSocket event for document ${documentId}:`,
        data.event_type,
        data,
      );

      switch (data.event_type) {
        case "cache_status":
          // Handle initial cache status response
          console.log("📊 Cache status received:", data.data);
          get().handleCacheStatus(data.data);
          break;

        case "document_uploaded":
          // Handle document uploaded event
          console.log(
            `📄 Document uploaded event received for document ${documentId}:`,
            data.data,
          );
          set({
            currentDocument: {
              id: data.data.document_id,
              user_id: "", // Will be set by the backend
              filename: data.data.filename,
              file_type: "unknown", // Will be updated when document details are fetched
              file_size: 0, // Will be updated when document details are fetched
              status: data.data.processing_status as
                | "uploaded"
                | "processing"
                | "processed"
                | "failed",
              storage_path: "", // Will be set by the backend
              created_at: new Date().toISOString(),
            } as DocumentDetails,
          });
          break;

        case "connection_established":
          console.log(
            `🔗 WebSocket connection established for document ${documentId}`,
          );
          set({
            currentDocumentId: documentId,
            currentContractId: data.data.contract_id,
          });
          break;

        case "analysis_progress":
          console.log("📈 Analysis progress received:", data.data);
          get().updateProgress(data.data as AnalysisProgressUpdate);
          break;

        case "analysis_completed":
          console.log("✅ Analysis completed event received");
          // Fetch full analysis result
          const contractId = get().currentContractId;
          if (contractId) {
            console.log(
              "📄 Fetching analysis result for contract:",
              contractId,
            );
            apiService.getAnalysisResult(contractId)
              .then((result) => {
                console.log("✅ Analysis result fetched:", result);
                get().setAnalysisResult(result);
                get().addRecentAnalysis(result);
                set({ isAnalyzing: false, analysisError: null });
              })
              .catch((error) => {
                console.error("❌ Failed to fetch analysis result:", error);
                set({
                  analysisError: `Failed to load analysis results: ${
                    apiService.handleError(error)
                  }`,
                });
              });
          }
          break;

        case "analysis_failed":
          console.log("❌ Analysis failed event received:", data.data);
          set({
            isAnalyzing: false,
            analysisError: data.data?.error_message || "Analysis failed",
            cacheStatus: "failed",
          });
          break;

        case "heartbeat":
          // Heartbeat received, connection is alive
          console.log("💓 WebSocket heartbeat received");
          break;

        default:
          console.log("❓ Unknown WebSocket event:", data.event_type, data);
      }
    };

    set({
      wsService,
      wsEventListener: handleUpdate,
      currentDocumentId: documentId,
    });

    try {
      console.log("🔗 Establishing WebSocket connection...");
      console.log("🔍 WebSocket service state before connect:", {
        serviceExists: !!wsService,
        serviceState: wsService.getConnectionState(),
        url: wsService.getConnectionState(), // This will show the URL in the state
      });

      await wsService.connect();
      console.log("✅ WebSocket connection established successfully");

      console.log("🎧 Adding document analysis update event listener...");
      window.addEventListener("analysis:update", handleUpdate as EventListener);

      console.log(
        `✅ WebSocket successfully connected and configured for document ${documentId}`,
      );
      console.log("🔍 Final WebSocket state:", {
        currentDocumentId: get().currentDocumentId,
        wsService: get().wsService ? "exists" : "null",
        isConnected: get().wsService?.isWebSocketConnected() || false,
        connectionState: get().wsService?.getConnectionState() || "unknown",
      });
    } catch (error) {
      console.error(
        `❌ WebSocket connection failed for document ${documentId}:`,
        error,
      );
      console.error("🔍 WebSocket connection error details:", {
        error,
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
        documentId,
        serviceState: wsService.getConnectionState(),
      });

      // Clean up the failed connection
      wsConnectionManager.removeConnection(documentId);

      set({
        analysisError: `Failed to establish real-time connection: ${
          error instanceof Error ? error.message : "Connection error"
        }`,
        wsService: null,
        wsEventListener: null,
        currentDocumentId: null,
      });

      // Re-throw the error so calling code can handle it
      throw error;
    }
  },

  startAnalysis: async (request: ContractAnalysisRequest) => {
    set({ isAnalyzing: true, analysisError: null, analysisProgress: null });

    try {
      console.log("📡 Starting contract analysis...", request);
      const response = await apiService.startAnalysis(request);
      console.log("✅ Analysis API call successful:", response);

      // Connect WebSocket for real-time updates
      try {
        console.log("🔌 Connecting WebSocket for real-time updates...");
        await get().connectWebSocket(response.contract_id);
        console.log("✅ WebSocket connection established successfully");
      } catch (wsError) {
        console.error("❌ WebSocket connection failed:", wsError);
        // Continue without WebSocket - show warning but don't fail analysis
        set({
          analysisError: `Analysis started but real-time updates unavailable: ${
            wsError instanceof Error
              ? wsError.message
              : "WebSocket connection failed"
          }`,
        });
        // Don't throw - let analysis continue without real-time updates
      }
    } catch (error: unknown) {
      console.error("❌ Analysis start failed:", error);
      set({
        isAnalyzing: false,
        analysisError: apiService.handleError(error as any),
      });
      throw error;
    }
  },

  connectWebSocket: async (contractId: string) => {
    const state = get();

    console.log(
      `🔌 Attempting to connect WebSocket for contract: ${contractId}`,
    );

    // Validate contract ID
    if (!contractId || contractId.trim() === "") {
      const error = "Contract ID is required for WebSocket connection";
      console.error(`❌ ${error}`);
      throw new Error(error);
    }

    // Don't reconnect to the same contract
    if (
      state.currentContractId === contractId &&
      state.wsService?.isWebSocketConnected()
    ) {
      console.log(`✅ Already connected to contract ${contractId}`);
      return;
    }

    // Disconnect existing connection
    console.log("🧽 Disconnecting any existing WebSocket connection...");
    get().disconnectWebSocket();

    // Use connection manager to prevent duplicate connections
    console.log(
      "🏠 Creating new WebSocket connection via connection manager...",
    );
    const wsService = wsConnectionManager.createConnection(contractId);

    // Create event handler with proper cleanup
    const handleUpdate = (event: any) => {
      const data = event.detail;

      // Ensure this event is for the current contract
      if (data.data?.contract_id && data.data.contract_id !== contractId) {
        console.log(
          `Ignoring WebSocket event for different contract: ${data.data.contract_id} (expected: ${contractId})`,
        );
        return;
      }

      console.log(
        `Processing WebSocket event for contract ${contractId}:`,
        data.event_type,
      );

      switch (data.event_type) {
        case "analysis_progress":
          get().updateProgress(data.data as AnalysisProgressUpdate);
          break;

        case "analysis_completed":
          // Fetch full analysis result
          apiService.getAnalysisResult(contractId)
            .then((result) => {
              get().setAnalysisResult(result);
              get().addRecentAnalysis(result);
              set({ isAnalyzing: false, analysisError: null });
            })
            .catch((error) => {
              console.error("Failed to fetch analysis result:", error);
              // Keep analyzing state to prevent blank page and show error
              set({
                analysisError: `Failed to load analysis results: ${
                  apiService.handleError(error)
                }`,
                // Don't set isAnalyzing to false to avoid blank page
                // Instead, show error while maintaining loading state context
              });

              // Retry fetching the result after a delay
              setTimeout(() => {
                apiService.getAnalysisResult(contractId)
                  .then((result) => {
                    get().setAnalysisResult(result);
                    get().addRecentAnalysis(result);
                    set({ isAnalyzing: false, analysisError: null });
                  })
                  .catch((retryError) => {
                    console.error(
                      "Retry failed for analysis result:",
                      retryError,
                    );
                    // After retry fails, stop loading and show error
                    set({
                      isAnalyzing: false,
                      analysisError:
                        `Analysis completed but results unavailable: ${
                          apiService.handleError(retryError)
                        }`,
                    });
                  });
              }, 2000); // Retry after 2 seconds
            });
          break;

        case "analysis_failed":
          set({
            isAnalyzing: false,
            analysisError: data.data?.error_message || "Analysis failed",
          });
          break;

        case "connection_established":
          console.log(
            `WebSocket connection established for contract ${contractId}`,
          );
          break;

        case "heartbeat":
          // Heartbeat received, connection is alive
          break;

        default:
          console.log("Received WebSocket event:", data.event_type, data);
      }
    };

    set({
      wsService,
      wsEventListener: handleUpdate,
      currentContractId: contractId,
    });

    try {
      console.log("🔗 Establishing WebSocket connection...");
      await wsService.connect();

      console.log("🎧 Adding analysis update event listener...");
      window.addEventListener("analysis:update", handleUpdate as EventListener);

      console.log(
        `✅ WebSocket successfully connected and configured for contract ${contractId}`,
      );
    } catch (error) {
      console.error(
        `❌ WebSocket connection failed for contract ${contractId}:`,
        error,
      );

      // Clean up the failed connection
      wsConnectionManager.removeConnection(contractId);

      set({
        analysisError: `Failed to establish real-time connection: ${
          error instanceof Error ? error.message : "Connection error"
        }`,
        wsService: null,
        wsEventListener: null,
        currentContractId: null,
      });

      // Re-throw the error so calling code can handle it
      throw error;
    }
  },

  handleCacheStatus: (cacheData: any) => {
    console.log("📊 Cache status received:", cacheData);

    const { cache_status, contract_id, analysis_result, error_message } =
      cacheData;

    set({
      cacheStatus: cache_status,
      currentContractId: contract_id,
    });

    switch (cache_status) {
      case "complete":
        console.log("✅ Cache HIT COMPLETE - Analysis results ready!");
        if (analysis_result) {
          // Transform and set the analysis result immediately
          get().setAnalysisResult(analysis_result as ContractAnalysisResult);
          get().addRecentAnalysis(analysis_result as ContractAnalysisResult);
        }
        set({ isAnalyzing: false, analysisError: null });
        break;

      case "in_progress":
        console.log("🔄 Cache HIT IN_PROGRESS - Joining existing analysis");
        set({ isAnalyzing: true, analysisError: null });
        // Progress updates will come via WebSocket events
        break;

      case "failed":
        console.log("❌ Cache HIT FAILED - Previous analysis failed");
        set({
          isAnalyzing: false,
          analysisError: error_message ||
            "Previous analysis failed - retry available",
        });
        break;

      case "miss":
        console.log("🆕 Cache MISS - New document, will start analysis");
        // Frontend should trigger analysis start
        set({ isAnalyzing: false, analysisError: null });
        break;

      default:
        console.warn("❓ Unknown cache status:", cache_status);
    }
  },

  triggerAnalysisStart: async () => {
    const { wsService, currentDocumentId } = get();

    if (!wsService || !currentDocumentId) {
      throw new Error("WebSocket not connected or document ID missing");
    }

    console.log("🎆 Triggering analysis start via WebSocket...");

    set({ isAnalyzing: true, analysisError: null });

    // Send start analysis message via WebSocket
    wsService.startAnalysis({
      include_financial_analysis: true,
      include_risk_assessment: true,
      include_compliance_check: true,
      include_recommendations: true,
    });
  },

  triggerAnalysisRetry: async () => {
    const { wsService, currentDocumentId } = get();

    if (!wsService || !currentDocumentId) {
      throw new Error("WebSocket not connected or document ID missing");
    }

    console.log("🔄 Triggering analysis retry via WebSocket...");

    set({ isAnalyzing: true, analysisError: null });

    // Send retry analysis message via WebSocket
    wsService.retryAnalysis();
  },

  disconnectWebSocket: () => {
    const { wsService, wsEventListener, currentDocumentId } = get();

    console.log(`Disconnecting WebSocket for document ${currentDocumentId}`);

    if (wsService) {
      wsService.disconnect();
    }

    // Also remove from connection manager
    if (currentDocumentId) {
      wsConnectionManager.removeConnection(currentDocumentId);
    }

    // Remove event listener with proper reference
    if (wsEventListener) {
      window.removeEventListener(
        "analysis:update",
        wsEventListener as EventListener,
      );
    }

    set({
      wsService: null,
      wsEventListener: null,
      currentDocumentId: null,
      currentContractId: null,
      cacheStatus: null,
    });
  },

  updateProgress: (progress: AnalysisProgressUpdate) => {
    set({ analysisProgress: progress });
  },

  setAnalysisResult: (result: ContractAnalysisResult) => {
    set({ currentAnalysis: result });
  },

  clearCurrentAnalysis: () => {
    console.log("Clearing current analysis and disconnecting WebSocket");
    get().disconnectWebSocket();
    set({
      currentDocument: null,
      currentAnalysis: null,
      analysisProgress: null,
      isUploading: false,
      uploadProgress: 0,
      isAnalyzing: false,
      analysisError: null,
      cacheStatus: null,
    });
  },

  addRecentAnalysis: (analysis: ContractAnalysisResult) => {
    // Validate that analysis has required properties before adding
    if (!analysis.contract_id || !analysis.analysis_timestamp) {
      console.warn("Skipping invalid analysis for recent list:", analysis);
      return;
    }

    // Ensure executive_summary exists with fallback values
    if (!analysis.executive_summary) {
      console.warn(
        "Analysis missing executive_summary, creating fallback:",
        analysis.contract_id,
      );
      analysis.executive_summary = {
        overall_risk_score: analysis.risk_assessment?.overall_risk_score || 0,
        compliance_status: analysis.compliance_check?.state_compliance
          ? "compliant"
          : "non-compliant",
        total_recommendations: analysis.recommendations?.length || 0,
        critical_issues: analysis.recommendations?.filter((r) =>
          r.priority === "critical"
        )?.length || 0,
        confidence_level: analysis.overall_confidence || 0.8,
      };
    }

    const recent = get().recentAnalyses;
    const updated = [
      analysis,
      ...recent.filter((a) => a.contract_id !== analysis.contract_id),
    ]
      .slice(0, 10); // Keep only 10 most recent

    set({ recentAnalyses: updated });
  },

  deleteAnalysis: async (contractId: string) => {
    try {
      await apiService.deleteAnalysis(contractId);
      const recent = get().recentAnalyses;
      const updated = recent.filter((a) => a.contract_id !== contractId);
      set({ recentAnalyses: updated });
    } catch (error: unknown) {
      console.error("Failed to delete analysis:", error);
      throw error;
    }
  },

  setError: (error: string | null) => {
    set({ analysisError: error });
  },
}));

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  useAnalysisStore.getState().disconnectWebSocket();
});
