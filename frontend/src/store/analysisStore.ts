import { create } from 'zustand'
import { 
  DocumentDetails, 
  ContractAnalysisResult, 
  AnalysisProgressUpdate,
  ContractAnalysisRequest 
} from '@/types'
import { apiService, WebSocketService } from '@/services/api'

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
  recentAnalyses: [],

  uploadDocument: async (file: File, contractType: string, state: string) => {
    set({ isUploading: true, uploadProgress: 0, analysisError: null })
    
    try {
      // Listen for upload progress
      const handleProgress = (event: any) => {
        set({ uploadProgress: event.detail.progress })
      }
      window.addEventListener('upload:progress', handleProgress)
      
      const response = await apiService.uploadDocument(file, contractType, state)
      
      // Get document details
      const document = await apiService.getDocument(response.document_id)
      
      set({
        currentDocument: document,
        isUploading: false,
        uploadProgress: 100
      })
      
      window.removeEventListener('upload:progress', handleProgress)
      return response.document_id
      
    } catch (error: any) {
      set({
        isUploading: false,
        uploadProgress: 0,
        analysisError: apiService.handleError(error)
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
      
    } catch (error: any) {
      set({
        isAnalyzing: false,
        analysisError: apiService.handleError(error)
      })
      throw error
    }
  },

  connectWebSocket: async (contractId: string) => {
    // Disconnect existing connection
    get().disconnectWebSocket()
    
    const wsService = new WebSocketService(contractId)
    set({ wsService })
    
    try {
      await wsService.connect()
      
      // Listen for analysis updates
      const handleUpdate = (event: any) => {
        const data = event.detail
        
        switch (data.event_type) {
          case 'analysis_progress':
            get().updateProgress(data.data)
            break
            
          case 'analysis_completed':
            // Fetch full analysis result
            apiService.getAnalysisResult(contractId)
              .then(result => {
                get().setAnalysisResult(result)
                get().addRecentAnalysis(result)
                set({ isAnalyzing: false })
              })
              .catch(error => {
                set({ 
                  isAnalyzing: false,
                  analysisError: apiService.handleError(error)
                })
              })
            break
            
          case 'analysis_failed':
            set({
              isAnalyzing: false,
              analysisError: data.data.error_message
            })
            break
        }
      }
      
      window.addEventListener('analysis:update', handleUpdate)
      
    } catch (error) {
      console.error('WebSocket connection failed:', error)
      set({ analysisError: 'Failed to connect for real-time updates' })
    }
  },

  disconnectWebSocket: () => {
    const { wsService } = get()
    if (wsService) {
      wsService.disconnect()
      set({ wsService: null })
    }
    
    // Remove event listeners
    window.removeEventListener('analysis:update', () => {})
  },

  updateProgress: (progress: AnalysisProgressUpdate) => {
    set({ analysisProgress: progress })
  },

  setAnalysisResult: (result: ContractAnalysisResult) => {
    set({ currentAnalysis: result })
  },

  clearCurrentAnalysis: () => {
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
    const recent = get().recentAnalyses
    const updated = [analysis, ...recent.filter(a => a.contract_id !== analysis.contract_id)]
      .slice(0, 10) // Keep only 10 most recent
    
    set({ recentAnalyses: updated })
  },

  setError: (error: string | null) => {
    set({ analysisError: error })
  }
}))

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  useAnalysisStore.getState().disconnectWebSocket()
})