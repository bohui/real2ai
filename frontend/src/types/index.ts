// Core API Types based on backend models
export type AustralianState = 'NSW' | 'VIC' | 'QLD' | 'SA' | 'WA' | 'TAS' | 'NT' | 'ACT'

export type ContractType = 'purchase_agreement' | 'lease_agreement' | 'off_plan' | 'auction'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export type UserType = 'buyer' | 'investor' | 'agent'

export type SubscriptionStatus = 'free' | 'basic' | 'premium' | 'enterprise'

// User Types
export interface User {
  id: string
  email: string
  australian_state: AustralianState
  user_type: UserType
  subscription_status: SubscriptionStatus
  credits_remaining: number
  preferences: Record<string, any>
  created_at?: string
}

export interface UserRegistrationRequest {
  email: string
  password: string
  australian_state: AustralianState
  user_type: UserType
}

export interface UserLoginRequest {
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user_profile: User
}

// Document Types
export interface DocumentUploadResponse {
  document_id: string
  filename: string
  file_size: number
  upload_status: string
  processing_time: number
}

export interface DocumentDetails {
  id: string
  user_id: string
  filename: string
  file_type: string
  file_size: number
  status: 'uploaded' | 'processing' | 'processed' | 'failed'
  storage_path: string
  upload_timestamp: string
  processing_results?: {
    extracted_text?: string
    extraction_confidence?: number
    character_count?: number
    word_count?: number
    text_quality?: {
      score: number
      issues: string[]
      contract_keywords_found: number
    }
  }
}

// Contract Analysis Types
export interface AnalysisOptions {
  include_financial_analysis: boolean
  include_risk_assessment: boolean
  include_compliance_check: boolean
  include_recommendations: boolean
  priority_analysis?: string
}

export interface ContractAnalysisRequest {
  document_id: string
  analysis_options: AnalysisOptions
  user_notes?: string
}

export interface ContractAnalysisResponse {
  contract_id: string
  analysis_id: string
  status: string
  estimated_completion_minutes: number
}

export interface RiskFactor {
  factor: string
  severity: RiskLevel
  description: string
  impact: string
  mitigation: string
  australian_specific: boolean
  confidence: number
}

export interface Recommendation {
  priority: RiskLevel
  category: 'legal' | 'financial' | 'practical'
  recommendation: string
  action_required: boolean
  australian_context: string
  estimated_cost?: number
  confidence: number
}

export interface StampDutyCalculation {
  state: AustralianState
  purchase_price: number
  base_duty: number
  exemptions: number
  surcharges: number
  total_duty: number
  is_first_home_buyer: boolean
  is_foreign_buyer: boolean
  breakdown: Record<string, number>
}

export interface ComplianceCheck {
  state_compliance: boolean
  compliance_issues: string[]
  cooling_off_compliance: boolean
  cooling_off_details: Record<string, any>
  stamp_duty_calculation?: StampDutyCalculation
  mandatory_disclosures: string[]
  warnings: string[]
  legal_references: string[]
}

export interface ContractAnalysisResult {
  contract_id: string
  analysis_id: string
  analysis_timestamp: string
  user_id: string
  australian_state: AustralianState
  contract_terms: Record<string, any>
  risk_assessment: {
    overall_risk_score: number
    risk_factors: RiskFactor[]
  }
  compliance_check: ComplianceCheck
  recommendations: Recommendation[]
  confidence_scores: Record<string, number>
  overall_confidence: number
  processing_time: number
  analysis_version: string
  executive_summary: {
    overall_risk_score: number
    compliance_status: 'compliant' | 'non-compliant'
    total_recommendations: number
    critical_issues: number
    confidence_level: number
  }
}

// WebSocket Types
export interface WebSocketMessage {
  event_type: string
  timestamp: string
  data: Record<string, any>
}

export interface AnalysisProgressUpdate {
  contract_id: string
  current_step: string
  progress_percent: number
  step_description?: string
  estimated_time_remaining?: number
}

// UI State Types
export interface LoadingState {
  isLoading: boolean
  message?: string
}

export interface ErrorState {
  hasError: boolean
  message?: string
  code?: string
}

export interface NotificationState {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
}

// Form Types
export interface ContractUploadForm {
  file: File
  contract_type: ContractType
  australian_state: AustralianState
  user_notes?: string
}

// Navigation Types
export interface NavigationItem {
  path: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  requiresAuth?: boolean
  badge?: string | number
}

// Theme Types
export interface Theme {
  name: string
  colors: {
    primary: string
    secondary: string
    background: string
    surface: string
    text: string
    textSecondary: string
  }
}

// API Response Types
export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
  timestamp?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Usage Statistics
export interface UsageStats {
  credits_remaining: number
  subscription_status: SubscriptionStatus
  total_contracts_analyzed: number
  current_month_usage: number
  recent_analyses: Array<{
    contract_id: string
    filename: string
    analysis_date: string
    risk_score: number
  }>
  usage_trend?: Record<string, number>
}