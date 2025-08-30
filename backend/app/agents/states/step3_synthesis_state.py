from typing import Dict, Any, Optional, List, Annotated
from operator import add
from datetime import datetime

from app.agents.states.base import LangGraphBaseState


class Step3SynthesisState(LangGraphBaseState):
    """LangGraph state schema for Step 3 synthesis (risk, actions, compliance, report)."""

    # Context from parent/state - must be annotated for concurrent updates
    australian_state: Annotated[Optional[str], lambda x, y: y]
    contract_type: Annotated[Optional[str], lambda x, y: y]

    # Seeds context
    section_seeds: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Inputs (from Step 2)
    special_risks_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    disclosure_compliance_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    cross_section_validation_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    title_encumbrances_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    settlement_logistics_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    adjustments_outgoings_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    conditions_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    parties_property_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    financial_terms_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    warranties_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    default_termination_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    diagram_risk_assessment_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Step 3 Outputs (aligned with contract attributes)
    risk_summary: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    recommendations: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    compliance_summary: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    buyer_report: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Tracking - must be annotated for concurrent updates
    start_time: Annotated[Optional[datetime], lambda x, y: y]
    processing_errors: Annotated[List[str], add]
