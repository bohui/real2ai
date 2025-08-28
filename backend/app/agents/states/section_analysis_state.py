from typing import Dict, Any, Optional, List, Annotated
from operator import add
from datetime import datetime

from app.agents.states.base import LangGraphBaseState


class Step2AnalysisState(LangGraphBaseState):
    """LangGraph state schema for Step 2 section-by-section analysis"""

    # Input data
    contract_text: str
    extracted_entity: Dict[str, Any]
    legal_requirements_matrix: Optional[Dict[str, Any]]
    uploaded_diagrams: Optional[Dict[str, List[Dict[str, Any]]]]

    # Context from parent state
    australian_state: Optional[str]
    contract_type: Optional[str]
    purchase_method: Optional[str]
    use_category: Optional[str]
    property_condition: Optional[str]
    contract_metadata: Optional[Dict[str, Any]]

    # Seeds / retrieval context
    section_seeds: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    retrieval_index_id: Annotated[Optional[str], lambda x, y: y]

    # Phase 1 Foundation Results (Parallel)
    parties_property: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    financial_terms: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    conditions: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    warranties: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    default_termination: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    image_semantics: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    diagram_risks: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Phase 2 Dependent Results (Sequential)
    settlement_logistics: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    title_encumbrances: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Phase 3 Synthesis Results (Sequential)
    adjustments_outgoings: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    disclosure_compliance: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    special_risks: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

    # Cross-section validation
    cross_section_validation: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

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
