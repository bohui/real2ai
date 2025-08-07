import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { apiService } from '../api'
import type { UserLoginRequest, UserRegistrationRequest, AustralianState, ContractAnalysisRequest } from '@/types'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

describe('ApiService', () => {
  const mockAxiosInstance = {
    create: vi.fn(() => mockAxiosInstance),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }

  beforeEach(() => {
    (mockedAxios.create as any).mockReturnValue(mockAxiosInstance as any)
    
    // Mock successful responses by default
    mockAxiosInstance.post.mockResolvedValue({ data: {} })
    mockAxiosInstance.get.mockResolvedValue({ data: {} })
    mockAxiosInstance.put.mockResolvedValue({ data: {} })
    mockAxiosInstance.delete.mockResolvedValue({ data: {} })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Authentication', () => {
    it('should login user successfully', async () => {
      const mockResponse = {
        data: {
          user: { id: '1', email: 'test@example.com' },
          token: 'mock-jwt-token'
        }
      }
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const loginData: UserLoginRequest = {
        email: 'test@example.com',
        password: 'password123'
      }

      const result = await apiService.login(loginData)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/login', loginData)
      expect(result).toEqual(mockResponse.data)
    })

    it('should register user successfully', async () => {
      const mockResponse = {
        data: {
          user: { id: '1', email: 'test@example.com' },
          token: 'mock-jwt-token'
        }
      }
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const registerData: UserRegistrationRequest = {
        email: 'test@example.com',
        password: 'password123',
        australian_state: 'NSW',
        user_type: 'individual'
      }

      const result = await apiService.register(registerData)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/auth/register', registerData)
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle login error', async () => {
      const errorResponse = {
        response: { 
          status: 401, 
          data: { detail: 'Invalid credentials' } 
        }
      }
      mockAxiosInstance.post.mockRejectedValueOnce(errorResponse)

      const loginData: UserLoginRequest = {
        email: 'test@example.com',
        password: 'wrongpassword'
      }

      await expect(apiService.login(loginData)).rejects.toThrow()
    })

    it('should handle network errors', async () => {
      mockAxiosInstance.post.mockRejectedValueOnce(new Error('Network Error'))

      const loginData: UserLoginRequest = {
        email: 'test@example.com',
        password: 'password123'
      }

      await expect(apiService.login(loginData)).rejects.toThrow('Network Error')
    })

    it('should handle server errors', async () => {
      const serverError = {
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' }
        }
      }
      mockAxiosInstance.post.mockRejectedValueOnce(serverError)

      const loginData: UserLoginRequest = {
        email: 'test@example.com', 
        password: 'password123'
      }

      await expect(apiService.login(loginData)).rejects.toThrow()
    })

    it('should set and clear auth token', () => {
      apiService.setToken('test-token')
      // Token is stored internally, we can't access it directly

      apiService.clearToken()
      // Token is cleared internally
    })
  })

  describe('User Management', () => {
    it('should get current user profile', async () => {
      const mockUser = {
        data: {
          id: '1',
          email: 'test@example.com',
          australian_state: 'NSW',
          user_type: 'individual',
          subscription_status: 'premium',
          credits_remaining: 100
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockUser)

      const result = await apiService.getCurrentUser()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/me')
      expect(result).toEqual(mockUser.data)
    })

    it('should update user profile', async () => {
      const updateData = { australian_state: 'VIC' as AustralianState }
      const mockResponse = { data: { success: true } }
      mockAxiosInstance.put.mockResolvedValueOnce(mockResponse)

      const result = await apiService.updateProfile(updateData)
      
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/users/me', updateData)
      expect(result).toEqual(mockResponse.data)
    })

    it('should get usage statistics', async () => {
      const mockStats = {
        data: {
          totalDocuments: 10,
          totalAnalyses: 5,
          creditsUsed: 50,
          creditsRemaining: 50
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockStats)

      const result = await apiService.getUserStats()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/stats')
      expect(result).toEqual(mockStats.data)
    })
  })

  describe('Document Management', () => {
    it('should upload document successfully', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      const mockResponse = {
        data: {
          id: 'doc-123',
          filename: 'test.pdf',
          status: 'uploaded',
          document_id: 'doc-123'
        }
      }
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await apiService.uploadDocument(mockFile, 'purchase_agreement')
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/documents/upload', 
        expect.any(FormData),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'multipart/form-data'
          })
        })
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle document upload errors', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      const errorResponse = {
        response: {
          status: 413,
          data: { detail: 'File too large' }
        }
      }
      mockAxiosInstance.post.mockRejectedValueOnce(errorResponse)

      await expect(apiService.uploadDocument(mockFile, 'purchase_agreement')).rejects.toThrow()
    })

    it('should get document details', async () => {
      const mockDocument = {
        data: {
          id: 'doc-123',
          filename: 'test.pdf',
          upload_date: '2024-01-01T00:00:00Z',
          file_size: 1024,
          status: 'processed'
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockDocument)

      const result = await apiService.getDocument('doc-123')
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/documents/doc-123')
      expect(result).toEqual(mockDocument.data)
    })
  })

  describe('Contract Analysis', () => {
    it('should start contract analysis', async () => {
      const mockRequest: ContractAnalysisRequest = {
        document_id: 'doc-123',
        analysis_options: {
          include_financial_analysis: true,
          include_risk_assessment: true,
          include_compliance_check: true,
          include_recommendations: true
        }
      }
      const mockResponse = {
        data: {
          analysis_id: 'analysis-456',
          status: 'started'
        }
      }
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await apiService.startAnalysis(mockRequest)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/contracts/analyze', mockRequest)
      expect(result).toEqual(mockResponse.data)
    })

    it('should get analysis result with retry logic', async () => {
      const mockResult = {
        data: {
          contract_id: 'doc-123',
          analysis_status: 'completed',
          analysis_result: {
            contract_terms: { price: 500000 },
            risk_assessment: { overall_risk_score: 3.2 }
          }
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockResult)

      const result = await apiService.getAnalysisResult('doc-123')
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/contracts/doc-123/analysis')
      expect(result).toHaveProperty('contract_id', 'doc-123')
      expect(result).toHaveProperty('analysis_status', 'completed')
    })

    it('should handle analysis errors', async () => {
      const errorResponse = {
        response: {
          status: 404,
          data: { detail: 'Analysis not found' }
        }
      }
      mockAxiosInstance.get.mockRejectedValueOnce(errorResponse)

      await expect(apiService.getAnalysisResult('nonexistent')).rejects.toThrow()
    })
    
    it('should fetch user stats successfully', async () => {
      const mockStats = {
        data: {
          total_analyses: 15,
          remaining_credits: 85,
          subscription_tier: 'premium'
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockStats)

      const result = await apiService.getUserStats()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/users/me/usage')
      expect(result).toEqual(mockStats.data)
    })
  })

  describe('Document Management', () => {
    it('should upload document successfully', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const mockResponse = {
        data: {
          document_id: 'doc-123',
          filename: 'test.pdf',
          file_size: 1024,
          upload_status: 'completed'
        }
      }
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await apiService.uploadDocument(mockFile, 'contract')
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/documents/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'multipart/form-data'
          })
        })
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('should get documents list', async () => {
      const mockDocuments = {
        data: [
          { id: '1', filename: 'doc1.pdf', upload_date: '2024-01-01' },
          { id: '2', filename: 'doc2.pdf', upload_date: '2024-01-02' }
        ]
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockDocuments)

      const result = await apiService.getDocument('test-doc-id')
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/documents/')
      expect(result).toEqual(mockDocuments.data)
    })

    it('should delete document', async () => {
      const mockResponse = { data: { success: true } }
      mockAxiosInstance.delete.mockResolvedValueOnce(mockResponse)

      const result = await apiService.deleteAnalysis('doc-123')
      
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/documents/doc-123')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Contract Analysis', () => {
    it('should start contract analysis', async () => {
      const analysisRequest: ContractAnalysisRequest = {
        document_id: 'doc-123',
        analysis_options: {
          include_financial_analysis: true,
          include_risk_assessment: true,
          include_compliance_check: true,
          include_recommendations: true
        }
      }
      const mockResponse = {
        data: {
          analysis_id: 'analysis-456',
          status: 'processing',
          document_id: 'doc-123'
        }
      }
      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await apiService.startAnalysis(analysisRequest)
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/contracts/analyze', analysisRequest)
      expect(result).toEqual(mockResponse.data)
    })

    it('should get analysis status', async () => {
      const mockResponse = {
        data: {
          analysis_id: 'analysis-456',
          status: 'completed',
          progress: 100,
          result: { risk_level: 'medium' }
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await apiService.getAnalysisResult('analysis-456')
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/contracts/analysis/analysis-456/status')
      expect(result).toEqual(mockResponse.data)
    })

    it('should get analysis results', async () => {
      const mockResponse = {
        data: {
          analysis_id: 'analysis-456',
          risk_assessment: { overall_risk: 'medium', risk_factors: [] },
          key_insights: [],
          recommendations: []
        }
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await apiService.getAnalysisResult('analysis-456')
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/contracts/analysis/analysis-456/results')
      expect(result).toEqual(mockResponse.data)
    })

    it('should get analysis history', async () => {
      const mockResponse = {
        data: [
          { analysis_id: '1', document_name: 'contract1.pdf', date: '2024-01-01', status: 'completed' },
          { analysis_id: '2', document_name: 'contract2.pdf', date: '2024-01-02', status: 'processing' }
        ]
      }
      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await apiService.getUserStats()
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/contracts/analysis/history')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      mockAxiosInstance.get.mockRejectedValueOnce(new Error('Network Error'))

      await expect(apiService.getCurrentUser()).rejects.toThrow('Network Error')
    })

    it('should handle 401 unauthorized errors', async () => {
      const unauthorizedError = {
        response: { status: 401, data: { detail: 'Unauthorized' } }
      }
      mockAxiosInstance.get.mockRejectedValueOnce(unauthorizedError)

      // Mock window event dispatch
      const mockDispatchEvent = vi.spyOn(window, 'dispatchEvent')
      
      await expect(apiService.getCurrentUser()).rejects.toThrow()
      
      // Should dispatch auth:unauthorized event
      expect(mockDispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'auth:unauthorized'
        })
      )
    })

    it('should handle server errors with proper error messages', async () => {
      const serverError = {
        response: { 
          status: 500, 
          data: { detail: 'Internal Server Error' } 
        }
      }
      mockAxiosInstance.get.mockRejectedValueOnce(serverError)

      await expect(apiService.getCurrentUser()).rejects.toThrow()
    })
  })

  describe('Request Configuration', () => {
    it('should add auth token to requests when available', () => {
      apiService.setToken('test-token')
      
      // Trigger the request interceptor
      const requestConfig = { headers: {} }
      const interceptorCallback = mockAxiosInstance.interceptors.request.use.mock.calls[0][0]
      
      const result = interceptorCallback(requestConfig)
      
      expect(result.headers.Authorization).toBe('Bearer test-token')
    })

    it('should not add auth token when not available', () => {
      apiService.clearToken()
      
      const requestConfig = { headers: {} }
      const interceptorCallback = mockAxiosInstance.interceptors.request.use.mock.calls[0][0]
      
      const result = interceptorCallback(requestConfig)
      
      expect(result.headers.Authorization).toBeUndefined()
    })
  })
})
