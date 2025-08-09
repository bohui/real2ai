"""Contract analysis schemas."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.schema.enums import AustralianState, RiskLevel
from app.schema.common import SchemaBaseModel


class AnalysisOptions(BaseModel):
    """Contract analysis options"""

    include_financial_analysis: bool = True
    include_risk_assessment: bool = True
    include_compliance_check: bool = True
    include_recommendations: bool = True
    priority_analysis: Optional[str] = None  # speed, accuracy, comprehensive


class ContractAnalysisRequest(BaseModel):
    """Contract analysis request"""

    document_id: str
    analysis_options: AnalysisOptions = AnalysisOptions()
    user_notes: Optional[str] = None


class ContractAnalysisResponse(BaseModel):
    """Contract analysis response"""

    contract_id: str
    analysis_id: str
    status: str = "pending"
    task_id: Optional[str] = None
    estimated_completion_minutes: int = 2


class RiskFactorResponse(BaseModel):
    """Risk factor in analysis response"""

    factor: str
    severity: RiskLevel
    description: str
    impact: str
    mitigation: str
    australian_specific: bool
    confidence: float


class RecommendationResponse(BaseModel):
    """Recommendation in analysis response"""

    priority: RiskLevel
    category: str  # legal, financial, practical
    recommendation: str
    action_required: bool
    australian_context: str
    estimated_cost: Optional[float] = None
    confidence: float


class StampDutyResponse(BaseModel):
    """Stamp duty calculation response"""

    state: AustralianState
    purchase_price: float
    base_duty: float
    exemptions: float
    surcharges: float
    total_duty: float
    is_first_home_buyer: bool
    is_foreign_buyer: bool
    breakdown: Dict[str, float]


class ComplianceCheckResponse(BaseModel):
    """Compliance check response"""

    state_compliance: bool
    compliance_issues: List[str]
    cooling_off_compliance: bool
    cooling_off_details: Dict[str, Any]
    stamp_duty_calculation: Optional[StampDutyResponse] = None
    mandatory_disclosures: List[str]
    warnings: List[str]
    legal_references: List[str]


class ContractAnalysisResult(BaseModel):
    """Complete contract analysis result"""

    contract_id: str
    analysis_id: str
    analysis_timestamp: datetime
    user_id: str
    australian_state: AustralianState

    # Analysis Results
    contract_terms: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    compliance_check: ComplianceCheckResponse
    recommendations: List[RecommendationResponse]

    # Analysis Metadata
    confidence_scores: Dict[str, float]
    overall_confidence: float
    processing_time: float
    analysis_version: str

    # Summary
    executive_summary: Dict[str, Any]


class StampDutyCalculationRequest(BaseModel):
    """Stamp duty calculation request"""

    purchase_price: float
    state: AustralianState
    is_first_home_buyer: bool = False
    is_foreign_buyer: bool = False
    is_investment_property: bool = False


class PropertyFinancialSummary(BaseModel):
    """Property financial summary"""

    purchase_price: float
    stamp_duty: StampDutyResponse
    legal_costs: Optional[float] = None
    inspection_costs: Optional[float] = None
    total_upfront_costs: float
    ongoing_costs: Optional[Dict[str, float]] = None


class WebSocketProgressUpdate(BaseModel):
    """WebSocket progress update"""

    contract_id: str
    current_step: str
    progress_percent: int
    step_description: Optional[str] = None
    estimated_time_remaining: Optional[int] = None


class ContractAnalysisFromOCR(BaseModel):
    """Contract analysis results from OCR extraction"""

    document_id: str
    ocr_confidence: float
    contract_elements: Dict[str, List[str]]
    australian_compliance_indicators: List[str]
    risk_indicators: List[str]
    completeness_score: float
    quality_metrics: Dict[str, Any]
    recommendations: List[str]
    requires_manual_review: bool


# Detailed, strongly-typed service responses used by `ContractAnalysisService`


class AnalysisQualityMetrics(SchemaBaseModel):
    overall_confidence: float = 0.0
    confidence_breakdown: Dict[str, float] = {}
    quality_assessment: str = ""
    processing_quality: Dict[str, Any] = {}
    document_quality: Dict[str, Any] = {}
    validation_results: Dict[str, Any] = {}


class WorkflowMetadata(SchemaBaseModel):
    steps_completed: int = 0
    total_steps: int = 0
    progress_percentage: float = 0.0
    configuration: Dict[str, Any] = {}
    performance_metrics: Dict[str, Any] = {}
    service_metrics: Dict[str, Any] = {}


class EnhancementFeaturesStatus(SchemaBaseModel):
    structured_parsing_used: bool = True
    prompt_manager_used: bool = False
    validation_performed: bool = False
    quality_checks_performed: bool = False
    enhanced_error_handling: bool = False
    fallback_mechanisms_available: bool = False


class ContractAnalysisServiceResponse(SchemaBaseModel):
    success: bool
    session_id: str
    analysis_timestamp: datetime
    processing_time_seconds: float
    workflow_version: str

    analysis_results: Dict[str, Any] = {}
    report_data: Dict[str, Any] = {}
    quality_metrics: AnalysisQualityMetrics = AnalysisQualityMetrics()
    workflow_metadata: WorkflowMetadata = WorkflowMetadata()

    error: Optional[str] = None
    warnings: List[str] = []
    enhancement_features: EnhancementFeaturesStatus = EnhancementFeaturesStatus()


class StartAnalysisResponse(SchemaBaseModel):
    success: bool
    contract_id: Optional[str] = None
    session_id: str
    final_state: Dict[str, Any] = {}
    analysis_results: Dict[str, Any] = {}
    processing_time: Optional[float] = None
    error: Optional[str] = None


class AnalysisStatus(SchemaBaseModel):
    start_time: datetime
    user_id: str
    session_id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AnalysesSummary(SchemaBaseModel):
    total_analyses: int
    status_breakdown: Dict[str, int]
    active_count: int


class ServiceHealthResponse(SchemaBaseModel):
    status: str
    timestamp: datetime
    version: str
    configuration: Dict[str, Any]
    metrics: Dict[str, Any]
    components: Dict[str, Any]


class ServiceMetricsResponse(SchemaBaseModel):
    service_metrics: Dict[str, Any]
    configuration: Dict[str, Any]
    workflow_metrics: Dict[str, Any]
    websocket_metrics: Dict[str, Any]
    timestamp: datetime
    prompt_manager_metrics: Optional[Dict[str, Any]] = None
    prompt_manager_error: Optional[str] = None


class ReloadConfigurationResponse(SchemaBaseModel):
    success: bool
    message: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    timestamp: datetime
    error: Optional[str] = None


class OperationResponse(SchemaBaseModel):
    """Generic operation response for simple success/error flows."""

    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
