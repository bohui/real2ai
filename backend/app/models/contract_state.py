"""
LangGraph State Models for Real2.AI Contract Analysis
"""

from typing import TypedDict, Optional, Dict, List, Any
from datetime import datetime
import uuid

from app.model.enums import AustralianState, ContractType, ProcessingStatus, RiskLevel


class RealEstateAgentState(TypedDict):
    """Central state for all Real2.AI agents"""
    
    # Session Management
    user_id: str
    session_id: str
    agent_version: str
    
    # Document Processing
    document_data: Optional[Dict[str, Any]]
    document_metadata: Optional[Dict[str, Any]]
    parsing_status: ProcessingStatus
    
    # Contract Analysis
    contract_terms: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    compliance_check: Optional[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    
    # Property Data (Phase 2+)
    property_data: Optional[Dict[str, Any]]
    market_analysis: Optional[Dict[str, Any]]
    financial_analysis: Optional[Dict[str, Any]]
    
    # User Context
    user_preferences: Dict[str, Any]
    australian_state: AustralianState
    user_type: str  # buyer, investor, agent
    
    # Processing State
    current_step: str
    error_state: Optional[str]
    confidence_scores: Dict[str, float]
    processing_time: Optional[float]
    
    # Output
    analysis_results: Dict[str, Any]
    report_data: Optional[Dict[str, Any]]
    final_recommendations: List[Dict[str, Any]]


class ContractTerms(TypedDict):
    """Structured contract terms extraction"""
    purchase_price: Optional[float]
    deposit_amount: Optional[float]
    settlement_date: Optional[str]
    cooling_off_period: Optional[str]
    property_address: Optional[str]
    vendor_details: Optional[Dict[str, str]]
    purchaser_details: Optional[Dict[str, str]]
    special_conditions: List[str]
    finance_clause: Optional[Dict[str, Any]]
    building_pest_clause: Optional[Dict[str, Any]]
    strata_clause: Optional[Dict[str, Any]]


class RiskFactor(TypedDict):
    """Risk assessment structure"""
    factor: str
    severity: RiskLevel
    description: str
    impact: str
    mitigation: str
    australian_specific: bool


class Recommendation(TypedDict):
    """Action recommendation structure"""
    priority: RiskLevel
    category: str
    recommendation: str
    action_required: bool
    australian_context: str
    estimated_cost: Optional[float]


class ComplianceCheck(TypedDict):
    """Australian law compliance structure"""
    state_compliance: bool
    compliance_issues: List[str]
    cooling_off_compliance: bool
    stamp_duty_requirements: Dict[str, Any]
    mandatory_disclosures: List[str]
    warnings: List[str]


class StampDutyCalculation(TypedDict):
    """Australian stamp duty calculation"""
    state: AustralianState
    purchase_price: float
    base_duty: float
    exemptions: float
    surcharges: float
    total_duty: float
    is_first_home_buyer: bool
    is_foreign_buyer: bool
    breakdown: Dict[str, float]


def create_initial_state(
    user_id: str,
    australian_state: AustralianState,
    user_type: str = "buyer",
    user_preferences: Optional[Dict[str, Any]] = None
) -> RealEstateAgentState:
    """Create initial agent state"""
    
    return RealEstateAgentState(
        # Session Management
        user_id=user_id,
        session_id=str(uuid.uuid4()),
        agent_version="1.0",
        
        # Document Processing
        document_data=None,
        document_metadata=None,
        parsing_status=ProcessingStatus.PENDING,
        
        # Contract Analysis
        contract_terms=None,
        risk_assessment=None,
        compliance_check=None,
        recommendations=[],
        
        # Property Data
        property_data=None,
        market_analysis=None,
        financial_analysis=None,
        
        # User Context
        user_preferences=user_preferences or {},
        australian_state=australian_state,
        user_type=user_type,
        
        # Processing State
        current_step="initialized",
        error_state=None,
        confidence_scores={},
        processing_time=None,
        
        # Output
        analysis_results={},
        report_data=None,
        final_recommendations=[]
    )


def update_state_step(
    state: RealEstateAgentState,
    step: str,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> RealEstateAgentState:
    """Update state with new step and optional data"""
    
    updated_state = state.copy()
    updated_state["current_step"] = step
    
    if error:
        updated_state["error_state"] = error
        updated_state["parsing_status"] = ProcessingStatus.FAILED
    
    if data:
        updated_state.update(data)
    
    return updated_state


def calculate_confidence_score(state: RealEstateAgentState) -> float:
    """Calculate overall confidence score for analysis"""
    
    scores = state.get("confidence_scores", {})
    if not scores:
        return 0.0
    
    # Weighted average of different analysis components
    weights = {
        "document_parsing": 0.2,
        "term_extraction": 0.3,
        "risk_assessment": 0.25,
        "compliance_check": 0.25
    }
    
    weighted_sum = 0.0
    total_weight = 0.0
    
    for component, weight in weights.items():
        if component in scores:
            weighted_sum += scores[component] * weight
            total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0