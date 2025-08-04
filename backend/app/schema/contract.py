"""Contract analysis schemas."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from app.model.enums import AustralianState, RiskLevel


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
