"""
LangGraph State Models for Real2.AI Contract Analysis
"""

from typing import TypedDict, Optional, Dict, List, Any, Annotated
from datetime import datetime
import uuid
from operator import add

from app.schema.enums import AustralianState, ContractType, ProcessingStatus, RiskLevel


class RealEstateAgentState(TypedDict):
    """Central state for all Real2.AI agents"""

    # Session Management
    user_id: Annotated[str, lambda x, y: y]  # Last value wins for concurrent updates
    session_id: Annotated[str, lambda x, y: y]  # Last value wins for concurrent updates
    agent_version: Annotated[
        str, lambda x, y: y
    ]  # Last value wins for concurrent updates

    # Document Processing
    document_data: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    document_metadata: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    parsing_status: Annotated[
        ProcessingStatus, lambda x, y: y
    ]  # Last value wins for status updates

    # Contract Analysis
    contract_terms: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    risk_assessment: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    compliance_check: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    recommendations: Annotated[
        List[Dict[str, Any]], add
    ]  # Use add for list concatenation

    # Property Data (Phase 2+)
    property_data: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    market_analysis: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    financial_analysis: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins

    # User Context
    user_preferences: Annotated[Dict[str, Any], lambda x, y: y]  # Last value wins
    australian_state: Annotated[AustralianState, lambda x, y: y]  # Last value wins
    user_type: Annotated[str, lambda x, y: y]  # Last value wins
    contract_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    document_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins

    # Processing State
    current_step: Annotated[List[str], add]  # Use add for list concatenation
    # Allow concurrent writes; last update wins to satisfy LangGraph's reducer requirement
    error_state: Annotated[Optional[str], lambda existing, incoming: incoming]
    confidence_scores: Annotated[Dict[str, float], lambda x, y: y]  # Last value wins
    processing_time: Annotated[Optional[float], lambda x, y: y]  # Last value wins
    progress: Annotated[Optional[Dict[str, Any]], lambda x, y: y]  # Last value wins

    # Output
    analysis_results: Annotated[
        Dict[str, Any],
        lambda existing, incoming: {**(existing or {}), **(incoming or {})},
    ]
    report_data: Annotated[Optional[Dict[str, Any]], lambda x, y: y]  # Last value wins
    final_recommendations: Annotated[
        List[Dict[str, Any]], add
    ]  # Use add for list concatenation


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
    user_preferences: Optional[Dict[str, Any]] = None,
    contract_type: str = "purchase_agreement",
    document_type: str = "contract",
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
        contract_type=contract_type,
        document_type=document_type,
        # Processing State
        current_step=["initialized"],  # Now a list for Annotated handling
        error_state=None,
        confidence_scores={},
        processing_time=None,
        progress={"percentage": 0, "step": "initialized"},
        # Output
        analysis_results={},
        report_data=None,
        final_recommendations=[],
    )


def update_state_step(
    state: RealEstateAgentState,
    step: str,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Update state with new step and optional data - returns minimal state to prevent concurrent updates"""

    # Handle backward compatibility: convert string step to list for Annotated pattern
    if isinstance(step, str):
        updated_state = {
            "current_step": [step]
        }  # Convert to list for concurrent updates
    else:
        # Already a list
        updated_state = {"current_step": step}

    # Handle errors (these are always allowed)
    if error:
        updated_state["error_state"] = error
        updated_state["parsing_status"] = ProcessingStatus.FAILED

    # Add explicitly provided data
    if data:
        for key, value in data.items():
            if value is not None:
                # For lists and dicts, we might need special handling
                if (
                    key in state
                    and isinstance(state[key], dict)
                    and isinstance(value, dict)
                ):
                    # Merge dictionaries
                    merged_dict = dict(state[key])
                    merged_dict.update(value)
                    updated_state[key] = merged_dict
                elif (
                    key in state
                    and isinstance(state[key], list)
                    and isinstance(value, list)
                ):
                    # Extend lists
                    updated_state[key] = state[key] + value
                else:
                    # Direct assignment - ensure this field is Annotated in the state model
                    updated_state[key] = value

    # CRITICAL: Ensure all fields in the update are properly handled for concurrent updates
    # This prevents LangGraph InvalidUpdateError
    return updated_state


def get_current_step(state: RealEstateAgentState) -> str:
    """Get the latest step from the Annotated list"""
    steps = state.get("current_step", ["initialized"])
    return steps[-1] if steps else "initialized"


def create_step_update(
    step_name: str, progress_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a proper state update for LangGraph concurrent handling"""
    update = {"current_step": [step_name]}

    if progress_data:
        update.update(progress_data)

    return update


def calculate_confidence_score(state: RealEstateAgentState) -> float:
    """Calculate overall confidence score for analysis with enhanced weighting"""

    scores = state.get("confidence_scores", {})
    if not scores:
        return 0.0

    # Enhanced weighted average of different analysis components
    weights = {
        "input_validation": 0.05,
        "document_processing": 0.15,
        "term_extraction": 0.30,
        "compliance_check": 0.25,
        "risk_assessment": 0.20,
        "recommendations": 0.05,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for component, weight in weights.items():
        if component in scores:
            score = scores[component]
            # Apply quality penalty for very low scores
            if score < 0.3:
                score *= 0.5  # Significant penalty for very low confidence
            elif score < 0.5:
                score *= 0.8  # Moderate penalty for low confidence

            weighted_sum += score * weight
            total_weight += weight

    base_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Apply additional penalties/bonuses
    document_metadata = state.get("document_metadata", {})
    text_quality = document_metadata.get("text_quality", {})

    # Bonus for high-quality text extraction
    if text_quality.get("score", 0) > 0.8:
        base_confidence *= 1.1
    elif text_quality.get("score", 0) < 0.5:
        base_confidence *= 0.9

    # Penalty for using fallback methods
    extraction_metadata = state.get("extraction_metadata", {})
    if extraction_metadata.get("extraction_method") == "fallback":
        base_confidence *= 0.8

    # Penalty for errors in workflow
    if state.get("error_state"):
        base_confidence *= 0.7

    # Ensure confidence is within valid range
    return max(0.0, min(1.0, base_confidence))
