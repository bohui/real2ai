"""
Refactored LangGraph Contract Analysis Workflow with Node-based Architecture

This refactored version separates concerns by extracting individual processing steps
into dedicated node classes, keeping the main workflow class focused on orchestration.
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph
import logging
import json
from datetime import datetime, UTC

# Core imports
from app.models.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus
from app.core.async_utils import AsyncContextManager, ensure_async_pool_initialization
from app.prompts.schema.workflow_outputs import (
    RiskAnalysisOutput,
    RecommendationsOutput,
    ContractTermsOutput,
    ContractTermsValidationOutput,
    ComplianceAnalysisOutput,
    DocumentQualityMetrics,
    WorkflowValidationOutput,
)
from app.prompts.schema.entity_extraction_schema import ContractEntityExtraction

# Client imports
from app.clients import get_openai_client, get_gemini_client
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientAuthenticationError,
)

# Prompt management imports
from app.core.prompts import (
    PromptManager,
    get_prompt_manager,
)
from app.core.prompts.parsers import create_parser

# Configuration imports
from app.core.config import get_settings

# LangSmith tracing imports
from app.core.langsmith_config import (
    langsmith_trace,
    langsmith_session,
    get_langsmith_config,
)

# Node imports
from app.agents.nodes import (
    # Document Processing
    DocumentProcessingNode,
    DocumentQualityValidationNode,
    # Contract Analysis
    SectionAnalysisNode,
    TermsValidationNode,
    # Compliance Analysis
    ComplianceAnalysisNode,
    DiagramAnalysisNode,
    # Risk Assessment
    RiskAssessmentNode,
    RecommendationsGenerationNode,
    EntitiesExtractionNode,
    # Validation
    FinalValidationNode,
    # Utilities
    InputValidationNode,
    ReportCompilationNode,
    ErrorHandlingNode,
    RetryProcessingNode,
)

logger = logging.getLogger(__name__)


class ContractAnalysisWorkflow:
    """
    Refactored LangGraph workflow with node-based architecture.

    This version separates processing logic into specialized node classes,
    keeping the main workflow class focused on:
    - Configuration management
    - Client initialization
    - Workflow orchestration
    - State management
    - Performance metrics

    Node Architecture Benefits:
    - Better code organization and maintainability
    - Easier testing of individual components
    - Clear separation of concerns
    - Reusable node components
    - Simplified debugging and monitoring

    Configuration remains the same as the original workflow for backwards compatibility.
    """

    def __init__(
        self,
        openai_api_key: str = None,
        model_name: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        prompt_manager: Optional[PromptManager] = None,
        enable_validation: bool = True,
        enable_quality_checks: bool = True,
        extraction_config: Optional[Dict[str, Any]] = None,
        use_llm_config: Optional[Dict[str, bool]] = None,
        enable_fallbacks: bool = True,
    ):
        """Initialize the workflow with configuration and create node instances."""

        # Initialize clients (will be set up in initialize method)
        self.openai_client = None
        self.gemini_client = None

        # Model configuration
        if model_name is None:
            try:
                from app.clients.openai.config import OpenAISettings

                self.model_name = OpenAISettings().openai_model_name
            except Exception:
                from app.clients.openai.config import DEFAULT_MODEL

                self.model_name = DEFAULT_MODEL
        else:
            self.model_name = model_name

        self.openai_api_base = openai_api_base

        # Initialize prompt manager
        if prompt_manager is None:
            self.prompt_manager = get_prompt_manager()
        else:
            self.prompt_manager = prompt_manager

        # Configuration
        self.enable_validation = enable_validation
        self.enable_quality_checks = enable_quality_checks
        self.enable_fallbacks = enable_fallbacks

        # Extraction configuration
        self.extraction_config = extraction_config or {
            "method": "llm_structured",
            "fallback_to_rule_based": True,
            "use_fragments": True,
            "confidence_threshold": 0.3,
            "max_retries": 2,
        }

        # LLM usage configuration
        self.use_llm_config = use_llm_config or {
            "document_processing": True,
            "contract_analysis": True,
            "compliance_analysis": True,
            "risk_assessment": True,
            "recommendations": True,
            "document_quality": True,
            "terms_validation": True,
            "final_validation": True,
        }

        # Initialize output parsers (kept for compatibility and shared access)
        self.risk_parser = create_parser(RiskAnalysisOutput, strict_mode=False)
        self.recommendations_parser = create_parser(
            RecommendationsOutput, strict_mode=False
        )

        # Remove state-aware parsers. Use single parsers or choose model upstream.
        self.state_aware_parsers = {}

        # Keep legacy structured_parsers for backward compatibility
        self.structured_parsers = {
            "risk_analysis": create_parser(
                RiskAnalysisOutput, strict_mode=False, retry_on_failure=True
            ),
            "recommendations": create_parser(
                RecommendationsOutput, strict_mode=False, retry_on_failure=True
            ),
            "contract_terms": create_parser(
                ContractTermsOutput, strict_mode=False, retry_on_failure=True
            ),
            "compliance_analysis": create_parser(
                ComplianceAnalysisOutput, strict_mode=False, retry_on_failure=True
            ),
            "terms_validation": create_parser(
                ContractTermsValidationOutput, strict_mode=False, retry_on_failure=True
            ),
            "document_quality": create_parser(
                DocumentQualityMetrics, strict_mode=False, retry_on_failure=True
            ),
            "workflow_validation": create_parser(
                WorkflowValidationOutput, strict_mode=False, retry_on_failure=True
            ),
            "entities_extraction": create_parser(
                ContractEntityExtraction, strict_mode=False, retry_on_failure=True
            ),
        }

        # Performance metrics
        self._metrics = {
            "total_analyses": 0,
            "successful_parses": 0,
            "fallback_uses": 0,
            "validation_failures": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
        }

        # Environment-aware logging
        self._settings = get_settings()
        self._is_production = self._settings.environment.lower() in (
            "production",
            "prod",
            "live",
        )
        self._verbose_logging = bool(
            self._settings.enhanced_workflow_detailed_logging
            and not self._is_production
        )

        # Persistent event loop for node execution in worker context to avoid
        # cross-loop issues with async resources (e.g., asyncpg pools, clients)
        self._event_loop = None
        self._event_loop_thread = None

        # Initialize node instances
        self._initialize_nodes()

        # Create workflow
        self.workflow = self._create_workflow()

        logger.info(
            f"Refactored ContractAnalysisWorkflow initialized with {len(self.nodes)} nodes, "
            f"extraction config: {self.extraction_config}, "
            f"use_llm config: {self.use_llm_config}, "
            f"fallbacks enabled: {self.enable_fallbacks}"
        )

    def _initialize_nodes(self):
        """Initialize all workflow nodes."""
        # Document Processing Nodes
        self.document_processing_node = DocumentProcessingNode(self)
        self.document_quality_validation_node = DocumentQualityValidationNode(self)

        # Contract Analysis Nodes
        self.entities_extraction_node = EntitiesExtractionNode(self)
        self.section_analysis_node = SectionAnalysisNode(self)
        self.terms_validation_node = TermsValidationNode(self)

        # Compliance Analysis Nodes
        self.compliance_analysis_node = ComplianceAnalysisNode(self)
        self.diagram_analysis_node = DiagramAnalysisNode(self)

        # Risk Assessment Nodes
        self.risk_assessment_node = RiskAssessmentNode(self)
        self.recommendations_generation_node = RecommendationsGenerationNode(self)

        # Validation Nodes
        self.final_validation_node = FinalValidationNode(self)

        # Utility Nodes
        self.input_validation_node = InputValidationNode(self)
        self.report_compilation_node = ReportCompilationNode(self)
        self.error_handling_node = ErrorHandlingNode(self)
        self.retry_processing_node = RetryProcessingNode(self)

        # Store nodes for easy access and metrics
        self.nodes = {
            "input_validation": self.input_validation_node,
            "document_processing": self.document_processing_node,
            "document_quality_validation": self.document_quality_validation_node,
            "entities_extraction": self.entities_extraction_node,
            "section_analysis": self.section_analysis_node,
            "terms_validation": self.terms_validation_node,
            "compliance_analysis": self.compliance_analysis_node,
            "diagram_analysis": self.diagram_analysis_node,
            "risk_assessment": self.risk_assessment_node,
            "recommendations_generation": self.recommendations_generation_node,
            "final_validation": self.final_validation_node,
            "report_compilation": self.report_compilation_node,
            "error_handling": self.error_handling_node,
            "retry_processing": self.retry_processing_node,
        }

    async def initialize(self):
        """Initialize clients and set up workflow for execution."""
        try:
            # Initialize OpenAI client with fallback
            try:
                self.openai_client = await get_openai_client()
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None

            # Initialize Gemini client with fallback
            try:
                self.gemini_client = await get_gemini_client()
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.gemini_client = None

            # Verify at least one client is available
            if not self.openai_client and not self.gemini_client:
                error_msg = (
                    "No AI clients could be initialized. Both OpenAI and Gemini failed. "
                    "Please check your API keys and configuration."
                )
                logger.error(error_msg)
                raise Exception(error_msg)

            # Set clients in all nodes that need them
            for node_name, node in self.nodes.items():
                if hasattr(node, "openai_client"):
                    node.openai_client = self.openai_client
                    logger.debug(f"Node {node_name}: OpenAI client set")
                if hasattr(node, "gemini_client"):
                    node.gemini_client = self.gemini_client
                    logger.debug(f"Node {node_name}: Gemini client set")

                # Log client availability for each node
                logger.debug(
                    f"Node {node_name}: OpenAI={self.openai_client is not None}, Gemini={self.gemini_client is not None}"
                )

                # Verify that at least one client is available for each node
                if not node.openai_client and not node.gemini_client:
                    logger.warning(f"Node {node_name} has no AI clients available")

            logger.info(
                f"Workflow clients initialized successfully - OpenAI: {self.openai_client is not None}, Gemini: {self.gemini_client is not None}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize workflow clients: {e}")
            raise

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with node-based architecture."""
        workflow = StateGraph(RealEstateAgentState)

        # Add all node execution methods to the workflow
        workflow.add_node("validate_input", self.validate_input)
        workflow.add_node("process_document", self.process_document)
        workflow.add_node("extract_entities", self.extract_entities)
        workflow.add_node("extract_terms", self.extract_section_analysis)
        workflow.add_node("analyze_compliance", self.analyze_australian_compliance)
        workflow.add_node("analyze_contract_diagrams", self.analyze_contract_diagrams)
        workflow.add_node("assess_risks", self.assess_contract_risks)
        workflow.add_node("generate_recommendations", self.generate_recommendations)
        workflow.add_node("compile_report", self.compile_analysis_report)

        # Add validation nodes if enabled
        if self.enable_validation:
            workflow.add_node(
                "validate_document_quality", self.validate_document_quality_step
            )
            workflow.add_node(
                "validate_terms_completeness", self.validate_terms_completeness_step
            )
            workflow.add_node("validate_final_output", self.validate_final_output_step)

        # Add utility nodes
        workflow.add_node("handle_error", self.handle_processing_error)
        workflow.add_node("retry_processing", self.retry_failed_step)

        # Set entry point
        workflow.set_entry_point("validate_input")

        # Minimal static edge to kick off processing; rely on conditional edges for flow
        workflow.add_edge("validate_input", "process_document")

        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "process_document",
            self.check_processing_success,
            {
                "success": "extract_entities",
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        # After entities extraction, go to terms extraction
        workflow.add_conditional_edges(
            "extract_entities",
            self.check_entities_extraction_success,
            {
                "success": "extract_terms",
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        # After terms extraction, check quality and proceed
        workflow.add_conditional_edges(
            "extract_terms",
            self.check_extraction_quality,
            {
                "high_confidence": (
                    "validate_terms_completeness"
                    if self.enable_validation
                    else "analyze_compliance"
                ),
                "low_confidence": "retry_processing",
                "error": "handle_error",
            },
        )

        # Add conditional edges to check for error states after critical nodes
        if self.enable_validation:
            workflow.add_conditional_edges(
                "validate_terms_completeness",
                self.check_terms_validation_success,
                {
                    "success": "analyze_compliance",
                    "retry": "retry_processing",
                    "error": "handle_error",
                },
            )

        workflow.add_conditional_edges(
            "analyze_compliance",
            self.check_compliance_analysis_success,
            {
                "success": "analyze_contract_diagrams",
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        workflow.add_conditional_edges(
            "analyze_contract_diagrams",
            self.check_diagram_analysis_success,
            {
                "success": "assess_risks",
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        workflow.add_conditional_edges(
            "assess_risks",
            self.check_risk_assessment_success,
            {
                "success": "generate_recommendations",
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        workflow.add_conditional_edges(
            "generate_recommendations",
            self.check_recommendations_success,
            {
                "success": (
                    "validate_final_output"
                    if self.enable_validation
                    else "compile_report"
                ),
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        if self.enable_validation:
            workflow.add_conditional_edges(
                "validate_final_output",
                self.check_final_validation_success,
                {
                    "success": "compile_report",
                    "retry": "retry_processing",
                    "error": "handle_error",
                },
            )

        # Terminal conditions
        workflow.add_edge("compile_report", "__end__")
        workflow.add_edge("handle_error", "__end__")

        # CRITICAL FIX: Add edges from retry_processing back to workflow steps
        # This allows the retry processing node to route back to the appropriate step
        # after successful retry or restart
        workflow.add_conditional_edges(
            "retry_processing",
            self._route_after_retry,
            {
                "restart_workflow": "validate_input",
                "retry_document_processing": "process_document",
                "retry_entities_extraction": "extract_entities",
                "retry_extraction": "extract_terms",
                "retry_compliance": "analyze_compliance",
                "retry_diagrams": "analyze_contract_diagrams",
                "retry_risks": "assess_risks",
                "retry_recommendations": "generate_recommendations",
                "retry_validation": (
                    "validate_final_output"
                    if self.enable_validation
                    else "compile_report"
                ),
                "continue_workflow": "extract_entities",  # Default fallback
            },
        )

        return workflow.compile()

    # Node execution wrapper methods
    def _run_async_node(self, node_coroutine):
        """Run async node in a persistent event loop to prevent cross-loop issues."""
        import asyncio
        import threading
        import contextvars

        # Diagnostic: capture loop/thread/auth context before execution
        try:
            from app.core.auth_context import AuthContext

            auth_ctx = AuthContext.create_task_context()
            logger.debug(
                "[Workflow] _run_async_node pre-exec",
                extra={
                    "thread_name": threading.current_thread().name,
                    "has_running_loop": True,
                    "user_id": AuthContext.get_user_id(),
                    "has_token": bool(AuthContext.get_user_token()),
                },
            )
        except Exception:
            auth_ctx = None  # type: ignore[assignment]

        try:
            # If already inside an async loop (e.g., being called from an async context),
            # dispatch the coroutine to a persistent background event loop running in a
            # dedicated thread to avoid creating a new loop per call (which breaks DB pools).
            running_loop = asyncio.get_running_loop()
            if running_loop is None:
                raise RuntimeError("No running event loop found")

            # Lazily start a dedicated background loop thread
            if (
                self._event_loop is None
                or self._event_loop.is_closed()
                or self._event_loop_thread is None
            ):
                import threading as _threading

                def _loop_worker():
                    self._event_loop = asyncio.new_event_loop()
                    try:
                        self._event_loop.run_forever()
                    finally:
                        try:
                            self._event_loop.close()
                        except Exception:
                            pass

                self._event_loop_thread = _threading.Thread(
                    target=_loop_worker, name="workflow-loop", daemon=True
                )
                self._event_loop_thread.start()

                # Wait briefly for loop to start
                import time as _time

                for _ in range(50):
                    if self._event_loop is not None and self._event_loop.is_running():
                        break
                    _time.sleep(0.01)

            # Submit coroutine to the persistent background loop
            import concurrent.futures as _cf

            # Capture contextvars to propagate tracing/auth context
            current_context = contextvars.copy_context()

            async def _wrapper():
                try:
                    from app.core.auth_context import AuthContext as _AC

                    if auth_ctx:
                        _AC.restore_task_context(auth_ctx)
                except Exception:
                    pass
                return await node_coroutine

            future = _cf.Future()

            def _submit_to_loop():
                try:
                    task = self._event_loop.create_task(_wrapper())
                    task.add_done_callback(
                        lambda t: (
                            future.set_result(t.result())
                            if not t.exception()
                            else future.set_exception(t.exception())
                        )
                    )
                except Exception as submit_error:
                    future.set_exception(submit_error)

            # Use call_soon_threadsafe to schedule the coroutine
            self._event_loop.call_soon_threadsafe(
                lambda: current_context.run(_submit_to_loop)
            )
            return future.result()
        except (RuntimeError, AttributeError, ImportError) as loop_error:
            # No running loop, asyncio not available, or loop detection failed
            logger.debug(
                f"[Workflow] No running loop detected ({type(loop_error).__name__}: {loop_error}), creating persistent loop"
            )
            # Ensure a persistent background loop is running, then schedule onto it
            import threading as _threading
            import time as _time
            import concurrent.futures as _cf
            import contextvars as _ctxvars

            # Start background loop thread if needed
            if (
                self._event_loop is None
                or self._event_loop.is_closed()
                or self._event_loop_thread is None
                or not getattr(self._event_loop, "is_running", lambda: False)()
            ):

                def _loop_worker():
                    import asyncio as _asyncio

                    self._event_loop = _asyncio.new_event_loop()
                    try:
                        self._event_loop.run_forever()
                    finally:
                        try:
                            self._event_loop.close()
                        except Exception:
                            pass

                self._event_loop_thread = _threading.Thread(
                    target=_loop_worker, name="workflow-loop", daemon=True
                )
                self._event_loop_thread.start()

                # Wait briefly for loop to start
                for _ in range(50):
                    if self._event_loop is not None and self._event_loop.is_running():
                        break
                    _time.sleep(0.01)

            # Schedule coroutine onto the background loop and wait synchronously
            current_context = _ctxvars.copy_context()

            async def _wrapper_bg():
                try:
                    from app.core.auth_context import AuthContext as _AC

                    if auth_ctx:
                        _AC.restore_task_context(auth_ctx)
                except Exception:
                    pass
                return await node_coroutine

            future = _cf.Future()

            def _submit_to_running_loop():
                try:
                    task = self._event_loop.create_task(_wrapper_bg())
                    task.add_done_callback(
                        lambda t: (
                            future.set_result(t.result())
                            if not t.exception()
                            else future.set_exception(t.exception())
                        )
                    )
                except Exception as submit_error:
                    future.set_exception(submit_error)

            self._event_loop.call_soon_threadsafe(
                lambda: current_context.run(_submit_to_running_loop)
            )

            result = future.result()

            # Do not close persistent loop; reuse across nodes
            try:
                from app.core.auth_context import AuthContext

                logger.debug(
                    "[Workflow] _run_async_node post-exec (background loop)",
                    extra={
                        "thread_name": _threading.current_thread().name,
                        "execution_path": "background_loop",
                        "had_running_loop": False,
                        "user_id": AuthContext.get_user_id(),
                        "has_token": bool(AuthContext.get_user_token()),
                    },
                )
            except Exception:
                pass

            return result

    @langsmith_trace(name="validate_input", run_type="tool")
    def validate_input(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Execute input validation node."""
        return self._run_async_node(self.input_validation_node.execute(state))

    async def extract_entities(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Extract entities from the contract using the entities extraction node."""
        try:
            return await self.entities_extraction_node.execute(state)
        except Exception as e:
            logger.error(f"Entities extraction failed: {e}")
            return self.error_handling_node._handle_node_error(
                state, e, "Entities extraction failed"
            )

    def process_document(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Execute document processing node."""
        return self._run_async_node(self.document_processing_node.execute(state))

    @langsmith_trace(name="validate_document_quality", run_type="tool")
    def validate_document_quality_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute document quality validation node."""
        return self._run_async_node(
            self.document_quality_validation_node.execute(state)
        )

    def extract_section_analysis(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute Step 2 section-by-section analysis node."""
        return self._run_async_node(self.section_analysis_node.execute(state))

    def validate_terms_completeness_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute terms validation node."""
        return self._run_async_node(self.terms_validation_node.execute(state))

    def analyze_australian_compliance(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute compliance analysis node."""
        return self._run_async_node(self.compliance_analysis_node.execute(state))

    def analyze_contract_diagrams(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute diagram analysis node."""
        return self._run_async_node(self.diagram_analysis_node.execute(state))

    def assess_contract_risks(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute risk assessment node."""
        return self._run_async_node(self.risk_assessment_node.execute(state))

    def generate_recommendations(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute recommendations generation node."""
        return self._run_async_node(self.recommendations_generation_node.execute(state))

    def validate_final_output_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute final validation node."""
        return self._run_async_node(self.final_validation_node.execute(state))

    def compile_analysis_report(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute report compilation node."""
        return self._run_async_node(self.report_compilation_node.execute(state))

    def handle_processing_error(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute error handling node."""
        return self._run_async_node(self.error_handling_node.execute(state))

    def retry_failed_step(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Execute retry processing node."""
        return self._run_async_node(self.retry_processing_node.execute(state))

    # Conditional edge check methods (kept simple for orchestration)
    def _has_error_state(self, state: RealEstateAgentState) -> bool:
        """Check if the workflow state has any error indicators."""
        return (
            state.get("error") is not None
            or state.get("error_state") is not None
            or any(key.endswith("_error") for key in state.keys())
            or state.get("parsing_status") == ProcessingStatus.FAILED
        )

    def check_processing_success(self, state: RealEstateAgentState) -> str:
        """Check if document processing was successful."""
        # Check for error state first - this prevents workflow from continuing
        if self._has_error_state(state):
            return "error"

        if state.get("parsing_status") == ProcessingStatus.COMPLETED:
            return "success"
        elif state.get("retry_attempts", 0) < 3:
            return "retry"
        else:
            return "error"

    def check_document_quality(self, state: RealEstateAgentState) -> str:
        """Check document quality validation results."""
        # Check for error state first - this prevents workflow from continuing
        if self._has_error_state(state):
            return "error"

        quality_metrics = state.get("document_quality_metrics", {})
        overall_confidence = quality_metrics.get("overall_confidence", 0)

        if overall_confidence >= 0.6:
            return "quality_passed"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_entities_extraction_success(self, state: RealEstateAgentState) -> str:
        """Check if entities extraction was successful."""
        try:
            # Check if entities extraction completed successfully
            if state.get("entities_extraction"):
                return "success"
            elif state.get("entities_extraction_skipped"):
                # If skipped, still continue to next step
                return "success"
            else:
                return "retry"
        except Exception as e:
            logger.error(f"Error checking entities extraction success: {e}")
            return "error"

    def check_extraction_quality(self, state: RealEstateAgentState) -> str:
        """Check contract terms extraction quality."""
        # Check for error state first - this prevents workflow from continuing
        if self._has_error_state(state):
            return "error"

        # Check if contract terms were actually extracted
        contract_terms = state.get("contract_terms", {})
        if not contract_terms:
            return "error"

        confidence_scores = state.get("confidence_scores", {})
        extraction_confidence = confidence_scores.get("contract_extraction", 0)

        threshold = self.extraction_config.get("confidence_threshold", 0.3)

        if extraction_confidence >= threshold:
            return "high_confidence"
        elif state.get("retry_attempts", 0) < self.extraction_config.get(
            "max_retries", 2
        ):
            return "low_confidence"
        else:
            return "error"

    def check_terms_validation_success(self, state: RealEstateAgentState) -> str:
        """Check if terms validation was successful."""
        # Check for error state first
        if self._has_error_state(state):
            return "error"

        validation_result = state.get("terms_validation_result", {})
        validation_passed = validation_result.get("validation_passed", False)

        if validation_passed:
            return "success"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_compliance_analysis_success(self, state: RealEstateAgentState) -> str:
        """Check if compliance analysis was successful."""
        # Check for error state first
        if self._has_error_state(state):
            return "error"

        compliance_result = state.get("compliance_analysis_result", {})
        if compliance_result and not state.get("error"):
            return "success"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_diagram_analysis_success(self, state: RealEstateAgentState) -> str:
        """Check if diagram analysis was successful."""
        # Check for error state first
        if self._has_error_state(state):
            return "error"

        diagram_result = state.get("diagram_analysis_result", {})
        if diagram_result and not state.get("error"):
            return "success"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_risk_assessment_success(self, state: RealEstateAgentState) -> str:
        """Check if risk assessment was successful."""
        # Check for error state first
        if self._has_error_state(state):
            return "error"

        risk_result = state.get("risk_analysis_result", {})
        if risk_result and not state.get("error"):
            return "success"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_recommendations_success(self, state: RealEstateAgentState) -> str:
        """Check if recommendations generation was successful."""
        # Check for error state first
        if self._has_error_state(state):
            return "error"

        recommendations_result = state.get("recommendations_result", {})
        if recommendations_result and not state.get("error"):
            return "success"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_final_validation_success(self, state: RealEstateAgentState) -> str:
        """Check if final validation was successful."""
        # Check for error state first
        if self._has_error_state(state):
            return "error"

        validation_result = state.get("final_validation_result", {})
        validation_passed = validation_result.get("validation_passed", False)

        if validation_passed:
            return "success"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def _route_after_retry(self, state: RealEstateAgentState) -> str:
        """
        Route workflow after retry processing completes.

        This method determines where to send the workflow based on the retry result
        and the current state.
        """
        try:
            retry_result = state.get("retry_result", {})
            strategy = retry_result.get("strategy_executed", "unknown")

            # Check if retry was successful
            if not retry_result.get("success", False):
                # Retry failed - go to error handling
                return (
                    "continue_workflow"  # This will route to extract_terms as fallback
                )

            # Route based on retry strategy
            if strategy == "restart_workflow":
                # Workflow restart - go back to beginning
                return "restart_workflow"

            elif strategy == "retry_step":
                # Specific step retry - route to that step
                target_step = retry_result.get("target_step", "unknown")

                if target_step == "process_document":
                    return "retry_document_processing"
                elif target_step == "extract_terms":
                    return "retry_extraction"
                elif target_step == "analyze_compliance":
                    return "retry_compliance"
                elif target_step == "analyze_contract_diagrams":
                    return "retry_diagrams"
                elif target_step == "assess_risks":
                    return "retry_risks"
                elif target_step == "generate_recommendations":
                    return "retry_recommendations"
                elif target_step == "validate_final_output":
                    return "retry_validation"
                else:
                    # Unknown target step - use default fallback
                    return "continue_workflow"

            elif strategy == "retry_current":
                # Current step retry - route to current step
                current_step = retry_result.get("target_step", "unknown")

                if current_step == "process_document":
                    return "retry_document_processing"
                elif current_step == "extract_terms":
                    return "retry_extraction"
                elif current_step == "analyze_compliance":
                    return "retry_compliance"
                elif current_step == "analyze_contract_diagrams":
                    return "retry_diagrams"
                elif current_step == "assess_risks":
                    return "retry_risks"
                elif current_step == "generate_recommendations":
                    return "retry_recommendations"
                elif current_step == "validate_final_output":
                    return "retry_validation"
                else:
                    # Unknown current step - use default fallback
                    return "continue_workflow"

            else:
                # Generic retry - continue workflow
                return "continue_workflow"

        except Exception as e:
            logger.error(f"Error in retry routing: {e}")
            # On error, use safe fallback
            return "continue_workflow"

    @langsmith_trace(name="contract_analysis_workflow", run_type="chain")
    async def analyze_contract(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """Main analysis method - maintains backward compatibility."""
        try:
            # Update metrics
            self._metrics["total_analyses"] += 1
            start_time = datetime.now(UTC)

            # Execute workflow with proper async context to prevent event loop conflicts
            async with AsyncContextManager():
                result = await self.workflow.ainvoke(state)

            # Update performance metrics
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            self._metrics["total_processing_time"] += processing_time
            self._metrics["average_processing_time"] = (
                self._metrics["total_processing_time"] / self._metrics["total_analyses"]
            )

            if result.get("processing_status") == ProcessingStatus.COMPLETED:
                self._metrics["successful_parses"] += 1

            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            self._metrics["validation_failures"] += 1
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get workflow performance metrics including node-specific metrics."""
        workflow_metrics = self._metrics.copy()

        # Add node-specific metrics
        node_metrics = {}
        for node_name, node in self.nodes.items():
            if hasattr(node, "get_node_metrics"):
                node_metrics[node_name] = node.get_node_metrics()

        return {
            "workflow_metrics": workflow_metrics,
            "node_metrics": node_metrics,
            "total_nodes": len(self.nodes),
            "configuration": {
                "enable_validation": self.enable_validation,
                "enable_quality_checks": self.enable_quality_checks,
                "enable_fallbacks": self.enable_fallbacks,
            },
        }

    def reset_metrics(self):
        """Reset all workflow and node metrics."""
        self._metrics = {
            "total_analyses": 0,
            "successful_parses": 0,
            "fallback_uses": 0,
            "validation_failures": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
        }

        # Reset node metrics
        for node in self.nodes.values():
            if hasattr(node, "reset_node_metrics"):
                node.reset_node_metrics()

    def __repr__(self) -> str:
        """String representation of the workflow."""
        return (
            f"ContractAnalysisWorkflow("
            f"nodes={len(self.nodes)}, "
            f"validation={self.enable_validation}, "
            f"quality_checks={self.enable_quality_checks}, "
            f"fallbacks={self.enable_fallbacks})"
        )


class ProgressTrackingWorkflow(ContractAnalysisWorkflow):
    """Workflow with built-in progress tracking and resume support.

    Reads per-run context from the state, so a single instance can serve multiple runs safely.
    """

    # Fixed order of primary steps per PRD for resume logic
    _STEP_ORDER = [
        "document_uploaded",  # 5% (emitted by service before workflow starts)
        "validate_input",  # 7%
        "process_document",  # 7-30%
        "save_pages",  # 30-40%
        "save_diagrams",  # 40-43%
        "layout_format_cleanup",  # 43-48%
        "validate_document_quality",  # 52%
        "extract_terms",  # 59%
        "validate_terms_completeness",  # 60%
        "analyze_compliance",  # 68%
        "assess_risks",  # 75%
        "generate_recommendations",  # 85%
        "compile_report",  # 98%
        "analysis_complete",  # 100%
    ]

    def __init__(self, parent_service: Any, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_service = parent_service

    # ---------- Helpers ----------
    def _get_resume_index(self, state: Dict[str, Any]) -> int:
        resume_from_step: Optional[str] = (state or {}).get("resume_from_step")
        if not resume_from_step:
            return 0
        # Handle failed suffix like "extract_terms_failed"
        clean_step = (
            resume_from_step[:-7]
            if resume_from_step.endswith("_failed")
            else resume_from_step
        )
        try:
            return self._STEP_ORDER.index(clean_step)
        except ValueError:
            logger.warning(
                f"Unknown resume step: {resume_from_step}; starting from beginning"
            )
            return 0

    def _should_skip(self, step_name: str, state: Dict[str, Any]) -> bool:
        try:
            step_idx = self._STEP_ORDER.index(step_name)
        except ValueError:
            return False
        return step_idx < self._get_resume_index(state)

    async def _notify_status(
        self, state: Dict[str, Any], step: str, percent: int, desc: str
    ) -> None:
        # Best-effort async persistence callback from state
        notify = (state or {}).get("notify_progress")
        if notify:
            try:
                await notify(step, percent, desc)
            except Exception as persist_error:
                logger.debug(
                    f"[ProgressTracking] Persist callback failed: {persist_error}"
                )

    def _ws_progress(
        self, state: Dict[str, Any], step: str, percent: int, desc: str
    ) -> None:
        # Removed: WebSocket progress is centralized via task-level progress callback
        return None

    # ---------- Step Overrides with Progress ----------
    async def validate_input(self, state):
        if self._should_skip("validate_input", state):
            return state
        # Mark session as processing when first step begins
        try:
            contract_id = (state or {}).get("contract_id")
            if contract_id in self.parent_service.active_analyses:
                self.parent_service.active_analyses[contract_id][
                    "status"
                ] = "processing"
        except Exception:
            pass
        result = super().validate_input(state)
        self._ws_progress(state, "validate_input", 7, "Initialize analysis")
        await self._notify_status(state, "validate_input", 7, "Initialize analysis")
        return result

    async def process_document(self, state):
        if self._should_skip("process_document", state):
            return state
        self._ws_progress(state, "document_processing", 7, "Extract text & diagrams")
        result = super().process_document(state)
        await self._notify_status(
            state, "document_processing", 30, "Extract text & diagrams"
        )
        return result

    async def validate_document_quality_step(self, state):
        if self._should_skip("validate_document_quality", state):
            return state
        self._ws_progress(
            state,
            "validate_document_quality",
            52,
            "Validating document quality and readability",
        )
        await self._notify_status(
            state,
            "validate_document_quality",
            52,
            "Validating document quality and readability",
        )
        return super().validate_document_quality_step(state)

    async def extract_section_analysis(self, state):
        if self._should_skip("extract_terms", state):
            return state
        self._ws_progress(
            state,
            "extract_terms",
            59,
            "Performing Step 2 section-by-section analysis",
        )
        await self._notify_status(
            state,
            "extract_terms",
            59,
            "Performing Step 2 section-by-section analysis",
        )
        return super().extract_section_analysis(state)

    async def analyze_australian_compliance(self, state):
        if self._should_skip("analyze_compliance", state):
            return state
        self._ws_progress(
            state,
            "analyze_compliance",
            68,
            "Analyzing compliance with Australian property laws",
        )
        await self._notify_status(
            state,
            "analyze_compliance",
            68,
            "Analyzing compliance with Australian property laws",
        )
        return super().analyze_australian_compliance(state)

    async def assess_contract_risks(self, state):
        if self._should_skip("assess_risks", state):
            return state
        self._ws_progress(
            state, "assess_risks", 75, "Assessing contract risks and potential issues"
        )
        await self._notify_status(
            state, "assess_risks", 75, "Assessing contract risks and potential issues"
        )
        return super().assess_contract_risks(state)

    async def generate_recommendations(self, state):
        if self._should_skip("generate_recommendations", state):
            return state
        self._ws_progress(
            state,
            "generate_recommendations",
            85,
            "Generating actionable recommendations",
        )
        await self._notify_status(
            state,
            "generate_recommendations",
            85,
            "Generating actionable recommendations",
        )
        return super().generate_recommendations(state)

    async def analyze_contract_diagrams(self, state):
        if self._should_skip("analyze_contract_diagrams", state):
            return state
        result = super().analyze_contract_diagrams(state)
        if not (isinstance(result, dict) and result.get("error_state")):
            self._ws_progress(
                state,
                "analyze_contract_diagrams",
                65,
                "Analyzing contract diagrams and visual elements",
            )
            await self._notify_status(
                state,
                "analyze_contract_diagrams",
                65,
                "Analyzing contract diagrams and visual elements",
            )
        return result

    async def validate_final_output_step(self, state):
        if self._should_skip("validate_final_output", state):
            return state
        result = super().validate_final_output_step(state)
        if not (isinstance(result, dict) and result.get("error_state")):
            self._ws_progress(
                state,
                "validate_final_output",
                95,
                "Performing final validation of analysis results",
            )
            await self._notify_status(
                state,
                "validate_final_output",
                95,
                "Performing final validation of analysis results",
            )
        return result

    # ---------- Conditional Edge Overrides to handle resume skip ----------
    def check_processing_success(self, state):
        if self._should_skip("process_document", state):
            return "success"
        return super().check_processing_success(state)

    def check_document_quality(self, state):
        if self._should_skip("validate_document_quality", state):
            return "quality_passed"
        return super().check_document_quality(state)

    def check_extraction_quality(self, state):
        if self._should_skip("extract_terms", state):
            try:
                contract_terms = (
                    state.get("contract_terms") if isinstance(state, dict) else None
                )
            except Exception:
                contract_terms = None
            return "high_confidence" if contract_terms else "error"
        return super().check_extraction_quality(state)

    def check_terms_validation_success(self, state):
        if self._should_skip("validate_terms_completeness", state):
            return "success"
        return super().check_terms_validation_success(state)
