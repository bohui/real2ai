from typing import Dict, Any, Optional, List, Annotated
from operator import add
from datetime import datetime

from app.agents.states.base import LangGraphBaseState


class Step3SynthesisState(LangGraphBaseState):
    """LangGraph state schema for Step 3 synthesis (risk, actions, compliance, report)."""

    # Context from parent/state
    australian_state: Optional[str]
    contract_type: Optional[str]

    # Seeds / retrieval context
    section_seeds: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    retrieval_index_id: Annotated[Optional[str], lambda x, y: y]

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

    # Step 3 Outputs
    risk_summary_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    action_plan_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    compliance_summary_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    buyer_report_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Tracking
    start_time: Optional[datetime]
    processing_errors: Annotated[List[str], add]