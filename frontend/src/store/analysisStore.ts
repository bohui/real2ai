import { create } from 'zustand'
import { 
  DocumentDetails, 
  ContractAnalysisResult, 
  AnalysisProgressUpdate,
  ContractAnalysisRequest,
  WebSocketEventData
} from '@/types'
import { apiService, WebSocketService, wsConnectionManager } from '@/services/api'

interface AnalysisState {
  // Current analysis state
  currentDocument: DocumentDetails | null
  currentAnalysis: ContractAnalysisResult | null
  analysisProgress: AnalysisProgressUpdate | null
  
  // Upload state
  isUploading: boolean
  uploadProgress: number
  
  // Analysis state
  isAnalyzing: boolean
  analysisError: string | null
  
  // WebSocket
  wsService: WebSocketService | null
  wsEventListener: ((event: any) => void) | null
  currentContractId: string | null
  
  // Recent analyses
  recentAnalyses: ContractAnalysisResult[]
  
  // Actions
  uploadDocument: (file: File, contractType: string, state: string) => Promise<string>
  startAnalysis: (request: ContractAnalysisRequest) => Promise<void>
  connectWebSocket: (contractId: string) => Promise<void>
  disconnectWebSocket: () => void
  updateProgress: (progress: AnalysisProgressUpdate) => void
  setAnalysisResult: (result: ContractAnalysisResult) => void
  clearCurrentAnalysis: () => void
  addRecentAnalysis: (analysis: ContractAnalysisResult) => void
  deleteAnalysis: (contractId: string) => Promise<void>
  setError: (error: string | null) => void
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
  currentContractId: null,
  recentAnalyses: [],

  uploadDocument: async (file: File, contractType: string, state: string) => {
    set({ isUploading: true, uploadProgress: 0, analysisError: null })
    
    try {
      // Listen for upload progress
      const handleProgress = (event: any) => {
        set({ uploadProgress: event.detail.progress })
      }
      window.addEventListener('upload:progress', handleProgress as EventListener)
      
      const response = await apiService.uploadDocument(file, contractType, state)
      
      // Get document details
      const document = await apiService.getDocument(response.document_id)
      
      set({
        currentDocument: document,
        isUploading: false,
        uploadProgress: 100
      })
      
      window.removeEventListener('upload:progress', handleProgress as EventListener)
      return response.document_id
      
    } catch (error: unknown) {
      set({
        isUploading: false,
        uploadProgress: 0,
        analysisError: apiService.handleError(error as any)
      })
      throw error
    }
  },

  startAnalysis: async (request: ContractAnalysisRequest) => {
    set({ isAnalyzing: true, analysisError: null, analysisProgress: null })
    
    try {
      const response = await apiService.startAnalysis(request)
      
      // Connect WebSocket for real-time updates
      await get().connectWebSocket(response.contract_id)
      
    } catch (error: unknown) {
      set({
        isAnalyzing: false,
        analysisError: apiService.handleError(error as any)
      })
      throw error
    }
  },

  connectWebSocket: async (contractId: string) => {
    const state = get();
    
    // Don't reconnect to the same contract
    if (state.currentContractId === contractId && state.wsService?.isWebSocketConnected()) {
      console.log(`Already connected to contract ${contractId}`);
      return;
    }
    
    // Disconnect existing connection
    get().disconnectWebSocket()
    
    // Use connection manager to prevent duplicate connections
    const wsService = wsConnectionManager.createConnection(contractId)
    
    // Create event handler with proper cleanup
    const handleUpdate = (event: any) => {
      const data = event.detail
      
      // Ensure this event is for the current contract
      if (data.data?.contract_id && data.data.contract_id !== contractId) {
        console.log(`Ignoring WebSocket event for different contract: ${data.data.contract_id} (expected: ${contractId})`);
        return;
      }
      
      console.log(`Processing WebSocket event for contract ${contractId}:`, data.event_type);
      
      switch (data.event_type) {
        case 'analysis_progress':
          get().updateProgress(data.data as AnalysisProgressUpdate)
          break
          
        case 'analysis_completed':
          // Fetch full analysis result
          apiService.getAnalysisResult(contractId)
            .then(result => {
              get().setAnalysisResult(result)
              get().addRecentAnalysis(result)
              set({ isAnalyzing: false, analysisError: null })
            })
            .catch(error => {
              console.error('Failed to fetch analysis result:', error)
              // Keep analyzing state to prevent blank page and show error
              set({ 
                analysisError: `Failed to load analysis results: ${apiService.handleError(error)}`,
                // Don't set isAnalyzing to false to avoid blank page
                // Instead, show error while maintaining loading state context
              })
              
              // Retry fetching the result after a delay
              setTimeout(() => {
                apiService.getAnalysisResult(contractId)
                  .then(result => {
                    get().setAnalysisResult(result)
                    get().addRecentAnalysis(result) 
                    set({ isAnalyzing: false, analysisError: null })
                  })
                  .catch(retryError => {
                    console.error('Retry failed for analysis result:', retryError)
                    // After retry fails, stop loading and show error
                    set({ 
                      isAnalyzing: false,
                      analysisError: `Analysis completed but results unavailable: ${apiService.handleError(retryError)}`
                    })
                  })
              }, 2000) // Retry after 2 seconds
            })
          break
          
        case 'analysis_failed':
          set({
            isAnalyzing: false,
            analysisError: data.data?.error_message || 'Analysis failed'
          })
          break

        case 'connection_established':
          console.log(`WebSocket connection established for contract ${contractId}`);
          break;
          
        case 'heartbeat':
          // Heartbeat received, connection is alive
          break;
          
        default:
          console.log('Received WebSocket event:', data.event_type, data);
      }
    }
    
    set({ 
      wsService, 
      wsEventListener: handleUpdate,
      currentContractId: contractId
    })
    
    try {
      await wsService.connect()
      window.addEventListener('analysis:update', handleUpdate as EventListener)
      
    } catch (error) {
      console.error('WebSocket connection failed:', error)
      set({ 
        analysisError: 'Failed to connect for real-time updates',
        wsService: null,
        wsEventListener: null,
        currentContractId: null
      })
    }
  },

  disconnectWebSocket: () => {
    const { wsService, wsEventListener, currentContractId } = get()
    
    console.log(`Disconnecting WebSocket for contract ${currentContractId}`);
    
    if (wsService) {
      wsService.disconnect()
    }
    
    // Also remove from connection manager
    if (currentContractId) {
      wsConnectionManager.removeConnection(currentContractId)
    }
    
    // Remove event listener with proper reference
    if (wsEventListener) {
      window.removeEventListener('analysis:update', wsEventListener as EventListener)
    }
    
    set({ 
      wsService: null, 
      wsEventListener: null,
      currentContractId: null
    })
  },

  updateProgress: (progress: AnalysisProgressUpdate) => {
    set({ analysisProgress: progress })
  },

  setAnalysisResult: (result: ContractAnalysisResult) => {
    set({ currentAnalysis: result })
  },

  clearCurrentAnalysis: () => {
    console.log('Clearing current analysis and disconnecting WebSocket');
    get().disconnectWebSocket()
    set({
      currentDocument: null,
      currentAnalysis: null,
      analysisProgress: null,
      isUploading: false,
      uploadProgress: 0,
      isAnalyzing: false,
      analysisError: null
    })
  },

  addRecentAnalysis: (analysis: ContractAnalysisResult) => {
    // Validate that analysis has required properties before adding
    if (!analysis.contract_id || !analysis.analysis_timestamp) {
      console.warn('Skipping invalid analysis for recent list:', analysis);
      return;
    }
    
    // Ensure executive_summary exists with fallback values
    if (!analysis.executive_summary) {
      console.warn('Analysis missing executive_summary, creating fallback:', analysis.contract_id);
      analysis.executive_summary = {
        overall_risk_score: analysis.risk_assessment?.overall_risk_score || 0,
        compliance_status: analysis.compliance_check?.state_compliance ? 'compliant' : 'non-compliant',
        total_recommendations: analysis.recommendations?.length || 0,
        critical_issues: analysis.recommendations?.filter(r => r.priority === 'critical')?.length || 0,
        confidence_level: analysis.overall_confidence || 0.8
      };
    }
    
    const recent = get().recentAnalyses
    const updated = [analysis, ...recent.filter(a => a.contract_id !== analysis.contract_id)]
      .slice(0, 10) // Keep only 10 most recent
    
    set({ recentAnalyses: updated })
  },

  deleteAnalysis: async (contractId: string) => {
    try {
      await apiService.deleteAnalysis(contractId)
      const recent = get().recentAnalyses
      const updated = recent.filter(a => a.contract_id !== contractId)
      set({ recentAnalyses: updated })
    } catch (error: unknown) {
      console.error('Failed to delete analysis:', error)
      throw error
    }
  },

  setError: (error: string | null) => {
    set({ analysisError: error })
  }
}))

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  useAnalysisStore.getState().disconnectWebSocket()
})