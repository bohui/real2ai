"""
Step 2 Section-by-Section Analysis LangGraph Sub-Workflow

This module implements the comprehensive contract analysis workflow with three phases:
- Phase 1: Foundation Analysis (parallel execution)
- Phase 2: Dependent Analysis (sequential with limited parallelism)
- Phase 3: Synthesis Analysis (sequential)

Replaces ContractTermsExtractionNode with specialized section analyzers.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Callable, Awaitable
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from app.models.contract_state import RealEstateAgentState
from app.core.langsmith_config import langsmith_trace

logger = logging.getLogger(__name__)


class Step2AnalysisState(TypedDict):
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

    # Phase 1 Foundation Results (Parallel)
    parties_property_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    financial_terms_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    conditions_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    warranties_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]
    default_termination_result: Annotated[Optional[Dict[str, Any]], lambda x, y: y]

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

    # Progress notification callback
    notify_progress: Annotated[
        Optional[Callable[[str, int, str], Awaitable[None]]],
        lambda x, y: y,
    ]


class Step2AnalysisWorkflow:
    """
    LangGraph workflow for Step 2 section-by-section contract analysis.

    Implements three-phase processing:
    1. Foundation Analysis (parallel): Parties, Financial, Conditions, Warranties, Default
    2. Dependent Analysis (sequential): Settlement, Title+Diagrams
    3. Synthesis Analysis (sequential): Adjustments, Disclosure, Special Risks

    Includes comprehensive error handling, dependency management, and performance monitoring.
    """

    def __init__(self):
        # Initialize prompt manager (will be properly configured in Story S13)
        from app.core.prompts import get_prompt_manager

        self.prompt_manager = get_prompt_manager()

        # Progress tracking ranges for each phase
        self.PROGRESS_RANGES = {
            "initialize_workflow": (0, 2),
            "analyze_parties_property": (2, 12),
            "analyze_financial_terms": (12, 22),
            "analyze_conditions": (22, 32),
            "analyze_warranties": (32, 40),
            "analyze_default_termination": (40, 48),
            "check_phase1_completion": (48, 50),
            "analyze_settlement_logistics": (50, 60),
            "analyze_title_encumbrances": (60, 75),
            "check_phase2_completion": (75, 77),
            "calculate_adjustments_outgoings": (77, 83),
            "check_disclosure_compliance": (83, 89),
            "identify_special_risks": (89, 94),
            "validate_cross_sections": (94, 98),
            "finalize_results": (98, 100),
        }

        # Initialize node instances for delegation
        self._create_nodes()

        # Build workflow graph bound to node.execute handlers
        self.graph = self._build_workflow_graph()

    def _create_nodes(self):
        """Create node instances for Step 2 subflow."""
        from app.agents.nodes.step2_section_analysis_subflow import (
            InitializeWorkflowNode,
            PartiesPropertyNode,
            FinancialTermsNode,
            ConditionsNode,
            WarrantiesNode,
            DefaultTerminationNode,
            CheckPhase1CompletionNode,
            SettlementLogisticsNode,
            TitleEncumbrancesNode,
            CheckPhase2CompletionNode,
            AdjustmentsOutgoingsNode,
            DisclosureComplianceNode,
            SpecialRisksNode,
            CrossSectionValidationNode,
            FinalizeResultsNode,
        )

        # Instantiate nodes with progress ranges
        self.initialize_workflow_node = InitializeWorkflowNode(
            progress_range=self.PROGRESS_RANGES["initialize_workflow"]
        )
        self.parties_property_node = PartiesPropertyNode(
            progress_range=self.PROGRESS_RANGES["analyze_parties_property"]
        )
        self.financial_terms_node = FinancialTermsNode(
            progress_range=self.PROGRESS_RANGES["analyze_financial_terms"]
        )
        self.conditions_node = ConditionsNode(
            progress_range=self.PROGRESS_RANGES["analyze_conditions"]
        )
        self.warranties_node = WarrantiesNode(
            progress_range=self.PROGRESS_RANGES["analyze_warranties"]
        )
        self.default_termination_node = DefaultTerminationNode(
            progress_range=self.PROGRESS_RANGES["analyze_default_termination"]
        )
        self.check_phase1_completion_node = CheckPhase1CompletionNode(
            progress_range=self.PROGRESS_RANGES["check_phase1_completion"]
        )
        self.settlement_logistics_node = SettlementLogisticsNode(
            progress_range=self.PROGRESS_RANGES["analyze_settlement_logistics"]
        )
        self.title_encumbrances_node = TitleEncumbrancesNode(
            progress_range=self.PROGRESS_RANGES["analyze_title_encumbrances"]
        )
        self.check_phase2_completion_node = CheckPhase2CompletionNode(
            progress_range=self.PROGRESS_RANGES["check_phase2_completion"]
        )
        self.adjustments_outgoings_node = AdjustmentsOutgoingsNode(
            progress_range=self.PROGRESS_RANGES["calculate_adjustments_outgoings"]
        )
        self.disclosure_compliance_node = DisclosureComplianceNode(
            progress_range=self.PROGRESS_RANGES["check_disclosure_compliance"]
        )
        self.special_risks_node = SpecialRisksNode(
            progress_range=self.PROGRESS_RANGES["identify_special_risks"]
        )
        self.cross_section_validation_node = CrossSectionValidationNode(
            progress_range=self.PROGRESS_RANGES["validate_cross_sections"]
        )
        self.finalize_results_node = FinalizeResultsNode(
            progress_range=self.PROGRESS_RANGES["finalize_results"]
        )

        # Optional: registry
        self.nodes = {
            "initialize_workflow": self.initialize_workflow_node,
            "analyze_parties_property": self.parties_property_node,
            "analyze_financial_terms": self.financial_terms_node,
            "analyze_conditions": self.conditions_node,
            "analyze_warranties": self.warranties_node,
            "analyze_default_termination": self.default_termination_node,
            "check_phase1_completion": self.check_phase1_completion_node,
            "analyze_settlement_logistics": self.settlement_logistics_node,
            "analyze_title_encumbrances": self.title_encumbrances_node,
            "check_phase2_completion": self.check_phase2_completion_node,
            "calculate_adjustments_outgoings": self.adjustments_outgoings_node,
            "check_disclosure_compliance": self.disclosure_compliance_node,
            "identify_special_risks": self.special_risks_node,
            "validate_cross_sections": self.cross_section_validation_node,
            "finalize_results": self.finalize_results_node,
        }

    def _build_workflow_graph(self) -> CompiledStateGraph:
        """Build the LangGraph state graph for Step 2 analysis"""

        # Create state graph
        graph = StateGraph(Step2AnalysisState)

        # Add workflow initialization
        graph.add_node("initialize_workflow", self.initialize_workflow)

        # Phase 1: Foundation Analysis Nodes (Parallel)
        graph.add_node("analyze_parties_property", self.analyze_parties_property)
        graph.add_node("analyze_financial_terms", self.analyze_financial_terms)
        graph.add_node("analyze_conditions", self.analyze_conditions)
        graph.add_node("analyze_warranties", self.analyze_warranties)
        graph.add_node("analyze_default_termination", self.analyze_default_termination)

        # Phase 1 completion check
        graph.add_node("check_phase1_completion", self.check_phase1_completion)

        # Phase 2: Dependent Analysis Nodes (Sequential)
        graph.add_node(
            "analyze_settlement_logistics", self.analyze_settlement_logistics
        )
        graph.add_node("analyze_title_encumbrances", self.analyze_title_encumbrances)

        # Phase 2 completion check
        graph.add_node("check_phase2_completion", self.check_phase2_completion)

        # Phase 3: Synthesis Analysis Nodes (Sequential)
        graph.add_node(
            "calculate_adjustments_outgoings", self.calculate_adjustments_outgoings
        )
        graph.add_node("check_disclosure_compliance", self.check_disclosure_compliance)
        graph.add_node("identify_special_risks", self.identify_special_risks)

        # Cross-section validation and finalization
        graph.add_node("validate_cross_sections", self.validate_cross_sections)
        graph.add_node("finalize_results", self.finalize_results)

        # Define workflow edges
        self._define_workflow_edges(graph)

        # Compile and return
        return graph.compile()

    def _define_workflow_edges(self, graph: StateGraph):
        """Define the workflow execution edges with dependency management"""

        # Start with initialization
        graph.add_edge(START, "initialize_workflow")

        # Phase 1: All foundation nodes start after initialization
        foundation_nodes = [
            "analyze_parties_property",
            "analyze_financial_terms",
            "analyze_conditions",
            "analyze_warranties",
            "analyze_default_termination",
        ]

        for node in foundation_nodes:
            graph.add_edge("initialize_workflow", node)
            graph.add_edge(node, "check_phase1_completion")

        # Phase 2: Dependent analysis after Phase 1 completion
        graph.add_edge("check_phase1_completion", "analyze_settlement_logistics")
        graph.add_edge("check_phase1_completion", "analyze_title_encumbrances")

        # Phase 2 completion check
        graph.add_edge("analyze_settlement_logistics", "check_phase2_completion")
        graph.add_edge("analyze_title_encumbrances", "check_phase2_completion")

        # Phase 3: Synthesis analysis after Phase 2 completion
        graph.add_edge("check_phase2_completion", "calculate_adjustments_outgoings")
        graph.add_edge("check_phase2_completion", "check_disclosure_compliance")
        graph.add_edge("check_phase2_completion", "identify_special_risks")

        # Cross-section validation after Phase 3
        synthesis_nodes = [
            "calculate_adjustments_outgoings",
            "check_disclosure_compliance",
            "identify_special_risks",
        ]

        for node in synthesis_nodes:
            graph.add_edge(node, "validate_cross_sections")

        # Finalize and end
        graph.add_edge("validate_cross_sections", "finalize_results")
        graph.add_edge("finalize_results", END)

    async def execute(
        self,
        contract_text: str,
        entities_extraction: Dict[str, Any],
        parent_state: RealEstateAgentState,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute the Step 2 analysis workflow.

        Args:
            contract_text: Full contract text from document processing
            entities_extraction: Results from Step 1 entity extraction
            parent_state: Parent workflow state for context
            **kwargs: Additional context (diagrams, legal matrix, etc.)

        Returns:
            Comprehensive Step 2 analysis results
        """

        # Initialize Step 2 state from inputs
        step2_state: Step2AnalysisState = {
            # Input data
            "contract_text": contract_text,
            "entities_extraction": entities_extraction,
            "legal_requirements_matrix": kwargs.get("legal_requirements_matrix"),
            "uploaded_diagrams": kwargs.get("uploaded_diagrams"),
            # Context from parent state
            "australian_state": parent_state.get("australian_state"),
            "contract_type": parent_state.get("contract_type"),
            "purchase_method": parent_state.get("purchase_method"),
            "use_category": parent_state.get("use_category"),
            "property_condition": parent_state.get("property_condition"),
            # Initialize results as None
            "parties_property_result": None,
            "financial_terms_result": None,
            "conditions_result": None,
            "warranties_result": None,
            "default_termination_result": None,
            "settlement_logistics_result": None,
            "title_encumbrances_result": None,
            "adjustments_outgoings_result": None,
            "disclosure_compliance_result": None,
            "special_risks_result": None,
            "cross_section_validation_result": None,
            # Initialize workflow control
            "phase1_complete": False,
            "phase2_complete": False,
            "phase3_complete": False,
            # Initialize tracking
            "processing_errors": [],
            "skipped_analyzers": [],
            "total_risk_flags": [],
            "start_time": datetime.now(UTC),
            "phase_completion_times": {},
            "total_diagrams_processed": 0,
            "diagram_processing_success_rate": 0.0,
            # Pass through progress callback from parent state
            "notify_progress": parent_state.get("notify_progress"),
        }

        try:
            # Execute the workflow
            result_state = await self.graph.ainvoke(step2_state)

            # Extract and structure results
            return self._extract_final_results(result_state)

        except Exception as e:
            logger.error(f"Step 2 workflow execution failed: {str(e)}", exc_info=True)

            # Return error result structure
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
                "partial_results": {},
                "processing_errors": [str(e)],
            }

    async def _notify_status(
        self, state: Step2AnalysisState, step: str, percent: int, desc: str
    ) -> None:
        """Notify progress status - similar to document processing workflow pattern."""
        try:
            # Best-effort async persistence callback from parent state
            notify = (state or {}).get("notify_progress")
            if notify and callable(notify):
                await notify(step, percent, desc)
        except Exception as e:
            logger.warning(f"Failed to notify progress for step {step}: {e}")

    async def _get_parser(self, parser_name: str, schema_class):
        """Get output parser for structured analysis"""
        try:
            # Use central parser factory
            from app.core.prompts.parsers import create_parser

            return create_parser(schema_class, strict_mode=False, retry_on_failure=True)
        except Exception as e:
            logger.warning(f"Failed to create parser {parser_name}: {e}")
            return None

    def _extract_final_results(self, state: Step2AnalysisState) -> Dict[str, Any]:
        """Extract and structure final results from Step 2 state"""

        total_duration = (
            (datetime.now(UTC) - state["start_time"]).total_seconds()
            if state.get("start_time")
            else 0
        )

        return {
            "success": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_duration_seconds": total_duration,
            # Section results
            "section_results": {
                "parties_property": state.get("parties_property_result"),
                "financial_terms": state.get("financial_terms_result"),
                "conditions": state.get("conditions_result"),
                "warranties": state.get("warranties_result"),
                "default_termination": state.get("default_termination_result"),
                "settlement_logistics": state.get("settlement_logistics_result"),
                "title_encumbrances": state.get("title_encumbrances_result"),
                "adjustments_outgoings": state.get("adjustments_outgoings_result"),
                "disclosure_compliance": state.get("disclosure_compliance_result"),
                "special_risks": state.get("special_risks_result"),
            },
            # Cross-section validation
            "cross_section_validation": state.get("cross_section_validation_result"),
            # Workflow metadata
            "workflow_metadata": {
                "phases_completed": {
                    "phase1": state.get("phase1_complete", False),
                    "phase2": state.get("phase2_complete", False),
                    "phase3": state.get("phase3_complete", False),
                },
                "phase_completion_times": state.get("phase_completion_times", {}),
                "processing_errors": state.get("processing_errors", []),
                "skipped_analyzers": state.get("skipped_analyzers", []),
                "total_risk_flags": state.get("total_risk_flags", []),
                "diagrams_processed": state.get("total_diagrams_processed", 0),
                "diagram_success_rate": state.get(
                    "diagram_processing_success_rate", 0.0
                ),
            },
        }

    # Node Implementation Methods
    # These will be implemented in subsequent stories

    @langsmith_trace(name="initialize_workflow", run_type="tool")
    async def initialize_workflow(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.initialize_workflow_node.execute(state)

    @langsmith_trace(name="analyze_parties_property", run_type="tool")
    async def analyze_parties_property(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.parties_property_node.execute(state)

    @langsmith_trace(name="analyze_financial_terms", run_type="tool")
    async def analyze_financial_terms(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.financial_terms_node.execute(state)

    @langsmith_trace(name="analyze_conditions", run_type="tool")
    async def analyze_conditions(self, state: Step2AnalysisState) -> Step2AnalysisState:
        return await self.conditions_node.execute(state)

    @langsmith_trace(name="analyze_warranties", run_type="tool")
    async def analyze_warranties(self, state: Step2AnalysisState) -> Step2AnalysisState:
        return await self.warranties_node.execute(state)

    @langsmith_trace(name="analyze_default_termination", run_type="tool")
    async def analyze_default_termination(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.default_termination_node.execute(state)

    async def _check_phase1_completion(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Check Phase 1 completion and manage dependencies"""
        logger.info("Checking Phase 1 completion")

        # Check if all Phase 1 analyzers completed
        required_results = [
            "parties_property_result",
            "financial_terms_result",
            "conditions_result",
            "warranties_result",
            "default_termination_result",
        ]

        completed_count = sum(
            1 for key in required_results if state.get(key) is not None
        )
        total_count = len(required_results)

        if completed_count == total_count:
            logger.info(
                f"Phase 1 completed successfully: {completed_count}/{total_count} analyzers"
            )
            return {
                "phase1_complete": True,
                "phase_completion_times": {"phase1": datetime.now(UTC)},
            }
        else:
            logger.warning(
                f"Phase 1 incomplete: {completed_count}/{total_count} analyzers completed"
            )
        return {}

    @langsmith_trace(name="analyze_settlement_logistics", run_type="tool")
    async def analyze_settlement_logistics(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.settlement_logistics_node.execute(state)

    @langsmith_trace(name="analyze_title_encumbrances", run_type="tool")
    async def analyze_title_encumbrances(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.title_encumbrances_node.execute(state)

    @langsmith_trace(name="check_phase2_completion", run_type="tool")
    async def check_phase2_completion(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.check_phase2_completion_node.execute(state)

    @langsmith_trace(name="calculate_adjustments_outgoings", run_type="tool")
    async def calculate_adjustments_outgoings(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.adjustments_outgoings_node.execute(state)

    @langsmith_trace(name="check_disclosure_compliance", run_type="tool")
    async def check_disclosure_compliance(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.disclosure_compliance_node.execute(state)

    @langsmith_trace(name="identify_special_risks", run_type="tool")
    async def identify_special_risks(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.special_risks_node.execute(state)

    @langsmith_trace(name="validate_cross_sections", run_type="tool")
    async def validate_cross_sections(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        return await self.cross_section_validation_node.execute(state)

    @langsmith_trace(name="finalize_results", run_type="tool")
    async def finalize_results(self, state: Step2AnalysisState) -> Step2AnalysisState:
        return await self.finalize_results_node.execute(state)


# Factory function for workflow creation
def create_step2_workflow() -> Step2AnalysisWorkflow:
    """Create and return a new Step 2 analysis workflow instance"""
    return Step2AnalysisWorkflow()
