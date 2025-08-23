"""
Step 2 Section-by-Section Analysis LangGraph Sub-Workflow

This module implements the comprehensive contract analysis workflow with three phases:
- Phase 1: Foundation Analysis (parallel execution)
- Phase 2: Dependent Analysis (sequential with limited parallelism)
- Phase 3: Synthesis Analysis (sequential)

Replaces ContractTermsExtractionNode with specialized section analyzers.
"""

import asyncio
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Callable, Awaitable
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from app.models.contract_state import RealEstateAgentState

logger = logging.getLogger(__name__)


class Step2AnalysisState(TypedDict):
    """LangGraph state schema for Step 2 section-by-section analysis"""

    # Input data
    contract_text: str
    entities_extraction_result: Dict[str, Any]
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

        self.graph = self._build_workflow_graph()

    def _build_workflow_graph(self) -> CompiledStateGraph:
        """Build the LangGraph state graph for Step 2 analysis"""

        # Create state graph
        graph = StateGraph(Step2AnalysisState)

        # Add workflow initialization
        graph.add_node("initialize_workflow", self._initialize_workflow)

        # Phase 1: Foundation Analysis Nodes (Parallel)
        graph.add_node("analyze_parties_property", self._analyze_parties_property)
        graph.add_node("analyze_financial_terms", self._analyze_financial_terms)
        graph.add_node("analyze_conditions", self._analyze_conditions)
        graph.add_node("analyze_warranties", self._analyze_warranties)
        graph.add_node("analyze_default_termination", self._analyze_default_termination)

        # Phase 1 completion check
        graph.add_node("check_phase1_completion", self._check_phase1_completion)

        # Phase 2: Dependent Analysis Nodes (Sequential)
        graph.add_node(
            "analyze_settlement_logistics", self._analyze_settlement_logistics
        )
        graph.add_node("analyze_title_encumbrances", self._analyze_title_encumbrances)

        # Phase 2 completion check
        graph.add_node("check_phase2_completion", self._check_phase2_completion)

        # Phase 3: Synthesis Analysis Nodes (Sequential)
        graph.add_node(
            "calculate_adjustments_outgoings", self._calculate_adjustments_outgoings
        )
        graph.add_node("check_disclosure_compliance", self._check_disclosure_compliance)
        graph.add_node("identify_special_risks", self._identify_special_risks)

        # Cross-section validation and finalization
        graph.add_node("validate_cross_sections", self._validate_cross_sections)
        graph.add_node("finalize_results", self._finalize_results)

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
        entities_extraction_result: Dict[str, Any],
        parent_state: RealEstateAgentState,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute the Step 2 analysis workflow.

        Args:
            contract_text: Full contract text from document processing
            entities_extraction_result: Results from Step 1 entity extraction
            parent_state: Parent workflow state for context
            **kwargs: Additional context (diagrams, legal matrix, etc.)

        Returns:
            Comprehensive Step 2 analysis results
        """

        # Initialize Step 2 state from inputs
        step2_state: Step2AnalysisState = {
            # Input data
            "contract_text": contract_text,
            "entities_extraction_result": entities_extraction_result,
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

    async def _initialize_workflow(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Initialize the Step 2 workflow with validation and setup"""
        logger.info("Initializing Step 2 section analysis workflow")

        # Notify progress
        await self._notify_status(
            state,
            "initialize_workflow",
            self.PROGRESS_RANGES["initialize_workflow"][1],
            "Starting Step 2 section analysis",
        )

        # Validate required inputs
        if not state.get("contract_text"):
            error_msg = "No contract text provided for Step 2 analysis"
            state["processing_errors"].append(error_msg)
            logger.error(error_msg)

        if not state.get("entities_extraction_result"):
            error_msg = "No entities extraction result provided for Step 2 analysis"
            state["processing_errors"].append(error_msg)
            logger.error(error_msg)

        # Prepare updates only (avoid returning entire state)
        updates: Dict[str, Any] = {}

        # Set workflow start time
        updates["start_time"] = datetime.now(UTC)

        # Log workflow initialization
        logger.info(
            "Step 2 workflow initialized",
            extra={
                "contract_text_length": len(state.get("contract_text", "")),
                "entities_present": bool(state.get("entities_extraction_result")),
                "diagrams_count": len(state.get("uploaded_diagrams") or {}),
                "legal_matrix_present": bool(state.get("legal_requirements_matrix")),
            },
        )

        return updates

    async def _analyze_parties_property(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze parties and property verification (Story S2)"""
        logger.info("Starting parties and property analysis")

        try:
            from app.core.prompts import PromptContext, ContextType
            from app.services import get_llm_service
            from app.prompts.schema.step2.parties_property_schema import (
                PartiesPropertyAnalysisResult,
            )

            # Prepare prompt context
            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "contract_text": state.get("contract_text", ""),
                    "australian_state": state.get("australian_state", "NSW"),
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "entities_extraction_result": state.get(
                        "entities_extraction_result", {}
                    ),
                    "legal_requirements_matrix": state.get(
                        "legal_requirements_matrix", {}
                    ),
                },
            )

            # Get parser for structured output
            parties_parser = await self._get_parser(
                "parties_property_analysis", PartiesPropertyAnalysisResult
            )

            # Use prompt manager to compose prompts (will be enhanced in Story S13)
            # For now, use a basic composition
            composition_result = await self.prompt_manager.render_composed(
                composition_name="step2_parties_property",
                context=context,
                output_parser=parties_parser,
            )

            system_prompt = composition_result.get(
                "system_prompt",
                "You are an expert Australian real estate contract analyst.",
            )
            user_prompt = composition_result.get(
                "user_prompt",
                f"Analyze parties and property in this contract: {context.variables.get('contract_text', '')}",
            )
            model_name = composition_result.get("metadata", {}).get("model", "gpt-4")

            # Execute LLM analysis
            llm_service = await get_llm_service()

            if parties_parser:
                parsing_result = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                    output_parser=parties_parser,
                    parse_generation_max_attempts=2,
                )

                if parsing_result.success and parsing_result.parsed_data:
                    result = parsing_result.parsed_data
                    if hasattr(result, "model_dump"):
                        result_dict = result.model_dump()
                    else:
                        result_dict = result

                    # Add metadata
                    result_dict["analyzer"] = "parties_property"
                    result_dict["status"] = "completed"
                    result_dict["timestamp"] = datetime.now(UTC).isoformat()

                    updates = {"parties_property_result": result_dict}

                    logger.info(
                        "Parties and property analysis completed successfully",
                        extra={
                            "confidence_score": result_dict.get("confidence_score", 0),
                            "risk_level": result_dict.get(
                                "overall_risk_level", "unknown"
                            ),
                            "parties_count": len(result_dict.get("parties", [])),
                        },
                    )

                    # Notify progress completion
                    await self._notify_status(
                        state,
                        "analyze_parties_property",
                        self.PROGRESS_RANGES["analyze_parties_property"][1],
                        "Parties and property analysis completed",
                    )
                else:
                    # Fallback result on parsing failure
                    result = {
                        "analyzer": "parties_property",
                        "status": "parsing_failed",
                        "error": "Failed to parse LLM output",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    updates = {
                        "parties_property_result": result,
                        "processing_errors": [
                            "Parties property analysis: parsing failed"
                        ],
                    }
            else:
                # Fallback without structured parsing
                response = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                )

                result = {
                    "analyzer": "parties_property",
                    "status": "unstructured",
                    "response": response,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                updates = {"parties_property_result": result}

        except Exception as e:
            error_msg = f"Parties and property analysis failed: {str(e)}"
            state["processing_errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

            # Store error result
            result = {
                "analyzer": "parties_property",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            updates = {"parties_property_result": result}

        return updates

    async def _analyze_financial_terms(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze financial terms (Story S3)"""
        logger.info("Starting financial terms analysis")

        try:
            from app.core.prompts import PromptContext, ContextType
            from app.services import get_llm_service
            from app.prompts.schema.step2.financial_terms_schema import (
                FinancialTermsAnalysisResult,
            )

            # Prepare prompt context
            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "contract_text": state.get("contract_text", ""),
                    "australian_state": state.get("australian_state", "NSW"),
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "entities_extraction_result": state.get(
                        "entities_extraction_result", {}
                    ),
                    "legal_requirements_matrix": state.get(
                        "legal_requirements_matrix", {}
                    ),
                },
            )

            # Get parser for structured output
            financial_parser = await self._get_parser(
                "financial_terms_analysis", FinancialTermsAnalysisResult
            )

            # Use prompt manager to compose prompts
            composition_result = await self.prompt_manager.render_composed(
                composition_name="step2_financial_terms",
                context=context,
                output_parser=financial_parser,
            )

            system_prompt = composition_result.get(
                "system_prompt",
                "You are an expert Australian real estate financial analyst.",
            )
            user_prompt = composition_result.get(
                "user_prompt",
                f"Analyze financial terms in this contract: {context.variables.get('contract_text', '')}",
            )
            model_name = composition_result.get("metadata", {}).get("model", "gpt-4")

            # Execute LLM analysis
            llm_service = await get_llm_service()

            if financial_parser:
                parsing_result = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                    output_parser=financial_parser,
                    parse_generation_max_attempts=2,
                )

                if parsing_result.success and parsing_result.parsed_data:
                    result = parsing_result.parsed_data
                    if hasattr(result, "model_dump"):
                        result_dict = result.model_dump()
                    else:
                        result_dict = result

                    # Add metadata
                    result_dict["analyzer"] = "financial_terms"
                    result_dict["status"] = "completed"
                    result_dict["timestamp"] = datetime.now(UTC).isoformat()

                    updates = {"financial_terms_result": result_dict}

                    logger.info(
                        "Financial terms analysis completed successfully",
                        extra={
                            "confidence_score": result_dict.get("confidence_score", 0),
                            "risk_level": result_dict.get(
                                "overall_risk_level", "unknown"
                            ),
                            "calculation_accuracy": result_dict.get(
                                "calculation_accuracy_score", 0
                            ),
                            "purchase_price": result_dict.get("purchase_price", {}).get(
                                "price_numeric"
                            ),
                        },
                    )

                    # Notify progress completion
                    await self._notify_status(
                        state,
                        "analyze_financial_terms",
                        self.PROGRESS_RANGES["analyze_financial_terms"][1],
                        "Financial terms analysis completed",
                    )
                else:
                    # Fallback result on parsing failure
                    result = {
                        "analyzer": "financial_terms",
                        "status": "parsing_failed",
                        "error": "Failed to parse LLM output",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    updates = {
                        "financial_terms_result": result,
                        "processing_errors": [
                            "Financial terms analysis: parsing failed"
                        ],
                    }
            else:
                # Fallback without structured parsing
                response = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                )

                result = {
                    "analyzer": "financial_terms",
                    "status": "unstructured",
                    "response": response,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                updates = {"financial_terms_result": result}

        except Exception as e:
            error_msg = f"Financial terms analysis failed: {str(e)}"
            state["processing_errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

            # Store error result
            result = {
                "analyzer": "financial_terms",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            updates = {"financial_terms_result": result}

        return updates

    async def _analyze_conditions(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze conditions and risk assessment (Story S4)"""
        logger.info("Starting conditions analysis")

        try:
            from app.core.prompts import PromptContext, ContextType
            from app.services import get_llm_service
            from app.prompts.schema.step2.conditions_schema import (
                ConditionsAnalysisResult,
            )

            # Prepare prompt context
            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "contract_text": state.get("contract_text", ""),
                    "australian_state": state.get("australian_state", "NSW"),
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "entities_extraction_result": state.get(
                        "entities_extraction_result", {}
                    ),
                    "legal_requirements_matrix": state.get(
                        "legal_requirements_matrix", {}
                    ),
                },
            )

            # Get parser for structured output
            conditions_parser = await self._get_parser(
                "conditions_analysis", ConditionsAnalysisResult
            )

            # Use prompt manager to compose prompts
            composition_result = await self.prompt_manager.render_composed(
                composition_name="step2_conditions",
                context=context,
                output_parser=conditions_parser,
            )

            system_prompt = composition_result.get(
                "system_prompt",
                "You are an expert Australian contract conditions analyst.",
            )
            user_prompt = composition_result.get(
                "user_prompt",
                f"Analyze conditions in this contract: {context.variables.get('contract_text', '')}",
            )
            model_name = composition_result.get("metadata", {}).get("model", "gpt-4")

            # Execute LLM analysis
            llm_service = await get_llm_service()

            if conditions_parser:
                parsing_result = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                    output_parser=conditions_parser,
                    parse_generation_max_attempts=2,
                )

                if parsing_result.success and parsing_result.parsed_data:
                    result = parsing_result.parsed_data
                    if hasattr(result, "model_dump"):
                        result_dict = result.model_dump()
                    else:
                        result_dict = result

                    # Add metadata
                    result_dict["analyzer"] = "conditions"
                    result_dict["status"] = "completed"
                    result_dict["timestamp"] = datetime.now(UTC).isoformat()

                    updates = {"conditions_result": result_dict}

                    logger.info(
                        "Conditions analysis completed successfully",
                        extra={
                            "confidence_score": result_dict.get("confidence_score", 0),
                            "total_conditions": result_dict.get("total_conditions", 0),
                            "special_conditions": result_dict.get(
                                "special_conditions_count", 0
                            ),
                            "overall_risk": result_dict.get(
                                "overall_condition_risk", "unknown"
                            ),
                        },
                    )

                    # Notify progress completion
                    await self._notify_status(
                        state,
                        "analyze_conditions",
                        self.PROGRESS_RANGES["analyze_conditions"][1],
                        "Conditions analysis completed",
                    )
                else:
                    # Fallback result on parsing failure
                    result = {
                        "analyzer": "conditions",
                        "status": "parsing_failed",
                        "error": "Failed to parse LLM output",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    updates = {
                        "conditions_result": result,
                        "processing_errors": ["Conditions analysis: parsing failed"],
                    }
            else:
                # Fallback without structured parsing
                response = await llm_service.generate_content(
                    prompt=user_prompt,
                    system_message=system_prompt,
                    model=model_name,
                )

                result = {
                    "analyzer": "conditions",
                    "status": "unstructured",
                    "response": response,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                updates = {"conditions_result": result}

        except Exception as e:
            error_msg = f"Conditions analysis failed: {str(e)}"
            state["processing_errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

            # Store error result
            result = {
                "analyzer": "conditions",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            updates = {"conditions_result": result}

        return updates

    async def _analyze_warranties(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze warranties and representations (Story S5)"""
        logger.info("Starting warranties analysis")

        try:
            # Placeholder implementation - will be completed in Story S5
            result = {
                "analyzer": "warranties",
                "status": "placeholder",
                "message": "Implementation pending Story S5",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Warranties analysis completed (placeholder)")

        except Exception as e:
            error_msg = f"Warranties analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {"warranties_result": result}

    async def _analyze_default_termination(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze default and termination terms (Story S6)"""
        logger.info("Starting default and termination analysis")

        try:
            # Placeholder implementation - will be completed in Story S6
            result = {
                "analyzer": "default_termination",
                "status": "placeholder",
                "message": "Implementation pending Story S6",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Default and termination analysis completed (placeholder)")

        except Exception as e:
            error_msg = f"Default and termination analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {"default_termination_result": result}

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

    async def _analyze_settlement_logistics(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze settlement logistics with dependencies (Story S7)"""
        logger.info("Starting settlement logistics analysis")

        try:
            # Check dependencies
            conditions_result = state.get("conditions_result")
            financial_result = state.get("financial_terms_result")

            if not conditions_result or not financial_result:
                error_msg = (
                    "Settlement analysis requires conditions and financial results"
                )
                logger.error(error_msg)
                return {"processing_errors": [error_msg]}

            # Placeholder implementation - will be completed in Story S7
            result = {
                "analyzer": "settlement_logistics",
                "status": "placeholder",
                "message": "Implementation pending Story S7",
                "dependencies_satisfied": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Settlement logistics analysis completed (placeholder)")

        except Exception as e:
            error_msg = f"Settlement logistics analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {"settlement_logistics_result": result}

    async def _analyze_title_encumbrances(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Analyze title and encumbrances with comprehensive diagrams (Story S8)"""
        logger.info("Starting title and encumbrances analysis")

        try:
            # Check dependencies
            parties_result = state.get("parties_property_result")
            if not parties_result:
                error_msg = "Title analysis requires parties and property result"
                logger.error(error_msg)
                return {"processing_errors": [error_msg]}

            # Count available diagrams
            diagrams = state.get("uploaded_diagrams") or {}
            total_diagrams_processed = len(diagrams)

            # Placeholder implementation - will be completed in Story S8
            result = {
                "analyzer": "title_encumbrances",
                "status": "placeholder",
                "message": "Implementation pending Story S8",
                "dependencies_satisfied": True,
                "diagrams_processed": total_diagrams_processed,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Assume 90% success rate for placeholder
            diagram_processing_success_rate = 0.9 if diagrams else 1.0
            logger.info("Title and encumbrances analysis completed (placeholder)")

        except Exception as e:
            error_msg = f"Title and encumbrances analysis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {
            "title_encumbrances_result": result,
            "total_diagrams_processed": total_diagrams_processed,
            "diagram_processing_success_rate": diagram_processing_success_rate,
        }

    async def _check_phase2_completion(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Check Phase 2 completion"""
        logger.info("Checking Phase 2 completion")

        # Check if all Phase 2 analyzers completed
        required_results = ["settlement_logistics_result", "title_encumbrances_result"]

        completed_count = sum(
            1 for key in required_results if state.get(key) is not None
        )
        total_count = len(required_results)

        if completed_count == total_count:
            logger.info(
                f"Phase 2 completed successfully: {completed_count}/{total_count} analyzers"
            )
            return {
                "phase2_complete": True,
                "phase_completion_times": {"phase2": datetime.now(UTC)},
            }
        else:
            logger.warning(
                f"Phase 2 incomplete: {completed_count}/{total_count} analyzers completed"
            )
        return {}

    async def _calculate_adjustments_outgoings(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Calculate adjustments and outgoings (Story S9)"""
        logger.info("Starting adjustments and outgoings calculation")

        try:
            # Check dependencies
            financial_result = state.get("financial_terms_result")
            settlement_result = state.get("settlement_logistics_result")

            if not financial_result or not settlement_result:
                error_msg = (
                    "Adjustments calculation requires financial and settlement results"
                )
                logger.error(error_msg)
                return {"processing_errors": [error_msg]}

            # Placeholder implementation - will be completed in Story S9
            result = {
                "analyzer": "adjustments_outgoings",
                "status": "placeholder",
                "message": "Implementation pending Story S9",
                "dependencies_satisfied": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Adjustments and outgoings calculation completed (placeholder)")

        except Exception as e:
            error_msg = f"Adjustments and outgoings calculation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {"adjustments_outgoings_result": result}

    async def _check_disclosure_compliance(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Check disclosure compliance (Story S10)"""
        logger.info("Starting disclosure compliance check")

        try:
            # Placeholder implementation - will be completed in Story S10
            result = {
                "analyzer": "disclosure_compliance",
                "status": "placeholder",
                "message": "Implementation pending Story S10",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Disclosure compliance check completed (placeholder)")

        except Exception as e:
            error_msg = f"Disclosure compliance check failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {"disclosure_compliance_result": result}

    async def _identify_special_risks(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Identify special risks (Story S11)"""
        logger.info("Starting special risks identification")

        try:
            # Placeholder implementation - will be completed in Story S11
            result = {
                "analyzer": "special_risks",
                "status": "placeholder",
                "message": "Implementation pending Story S11",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Special risks identification completed (placeholder)")

        except Exception as e:
            error_msg = f"Special risks identification failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {"special_risks_result": result}

    async def _validate_cross_sections(
        self, state: Step2AnalysisState
    ) -> Step2AnalysisState:
        """Validate cross-section consistency (Story S12)"""
        logger.info("Starting cross-section validation")

        try:
            phase3_time = datetime.now(UTC)

            # Placeholder implementation - will be completed in Story S12
            result = {
                "validator": "cross_section_validation",
                "status": "placeholder",
                "message": "Implementation pending Story S12",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Cross-section validation completed (placeholder)")

        except Exception as e:
            error_msg = f"Cross-section validation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"processing_errors": [error_msg]}

        return {
            "phase3_complete": True,
            "phase_completion_times": {"phase3": phase3_time},
            "cross_section_validation_result": result,
        }

    async def _finalize_results(self, state: Step2AnalysisState) -> Step2AnalysisState:
        """Finalize Step 2 results and prepare for Step 3"""
        logger.info("Finalizing Step 2 results")

        total_duration = (
            (datetime.now(UTC) - state["start_time"]).total_seconds()
            if state.get("start_time")
            else 0
        )

        # Log completion summary
        logger.info(
            "Step 2 workflow completed",
            extra={
                "total_duration_seconds": total_duration,
                "phase1_complete": state.get("phase1_complete", False),
                "phase2_complete": state.get("phase2_complete", False),
                "phase3_complete": state.get("phase3_complete", False),
                "processing_errors": len(state.get("processing_errors", [])),
                "skipped_analyzers": len(state.get("skipped_analyzers", [])),
                "total_risk_flags": len(state.get("total_risk_flags", [])),
                "diagrams_processed": state.get("total_diagrams_processed", 0),
            },
        )

        # Final node returns no updates
        return {}


# Factory function for workflow creation
def create_step2_workflow() -> Step2AnalysisWorkflow:
    """Create and return a new Step 2 analysis workflow instance"""
    return Step2AnalysisWorkflow()
