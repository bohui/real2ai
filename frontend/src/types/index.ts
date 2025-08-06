// Core API Types based on backend models
export type AustralianState =
  | "NSW"
  | "VIC"
  | "QLD"
  | "SA"
  | "WA"
  | "TAS"
  | "NT"
  | "ACT";

export type ContractType =
  | "purchase_agreement"
  | "lease_agreement"
  | "off_plan"
  | "auction";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type UserType = "buyer" | "investor" | "agent";

export type SubscriptionStatus = "free" | "basic" | "premium" | "enterprise";

// User Types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  phone_number?: string;
  organization?: string;
  australian_state: AustralianState;
  user_type: UserType;
  subscription_status: SubscriptionStatus;
  credits_remaining: number;
  preferences: Record<string, any>;
  onboarding_completed: boolean;
  onboarding_completed_at?: string;
  onboarding_preferences: Record<string, any>;
  created_at?: string;
}

export interface UserRegistrationRequest {
  email: string;
  password: string;
  australian_state: AustralianState;
  user_type: UserType;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user_profile: User;
}

// Document Types
export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  file_size: number;
  upload_status: string;
  processing_time: number;
}

export interface DocumentDetails {
  id: string;
  user_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "uploaded" | "processing" | "processed" | "failed";
  storage_path: string;
  created_at: string;
  processing_results?: {
    extracted_text?: string;
    extraction_confidence?: number;
    character_count?: number;
    word_count?: number;
    text_quality?: {
      score: number;
      issues: string[];
      contract_keywords_found: number;
    };
  };
}

// Contract Analysis Types
export interface AnalysisOptions {
  include_financial_analysis: boolean;
  include_risk_assessment: boolean;
  include_compliance_check: boolean;
  include_recommendations: boolean;
  priority_analysis?: string;
}

export interface ContractAnalysisRequest {
  document_id: string;
  analysis_options: AnalysisOptions;
  user_notes?: string;
}

export interface ContractAnalysisResponse {
  contract_id: string;
  analysis_id: string;
  status: string;
  estimated_completion_minutes: number;
}

export interface RiskFactor {
  factor: string;
  severity: RiskLevel;
  description: string;
  impact: string;
  mitigation: string;
  australian_specific: boolean;
  confidence: number;
}

export interface Recommendation {
  priority: RiskLevel;
  category: "legal" | "financial" | "practical";
  recommendation: string;
  action_required: boolean;
  australian_context: string;
  estimated_cost?: number;
  confidence: number;
}

export interface StampDutyCalculation {
  state: AustralianState;
  purchase_price: number;
  base_duty: number;
  exemptions: number;
  surcharges: number;
  total_duty: number;
  is_first_home_buyer: boolean;
  is_foreign_buyer: boolean;
  breakdown: Record<string, number>;
}

export interface ComplianceCheck {
  state_compliance: boolean;
  compliance_issues: string[];
  cooling_off_compliance: boolean;
  cooling_off_details: Record<string, any>;
  stamp_duty_calculation?: StampDutyCalculation;
  mandatory_disclosures: string[];
  warnings: string[];
  legal_references: string[];
}

export interface ContractAnalysisResult {
  contract_id: string;
  analysis_id: string;
  analysis_timestamp: string;
  user_id: string;
  australian_state: AustralianState;
  analysis_status: "pending" | "processing" | "completed" | "failed";
  contract_terms: Record<string, any>;
  risk_assessment: {
    overall_risk_score: number;
    risk_factors: RiskFactor[];
  };
  compliance_check: ComplianceCheck;
  recommendations: Recommendation[];
  confidence_scores: Record<string, number>;
  overall_confidence: number;
  processing_time: number;
  analysis_version: string;
  executive_summary: {
    overall_risk_score: number;
    compliance_status: "compliant" | "non-compliant";
    total_recommendations: number;
    critical_issues: number;
    confidence_level: number;
  };
}

// Alias for backward compatibility
export type ContractAnalysis = ContractAnalysisResult;

// WebSocket Types
export interface WebSocketMessage {
  event_type: string;
  timestamp: string;
  data: Record<string, any>;
}

export interface AnalysisProgressUpdate {
  contract_id: string;
  current_step: string;
  progress_percent: number;
  step_description?: string;
  estimated_time_remaining?: number;
}

// UI State Types
export interface LoadingState {
  isLoading: boolean;
  message?: string;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  code?: string;
}

export interface NotificationState {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message: string;
  duration?: number;
}

// Form Types
export interface ContractUploadForm {
  file: File;
  contract_type: ContractType;
  australian_state: AustralianState;
  user_notes?: string;
}

// Navigation Types
export interface NavigationItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  requiresAuth?: boolean;
  badge?: string | number;
}

// Theme Types
export interface Theme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
  };
}

// API Response Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  timestamp?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Usage Statistics
export interface UsageStats {
  credits_remaining: number;
  subscription_status: SubscriptionStatus;
  total_contracts_analyzed: number;
  current_month_usage: number;
  recent_analyses: Array<{
    contract_id: string;
    filename: string;
    analysis_date: string;
    risk_score: number;
  }>;
  usage_trend?: Record<string, number>;
}

// Property Intelligence Types
export interface PropertyAddress {
  unit_number?: string;
  street_number: string;
  street_name: string;
  street_type: string;
  suburb: string;
  state: AustralianState;
  postcode: string;
  full_address?: string;
  latitude?: number;
  longitude?: number;
}

export interface PropertyDetails {
  property_type: 'House' | 'Unit' | 'Apartment' | 'Townhouse' | 'Villa' | 'Land';
  bedrooms?: number;
  bathrooms?: number;
  carspaces?: number;
  land_area?: number;
  building_area?: number;
  year_built?: number;
  features: string[];
}

export interface PropertyValuation {
  estimated_value: number;
  valuation_range_lower: number;
  valuation_range_upper: number;
  confidence: number;
  valuation_date: string;
  valuation_source: string;
  methodology: string;
}

export interface PropertyMarketData {
  median_price: number;
  price_growth_12_month: number;
  price_growth_3_year: number;
  days_on_market: number;
  sales_volume_12_month: number;
  market_outlook: string;
  median_rent?: number;
  rental_yield?: number;
  vacancy_rate?: number;
}

export interface PropertyRiskAssessment {
  overall_risk: RiskLevel;
  liquidity_risk: RiskLevel;
  market_risk: RiskLevel;
  structural_risk: RiskLevel;
  risk_factors: string[];
  confidence: number;
  risk_score?: number;
}

export interface PropertyInvestmentAnalysis {
  rental_yield: number;
  capital_growth_forecast_1_year: number;
  capital_growth_forecast_3_year: number;
  capital_growth_forecast_5_year: number;
  cash_flow_monthly: number;
  roi_percentage: number;
  payback_period_years: number;
  investment_score: number;
  investment_grade: string;
  comparable_roi: number;
}

export interface PropertyProfile {
  address: PropertyAddress;
  property_details: PropertyDetails;
  valuation: PropertyValuation;
  market_data: PropertyMarketData;
  risk_assessment: PropertyRiskAssessment;
  investment_analysis?: PropertyInvestmentAnalysis;
  comparable_sales: ComparableSale[];
  sales_history: PropertySalesHistory[];
  rental_history: PropertyRentalHistory[];
  data_sources: string[];
  profile_created_at: string;
  profile_confidence: number;
}

export interface ComparableSale {
  address: string;
  sale_date: string;
  sale_price: number;
  property_details: PropertyDetails;
  similarity_score: number;
  adjusted_price?: number;
  adjustments?: Record<string, number>;
}

export interface PropertySalesHistory {
  date: string;
  price: number;
  sale_type: string;
  days_on_market?: number;
}

export interface PropertyRentalHistory {
  date: string;
  weekly_rent: number;
  lease_type: string;
  lease_duration?: string;
}

export interface PropertySearchFilters {
  min_price?: number;
  max_price?: number;
  min_bedrooms?: number;
  max_bedrooms?: number;
  min_bathrooms?: number;
  max_bathrooms?: number;
  min_carspaces?: number;
  property_types: string[];
  suburbs: string[];
  states: AustralianState[];
  min_land_area?: number;
  max_land_area?: number;
  features_required: string[];
}

export interface PropertySearchRequest {
  query?: string;
  filters: PropertySearchFilters;
  location?: string;
  radius_km: number;
  limit: number;
  sort_by: 'relevance' | 'price_asc' | 'price_desc' | 'size_asc' | 'size_desc' | 'date_asc' | 'date_desc';
  include_off_market: boolean;
  include_historical: boolean;
}

export interface PropertySearchResponse {
  search_id: string;
  query?: string;
  total_results: number;
  results_returned: number;
  search_time_ms: number;
  properties: PropertyListing[];
  facets: {
    price_ranges: Record<string, number>;
    property_types: Record<string, number>;
    bedrooms: Record<string, number>;
  };
  market_summary: {
    median_price: number;
    price_trend: string;
    market_activity: string;
  };
}

export interface PropertyListing {
  id: string;
  address: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  carspaces: number;
  property_type: string;
  land_area?: number;
  building_area: number;
  market_score: number;
  investment_score: number;
  listing_date: string;
  estimated_rental: number;
}

export interface PropertyAnalyticsRequest {
  properties: string[];
  analysis_type: 'basic' | 'standard' | 'comprehensive' | 'investment';
  include_forecasting: boolean;
  include_neighborhood_analysis: boolean;
  include_investment_metrics: boolean;
  include_risk_analysis: boolean;
  comparison_properties: string[];
  custom_parameters: Record<string, any>;
}

export interface PropertyAnalyticsResponse {
  request_id: string;
  properties_analyzed: number;
  analysis_type: string;
  property_profiles: PropertyProfile[];
  investment_analysis?: PropertyInvestmentAnalysis[];
  market_trends?: PropertyMarketTrends[];
  neighborhood_analysis?: PropertyNeighborhoodAnalysis[];
  financial_breakdown?: PropertyFinancialBreakdown[];
  comparison_result?: PropertyComparisonResult;
  recommendations: PropertyInvestmentRecommendation[];
  market_insights: PropertyMarketInsight[];
  data_quality_score: number;
  processing_time: number;
  total_cost: number;
  created_at: string;
}

export interface PropertyMarketTrends {
  suburb: string;
  state: AustralianState;
  property_type: string;
  median_price_current: number;
  median_price_12_months_ago: number;
  price_change_percentage: number;
  price_volatility_score: number;
  market_activity_score: number;
  demand_supply_ratio: number;
  auction_clearance_rate?: number;
  days_on_market_average: number;
  sales_volume_trend: string;
  market_segment_performance: string;
  forecast_confidence: number;
}

export interface PropertyNeighborhoodAnalysis {
  walkability_score?: number;
  transport_score?: number;
  schools_nearby: Array<Record<string, any>>;
  shopping_centers_nearby: Array<Record<string, any>>;
  parks_recreation: Array<Record<string, any>>;
  crime_statistics?: Record<string, any>;
  demographic_profile?: Record<string, any>;
  future_development_plans: string[];
  noise_pollution_level?: string;
  flood_risk?: string;
  fire_risk?: string;
}

export interface PropertyFinancialBreakdown {
  purchase_price: number;
  stamp_duty: number;
  legal_fees: number;
  inspection_costs: number;
  loan_application_fees: number;
  building_inspection: number;
  pest_inspection: number;
  strata_report_cost?: number;
  total_upfront_costs: number;
  council_rates_annual: number;
  strata_fees_quarterly?: number;
  land_tax_annual: number;
  insurance_annual: number;
  property_management_annual?: number;
  maintenance_reserve_annual: number;
  total_annual_costs: number;
}

export interface PropertyComparisonResult {
  comparison_id: string;
  properties: PropertyProfile[];
  comparison_matrix: Record<string, Record<string, any>>;
  rankings: Record<string, string[]>;
  summary_insights: string[];
  recommendation?: string;
  created_at: string;
}

export interface PropertyInvestmentRecommendation {
  recommendation_type: string;
  confidence_score: number;
  reasoning: string[];
  key_factors: string[];
  risk_warnings: string[];
  optimal_holding_period?: string;
  expected_return_range?: Record<string, number>;
  alternative_suggestions: string[];
}

export interface PropertyMarketInsight {
  insight_id: string;
  insight_type: string;
  title: string;
  description: string;
  impact_level: string;
  affected_areas: string[];
  time_horizon: string;
  confidence_level: string;
  data_sources: string[];
  created_at: string;
  expires_at?: string;
}

export interface PropertyWatchlistItem {
  id: string;
  property: PropertyProfile;
  saved_at: string;
  notes?: string;
  tags: string[];
  alert_preferences: Record<string, any>;
  is_favorite: boolean;
  price_alerts_triggered: number;
  last_price_change?: string;
}

export interface BulkPropertyAnalysisRequest {
  properties: string[];
  analysis_depth: 'basic' | 'standard' | 'detailed';
  include_portfolio_metrics: boolean;
  include_diversification_analysis: boolean;
  include_market_correlation: boolean;
  output_format: 'json' | 'csv' | 'pdf';
}
