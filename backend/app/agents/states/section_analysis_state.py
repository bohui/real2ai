from typing import Dict, Any, Optional, List, Annotated
from operator import add
from datetime import datetime

from app.agents.states.base import LangGraphBaseState


class Step2AnalysisState(LangGraphBaseState):
    """LangGraph state schema for Step 2 section-by-section analysis"""

    # Input data
    contract_text: str
    entities_extraction: Dict[str, Any]
    legal_requirements_matrix: Optional[Dict[str, Any]]
    uploaded_diagrams: Optional[Dict[str, bytes]]

    # Context from parent state
    australian_state: Optional[str]
    contract_type: Optional[str]
    purchase_method: Optional[str]
    use_category: Optional[str]
    property_condition: Optional[str]

    # Seeds / retrieval context
    section_seeds: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    retrieval_index_id: Annotated[Optional[str], lambda x, y: y]

    # Phase 1 Foundation Results (Parallel)
    parties_property_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    financial_terms_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    conditions_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    warranties_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    default_termination_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    image_semantics_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Phase 2 Dependent Results (Sequential)
    settlement_logistics_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    title_encumbrances_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Phase 3 Synthesis Results (Sequential)
    adjustments_outgoings_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    disclosure_compliance_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    special_risks_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Cross-section validation
    cross_section_validation_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Workflow control
    phase1_complete: Annotated[bool, lambda x, y: y]
    phase2_complete: Annotated[bool, lambda x, y: y]
    phase3_complete: Annotated[bool, lambda x, y: y]

    # Error and monitoring
    processing_errors: Annotated[List[str], add]
    skipped_analyzers: Annotated[List[str], add]
    total_risk_flags: Annotated[List[str], add]

    # Performance tracking
    start_time: Annotated[Optional[datetime], lambda x, y: y]
    phase_completion_times: Annotated[
        Dict[str, datetime], lambda x, y: {**(x or {}), **(y or {})}
    ]
    total_diagrams_processed: Annotated[int, lambda x, y: y]
    diagram_processing_success_rate: Annotated[float, lambda x, y: y]
