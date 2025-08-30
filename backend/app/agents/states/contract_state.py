"""
LangGraph State Models for Real2.AI Contract Analysis
"""

from typing import TypedDict, Optional, Dict, List, Any, Annotated
import uuid
from operator import add

from app.schema.enums import AustralianState, ProcessingStatus, RiskLevel
from app.agents.states.base import LangGraphBaseState


class ProgressState(TypedDict, total=False):
    """Canonical progress structure for the workflow.

    - current_step: Zero-based numeric index of the current step
    - total_steps: Total number of steps configured for this run
    - percentage: Integer percentage derived from current_step/total_steps
    - status: ProcessingStatus indicating overall run status
    - step_name: Human-readable name of the latest step
    - step_history: Ordered list of step names reached
    - error: Optional error message when status is FAILED
    """

    current_step: int
    total_steps: int
    percentage: int
    status: ProcessingStatus
    step_name: str
    step_history: List[str]
    error: Optional[str]


class RealEstateAgentState(LangGraphBaseState):
    """Central state for all Real2.AI agents"""

    # Session Management
    user_id: Annotated[str, lambda x, y: y]  # Last value wins for concurrent updates
    session_id: Annotated[str, lambda x, y: y]  # Last value wins for concurrent updates
    agent_version: Annotated[
        str, lambda x, y: y
    ]  # Last value wins for concurrent updates
    # Contract identifier for UI progress payloads (UUID)
    contract_id: Annotated[Optional[str], lambda x, y: y]

    # Property Data (removed: not used in contract analysis workflow)

    # User Context
    user_preferences: Annotated[Dict[str, Any], lambda x, y: y]  # Last value wins
    australian_state: Annotated[AustralianState, lambda x, y: y]  # Last value wins
    user_type: Annotated[str, lambda x, y: y]  # Last value wins
    contract_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins
    document_type: Annotated[Optional[str], lambda x, y: y]  # Last value wins

    # Processing State
    processing_time: Annotated[Optional[float], lambda x, y: y]  # Last value wins
    # Single source of truth for workflow progress
    progress: Annotated[Optional[ProgressState], lambda x, y: y]  # Last value wins

    confidence_scores: Annotated[Dict[str, float], lambda x, y: y]  # Last value wins

    # Document Processing
    step0_document_data: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    step0_ocr_processing: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins

    # Analysis Results Structure
    # Step 1: Entity extraction results
    step1_extracted_entity: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins

    # Step 1 (parallel): Section seeds extraction results
    step1_extracted_sections: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins

    # Contract Analysis (legacy `contract_terms` removed; use `step2_analysis_result`)

    # Step 2: Section-by-section analysis results (NEW)
    step2_analysis_result: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins

    # Output (Step 3 synthesis)
    step3_risk_assessment: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    step3_compliance_check: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    step3_recommendations: Annotated[
        List[Dict[str, Any]], add
    ]  # Use add for list concatenation
    step3_buyer_report: Annotated[
        Optional[Dict[str, Any]], lambda x, y: y
    ]  # Last value wins
    report_data: Annotated[Optional[Dict[str, Any]], lambda x, y: y]  # Last value wins


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


class ProgressState(TypedDict, total=False):
    """Canonical progress structure for the workflow.

    - current_step: Zero-based numeric index of the current step
    - total_steps: Total number of steps configured for this run
    - percentage: Integer percentage derived from current_step/total_steps
    - status: ProcessingStatus indicating overall run status
    - step_name: Human-readable name of the latest step
    - step_history: Ordered list of step names reached
    - error: Optional error message when status is FAILED
    """

    current_step: int
    total_steps: int
    percentage: int
    status: ProcessingStatus
    step_name: str
    step_history: List[str]
    error: Optional[str]


def create_initial_state(
    user_id: str,
    content_hash: str,
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
        contract_id=None,
        # Base required field for LangGraph state
        content_hash=content_hash,
        # Document Processing
        step0_document_data=None,
        step0_ocr_processing=None,
        # Contract Analysis
        step3_risk_assessment=None,
        step3_compliance_check=None,
        step3_recommendations=[],
        step3_buyer_report=None,
        # Property Data (removed)
        # User Context
        user_preferences=user_preferences or {},
        australian_state=australian_state,
        user_type=user_type,
        contract_type=contract_type,
        document_type=document_type,
        # Processing State
        confidence_scores={},
        processing_time=None,
        progress={
            "current_step": 0,
            "total_steps": 0,
            "percentage": 0,
            "status": ProcessingStatus.PENDING,
            "step_name": "initialized",
            "step_history": [],
        },
        notify_progress=None,
        # Output
        report_data=None,
    )


def update_state_step(
    state: RealEstateAgentState,
    step: str,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Update state with new step and optional data - returns minimal state to prevent concurrent updates"""

    # Build minimal updated state
    updated_state: Dict[str, Any] = {}

    # Build canonical progress update
    existing_progress: ProgressState = state.get("progress") or {}  # type: ignore[assignment]
    current_index = (
        int(existing_progress.get("current_step", 0))
        if isinstance(existing_progress, dict)
        else 0
    )
    total_steps = (
        int(existing_progress.get("total_steps", 0))
        if isinstance(existing_progress, dict)
        else 0
    )
    # Increment index by one when advancing a step, but don't exceed total_steps if set
    next_index = (
        current_index + 1
        if total_steps == 0 or current_index + 1 <= total_steps
        else total_steps
    )

    # Compute percentage if total_steps is known (>0)
    percentage = (
        (
            int((next_index / total_steps) * 100)
            if isinstance(total_steps, int) and total_steps > 0
            else existing_progress.get("percentage", 0)
        )
        if isinstance(existing_progress, dict)
        else 0
    )

    # Derive status from error or keep as IN_PROGRESS/PENDING
    if error:
        status = ProcessingStatus.FAILED
    else:
        # If previously pending, mark as in progress; keep COMPLETED if already set by finalizer
        previous_status = (
            existing_progress.get("status", ProcessingStatus.PENDING)
            if isinstance(existing_progress, dict)
            else ProcessingStatus.PENDING
        )
        status = (
            previous_status
            if previous_status == ProcessingStatus.COMPLETED
            else (
                ProcessingStatus.IN_PROGRESS
                if previous_status in (ProcessingStatus.PENDING, None)
                else previous_status
            )
        )

    # Update progress structure
    new_progress: ProgressState = {
        "current_step": next_index,
        "total_steps": total_steps or 0,
        "percentage": percentage if isinstance(percentage, int) else 0,
        "status": status,
        "step_name": step,
        "step_history": (
            list(existing_progress.get("step_history", []))
            if isinstance(existing_progress, dict)
            else []
        ),
    }
    new_progress["step_history"].append(step)
    if error:
        new_progress["error"] = error

    updated_state["progress"] = {**(existing_progress or {}), **new_progress}

    # Add explicitly provided data
    if data:
        for key, value in data.items():
            if value is not None:
                # Special handling for progress to preserve canonical fields
                if key == "progress" and isinstance(value, dict):
                    base_progress = updated_state.get("progress") or {}
                    merged = {**base_progress, **value}
                    # Ensure step_name reflects latest step
                    merged.setdefault("step_name", step)
                    updated_state["progress"] = merged
                    # Keep parsing_status in sync if provided
                    status_override = merged.get("status")
                    if status_override:
                        updated_state["parsing_status"] = status_override
                    continue

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
    """Get the latest human-readable step name.

    Prefers the canonical progress.step_name; falls back to last item of current_step list.
    """
    progress = state.get("progress") or {}
    if isinstance(progress, dict) and progress.get("step_name"):
        return progress["step_name"]
    return "initialized"


def create_step_update(
    step_name: str, progress_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a proper state update for LangGraph concurrent handling.

    This ensures both the canonical progress structure and the legacy current_step list are updated.
    """
    update: Dict[str, Any] = {}

    if progress_data and isinstance(progress_data, dict):
        # If caller provides progress partials, place them under the progress key
        # without overwriting other unrelated fields in the state at call site
        update["progress"] = progress_data

    # Always include step_name in progress
    if "progress" not in update:
        update["progress"] = {}
    update["progress"]["step_name"] = step_name

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
    ocr_processing = state.get("step0_ocr_processing", {})
    text_quality = ocr_processing.get("text_quality", {})

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
