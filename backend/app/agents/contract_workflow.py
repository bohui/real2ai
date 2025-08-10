"""
Enhanced LangGraph Contract Analysis Workflow with PromptManager and OutputParser integration
"""

from typing import Dict, Any, Optional, List, Union
from langgraph.graph import StateGraph
from langchain.schema import HumanMessage, SystemMessage
import json
import time
import logging
from typing import Dict, Any
from datetime import datetime, UTC
from pathlib import Path
import uuid

# Import new client architecture
from app.clients import get_openai_client, get_gemini_client
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError,
    ClientAuthenticationError,
)

from app.models.contract_state import (
    RealEstateAgentState,
    ContractTerms,
    RiskFactor,
    ComplianceCheck,
    update_state_step,
    calculate_confidence_score,
    create_step_update,
    get_current_step,
)
from app.schema.enums import ProcessingStatus
from app.models.workflow_outputs import (
    RiskAnalysisOutput,
    RecommendationsOutput,
    DocumentQualityMetrics,
    WorkflowValidationOutput,
    ContractTermsValidationOutput,
    ContractTermsOutput,
)

# Import categorized tools
from app.agents.tools.domain import (
    extract_australian_contract_terms,
    identify_contract_template_type,
)
from app.agents.tools.compliance import (
    validate_cooling_off_period,
    calculate_stamp_duty,
)
from app.agents.tools.analysis import (
    calculate_overall_confidence_score,
    analyze_special_conditions,
    comprehensive_risk_scoring_system,
)
from app.agents.tools.validation import (
    validate_document_quality,
    validate_contract_terms_completeness,
    validate_workflow_step,
)

# Import prompt management system
from app.core.prompts import (
    PromptManager,
    PromptManagerConfig,
    PromptContext,
    ContextType,
    get_prompt_manager,
)
from app.core.prompts.output_parser import create_parser, ParsingResult
from app.core.prompts.exceptions import (
    PromptNotFoundError,
    PromptValidationError,
    PromptContextError,
)

# Import LangSmith tracing
from app.core.langsmith_config import (
    langsmith_trace,
    langsmith_session,
    get_langsmith_config,
    log_trace_info,
)

# App settings for environment-aware logging
from app.core.config import get_settings

# DocumentService imported lazily to avoid circular imports

logger = logging.getLogger(__name__)


class ContractAnalysisWorkflow:
    """Enhanced LangGraph workflow with PromptManager and OutputParser integration

    Extraction Configuration Options:
    - method: "llm_structured" (default) or "rule_based"
    - fallback_to_rule_based: True (default) - fallback to rule-based if LLM fails
    - use_fragments: True (default) - use fragment-based prompts
    - confidence_threshold: 0.3 (default) - minimum confidence for extraction
    - max_retries: 2 (default) - maximum retry attempts

    Use LLM Configuration Options (all default to True):
    - document_processing: Use LLM for document processing and text extraction
    - contract_analysis: Use LLM for contract terms extraction
    - compliance_analysis: Use LLM for compliance analysis
    - risk_assessment: Use LLM for risk assessment
    - recommendations: Use LLM for recommendations generation
    - document_quality: Use LLM for document quality validation
    - terms_validation: Use LLM for terms completeness validation
    - final_validation: Use LLM for final output validation

    Example:
        # Development configuration (fail fast, no fallbacks)
        dev_workflow = ContractAnalysisWorkflow(
            extraction_config={
                "method": "llm_structured",
                "fallback_to_rule_based": True,
                "use_fragments": True,
                "confidence_threshold": 0.3,
                "max_retries": 2,
            },
            use_llm_config={
                "document_processing": True,
                "contract_analysis": True,
                "compliance_analysis": True,
                "risk_assessment": True,
                "recommendations": True,
                "document_quality": True,
                "terms_validation": True,
                "final_validation": True,
            },
            enable_fallbacks=False  # Development: fail fast on template issues
        )

        # Production configuration (with fallbacks for reliability)
        prod_workflow = ContractAnalysisWorkflow(
            use_llm_config={
                "document_processing": True,
                "contract_analysis": True,
                "compliance_analysis": True,
                "risk_assessment": True,
                "recommendations": True,
                "document_quality": True,
                "terms_validation": True,
                "final_validation": True,
            },
            enable_fallbacks=True  # Production: enable fallbacks for reliability
        )
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
        # Initialize clients (will be set up in initialize method)
        self.openai_client = None
        self.gemini_client = None
        # Resolve model name from environment/config if not explicitly provided
        if model_name is None:
            try:
                from app.clients.openai.config import OpenAISettings

                self.model_name = OpenAISettings().openai_model_name
            except Exception:
                # Final fallback to config's DEFAULT_MODEL to avoid hardcoding
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

        self.enable_validation = enable_validation
        self.enable_quality_checks = enable_quality_checks
        self.enable_fallbacks = enable_fallbacks

        # Initialize extraction configuration
        self.extraction_config = extraction_config or {
            "method": "llm_structured",  # "llm_structured" or "rule_based"
            "fallback_to_rule_based": True,
            "use_fragments": True,
            "confidence_threshold": 0.3,
            "max_retries": 2,
        }

        # Initialize use_llm configuration for each task
        self.use_llm_config = use_llm_config or {
            "document_processing": True,  # process_document
            "contract_analysis": True,  # extract_contract_terms
            "compliance_analysis": True,  # analyze_australian_compliance
            "risk_assessment": True,  # assess_contract_risks
            "recommendations": True,  # generate_recommendations
            "document_quality": True,  # validate_document_quality_step
            "terms_validation": True,  # validate_terms_completeness_step
            "final_validation": True,  # validate_final_output_step
        }

        # Initialize output parsers
        self.risk_parser = create_parser(RiskAnalysisOutput, strict_mode=False)
        self.recommendations_parser = create_parser(
            RecommendationsOutput, strict_mode=False
        )

        # Performance metrics
        self._metrics = {
            "total_analyses": 0,
            "successful_parses": 0,
            "fallback_uses": 0,
            "validation_failures": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
        }

        # Environment-aware logging controls
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
        # Note: root logger level is configured globally; this only marks our intent
        if self._verbose_logging:
            try:
                logger.setLevel(logging.DEBUG)
            except Exception:
                pass

        self.workflow = self._create_workflow()
        logger.info(
            f"Enhanced ContractAnalysisWorkflow initialized with extraction config: {self.extraction_config}, use_llm config: {self.use_llm_config}, and fallbacks enabled: {self.enable_fallbacks}"
        )

    # ---- Logging helpers (environment-aware) ----
    def _log_step_debug(
        self,
        step_name: str,
        message: str,
        state: Optional[RealEstateAgentState] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._verbose_logging:
            return
        safe_state = {}
        try:
            if state:
                safe_state = {
                    "session_id": state.get("session_id"),
                    "user_id": state.get("user_id"),
                    "progress": state.get("progress", {}).get("current_step"),
                }
        except Exception:
            safe_state = {}
        payload = {
            "step": step_name,
            "state": safe_state,
            "details": details or {},
        }
        logger.debug(
            f"[ContractWorkflow] {message} | context={json.dumps(payload, default=str)}"
        )

    def _log_exception(
        self,
        step_name: str,
        error: Exception,
        state: Optional[RealEstateAgentState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        base: Dict[str, Any] = {
            "step": step_name,
            "error_type": type(error).__name__,
            "message": str(error),
        }
        if state:
            base["session_id"] = state.get("session_id")
            # Only include user_id when verbose logging is enabled (avoid PII in prod)
            if self._verbose_logging:
                base["user_id"] = state.get("user_id")
        if context:
            base["context"] = context

        if self._verbose_logging:
            logger.exception(
                f"[ContractWorkflow] Error occurred | data={json.dumps(base, default=str)}",
            )
        else:
            minimal = {
                k: base.get(k)
                for k in ("step", "error_type", "message", "session_id")
                if k in base
            }
            logger.error(
                f"[ContractWorkflow] Error occurred | data={json.dumps(minimal, default=str)}"
            )

    async def initialize(self):
        """Initialize the workflow clients"""
        try:
            logger.info("Initializing ContractAnalysisWorkflow clients...")

            # Initialize OpenAI client
            self.openai_client = await get_openai_client()
            logger.info("OpenAI client initialized successfully")

            # Initialize Gemini client (for enhanced capabilities)
            try:
                self.gemini_client = await get_gemini_client()
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.warning(f"Gemini client initialization failed: {e}")
                self.gemini_client = None

            logger.info("ContractAnalysisWorkflow clients initialized successfully")

        except Exception as e:
            self._log_exception(
                step_name="initialize",
                error=e,
                state=None,
                context={
                    "openai_client_init": bool(self.openai_client is not None),
                    "gemini_client_init": bool(self.gemini_client is not None),
                },
            )
            raise ClientConnectionError(
                f"Failed to initialize workflow clients: {str(e)}",
                client_name="ContractAnalysisWorkflow",
                original_error=e,
            )

    def _create_workflow(self) -> StateGraph:
        """Create the enhanced LangGraph workflow"""

        workflow = StateGraph(RealEstateAgentState)

        # Core Processing Nodes (enhanced)
        workflow.add_node("validate_input", self.validate_input)
        workflow.add_node("process_document", self.process_document)
        workflow.add_node("extract_terms", self.extract_contract_terms)
        workflow.add_node("analyze_compliance", self.analyze_australian_compliance)
        workflow.add_node("analyze_contract_diagrams", self.analyze_contract_diagrams)
        workflow.add_node("assess_risks", self.assess_contract_risks)
        workflow.add_node("generate_recommendations", self.generate_recommendations)
        workflow.add_node("compile_report", self.compile_analysis_report)

        # Enhanced validation nodes
        if self.enable_validation:
            workflow.add_node(
                "validate_document_quality", self.validate_document_quality_step
            )
            workflow.add_node(
                "validate_terms_completeness", self.validate_terms_completeness_step
            )
            workflow.add_node("validate_final_output", self.validate_final_output_step)

        # Error Handling Nodes
        workflow.add_node("handle_error", self.handle_processing_error)
        workflow.add_node("retry_processing", self.retry_failed_step)

        # Entry Point
        workflow.set_entry_point("validate_input")

        # Enhanced Processing Flow with validation
        if self.enable_validation:
            workflow.add_edge("validate_input", "validate_document_quality")
            workflow.add_edge("validate_document_quality", "process_document")
            workflow.add_edge("process_document", "extract_terms")
            workflow.add_edge("extract_terms", "validate_terms_completeness")
            workflow.add_edge("validate_terms_completeness", "analyze_compliance")
            workflow.add_edge("analyze_compliance", "analyze_contract_diagrams")
            workflow.add_edge("analyze_contract_diagrams", "assess_risks")
            workflow.add_edge("assess_risks", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "validate_final_output")
            workflow.add_edge("validate_final_output", "compile_report")
        else:
            # Standard flow without validation
            workflow.add_edge("validate_input", "process_document")
            workflow.add_edge("process_document", "extract_terms")
            workflow.add_edge("extract_terms", "analyze_compliance")
            workflow.add_edge("analyze_compliance", "analyze_contract_diagrams")
            workflow.add_edge("analyze_contract_diagrams", "assess_risks")
            workflow.add_edge("assess_risks", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "compile_report")

        # Conditional Error Handling (enhanced)
        workflow.add_conditional_edges(
            "process_document",
            self.check_processing_success,
            {
                "success": "extract_terms",
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

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

        # Terminal Conditions
        workflow.add_edge("compile_report", "__end__")
        workflow.add_edge("handle_error", "__end__")

        return workflow.compile()

    @langsmith_trace(name="contract_analysis_workflow", run_type="chain")
    async def analyze_contract(
        self, initial_state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute the complete enhanced contract analysis workflow"""

        start_time = time.time()
        self._metrics["total_analyses"] += 1

        # Ensure initial state is properly initialized
        if not initial_state.get("session_id"):
            initial_state["session_id"] = str(uuid.uuid4())

        if not initial_state.get("agent_version"):
            initial_state["agent_version"] = "1.0"

        if "confidence_scores" not in initial_state:
            initial_state["confidence_scores"] = {}

        if "analysis_results" not in initial_state:
            initial_state["analysis_results"] = {}

        if "recommendations" not in initial_state:
            initial_state["recommendations"] = []

        if "final_recommendations" not in initial_state:
            initial_state["final_recommendations"] = []

        if "user_preferences" not in initial_state:
            initial_state["user_preferences"] = {}

        # Initialize progress tracking
        total_steps = 8 + (3 if self.enable_validation else 0)
        step_names = [
            "validate_input",
            "process_document",
            "extract_terms",
            "analyze_compliance",
            "analyze_contract_diagrams",
            "assess_risks",
            "generate_recommendations",
            "compile_report",
        ]

        if self.enable_validation:
            step_names.insert(1, "validate_document_quality")
            step_names.insert(4, "validate_terms_completeness")
            step_names.insert(-1, "validate_final_output")

        initial_state["progress"] = {
            "current_step": 0,
            "total_steps": total_steps,
            "step_names": step_names,
            "percentage": 0,
        }

        # Initialize clients if not already initialized
        if not self.openai_client:
            await self.initialize()

        try:
            self._log_step_debug(
                step_name="analyze_contract",
                message="Starting workflow execution",
                state=initial_state,
                details={
                    "enable_validation": self.enable_validation,
                    "enable_quality_checks": self.enable_quality_checks,
                    "use_llm_config": self.use_llm_config,
                },
            )
            # Create and compile workflow
            workflow = self._create_workflow()

            # Execute workflow
            final_state = await workflow.ainvoke(initial_state)

            # Calculate processing time
            processing_time = time.time() - start_time
            final_state["processing_time"] = processing_time

            # Update metrics
            self._metrics["total_processing_time"] += processing_time
            self._metrics["average_processing_time"] = (
                self._metrics["total_processing_time"] / self._metrics["total_analyses"]
            )

            logger.info(
                f"Contract analysis completed in {processing_time:.2f}s for session {final_state['session_id']}"
            )

            return final_state

        except Exception as e:
            self._log_exception(
                step_name="analyze_contract",
                error=e,
                state=initial_state,
            )
            # Return error state
            error_state = initial_state.copy()
            error_state["error_state"] = str(e)
            error_state["parsing_status"] = ProcessingStatus.FAILED
            error_state["processing_time"] = time.time() - start_time
            return error_state

    # Enhanced workflow steps

    @langsmith_trace(name="validate_input", run_type="tool")
    def validate_input(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Validate input state and ensure all required fields are present"""

        try:
            # Ensure required fields are present
            if not state.get("user_id"):
                raise ValueError("user_id is required")

            if not state.get("australian_state"):
                raise ValueError("australian_state is required")

            if not state.get("session_id"):
                state["session_id"] = str(uuid.uuid4())

            if not state.get("agent_version"):
                state["agent_version"] = "1.0"

            # Initialize missing fields with defaults
            if "confidence_scores" not in state:
                state["confidence_scores"] = {}

            if "progress" not in state:
                state["progress"] = {
                    "current_step": 0,
                    "total_steps": 7 + (3 if self.enable_validation else 0),
                    "percentage": 0,
                }

            if "analysis_results" not in state:
                state["analysis_results"] = {}

            if "recommendations" not in state:
                state["recommendations"] = []

            if "final_recommendations" not in state:
                state["final_recommendations"] = []

            if "user_preferences" not in state:
                state["user_preferences"] = {}

            # Validate document data if present
            document_data = state.get("document_data")
            if document_data is not None:
                if not isinstance(document_data, dict):
                    raise ValueError("document_data must be a dictionary")

            # Update progress using the new pattern
            progress_update = {}
            if "progress" in state and state["progress"]:
                current_step_num = state["progress"]["current_step"] + 1
                progress_update["progress"] = {
                    **state["progress"],
                    "current_step": current_step_num,
                    "percentage": int(
                        (current_step_num / state["progress"]["total_steps"]) * 100
                    ),
                }

            # Return proper state update
            logger.debug(f"Input validation completed for user {state['user_id']}")
            return create_step_update("input_validated", progress_update)

        except Exception as e:
            self._log_exception(
                step_name="validate_input",
                error=e,
                state=state,
            )
            return update_state_step(
                state,
                "input_validation_failed",
                error=f"Input validation failed: {str(e)}",
            )

    async def validate_document_quality_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Validate document quality using enhanced tools with configurable LLM usage"""

        if not self.enable_quality_checks:
            return state

        # Prepare progress update
        progress_update = {}
        if "progress" in state and state["progress"]:
            current_step_num = state["progress"]["current_step"] + 1
            progress_update["progress"] = {
                **state["progress"],
                "current_step": current_step_num,
                "percentage": int(
                    (current_step_num / state["progress"]["total_steps"]) * 100
                ),
            }

        try:
            # Handle case where document_data might be None
            document_data = state.get("document_data", {})
            if not document_data:
                logger.warning("No document data available for quality validation")
                # Return state with default quality metrics
                state["document_quality_metrics"] = {
                    "text_quality_score": 0.5,
                    "completeness_score": 0.5,
                    "readability_score": 0.5,
                    "key_terms_coverage": 0.5,
                    "extraction_confidence": 0.5,
                    "issues_identified": ["No document data available"],
                    "improvement_suggestions": [
                        "Verify document was properly uploaded"
                    ],
                }
                state["confidence_scores"]["document_quality"] = 0.5
                return update_state_step(
                    state,
                    "document_quality_validation_warning",
                    error="No document data available for quality validation",
                )

            document_text = document_data.get("content", "")
            document_metadata = document_data.get("metadata", {})

            # Fail-fast for empty documents - prevent UI hang
            if not document_text or len(document_text.strip()) < 50:
                logger.error("Document text is too short or empty - failing analysis")
                state["document_quality_metrics"] = {
                    "text_quality_score": 0.0,
                    "completeness_score": 0.0,
                    "readability_score": 0.0,
                    "key_terms_coverage": 0.0,
                    "extraction_confidence": 0.0,
                    "issues_identified": ["Document text is too short or empty"],
                    "improvement_suggestions": [
                        "Verify document was properly extracted",
                        "Check document format and quality",
                    ],
                }
                state["confidence_scores"]["document_quality"] = 0.0
                # Return failed status to prevent UI hang
                return update_state_step(
                    state,
                    "document_analysis_failed",
                    error="Document content is insufficient for analysis. Please upload a valid document.",
                )

            use_llm = self.use_llm_config.get("document_quality", True)

            # Check if we should use LLM for document quality validation
            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based document quality validation
                quality_metrics = await self._validate_document_quality_with_llm(
                    document_text, document_metadata
                )
            else:
                # Use rule-based document quality validation
                quality_metrics = validate_document_quality.invoke(
                    {
                        "document_text": document_text,
                        "document_metadata": document_metadata,
                    }
                )
                quality_metrics = quality_metrics.dict()

            # Store quality metrics
            state["document_quality_metrics"] = quality_metrics
            state["confidence_scores"]["document_quality"] = quality_metrics.get(
                "text_quality_score", 0.5
            )

            # Fail-fast for critical quality issues - prevent UI hang
            issues = quality_metrics.get("issues_identified", [])
            if issues and "Document text is too short or empty" in issues:
                logger.error(
                    "Critical document quality issue detected - failing analysis"
                )
                return update_state_step(
                    state,
                    "document_analysis_failed",
                    error="Document quality is too poor for analysis. Please upload a higher quality document.",
                )

            # Check overall quality score for fail-fast
            overall_quality = quality_metrics.get(
                "overall_quality_score", quality_metrics.get("text_quality_score", 0.5)
            )
            if overall_quality < 0.3:  # Very poor quality threshold
                logger.error(
                    f"Document quality too poor (score: {overall_quality}) - failing analysis"
                )
                return update_state_step(
                    state,
                    "document_analysis_failed",
                    error=f"Document quality score ({overall_quality:.2f}) is too low for reliable analysis. Please upload a clearer document.",
                )

            # Log quality issues
            if issues:
                logger.warning(f"Document quality issues: {issues}")

            updated_data = {
                "document_quality_metrics": quality_metrics,
                "llm_used": use_llm and (self.openai_client or self.gemini_client),
            }

            # Merge with progress update
            progress_update.update(updated_data)

            logger.debug(
                f"Document quality validation completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return create_step_update("document_quality_validated", progress_update)

        except Exception as e:
            self._log_exception(
                step_name="validate_document_quality_step",
                error=e,
                state=state,
            )
            # Continue workflow with warning
            state["confidence_scores"]["document_quality"] = 0.5
            return update_state_step(
                state,
                "document_quality_validation_warning",
                error=f"Quality validation failed: {str(e)}",
            )

    @langsmith_trace(name="extract_contract_terms", run_type="chain")
    async def extract_contract_terms(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced contract terms extraction using contract_structure.md with configurable methods"""

        # Update progress
        if "progress" in state and state["progress"]:
            state["progress"]["current_step"] += 1
            state["progress"]["percentage"] = int(
                (state["progress"]["current_step"] / state["progress"]["total_steps"])
                * 100
            )

        try:
            # Handle case where document_metadata might be None
            document_metadata = state.get("document_metadata", {})
            if not document_metadata:
                logger.warning("No document metadata available for term extraction")
                # Try to get text from document_data as fallback
                document_data = state.get("document_data", {})
                document_text = (
                    document_data.get("content", "") if document_data else ""
                )
            else:
                document_text = document_metadata.get(
                    "full_text"
                ) or document_metadata.get("extracted_text", "")

            if not document_text:
                logger.error("No document text available for term extraction")
                return update_state_step(
                    state,
                    "term_extraction_failed",
                    error="No document text available for term extraction",
                )

            australian_state = state.get("australian_state", "NSW")
            contract_type = state.get("contract_type", "purchase_agreement")
            user_experience = state.get("user_experience", "novice")
            user_type = state.get("user_type", "buyer")

            # Check if we should use LLM for contract analysis
            use_llm = self.use_llm_config.get("contract_analysis", True)

            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based extraction with contract_structure.md template
                extraction_result = await self._extract_terms_llm(
                    document_text,
                    australian_state,
                    contract_type,
                    user_experience,
                    user_type,
                )
            else:
                # Use rule-based extraction as fallback
                extraction_result = self._extract_terms_rule_based(
                    document_text, australian_state
                )

            # Store results in state with enhanced metadata
            state["confidence_scores"]["term_extraction"] = extraction_result.get(
                "overall_confidence", 0.5
            )

            updated_data = {
                "contract_terms": extraction_result.get("terms", {}),
                "extraction_metadata": {
                    "confidence_scores": extraction_result.get("confidence_scores", {}),
                    "state_requirements": extraction_result.get(
                        "state_requirements", {}
                    ),
                    "extraction_method": "llm_structured" if use_llm else "rule_based",
                    "enhanced_extraction": use_llm,
                    "extraction_timestamp": datetime.now(UTC).isoformat(),
                    "llm_used": use_llm and (self.openai_client or self.gemini_client),
                },
            }

            logger.debug(
                f"Contract terms extraction completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return update_state_step(state, "terms_extracted", data=updated_data)

        except Exception as e:
            self._log_exception(
                step_name="extract_contract_terms",
                error=e,
                state=state,
                context={
                    "use_llm": self.use_llm_config.get("contract_analysis", True),
                },
            )
            return update_state_step(
                state,
                "term_extraction_failed",
                error=f"Contract terms extraction failed: {str(e)}",
            )

    def _get_extraction_method(self, state: RealEstateAgentState) -> str:
        """Determine extraction method based on configuration and state"""
        # Check extraction configuration first
        if hasattr(self, "extraction_config") and self.extraction_config:
            configured_method = self.extraction_config.get("method", "llm_structured")

            # If configured for LLM but no clients available, fallback to rule-based
            if configured_method == "llm_structured" and not (
                self.openai_client or self.gemini_client
            ):
                logger.warning(
                    "LLM extraction configured but no clients available, falling back to rule-based"
                )
                return "rule_based"

            return configured_method

        # Default to LLM if available, otherwise rule-based
        if self.openai_client or self.gemini_client:
            return "llm_structured"
        else:
            return "rule_based"

    async def _extract_terms_llm(
        self,
        document_text: str,
        australian_state: str,
        contract_type: str,
        user_experience: str,
        user_type: str,
    ) -> Dict[str, Any]:
        """Extract contract terms using LLM with contract_structure.md template and fragments"""

        try:
            # Create enhanced context for contract structure analysis
            extraction_context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "extracted_text": document_text,
                    "australian_state": australian_state,
                    "contract_type": contract_type,
                    "user_type": user_type,
                    "user_experience_level": user_experience,
                    "complexity": "standard",
                    "analysis_depth": "comprehensive",
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use the existing contract_structure.md template with fragments
            try:
                # Check if we should use fragments based on configuration
                if self.extraction_config.get("use_fragments", True):
                    # Use fragment-based orchestration
                    rendered_prompt = await self.prompt_manager.render_composed(
                        composition_name="contract_analysis_complete",
                        context=extraction_context,
                        service_name="contract_analysis_workflow",
                    )
                    logger.debug(
                        "Contract structure analysis with fragments rendered successfully"
                    )
                else:
                    # Use direct template rendering
                    rendered_prompt = await self.prompt_manager.render(
                        template_name="analysis/contract_structure",
                        context=extraction_context,
                        service_name="contract_analysis_workflow",
                    )
                    logger.debug(
                        "Contract structure analysis prompt rendered successfully"
                    )

            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to manual prompt creation
                rendered_prompt = self._create_contract_structure_prompt(
                    document_text,
                    australian_state,
                    contract_type,
                    user_experience,
                    user_type,
                )

            # Get LLM response using new client architecture with fallback
            try:
                system_message = "You are an expert Australian property lawyer analyzing contract structure."
                llm_response = await self._generate_content_with_fallback(
                    rendered_prompt, system_message, use_gemini_fallback=True
                )

                # Parse JSON response
                try:
                    import json

                    extraction_result = json.loads(llm_response)

                    # Validate and structure the result
                    structured_result = self._structure_extraction_result(
                        extraction_result
                    )
                    structured_result["extraction_method"] = "llm_structured"
                    structured_result["overall_confidence"] = (
                        self._calculate_extraction_confidence(structured_result)
                    )

                    self._metrics["successful_parses"] += 1
                    logger.debug(f"Contract structure analysis completed successfully")

                    return structured_result

                except json.JSONDecodeError as json_error:
                    logger.warning(f"JSON parsing failed: {json_error}")
                    # Fallback to rule-based extraction
                    return self._extract_terms_rule_based(
                        document_text, australian_state
                    )

            except Exception as llm_error:
                logger.error(f"LLM contract structure analysis failed: {llm_error}")
                # Fallback to rule-based extraction
                return self._extract_terms_rule_based(document_text, australian_state)

        except Exception as extraction_error:
            logger.warning(f"LLM extraction failed, using fallback: {extraction_error}")
            return self._extract_terms_rule_based(document_text, australian_state)

    def _extract_terms_rule_based(
        self, document_text: str, australian_state: str
    ) -> Dict[str, Any]:
        """Extract contract terms using rule-based methods"""
        try:
            # Use existing rule-based extraction tools
            extraction_result = extract_australian_contract_terms.invoke(
                {"document_text": document_text, "state": australian_state}
            )

            # Structure the result to match the expected format
            structured_result = {
                "terms": extraction_result.get("terms", {}),
                "confidence_scores": extraction_result.get("confidence_scores", {}),
                "state_requirements": extraction_result.get("state_requirements", {}),
                "extraction_method": "rule_based",
                "overall_confidence": extraction_result.get("overall_confidence", 0.3),
                "missing_terms": [],
                "extraction_notes": ["Extracted using rule-based patterns"],
            }

            return structured_result

        except Exception as e:
            logger.error(f"Rule-based extraction failed: {e}")
            return {
                "terms": {},
                "confidence_scores": {},
                "state_requirements": {},
                "extraction_method": "rule_based",
                "overall_confidence": 0.1,
                "missing_terms": ["extraction_failed"],
                "extraction_notes": [f"Extraction failed: {str(e)}"],
            }

    def _structure_extraction_result(
        self, raw_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Structure the raw extraction result to match ContractTermsOutput format"""
        try:
            # Extract key terms from the structured analysis
            terms = {}

            # Financial terms
            if "financial_terms" in raw_result:
                financial = raw_result["financial_terms"]
                terms["purchase_price"] = financial.get("purchase_price")
                terms["deposit_amount"] = financial.get("deposit", {}).get("amount")
                terms["settlement_date"] = raw_result.get("settlement_terms", {}).get(
                    "settlement_date"
                )

            # Property details
            if "property_details" in raw_result:
                property_details = raw_result["property_details"]
                terms["property_address"] = property_details.get("address")
                terms["legal_description"] = property_details.get("legal_description")
                terms["property_type"] = property_details.get("property_type")

            # Party information
            if "parties" in raw_result:
                parties = raw_result["parties"]
                terms["vendor_details"] = parties.get("vendor", {})
                terms["purchaser_details"] = parties.get("purchaser", {})

            # Special conditions
            if "special_conditions" in raw_result:
                special = raw_result["special_conditions"]
                terms["special_conditions"] = special.get("conditions_list", [])

            # Conditions and warranties
            if "conditions_and_warranties" in raw_result:
                conditions = raw_result["conditions_and_warranties"]
                terms["finance_clause"] = conditions.get("finance_clause", {})
                terms["building_pest_clause"] = conditions.get(
                    "building_inspection", {}
                )
                terms["cooling_off_period"] = conditions.get(
                    "cooling_off_period", {}
                ).get("duration")

            # Calculate confidence scores
            confidence_scores = {}
            for key, value in terms.items():
                if value is not None:
                    confidence_scores[key] = (
                        0.8  # High confidence for structured extraction
                    )
                else:
                    confidence_scores[key] = 0.0

            return {
                "terms": terms,
                "confidence_scores": confidence_scores,
                "state_requirements": raw_result.get("legal_and_compliance", {}),
                "extraction_method": "llm_structured",
                "overall_confidence": self._calculate_extraction_confidence(
                    {"terms": terms, "confidence_scores": confidence_scores}
                ),
                "missing_terms": [k for k, v in terms.items() if v is None],
                "extraction_notes": ["Extracted using LLM-based structured analysis"],
            }

        except Exception as e:
            logger.error(f"Failed to structure extraction result: {e}")
            return {
                "terms": {},
                "confidence_scores": {},
                "state_requirements": {},
                "extraction_method": "llm_structured",
                "overall_confidence": 0.3,
                "missing_terms": ["structuring_failed"],
                "extraction_notes": [f"Structuring failed: {str(e)}"],
            }

    def _calculate_extraction_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate overall confidence score for extraction"""
        try:
            confidence_scores = result.get("confidence_scores", {})
            if not confidence_scores:
                return 0.3

            # Calculate average confidence
            total_confidence = sum(confidence_scores.values())
            avg_confidence = total_confidence / len(confidence_scores)

            # Boost confidence if we have key terms
            key_terms = ["purchase_price", "property_address", "settlement_date"]
            key_terms_found = sum(
                1 for term in key_terms if result.get("terms", {}).get(term)
            )
            key_terms_boost = min(0.2, key_terms_found * 0.05)

            return min(1.0, avg_confidence + key_terms_boost)

        except Exception:
            return 0.3

    def _create_contract_structure_prompt(
        self,
        document_text: str,
        australian_state: str,
        contract_type: str,
        user_experience: str,
        user_type: str,
    ) -> str:
        """Create fallback contract structure analysis prompt"""
        return f"""
        Analyze this Australian {contract_type} contract from {australian_state} for a {user_type} with {user_experience} experience.
        
        CONTRACT TEXT:
        {document_text[:6000]}
        
        Extract structured information following this JSON schema:
        {{
            "document_metadata": {{
                "contract_type": "{contract_type}",
                "state_jurisdiction": "{australian_state}",
                "document_date": "date if identifiable or null",
                "document_quality": "assess text clarity: excellent/good/fair/poor"
            }},
            "parties": {{
                "vendor": {{
                    "name": "full legal name or entity name",
                    "address": "registered address if provided"
                }},
                "purchaser": {{
                    "name": "full legal name(s)",
                    "address": "address if provided"
                }}
            }},
            "property_details": {{
                "address": "complete property address including postcode",
                "legal_description": "lot/plan details or title reference",
                "property_type": "house/unit/townhouse/land/commercial/industrial"
            }},
            "financial_terms": {{
                "purchase_price": "numeric value only (remove $ and commas)",
                "deposit": {{
                    "amount": "numeric value only",
                    "percentage": "calculated percentage of purchase price"
                }}
            }},
            "settlement_terms": {{
                "settlement_date": "specific settlement date if fixed"
            }},
            "conditions_and_warranties": {{
                "cooling_off_period": {{
                    "applicable": true/false,
                    "duration": "number of business days"
                }},
                "finance_clause": {{
                    "applicable": true/false,
                    "approval_period": "days for finance approval"
                }},
                "building_inspection": {{
                    "required": true/false,
                    "period": "inspection period in days"
                }}
            }}
        }}
        
        Return ONLY the JSON structure with extracted information. Use null for missing information.
        """

    async def validate_terms_completeness_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Validate contract terms completeness with configurable LLM usage"""

        if not self.enable_validation:
            return state

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            contract_terms = state["contract_terms"]
            australian_state = state["australian_state"]
            use_llm = self.use_llm_config.get("terms_validation", True)

            # Check if we should use LLM for terms validation
            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based terms validation
                validation_result = await self._validate_terms_completeness_with_llm(
                    contract_terms, australian_state
                )
            else:
                # Use rule-based terms validation
                validation_result = validate_contract_terms_completeness.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )
                validation_result = validation_result.dict()

            # Store validation results
            state["terms_validation"] = validation_result
            state["confidence_scores"]["terms_validation"] = validation_result.get(
                "validation_score", 0.5
            )

            updated_data = {
                "terms_validation": validation_result,
                "llm_used": use_llm and (self.openai_client or self.gemini_client),
            }

            logger.debug(
                f"Terms completeness validation completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return update_state_step(
                state, "terms_validation_completed", data=updated_data
            )

        except Exception as e:
            logger.error(f"Terms completeness validation failed: {e}")
            # Continue workflow with warning
            state["confidence_scores"]["terms_validation"] = 0.5
            return update_state_step(
                state,
                "terms_validation_warning",
                error=f"Terms validation failed: {str(e)}",
            )

    @langsmith_trace(name="analyze_australian_compliance", run_type="chain")
    async def analyze_australian_compliance(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced Australian compliance analysis with configurable LLM usage"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            contract_terms = state["contract_terms"]
            australian_state = state["australian_state"]
            use_llm = self.use_llm_config.get("compliance_analysis", True)

            # Initialize compliance tracking
            compliance_confidence = 0.0
            compliance_components = 0

            # Check if we should use LLM for compliance analysis
            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based compliance analysis
                compliance_check = await self._analyze_compliance_with_llm(
                    contract_terms, australian_state
                )
                compliance_confidence = compliance_check.get(
                    "compliance_confidence", 0.7
                )
            else:
                # Use rule-based compliance analysis
                compliance_check = self._analyze_compliance_rule_based(
                    contract_terms, australian_state
                )
                compliance_confidence = compliance_check.get(
                    "compliance_confidence", 0.5
                )

            state["confidence_scores"]["compliance_check"] = compliance_confidence

            updated_data = {
                "compliance_check": compliance_check,
                "llm_used": use_llm and (self.openai_client or self.gemini_client),
            }

            logger.debug(
                f"Enhanced compliance analysis completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return update_state_step(state, "compliance_analyzed", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced compliance analysis failed: {e}")
            return update_state_step(
                state,
                "compliance_analysis_failed",
                error=f"Enhanced compliance analysis failed: {str(e)}",
            )

    @langsmith_trace(name="analyze_contract_diagrams", run_type="chain")
    async def analyze_contract_diagrams(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Analyze contract-related diagrams using SemanticAnalysisService.

        - Loads `document_diagrams` for the current `document_id`
        - Builds storage paths from `extracted_image_path` when available
        - Uses LLM-backed `SemanticAnalysisService.analyze_contract_diagrams`
        - Stores consolidated results on the state for downstream risk assessment
        """

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            document_data: Dict[str, Any] = state.get("document_data", {})
            document_id = document_data.get("document_id")
            if not document_id:
                logger.warning(
                    "No document_id provided in state.document_data for diagram analysis"
                )
                return update_state_step(
                    state,
                    "diagram_analysis_skipped",
                    error="Missing document_id in document_data for diagram analysis",
                )

            # Initialize dependent services
            from app.services.document_service import DocumentService
            from app.services.ai.semantic_analysis_service import (
                SemanticAnalysisService,
            )

            doc_service = DocumentService(
                use_llm_document_processing=self.use_llm_config.get(
                    "document_processing", True
                )
            )
            await doc_service.initialize()

            sem_service = SemanticAnalysisService(document_service=doc_service)
            await sem_service.initialize()

            # Fetch diagrams for this document
            user_client = await doc_service.get_user_client()
            diagrams = await user_client.database.read(
                "document_diagrams",
                filters={"document_id": document_id},
            )

            if not diagrams:
                logger.info(
                    f"No diagrams found for document {document_id}; skipping diagram analysis"
                )
                return update_state_step(state, "diagram_analysis_skipped")

            # Build storage paths list from extracted_image_path when present
            storage_paths: List[str] = []
            for d in diagrams:
                path = d.get("extracted_image_path")
                if path:
                    storage_paths.append(path)

            if not storage_paths:
                logger.info(
                    f"document_diagrams present for {document_id} but no extracted_image_path values; skipping"
                )
                return update_state_step(state, "diagram_analysis_skipped")

            # Prepare contract context
            contract_context: Dict[str, Any] = {
                "australian_state": state.get("australian_state"),
                "document_type": document_data.get("document_type") or "contract",
                "user_type": state.get("user_type", "buyer"),
            }

            # Run consolidated diagram analysis
            consolidated = await sem_service.analyze_contract_diagrams(
                storage_paths=storage_paths,
                contract_context=contract_context,
                document_id=document_id,
            )

            # Confidence heuristic from overall assessment
            overall = consolidated.get("overall_assessment", {})
            confidence = overall.get("confidence_level", 0.7)
            state["confidence_scores"]["diagram_analysis"] = confidence

            updated_data = {
                "diagram_analyses": consolidated.get("diagram_analyses", []),
                "diagram_consolidated_risks": consolidated.get(
                    "consolidated_risks", []
                ),
                "diagram_overall_assessment": consolidated.get(
                    "overall_assessment", {}
                ),
                "diagram_recommendations": consolidated.get("recommendations", []),
                "llm_used": True,
            }

            logger.debug(
                f"Diagram analysis completed for document {document_id} with {len(storage_paths)} diagrams"
            )
            return update_state_step(
                state, "diagram_analysis_completed", data=updated_data
            )

        except Exception as e:
            logger.error(f"Diagram analysis failed: {e}")
            return update_state_step(
                state,
                "diagram_analysis_failed",
                error=f"Diagram analysis failed: {str(e)}",
            )

    @langsmith_trace(name="assess_contract_risks", run_type="chain")
    async def assess_contract_risks(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced risk assessment using PromptManager and OutputParser with configurable LLM usage"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            contract_terms = state["contract_terms"]
            compliance_check = state["compliance_check"]
            use_llm = self.use_llm_config.get("risk_assessment", True)

            # Check if we should use LLM for risk assessment
            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based risk assessment
                risk_analysis = await self._assess_risks_with_llm(
                    contract_terms, compliance_check, state["australian_state"]
                )
                risk_confidence = risk_analysis.get("confidence_level", 0.7)
            else:
                # Use rule-based risk assessment
                risk_analysis = self._assess_risks_rule_based(
                    contract_terms, compliance_check
                )
                risk_confidence = risk_analysis.get("confidence_level", 0.5)

            # Store results in state
            state["confidence_scores"]["risk_assessment"] = risk_confidence

            updated_data = {
                "risk_analysis": risk_analysis,
                "llm_used": use_llm and (self.openai_client or self.gemini_client),
            }

            logger.debug(
                f"Enhanced risk assessment completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return update_state_step(state, "risks_assessed", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced risk assessment failed: {e}")
            return update_state_step(
                state,
                "risk_assessment_failed",
                error=f"Enhanced risk assessment failed: {str(e)}",
            )

    @langsmith_trace(name="generate_recommendations", run_type="chain")
    async def generate_recommendations(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced recommendations generation with configurable LLM usage"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            use_llm = self.use_llm_config.get("recommendations", True)

            # Check if we should use LLM for recommendations
            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based recommendations generation
                recommendations = await self._generate_recommendations_with_llm(state)
            else:
                # Use rule-based recommendations generation
                recommendations = self._generate_recommendations_rule_based(state)

            # Store results in state
            state["confidence_scores"]["recommendations"] = 0.8 if use_llm else 0.6

            updated_data = {
                "recommendations": recommendations,
                "llm_used": use_llm and (self.openai_client or self.gemini_client),
            }

            logger.debug(
                f"Enhanced recommendations generation completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return update_state_step(
                state, "recommendations_generated", data=updated_data
            )

        except Exception as e:
            logger.error(f"Enhanced recommendations generation failed: {e}")
            return update_state_step(
                state,
                "recommendations_generation_failed",
                error=f"Enhanced recommendations generation failed: {str(e)}",
            )

    async def validate_final_output_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Validate final output quality with configurable LLM usage"""

        if not self.enable_validation:
            return state

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            use_llm = self.use_llm_config.get("final_validation", True)

            # Check if we should use LLM for final validation
            if use_llm and (self.openai_client or self.gemini_client):
                # Use LLM-based final validation
                validation_result = await self._validate_final_output_with_llm(state)
            else:
                # Use rule-based final validation
                validation_result = self._validate_final_output_rule_based(state)

            # Store validation results
            state["final_validation"] = validation_result
            state["confidence_scores"]["final_validation"] = validation_result.get(
                "validation_score", 0.5
            )

            updated_data = {
                "final_validation": validation_result,
                "llm_used": use_llm and (self.openai_client or self.gemini_client),
            }

            logger.debug(
                f"Final output validation completed using {'LLM' if use_llm else 'rule-based'} method"
            )
            return update_state_step(
                state, "final_validation_completed", data=updated_data
            )

        except Exception as e:
            logger.error(f"Final output validation failed: {e}")
            # Continue workflow with warning
            state["confidence_scores"]["final_validation"] = 0.5
            return update_state_step(
                state,
                "final_validation_warning",
                error=f"Final validation failed: {str(e)}",
            )

    @langsmith_trace(name="compile_analysis_report", run_type="chain")
    def compile_analysis_report(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced report compilation with comprehensive metadata"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = 100

        try:
            # Calculate enhanced overall confidence
            confidence_result = calculate_overall_confidence_score.invoke(
                {
                    "confidence_scores": state.get("confidence_scores", {}),
                    "step_weights": None,  # Use default weights
                }
            )

            overall_confidence = confidence_result["overall_confidence"]

            # Compile enhanced analysis results
            analysis_results = {
                "contract_id": state.get("session_id"),
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "user_id": state["user_id"],
                "australian_state": state["australian_state"],
                "contract_terms": state.get("contract_terms") or {},
                "risk_assessment": state.get("risk_assessment") or {},
                "compliance_check": state.get("compliance_check") or {},
                "recommendations": state.get("final_recommendations") or [],
                "confidence_scores": state.get("confidence_scores") or {},
                "overall_confidence": overall_confidence,
                "confidence_assessment": confidence_result.get(
                    "quality_assessment", ""
                ),
                "processing_summary": {
                    "steps_completed": state["current_step"],
                    "processing_time": state.get("processing_time"),
                    "analysis_version": state["agent_version"],
                    "progress": state.get("progress") or {},
                    "enhanced_workflow": True,
                    "validation_enabled": self.enable_validation,
                    "quality_checks_enabled": self.enable_quality_checks,
                },
                "quality_metrics": {
                    "extraction_quality": (state.get("document_metadata") or {}).get(
                        "text_quality", {}
                    ),
                    "confidence_breakdown": state.get("confidence_scores", {}),
                    "processing_method": {
                        "document_extraction": (
                            state.get("document_metadata") or {}
                        ).get("extraction_method", "unknown"),
                        "term_extraction": (state.get("extraction_metadata") or {}).get(
                            "extraction_method", "standard"
                        ),
                        "risk_parsing": (state.get("risk_assessment") or {}).get(
                            "parsing_method", "unknown"
                        ),
                        "recommendations_parsing": (
                            state.get("recommendations_metadata") or {}
                        ).get("parsing_method", "unknown"),
                    },
                    "workflow_metrics": self._get_workflow_metrics(),
                    "document_quality_metrics": state.get("document_quality_metrics")
                    or {},
                    "validation_results": {
                        "terms_validation": state.get("terms_validation") or {},
                        "final_output_validation": state.get("final_output_validation")
                        or {},
                    },
                },
            }

            # Enhanced report data
            enhanced_report_data = self._create_enhanced_report_summary(
                analysis_results
            )

            updated_data = {
                "analysis_results": analysis_results,
                "report_data": enhanced_report_data,
                "parsing_status": ProcessingStatus.COMPLETED,
            }

            logger.info("Enhanced analysis report compiled successfully")
            return update_state_step(state, "report_compiled", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced report compilation failed: {e}")
            return update_state_step(
                state,
                "report_compilation_failed",
                error=f"Enhanced report compilation failed: {str(e)}",
            )

    # Enhanced helper methods and existing methods with improvements

    def _get_workflow_metrics(self) -> Dict[str, Any]:
        """Get enhanced workflow performance metrics"""
        return {
            **self._metrics,
            "parsing_success_rate": (
                self._metrics["successful_parses"]
                / max(self._metrics["total_analyses"], 1)
            ),
            "fallback_usage_rate": (
                self._metrics["fallback_uses"] / max(self._metrics["total_analyses"], 1)
            ),
        }

    def _create_enhanced_report_summary(
        self, analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create enhanced summary report for display"""

        risk_assessment = analysis_results.get("risk_assessment") or {}
        compliance_check = analysis_results.get("compliance_check") or {}
        recommendations = analysis_results.get("recommendations") or []

        # Enhanced executive summary
        executive_summary = {
            "overall_risk_score": risk_assessment.get("overall_risk_score", 0),
            "compliance_status": (
                "compliant"
                if compliance_check.get("state_compliance", False)
                else "non-compliant"
            ),
            "total_recommendations": len(recommendations),
            "critical_issues": len(
                [r for r in recommendations if r.get("priority") == "critical"]
            ),
            "confidence_level": analysis_results.get("overall_confidence", 0),
            "quality_assessment": analysis_results.get("confidence_assessment", ""),
            "analysis_method": "enhanced_workflow",
        }

        # Enhanced key findings
        key_findings = {
            "highest_risks": [
                rf
                for rf in risk_assessment.get("risk_factors", [])
                if rf.get("severity") in ["high", "critical"]
            ][:3],
            "compliance_issues": compliance_check.get("compliance_issues", []),
            "immediate_actions": [
                r for r in recommendations if r.get("action_required", False)
            ][:5],
            "australian_specific_risks": risk_assessment.get(
                "state_specific_risks", []
            ),
        }

        # Enhanced financial summary
        financial_summary = {
            "stamp_duty": compliance_check.get("stamp_duty_calculation", {}),
            "estimated_costs": sum(
                r.get("estimated_cost", 0) or 0 for r in recommendations
            ),
            "cost_breakdown": [
                {"category": r.get("category"), "cost": r.get("estimated_cost", 0) or 0}
                for r in recommendations
                if r.get("estimated_cost")
            ],
        }

        # Enhanced quality indicators
        quality_indicators = {
            "confidence_breakdown": analysis_results.get("confidence_scores", {}),
            "processing_quality": analysis_results.get("quality_metrics", {}),
            "overall_confidence": analysis_results.get("overall_confidence", 0),
            "validation_results": (analysis_results.get("quality_metrics") or {}).get(
                "validation_results", {}
            ),
            "enhancement_indicators": {
                "structured_parsing_used": True,
                "validation_enabled": self.enable_validation,
                "quality_checks_enabled": self.enable_quality_checks,
                "prompt_management_used": True,
            },
        }

        return {
            "executive_summary": executive_summary,
            "key_findings": key_findings,
            "financial_summary": financial_summary,
            "quality_indicators": quality_indicators,
            "processing_metadata": {
                "workflow_version": "enhanced_v1.0",
                "analysis_timestamp": analysis_results.get("analysis_timestamp"),
                "processing_time": (
                    analysis_results.get("processing_summary") or {}
                ).get("processing_time"),
                "performance_metrics": self._get_workflow_metrics(),
            },
        }

    # Keep existing helper methods but enhance them

    def handle_processing_error(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced error handling with detailed diagnostics"""

        error_message = state.get("error_state", "Unknown error occurred")

        # Enhanced error details with workflow context
        error_details = {
            "error_message": error_message,
            "failed_step": state["current_step"],
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": state["session_id"],
            "workflow_version": "enhanced_v1.0",
            "enhancement_features": {
                "validation_enabled": self.enable_validation,
                "quality_checks_enabled": self.enable_quality_checks,
                "prompt_manager_used": True,
            },
            "processing_context": {
                "australian_state": state.get("australian_state"),
                "document_available": bool(state.get("document_data")),
                "confidence_scores": state.get("confidence_scores", {}),
            },
        }
        # Avoid updating 'analysis_results' in error path to prevent concurrent graph update conflicts
        updated_data = {
            "error_details": error_details,
            "parsing_status": ProcessingStatus.FAILED,
        }

        self._log_exception(
            step_name="handle_processing_error",
            error=Exception(error_message),
            state=state,
            context={"failed_step": state.get("current_step")},
        )
        return update_state_step(state, "error_handled", data=updated_data)

    def retry_failed_step(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Enhanced retry logic with intelligent backoff"""

        retry_count = state.get("retry_count", 0)
        max_retries = 3  # Increased for enhanced workflow

        if retry_count >= max_retries:
            self._log_step_debug(
                step_name="retry_failed_step",
                message=f"Max retries ({max_retries}) exceeded, delegating to error handler",
                state=state,
                details={"retry_count": retry_count},
            )
            return self.handle_processing_error(state)

        # Enhanced retry with exponential backoff
        retry_delay = 2**retry_count  # 2, 4, 8 seconds
        logger.info(
            f"Retrying step (attempt {retry_count + 1}/{max_retries}) after {retry_delay}s delay"
        )
        self._log_step_debug(
            step_name="retry_failed_step",
            message="Retry scheduled",
            state=state,
            details={
                "attempt": retry_count + 1,
                "max_retries": max_retries,
                "delay_seconds": retry_delay,
            },
        )

        time.sleep(retry_delay)

        updated_data = {
            "retry_count": retry_count + 1,
            "retry_timestamp": datetime.now(UTC).isoformat(),
            "retry_reason": state.get("error_state", "Unknown retry reason"),
        }

        return update_state_step(state, "retrying", data=updated_data)

    # Keep existing conditional methods with enhancements

    def check_processing_success(self, state: RealEstateAgentState) -> str:
        """Enhanced processing success check"""

        if state.get("error_state"):
            return "error"

        parsing_status = state.get("parsing_status")
        if parsing_status == ProcessingStatus.COMPLETED:
            # Additional check for document quality if enabled
            if self.enable_quality_checks:
                doc_quality = state.get("document_quality_metrics", {})
                if doc_quality.get("text_quality_score", 1.0) < 0.5:
                    logger.warning("Document quality below threshold")
                    return "retry"
            return "success"

        retry_count = state.get("retry_count", 0)
        return "retry" if retry_count < 3 else "error"

    def check_extraction_quality(self, state: RealEstateAgentState) -> str:
        """Enhanced extraction quality check"""

        if state.get("error_state"):
            return "error"

        confidence_scores = state.get("confidence_scores", {})
        extraction_confidence = confidence_scores.get("term_extraction", 0.0)

        # Enhanced thresholds
        if extraction_confidence >= 0.8:
            return "high_confidence"
        elif extraction_confidence >= 0.5:
            # Additional validation check if enabled
            if self.enable_validation:
                terms_validation = state.get("terms_validation", {})
                if terms_validation.get("validation_confidence", 0) >= 0.6:
                    return "high_confidence"
            return "low_confidence"
        else:
            return "error"

    # Keep existing fallback methods but add enhanced logging

    def _create_risk_assessment_prompt(
        self, contract_terms: Dict, compliance_check: Dict, state: str
    ) -> str:
        """Enhanced fallback risk assessment prompt"""
        logger.debug("Using fallback risk assessment prompt")
        return f"""
        Analyze the following Australian property contract for risks and issues:
        
        CONTRACT TERMS:
        {json.dumps(contract_terms, indent=2)}
        
        COMPLIANCE STATUS:
        {json.dumps(compliance_check, indent=2)}
        
        STATE: {state}
        
        Please provide a comprehensive risk assessment including:
        1. Overall risk score (0-10, where 10 is highest risk)
        2. Specific risk factors with severity levels
        3. Potential financial impacts
        4. Legal compliance issues
        
        Format response as JSON with the following structure:
        {{
            "overall_risk_score": <number>,
            "risk_factors": [
                {{
                    "factor": "<description>",
                    "severity": "<low|medium|high|critical>",
                    "description": "<detailed explanation>",
                    "impact": "<potential consequences>",
                    "australian_specific": <boolean>
                }}
            ],
            "risk_summary": "<executive summary>",
            "confidence_level": <0-1>,
            "critical_issues": ["<issue1>", "<issue2>"],
            "state_specific_risks": ["<risk1>", "<risk2>"]
        }}
        """

    def _create_recommendations_prompt(self, state: RealEstateAgentState) -> str:
        """Enhanced fallback recommendations prompt"""
        logger.debug("Using fallback recommendations prompt")
        return f"""
        Based on this contract analysis, provide specific actionable recommendations:
        
        ANALYSIS SUMMARY:
        - Risk Assessment: {json.dumps(state.get("risk_analysis", {}), indent=2)}
        - Compliance Issues: {json.dumps(state.get("compliance_check", {}), indent=2)}
        - Australian State: {state["australian_state"]}
        - User Type: {state["user_type"]}
        
        Provide recommendations in JSON format:
        {{
            "recommendations": [
                {{
                    "priority": "<low|medium|high|critical>",
                    "category": "<legal|financial|practical>",
                    "recommendation": "<specific action>",
                    "action_required": <boolean>,
                    "australian_context": "<state-specific notes>",
                    "estimated_cost": <number or null>
                }}
            ],
            "executive_summary": "<summary of key recommendations>",
            "immediate_actions": ["<action1>", "<action2>"],
            "next_steps": ["<step1>", "<step2>"]
        }}
        """

    def _create_contract_extraction_prompt(self, document_text: str, state: str) -> str:
        """Enhanced fallback contract terms extraction prompt"""
        logger.debug("Using fallback contract terms extraction prompt")
        return f"""
        Extract key contract terms from the following Australian property contract:
        
        CONTRACT TEXT:
        {document_text}
        
        STATE: {state}
        
        Please provide a JSON response with the following structure:
        {{
            "terms": {{
                "purchase_price": <number or null>,
                "deposit_amount": <number or null>,
                "property_address": "<string or null>",
                "settlement_date": "<string or null>"
            }},
            "confidence_scores": {{
                "purchase_price": <0-1>,
                "deposit_amount": <0-1>,
                "property_address": <0-1>,
                "settlement_date": <0-1>
            }},
            "overall_confidence": <0-1>,
            "extraction_method": "fallback",
            "extraction_timestamp": "<ISO 8601 timestamp>"
        }}
        """

    # Keep all existing helper methods with enhanced error handling and logging
    def _parse_risk_analysis(self, llm_response: str) -> Dict[str, Any]:
        """Enhanced risk analysis parsing with better fallback"""
        try:
            parsed = json.loads(llm_response)
            logger.debug("Risk analysis parsed successfully using JSON")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed for risk analysis: {e}")
            # Enhanced fallback
            return {
                "overall_risk_score": 5.0,
                "risk_factors": [
                    {
                        "factor": "Unable to parse detailed risk analysis",
                        "severity": "medium",
                        "description": "LLM response could not be parsed using structured format",
                        "impact": "Manual review recommended for accurate risk assessment",
                        "australian_specific": False,
                        "mitigation_suggestions": ["Seek professional legal review"],
                    }
                ],
                "risk_summary": "Risk analysis parsing failed - manual review required",
                "confidence_level": 0.3,
                "critical_issues": ["Parser failure - manual verification needed"],
                "state_specific_risks": [],
            }

    def _parse_recommendations(self, llm_response: str) -> List[Dict[str, Any]]:
        """Enhanced recommendations parsing with better fallback"""
        try:
            parsed = json.loads(llm_response)
            recommendations = parsed.get("recommendations", [])
            logger.debug(
                f"Recommendations parsed successfully: {len(recommendations)} items"
            )
            return recommendations
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed for recommendations: {e}")
            # Enhanced fallback recommendations
            return [
                {
                    "priority": "high",
                    "category": "legal",
                    "recommendation": "Seek professional legal advice due to analysis parsing issues",
                    "action_required": True,
                    "australian_context": "Consult qualified property lawyer familiar with local regulations",
                    "estimated_cost": 500.0,
                    "timeline": "Before settlement",
                    "consequences_if_ignored": "May miss critical legal issues or compliance requirements",
                },
                {
                    "priority": "medium",
                    "category": "practical",
                    "recommendation": "Request manual review of contract analysis results",
                    "action_required": True,
                    "australian_context": "Have qualified professional review automated analysis",
                    "estimated_cost": 200.0,
                    "timeline": "Within 48 hours",
                    "consequences_if_ignored": "Reduced confidence in analysis accuracy",
                },
            ]

    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """Enhanced text quality assessment"""
        if not text:
            return {"score": 0.0, "issues": ["No text content"]}

        # Enhanced quality metrics
        words = text.split()
        total_chars = len(text)
        total_words = len(words)

        issues = []
        score = 1.0

        # Check for minimum content
        if total_chars < 200:
            issues.append("Very short document")
            score *= 0.5

        if total_words < 50:
            issues.append("Too few words extracted")
            score *= 0.5

        # Enhanced OCR quality checks
        if words:
            single_char_words = sum(1 for word in words if len(word) == 1)
            single_char_ratio = single_char_words / total_words

            if single_char_ratio > 0.3:
                issues.append("High ratio of single characters (poor OCR)")
                score *= 0.6

            # Check for repeated characters (OCR artifacts)
            import re

            repeated_patterns = len(re.findall(r"(.)\1{3,}", text))
            if repeated_patterns > 5:
                issues.append("Multiple repeated character patterns detected")
                score *= 0.7

        # Enhanced contract keyword detection
        contract_keywords = [
            "contract",
            "agreement",
            "purchase",
            "sale",
            "property",
            "vendor",
            "purchaser",
            "settlement",
            "deposit",
            "price",
            "cooling",
            "condition",
            "warranty",
            "title",
            "conveyance",
        ]

        text_lower = text.lower()
        found_keywords = sum(
            1 for keyword in contract_keywords if keyword in text_lower
        )

        if found_keywords < 3:
            issues.append("Few contract-relevant keywords found")
            score *= 0.8
        else:
            # Bonus for good keyword coverage
            keyword_bonus = min(0.2, (found_keywords - 3) * 0.02)
            score = min(1.0, score + keyword_bonus)

        return {
            "score": max(0.0, min(1.0, score)),
            "issues": issues,
            "character_count": total_chars,
            "word_count": total_words,
            "contract_keywords_found": found_keywords,
            "single_char_ratio": (
                single_char_words / total_words if total_words > 0 else 0
            ),
            "quality_indicators": {
                "sufficient_length": total_chars >= 200,
                "adequate_words": total_words >= 50,
                "good_keyword_coverage": found_keywords >= 5,
                "low_ocr_artifacts": (
                    single_char_words / total_words < 0.2 if total_words > 0 else False
                ),
            },
        }

    def _fallback_term_extraction(
        self, document_text: str, australian_state: str
    ) -> Dict[str, Any]:
        """Enhanced fallback term extraction"""
        import re

        logger.debug("Using enhanced fallback term extraction")
        terms = {}
        confidence_scores = {}

        # Enhanced price extraction patterns
        price_patterns = [
            r"purchase\s+price[:\s]+\$?([\d,]+(?:\.\d{2})?)",
            r"consideration[:\s]+\$?([\d,]+(?:\.\d{2})?)",
            r"total\s+(?:amount|price)[:\s]+\$?([\d,]+(?:\.\d{2})?)",
            r"\$\s*([\d,]+(?:\.\d{2})?)",
        ]

        for pattern in price_patterns:
            matches = re.finditer(pattern, document_text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.group(1).replace(",", "")
                    price_value = float(price_str)
                    if (
                        50000 <= price_value <= 50000000
                    ):  # Reasonable property price range
                        terms["purchase_price"] = price_value
                        confidence_scores["purchase_price"] = 0.7
                        break
                except ValueError:
                    continue
            if "purchase_price" in terms:
                break

        # Enhanced deposit extraction
        deposit_patterns = [
            r"deposit[:\s]+\$?([\d,]+(?:\.\d{2})?)",
            r"initial[\s]+payment[:\s]+\$?([\d,]+(?:\.\d{2})?)",
            r"down[\s]+payment[:\s]+\$?([\d,]+(?:\.\d{2})?)",
        ]

        for pattern in deposit_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE)
            if match:
                try:
                    deposit_str = match.group(1).replace(",", "")
                    deposit_value = float(deposit_str)
                    if 1000 <= deposit_value <= 1000000:  # Reasonable deposit range
                        terms["deposit_amount"] = deposit_value
                        confidence_scores["deposit_amount"] = 0.6
                        break
                except ValueError:
                    pass

        # Enhanced address extraction
        address_patterns = [
            r"property[:\s]+(.+?)(?=\n|settlement|deposit|price)",
            r"premises[:\s]+(.+?)(?=\n|settlement|deposit|price)",
            r"land[:\s]+(.+?)(?=\n|settlement|deposit|price)",
        ]

        for pattern in address_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                if len(address) > 10 and len(address) < 200:
                    terms["property_address"] = address
                    confidence_scores["property_address"] = 0.5
                    break

        # Enhanced settlement date extraction
        date_patterns = [
            r"settlement[:\s]+(?:date[:\s]+)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"completion[:\s]+(?:date[:\s]+)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"settlement[:\s]+.*?(\d+)\s+days?",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE)
            if match:
                terms["settlement_date"] = match.group(1).strip()
                confidence_scores["settlement_date"] = 0.4
                break

        overall_confidence = (
            sum(confidence_scores.values()) / len(confidence_scores)
            if confidence_scores
            else 0.2
        )

        logger.debug(
            f"Enhanced fallback extraction found {len(terms)} terms with {overall_confidence:.2f} confidence"
        )

        return {
            "terms": terms,
            "confidence_scores": confidence_scores,
            "overall_confidence": overall_confidence,
            "extraction_method": "enhanced_fallback",
            "extraction_timestamp": datetime.now(UTC).isoformat(),
        }

    def _fallback_risk_analysis(
        self, contract_terms: Dict, compliance_check: Dict
    ) -> Dict[str, Any]:
        """Enhanced fallback risk analysis"""
        logger.debug("Using enhanced fallback risk analysis")

        risk_factors = []
        risk_score = 5.0  # Default medium risk

        # Enhanced risk factor detection
        if not contract_terms.get("purchase_price"):
            risk_factors.append(
                {
                    "factor": "Missing purchase price",
                    "severity": "high",
                    "description": "Purchase price not clearly identified in contract",
                    "impact": "Unable to calculate stamp duty and assess financial risks accurately",
                    "australian_specific": False,
                    "mitigation_suggestions": [
                        "Verify purchase price with vendor",
                        "Review contract for price clauses",
                    ],
                }
            )
            risk_score += 2.0

        # Check for missing deposit information
        if not contract_terms.get("deposit_amount"):
            risk_factors.append(
                {
                    "factor": "Missing deposit information",
                    "severity": "medium",
                    "description": "Deposit amount not clearly specified",
                    "impact": "Unclear financial obligations and settlement requirements",
                    "australian_specific": False,
                    "mitigation_suggestions": [
                        "Clarify deposit amount and payment terms"
                    ],
                }
            )
            risk_score += 1.0

        # Enhanced compliance issues
        if not compliance_check.get("state_compliance", False):
            risk_factors.append(
                {
                    "factor": "State compliance issues identified",
                    "severity": "high",
                    "description": "Contract may not comply with state property laws",
                    "impact": "Legal risks, potential contract invalidation, and settlement delays",
                    "australian_specific": True,
                    "mitigation_suggestions": [
                        "Seek legal review from qualified property lawyer",
                        "Verify compliance with state regulations",
                    ],
                }
            )
            risk_score += 2.0

        # Check for cooling-off period issues
        cooling_off = compliance_check.get("cooling_off_validation", {})
        if not cooling_off.get("compliant", True):
            risk_factors.append(
                {
                    "factor": "Cooling-off period non-compliance",
                    "severity": "medium",
                    "description": "Cooling-off period may not meet state requirements",
                    "impact": "Reduced buyer protection and potential legal complications",
                    "australian_specific": True,
                    "mitigation_suggestions": [
                        "Review cooling-off provisions with legal advisor"
                    ],
                }
            )
            risk_score += 1.5

        # Cap risk score at 10
        risk_score = min(10.0, risk_score)

        return {
            "overall_risk_score": risk_score,
            "risk_factors": risk_factors,
            "risk_summary": f"Enhanced fallback analysis identified {len(risk_factors)} risk factors with overall score of {risk_score}/10",
            "confidence_level": 0.4,  # Lower confidence for fallback
            "critical_issues": [
                rf["factor"] for rf in risk_factors if rf["severity"] == "critical"
            ],
            "state_specific_risks": [
                rf["factor"] for rf in risk_factors if rf["australian_specific"]
            ],
        }

    def _fallback_recommendations(
        self, state: RealEstateAgentState
    ) -> List[Dict[str, Any]]:
        """Enhanced fallback recommendations"""
        logger.debug("Using enhanced fallback recommendations")

        recommendations = []

        # Always recommend legal review with enhanced context
        recommendations.append(
            {
                "priority": "high",
                "category": "legal",
                "recommendation": "Seek comprehensive legal advice from a qualified property lawyer",
                "action_required": True,
                "australian_context": f"Ensure lawyer is qualified in {state['australian_state']} property law and familiar with recent regulatory changes",
                "estimated_cost": 500.0,
                "timeline": "Before contract exchange or within cooling-off period",
                "legal_basis": "Due diligence requirement for property transactions",
                "consequences_if_ignored": "May miss critical legal issues or compliance requirements",
            }
        )

        # Enhanced missing information checks
        contract_terms = state.get("contract_terms", {})
        if not contract_terms.get("purchase_price"):
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "legal",
                    "recommendation": "Clarify and verify all purchase price and financial terms",
                    "action_required": True,
                    "australian_context": "Required for stamp duty calculation and contract validity under Australian law",
                    "estimated_cost": None,
                    "timeline": "Immediately",
                    "legal_basis": "Essential contract term requirement",
                    "consequences_if_ignored": "Contract may be void or unenforceable",
                }
            )

        # Enhanced compliance recommendations
        compliance_check = state.get("compliance_check", {})
        if not compliance_check.get("state_compliance", False):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "compliance",
                    "recommendation": "Conduct comprehensive state law compliance review",
                    "action_required": True,
                    "australian_context": f"Ensure full compliance with {state['australian_state']} property laws and recent legislative changes",
                    "estimated_cost": 300.0,
                    "timeline": "Within 5 business days",
                    "legal_basis": "State property law compliance requirement",
                    "consequences_if_ignored": "Legal penalties, contract disputes, or settlement delays",
                }
            )

        # Document quality recommendation if issues detected
        doc_quality = state.get("document_quality_metrics", {})
        if doc_quality.get("text_quality_score", 1.0) < 0.7:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "practical",
                    "recommendation": "Obtain higher quality copy of contract for thorough review",
                    "action_required": True,
                    "australian_context": "Ensure all contract terms are clearly legible for accurate analysis",
                    "estimated_cost": 50.0,
                    "timeline": "Within 2 business days",
                    "legal_basis": "Due diligence requirement",
                    "consequences_if_ignored": "May miss important contract provisions or conditions",
                }
            )

        return recommendations

    async def _generate_content_with_fallback(
        self, prompt: str, system_message: str = "", use_gemini_fallback: bool = True
    ) -> str:
        """Generate content using OpenAI with fallback to Gemini if needed"""
        try:
            # Prepare full prompt
            if system_message:
                full_prompt = f"{system_message}\n\n{prompt}"
            else:
                full_prompt = prompt

            # Try OpenAI first
            response = await self.openai_client.generate_content(
                full_prompt,
                model=self.model_name,
                temperature=0.1,
            )

            # Monitor response quality
            self._monitor_response_quality(response, "openai")
            return response

        except Exception as openai_error:
            logger.warning(f"OpenAI generation failed: {openai_error}")

            # Fallback to Gemini if available and enabled
            if use_gemini_fallback and self.gemini_client:
                try:
                    logger.info("Falling back to Gemini client")
                    response = await self.gemini_client.generate_content(
                        full_prompt,
                        model="gemini-2.5-flash",
                        temperature=0.1,
                    )

                    # Monitor fallback response quality
                    self._monitor_response_quality(response, "gemini_fallback")
                    return response
                except Exception as gemini_error:
                    logger.error(f"Gemini fallback also failed: {gemini_error}")
                    raise openai_error  # Re-raise original error

            raise openai_error

    def _monitor_response_quality(self, response: str, provider: str) -> None:
        """Monitor response quality for debugging malformed JSON issues"""
        try:
            # Basic quality checks
            response_length = len(response)
            is_json_like = response.strip().startswith(
                "{"
            ) and response.strip().endswith("}")

            # Try JSON parsing to check validity
            is_valid_json = False
            try:
                import json

                json.loads(response)
                is_valid_json = True
                self._metrics["successful_parses"] += 1
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Response quality issue from {provider}: Invalid JSON. Error: {e}"
                )
                logger.debug(
                    f"Malformed response preview (first 200 chars): {response[:200]}"
                )
                self._metrics["failed_parses"] += 1

            # Update quality metrics
            quality_metrics = {
                "provider": provider,
                "response_length": response_length,
                "is_json_like": is_json_like,
                "is_valid_json": is_valid_json,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Store last few responses for debugging
            if not hasattr(self, "_response_quality_history"):
                self._response_quality_history = []

            self._response_quality_history.append(quality_metrics)
            # Keep only last 10 responses
            if len(self._response_quality_history) > 10:
                self._response_quality_history.pop(0)

            logger.debug(f"Response quality metrics for {provider}: {quality_metrics}")

        except Exception as e:
            logger.error(f"Failed to monitor response quality: {e}")

    def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get comprehensive workflow performance metrics"""
        return {
            **self._metrics,
            "enhanced_features": {
                "prompt_manager_enabled": True,
                "structured_parsing_enabled": True,
                "validation_enabled": self.enable_validation,
                "quality_checks_enabled": self.enable_quality_checks,
                "client_architecture_enabled": True,
                "fallbacks_enabled": self.enable_fallbacks,
            },
            "parsing_metrics": {
                "success_rate": self._metrics["successful_parses"]
                / max(self._metrics["total_analyses"], 1),
                "fallback_rate": self._metrics["fallback_uses"]
                / max(self._metrics["total_analyses"], 1),
            },
        }

    async def _process_document_with_llm(self, document_data: Dict[str, Any]) -> str:
        """Process document using LLM for enhanced text extraction"""
        try:
            # Create prompt for document processing
            prompt = f"""
            Process the following document data and extract all relevant text content:
            
            Document Type: {document_data.get('document_type', 'unknown')}
            Document Name: {document_data.get('filename', 'unknown')}
            Document Size: {document_data.get('size', 'unknown')}
            
            Please extract all text content from this document, focusing on:
            - Contract terms and conditions
            - Financial information
            - Property details
            - Legal clauses
            - Dates and deadlines
            - Party information
            
            Return only the extracted text content, no explanations or formatting.
            """

            system_message = "You are an expert document processor specializing in Australian property contracts."

            # Use LLM to process document
            llm_response = await self._generate_content_with_fallback(
                prompt, system_message, use_gemini_fallback=True
            )

            return llm_response.strip()

        except Exception as e:
            logger.warning(f"LLM document processing failed: {e}")

    async def _assess_text_quality_with_llm(self, text: str) -> Dict[str, Any]:
        """Assess text quality using LLM"""
        try:
            prompt = f"""
            Assess the quality of the following extracted text from a property contract:
            
            {text[:2000]}...
            
            Evaluate the text quality across these dimensions:
            1. Completeness (0-1): How complete is the text extraction?
            2. Readability (0-1): How readable and clear is the text?
            3. Accuracy (0-1): How accurate is the extracted content?
            4. Structure (0-1): How well-structured is the content?
            
            Return a JSON response with this structure:
            {{
                "score": 0.85,
                "issues": ["list of quality issues found"],
                "completeness": 0.9,
                "readability": 0.8,
                "accuracy": 0.85,
                "structure": 0.8
            }}
            """

            system_message = "You are an expert in document quality assessment."

            llm_response = await self._generate_content_with_fallback(
                prompt, system_message, use_gemini_fallback=True
            )

            try:
                import json

                quality_result = json.loads(llm_response)
                return quality_result
            except json.JSONDecodeError:
                # Fallback to rule-based assessment
                return self._assess_text_quality(text)

        except Exception as e:
            logger.warning(f"LLM text quality assessment failed: {e}")
            # Fallback to rule-based assessment
            return self._assess_text_quality(text)

    @langsmith_trace(name="process_document", run_type="chain")
    async def process_document(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Document processing using DocumentService with persistence.

        - If the document was already processed, fetch summary from DB
        - Otherwise, process via DocumentService and persist
        - Populate state with consistent metadata
        """

        # Update progress
        if "progress" in state and state["progress"]:
            state["progress"]["current_step"] += 1
            state["progress"]["percentage"] = int(
                (state["progress"]["current_step"] / state["progress"]["total_steps"])
                * 100
            )

        try:
            # Ensure document metadata exists
            document_data: Dict[str, Any] = state.get("document_data", {})
            document_id = document_data.get("document_id")
            if not document_id:
                logger.warning("No document_id provided in state.document_data")
                return update_state_step(
                    state,
                    "document_processing_failed",
                    error="Missing document_id in document_data",
                )

            use_llm = self.use_llm_config.get("document_processing", True)

            # Initialize document service with LLM flag from workflow config
            from app.services.document_service import DocumentService

            doc_service = DocumentService(
                use_llm_document_processing=self.use_llm_config.get(
                    "document_processing", True
                )
            )
            await doc_service.initialize()

            # Fall back to processing and persisting
            summary = await doc_service.process_document_by_id(document_id=document_id)

            if not summary or not summary.get("success"):
                error_msg = (
                    summary.get("error")
                    if isinstance(summary, dict)
                    else "Processing failed"
                )
                return update_state_step(
                    state,
                    "document_processing_failed",
                    error=error_msg,
                )

            extracted_text = summary.get("full_text") or summary.get(
                "extracted_text", ""
            )
            extraction_method = summary.get("extraction_method", "unknown")
            extraction_confidence = summary.get("extraction_confidence", 0.0)

            # Text quality assessment (keep consistent behavior)
            if self.enable_quality_checks and extracted_text:
                text_quality = self._assess_text_quality(extracted_text)
            else:
                text_quality = {"score": 0.8, "issues": []}

            # Validate extracted text quality
            if not extracted_text or len(extracted_text.strip()) < 100:
                return update_state_step(
                    state,
                    "document_processing_failed",
                    error="Insufficient text content extracted from document",
                )

            # Update confidence scores
            if "confidence_scores" not in state:
                state["confidence_scores"] = {}
            state["confidence_scores"]["document_processing"] = (
                extraction_confidence * text_quality["score"]
            )

            # Update state with extracted text and enhanced metadata
            updated_data = {
                "document_metadata": {
                    "full_text": extracted_text,
                    "extraction_method": extraction_method,
                    "extraction_confidence": extraction_confidence,
                    "text_quality": text_quality,
                    "character_count": len(extracted_text),
                    "total_word_count": len(extracted_text.split()),
                    "processing_timestamp": summary.get(
                        "processing_timestamp", datetime.now(UTC).isoformat()
                    ),
                    "enhanced_processing": True,
                    "llm_used": summary.get("llm_used", False),
                },
                "parsing_status": ProcessingStatus.COMPLETED,
            }

            logger.debug(
                f"Enhanced document processing completed: {len(extracted_text)} chars extracted (LLM: {use_llm})"
            )
            return update_state_step(state, "document_processed", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced document processing failed: {e}")
            return update_state_step(
                state,
                "document_processing_failed",
                error=f"Enhanced document processing failed: {str(e)}",
            )

    async def _analyze_compliance_with_llm(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Analyze compliance using LLM with template system"""
        try:
            # Use PromptManager with compliance_check template
            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "extracted_text": "",  # Required by service mapping - not used in this template but required
                    "australian_state": australian_state,
                    "contract_terms": contract_terms,
                    "contract_type": "property_contract",
                    "user_type": "general",  # Required by service mapping - default value
                    "user_experience_level": "intermediate",  # Required by service mapping - default value
                    "analysis_type": "compliance_check",
                    "user_experience": "intermediate",  # Keep existing for template compatibility
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="analysis/compliance_check",
                context=context,
                service_name="contract_analysis_workflow",
            )

            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            try:
                import json

                compliance_result = json.loads(llm_response)
                return compliance_result
            except json.JSONDecodeError:
                # Fallback to rule-based analysis
                return self._analyze_compliance_rule_based(
                    contract_terms, australian_state
                )

        except Exception as e:
            if not self.enable_fallbacks:
                logger.error(
                    f"LLM compliance analysis template failed and fallbacks disabled: {e}"
                )
                raise e

            logger.warning(f"LLM compliance analysis template failed: {e}")
            # Try fallback prompt method
            try:
                fallback_prompt = self._create_compliance_fallback_prompt(
                    contract_terms, australian_state
                )
                llm_response = await self._generate_content_with_fallback(
                    fallback_prompt, use_gemini_fallback=True
                )

                compliance_result = json.loads(llm_response)
                return compliance_result
            except Exception as fallback_error:
                logger.warning(
                    f"LLM compliance analysis fallback failed: {fallback_error}"
                )
                # Final fallback to rule-based analysis
                return self._analyze_compliance_rule_based(
                    contract_terms, australian_state
                )

    def _analyze_compliance_rule_based(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Analyze compliance using rule-based methods"""
        try:
            compliance_confidence = 0.0
            compliance_components = 0

            # Validate cooling-off period
            try:
                cooling_off_result = validate_cooling_off_period.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )
                compliance_confidence += 0.9
                compliance_components += 1
            except Exception as e:
                logger.warning(f"Cooling-off validation failed: {e}")
                cooling_off_result = {
                    "compliant": False,
                    "error": f"Cooling-off validation failed: {str(e)}",
                    "warnings": ["Unable to validate cooling-off period"],
                }

            # Calculate stamp duty
            stamp_duty_result = None
            purchase_price = contract_terms.get("purchase_price", 0)
            if purchase_price > 0:
                try:
                    stamp_duty_result = calculate_stamp_duty.invoke(
                        {
                            "purchase_price": purchase_price,
                            "state": australian_state,
                            "is_first_home": False,
                            "is_foreign_buyer": False,
                        }
                    )
                    compliance_confidence += 0.95
                    compliance_components += 1
                except Exception as e:
                    logger.warning(f"Stamp duty calculation failed: {e}")
                    stamp_duty_result = {
                        "error": f"Stamp duty calculation failed: {str(e)}",
                        "total_duty": 0,
                        "state": australian_state,
                    }

            # Analyze special conditions
            try:
                special_conditions_result = analyze_special_conditions.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )
                compliance_confidence += 0.8
                compliance_components += 1
            except Exception as e:
                logger.warning(f"Special conditions analysis failed: {e}")
                special_conditions_result = {
                    "error": f"Special conditions analysis failed: {str(e)}",
                    "conditions": [],
                }

            # Calculate average compliance confidence
            if compliance_components > 0:
                compliance_confidence = compliance_confidence / compliance_components
            else:
                compliance_confidence = 0.5

            # Compile compliance check
            compliance_check = {
                "state_compliance": cooling_off_result.get("compliant", False),
                "cooling_off_validation": cooling_off_result,
                "stamp_duty_calculation": stamp_duty_result,
                "special_conditions_analysis": special_conditions_result,
                "compliance_issues": [],
                "warnings": cooling_off_result.get("warnings", []),
                "compliance_confidence": compliance_confidence,
                "enhanced_analysis": False,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            # Add compliance issues
            if not cooling_off_result.get("compliant", False):
                compliance_check["compliance_issues"].append(
                    "Cooling-off period non-compliant"
                )

            if stamp_duty_result and stamp_duty_result.get("error"):
                compliance_check["compliance_issues"].append(
                    "Stamp duty calculation incomplete"
                )

            return compliance_check

        except Exception as e:
            logger.error(f"Rule-based compliance analysis failed: {e}")
            return {
                "state_compliance": False,
                "compliance_issues": [f"Compliance analysis failed: {str(e)}"],
                "compliance_confidence": 0.3,
                "enhanced_analysis": False,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

    async def _assess_risks_with_llm(
        self,
        contract_terms: Dict[str, Any],
        compliance_check: Dict[str, Any],
        australian_state: str,
    ) -> Dict[str, Any]:
        """Assess contract risks using LLM with contract_risk_assessment.md template"""
        try:
            # Create enhanced context for risk assessment
            risk_context = PromptContext(
                context_type=ContextType.CONTRACT_ANALYSIS,
                variables={
                    "extracted_text": "",  # Required by service mapping - not used in this template but required
                    "australian_state": australian_state,
                    "contract_type": "purchase_agreement",
                    "user_type": "general",  # Required by service mapping - default value
                    "user_experience_level": "intermediate",  # Required by service mapping - default value
                    "user_experience": "novice",  # Keep existing for template compatibility
                    "contract_terms": contract_terms,
                    "compliance_check": compliance_check,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use the contract_risk_assessment.md template
            try:
                rendered_prompt = await self.prompt_manager.render(
                    template_name="workflow/contract_risk_assessment",
                    context=risk_context,
                    service_name="contract_analysis_workflow",
                )
                logger.debug("Contract risk assessment prompt rendered successfully")
            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                if not self.enable_fallbacks:
                    logger.error(f"Prompt manager failed and fallbacks disabled: {e}")
                    raise e

                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to hardcoded prompt
                rendered_prompt = self._create_risk_assessment_fallback_prompt(
                    contract_terms, compliance_check, australian_state
                )

            # Get LLM response using client architecture
            system_message = "You are an expert Australian property lawyer specializing in risk assessment."
            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, system_message, use_gemini_fallback=True
            )

            try:
                import json

                risk_result = json.loads(llm_response)
                return risk_result
            except json.JSONDecodeError as json_error:
                # Log the raw response for debugging
                logger.error(
                    f"JSON parsing failed for risk assessment. Raw response (first 500 chars): {llm_response[:500]}"
                )
                logger.error(f"JSON decode error: {json_error}")

                if not self.enable_fallbacks:
                    logger.error("JSON parsing failed and fallbacks disabled")
                    raise ValueError("Failed to parse LLM risk assessment response")

                # Fallback to rule-based analysis
                logger.warning(
                    "Falling back to rule-based risk assessment due to JSON parsing failure"
                )
                return self._assess_risks_rule_based(contract_terms, compliance_check)

        except Exception as e:
            if not self.enable_fallbacks:
                logger.error(f"LLM risk assessment failed and fallbacks disabled: {e}")
                raise e

            logger.warning(f"LLM risk assessment failed: {e}")
            # Fallback to rule-based analysis
            return self._assess_risks_rule_based(contract_terms, compliance_check)

    def _assess_risks_rule_based(
        self, contract_terms: Dict[str, Any], compliance_check: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess contract risks using rule-based methods"""
        try:
            # Use existing fallback risk analysis
            risk_analysis = self._fallback_risk_analysis(
                contract_terms, compliance_check
            )

            # Ensure the structure matches the expected format
            if isinstance(risk_analysis, dict):
                return {
                    "overall_risk_score": risk_analysis.get("overall_risk_score", 5.0),
                    "risk_factors": risk_analysis.get("risk_factors", []),
                    "risk_summary": risk_analysis.get(
                        "risk_summary", "Risk assessment completed"
                    ),
                    "confidence_level": risk_analysis.get("confidence_level", 0.5),
                    "critical_issues": risk_analysis.get("critical_issues", []),
                    "state_specific_risks": risk_analysis.get(
                        "state_specific_risks", []
                    ),
                }
            else:
                return {
                    "overall_risk_score": 5.0,
                    "risk_factors": [],
                    "risk_summary": "Risk assessment completed using rule-based methods",
                    "confidence_level": 0.5,
                    "critical_issues": [],
                    "state_specific_risks": [],
                }

        except Exception as e:
            logger.error(f"Rule-based risk assessment failed: {e}")
            return {
                "overall_risk_score": 5.0,
                "risk_factors": [],
                "risk_summary": f"Risk assessment failed: {str(e)}",
                "confidence_level": 0.3,
                "critical_issues": [f"Risk assessment failed: {str(e)}"],
                "state_specific_risks": [],
            }

    async def _generate_recommendations_with_llm(
        self, state: RealEstateAgentState
    ) -> List[Dict[str, Any]]:
        """Generate recommendations using LLM with contract_recommendations.md template"""
        try:
            # Create enhanced context for recommendations
            recommendations_context = PromptContext(
                context_type=ContextType.CONTRACT_ANALYSIS,
                variables={
                    "extracted_text": state.get(
                        "document_text", ""
                    ),  # Required by service mapping
                    "australian_state": state.get("australian_state", "NSW"),
                    "user_type": state.get("user_type", "buyer"),
                    "user_experience_level": "intermediate",  # Required by service mapping - default value
                    "user_experience": state.get(
                        "user_experience", "novice"
                    ),  # Keep existing for template compatibility
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "risk_assessment": state.get("risk_analysis", {}),
                    "compliance_check": state.get("compliance_check", {}),
                    "contract_terms": state.get("contract_terms", {}),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use the contract_recommendations.md template
            try:
                rendered_prompt = await self.prompt_manager.render(
                    template_name="workflow/contract_recommendations",
                    context=recommendations_context,
                    service_name="contract_analysis_workflow",
                )
                logger.debug("Contract recommendations prompt rendered successfully")
            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                if not self.enable_fallbacks:
                    logger.error(f"Prompt manager failed and fallbacks disabled: {e}")
                    raise e

                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to hardcoded prompt (previous implementation)
                rendered_prompt = self._create_recommendations_fallback_prompt(state)

            # Get LLM response using client architecture
            system_message = "You are an expert Australian property advisor providing actionable recommendations."
            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, system_message, use_gemini_fallback=True
            )

            try:
                import json

                recommendations_result = json.loads(llm_response)
                return recommendations_result.get("recommendations", [])
            except json.JSONDecodeError:
                if not self.enable_fallbacks:
                    logger.error("JSON parsing failed and fallbacks disabled")
                    raise ValueError("Failed to parse LLM recommendations response")

                # Fallback to rule-based recommendations
                return self._generate_recommendations_rule_based(state)

        except Exception as e:
            if not self.enable_fallbacks:
                logger.error(
                    f"LLM recommendations generation failed and fallbacks disabled: {e}"
                )
                raise e

            logger.warning(f"LLM recommendations generation failed: {e}")
            # Fallback to rule-based recommendations
            return self._generate_recommendations_rule_based(state)

    def _generate_recommendations_rule_based(
        self, state: RealEstateAgentState
    ) -> List[Dict[str, Any]]:
        """Generate recommendations using rule-based methods"""
        try:
            # Use existing fallback recommendations
            recommendations = self._fallback_recommendations(state)

            # Ensure the structure matches the expected format
            if isinstance(recommendations, list):
                return recommendations
            else:
                return [
                    {
                        "priority": "medium",
                        "category": "general",
                        "recommendation": "Consider professional legal review of this contract",
                        "action_required": True,
                        "australian_context": "Standard recommendation for property contracts",
                        "estimated_cost": 500,
                        "timeline": "Before settlement",
                        "legal_basis": "Due diligence requirement",
                        "consequences_if_ignored": "May miss critical legal issues",
                    }
                ]

        except Exception as e:
            logger.error(f"Rule-based recommendations generation failed: {e}")
            return [
                {
                    "priority": "high",
                    "category": "general",
                    "recommendation": f"Recommendations generation failed: {str(e)}",
                    "action_required": True,
                    "australian_context": "Error in recommendations generation",
                    "estimated_cost": 0,
                    "timeline": "Immediate",
                    "legal_basis": "Error handling",
                    "consequences_if_ignored": "No recommendations available",
                }
            ]

    async def _validate_document_quality_with_llm(
        self, document_text: str, document_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate document quality using LLM with template system"""
        try:
            # Use PromptManager with document_quality_validation template
            context = PromptContext(
                context_type=ContextType.ANALYSIS,
                variables={
                    "document_text": document_text,
                    "extracted_text": document_text,  # Required by service mapping
                    "document_metadata": document_metadata,
                    "document_type": "property_contract",
                    "contract_type": "property_contract",  # Required by service mapping
                    "australian_state": document_metadata.get("state", "NSW"),
                    "user_type": "general",  # Required by service mapping - default value
                    "user_experience_level": "intermediate",  # Required by service mapping - default value
                    "extraction_method": document_metadata.get(
                        "extraction_method", "ocr"
                    ),
                    # Ensure templates that expect analysis timestamp can render
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            rendered_prompt = await self.prompt_manager.render(
                template_name="validation/document_quality_validation",
                context=context,
                service_name="contract_analysis_workflow",
            )

            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, use_gemini_fallback=True
            )

            try:
                import json

                quality_result = json.loads(llm_response)
                return quality_result
            except json.JSONDecodeError:
                # Fallback to rule-based validation
                quality_metrics = validate_document_quality.invoke(
                    {
                        "document_text": document_text,
                        "document_metadata": document_metadata,
                    }
                )
                return quality_metrics.dict()

        except Exception as e:
            if not self.enable_fallbacks:
                logger.error(
                    f"LLM document quality validation template failed and fallbacks disabled: {e}"
                )
                raise e

            logger.warning(f"LLM document quality validation template failed: {e}")
            # Try fallback prompt method
            try:
                fallback_prompt = self._create_document_quality_fallback_prompt(
                    document_text, document_metadata
                )
                llm_response = await self._generate_content_with_fallback(
                    fallback_prompt, use_gemini_fallback=True
                )

                quality_result = json.loads(llm_response)
                return quality_result
            except Exception as fallback_error:
                logger.warning(
                    f"LLM document quality validation fallback failed: {fallback_error}"
                )
                # Final fallback to rule-based validation
                quality_metrics = validate_document_quality.invoke(
                    {
                        "document_text": document_text,
                        "document_metadata": document_metadata,
                    }
                )
                return quality_metrics.dict()

    async def _validate_terms_completeness_with_llm(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> Dict[str, Any]:
        """Validate contract terms completeness using LLM with validation template"""
        try:
            # Create enhanced context for terms completeness validation
            validation_context = PromptContext(
                context_type=ContextType.CONTRACT_ANALYSIS,
                variables={
                    "extracted_text": "",  # Required by service mapping - not used in this template but required
                    "australian_state": australian_state,
                    "contract_type": "purchase_agreement",
                    "user_type": "general",  # Required by service mapping - default value
                    "user_experience_level": "intermediate",  # Required by service mapping - default value
                    "user_experience": "novice",  # Keep existing for template compatibility
                    "contract_terms": contract_terms,
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use the terms_completeness_validation.md template
            try:
                rendered_prompt = await self.prompt_manager.render(
                    template_name="validation/terms_completeness_validation",
                    context=validation_context,
                    service_name="contract_analysis_workflow",
                )
                logger.debug(
                    "Terms completeness validation prompt rendered successfully"
                )
            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                if not self.enable_fallbacks:
                    logger.error(f"Prompt manager failed and fallbacks disabled: {e}")
                    raise e

                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to hardcoded prompt
                rendered_prompt = self._create_terms_validation_fallback_prompt(
                    contract_terms, australian_state
                )

            system_message = "You are an expert Australian property lawyer validating contract terms completeness."

            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, system_message, use_gemini_fallback=True
            )

            try:
                import json

                validation_result = json.loads(llm_response)
                return validation_result
            except json.JSONDecodeError:
                if not self.enable_fallbacks:
                    logger.error("JSON parsing failed and fallbacks disabled")
                    raise ValueError("Failed to parse LLM terms validation response")

                # Fallback to rule-based validation
                validation_result = validate_contract_terms_completeness.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )
                return validation_result.dict()

        except Exception as e:
            if not self.enable_fallbacks:
                logger.error(f"LLM terms validation failed and fallbacks disabled: {e}")
                raise e

            logger.warning(f"LLM terms validation failed: {e}")
            # Fallback to rule-based validation
            validation_result = validate_contract_terms_completeness.invoke(
                {"contract_terms": contract_terms, "state": australian_state}
            )
            return validation_result.dict()

    async def _validate_final_output_with_llm(
        self, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Validate final output using LLM with final output validation template"""
        try:
            # Create enhanced context for final output validation
            validation_context = PromptContext(
                context_type=ContextType.CONTRACT_ANALYSIS,
                variables={
                    "extracted_text": state.get(
                        "document_text", ""
                    ),  # Required by service mapping
                    "australian_state": state.get("australian_state", "NSW"),
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                    "user_type": "general",  # Required by service mapping - default value
                    "user_experience_level": "intermediate",  # Required by service mapping - default value
                    "analysis_type": "comprehensive",
                    "user_experience": state.get(
                        "user_experience", "novice"
                    ),  # Keep existing for template compatibility
                    "risk_assessment": state.get("risk_analysis", {}),
                    "compliance_check": state.get("compliance_check", {}),
                    "recommendations": state.get("recommendations", []),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                },
            )

            # Use the final_output_validation.md template
            try:
                rendered_prompt = await self.prompt_manager.render(
                    template_name="validation/final_output_validation",
                    context=validation_context,
                    service_name="contract_analysis_workflow",
                )
                logger.debug("Final output validation prompt rendered successfully")
            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                if not self.enable_fallbacks:
                    logger.error(f"Prompt manager failed and fallbacks disabled: {e}")
                    raise e

                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to hardcoded prompt
                rendered_prompt = self._create_final_validation_fallback_prompt(state)

            # Get LLM response using client architecture
            system_message = "You are an expert Australian property lawyer validating final analysis output."
            llm_response = await self._generate_content_with_fallback(
                rendered_prompt, system_message, use_gemini_fallback=True
            )

            try:
                import json

                validation_result = json.loads(llm_response)
                return validation_result
            except json.JSONDecodeError:
                if not self.enable_fallbacks:
                    logger.error("JSON parsing failed and fallbacks disabled")
                    raise ValueError("Failed to parse LLM final validation response")

                # Fallback to rule-based validation
                return self._validate_final_output_rule_based(state)

        except Exception as e:
            if not self.enable_fallbacks:
                logger.error(f"LLM final validation failed and fallbacks disabled: {e}")
                raise e

            logger.warning(f"LLM final validation failed: {e}")
            # Fallback to rule-based validation
            return self._validate_final_output_rule_based(state)

    def _validate_final_output_rule_based(
        self, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Validate final output using rule-based methods"""
        try:
            # Check if all required components are present
            required_components = [
                "risk_analysis",
                "recommendations",
                "compliance_check",
                "contract_terms",
            ]
            missing_components = [
                comp for comp in required_components if not state.get(comp)
            ]

            # Calculate validation score based on presence and quality
            validation_score = 0.5  # Base score

            if not missing_components:
                validation_score += 0.3  # All components present

            if state.get("risk_analysis"):
                validation_score += 0.1  # Risk analysis present

            if (
                state.get("recommendations")
                and len(state.get("recommendations", [])) > 0
            ):
                validation_score += 0.1  # Recommendations present

            validation_score = min(1.0, validation_score)

            validation_result = {
                "validation_score": validation_score,
                "validation_passed": validation_score >= 0.7,
                "issues_found": missing_components,
                "recommendations": [],
                "metadata": {
                    "validation_method": "rule_based",
                    "validation_timestamp": datetime.now(UTC).isoformat(),
                },
            }

            return validation_result

        except Exception as e:
            logger.error(f"Rule-based final validation failed: {e}")
            return {
                "validation_score": 0.3,
                "validation_passed": False,
                "issues_found": [f"Validation failed: {str(e)}"],
                "recommendations": [],
                "metadata": {
                    "validation_method": "rule_based",
                    "validation_timestamp": datetime.now(UTC).isoformat(),
                },
            }

    def _create_recommendations_fallback_prompt(
        self, state: RealEstateAgentState
    ) -> str:
        """Create fallback recommendations prompt when template fails"""
        return f"""
        Generate actionable recommendations for this Australian property contract analysis:
        
        Contract Terms:
        {json.dumps(state.get("contract_terms", {}), indent=2)}
        
        Risk Analysis:
        {json.dumps(state.get("risk_analysis", {}), indent=2)}
        
        Compliance Check:
        {json.dumps(state.get("compliance_check", {}), indent=2)}
        
        User Context:
        - Experience: {state.get("user_experience", "novice")}
        - State: {state.get("australian_state", "NSW")}
        - Contract Type: {state.get("contract_type", "purchase_agreement")}
        
        Generate recommendations across these categories:
        1. Legal recommendations (immediate actions, professional review needs)
        2. Financial recommendations (cost management, optimization strategies)
        3. Practical recommendations (timeline planning, due diligence steps)
        4. Compliance recommendations (state law compliance, mandatory actions)
        
        Return a JSON response with this structure:
        {{
            "recommendations": [
                {{
                    "priority": "low/medium/high",
                    "category": "legal/financial/practical/compliance",
                    "recommendation": "string",
                    "action_required": true/false,
                    "australian_context": "string",
                    "estimated_cost": 0,
                    "timeline": "string",
                    "legal_basis": "string",
                    "consequences_if_ignored": "string"
                }}
            ],
            "executive_summary": "string",
            "immediate_actions": [],
            "next_steps": []
        }}
        """

    def _create_risk_assessment_fallback_prompt(
        self,
        contract_terms: Dict[str, Any],
        compliance_check: Dict[str, Any],
        australian_state: str,
    ) -> str:
        """Create fallback risk assessment prompt when template fails"""
        return f"""
        Assess the risks in this Australian property contract for {australian_state}:
        
        Contract Terms:
        {json.dumps(contract_terms, indent=2)}
        
        Compliance Check:
        {json.dumps(compliance_check, indent=2)}
        
        Evaluate risks across these dimensions:
        1. Financial risks (price, financing, costs)
        2. Legal risks (compliance, enforceability)
        3. Property risks (condition, location, title)
        4. Transaction risks (settlement, timing)
        5. State-specific risks ({australian_state} regulations)
        
        Return a JSON response with this structure:
        {{
            "overall_risk_score": 5.5,
            "risk_factors": [
                {{
                    "factor": "string",
                    "severity": "low/medium/high/critical",
                    "description": "string",
                    "impact": "string",
                    "australian_specific": true/false,
                    "mitigation_suggestions": []
                }}
            ],
            "risk_summary": "string",
            "confidence_level": 0.85,
            "critical_issues": [],
            "state_specific_risks": []
        }}
        """

    def _create_terms_validation_fallback_prompt(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> str:
        """Create fallback terms validation prompt when template fails"""
        return f"""
        Validate the completeness of contract terms for {australian_state}:
        
        Contract Terms:
        {json.dumps(contract_terms, indent=2)}
        
        Evaluate the completeness of contract terms across these areas:
        1. Essential terms (parties, property, price, settlement)
        2. Financial terms (deposit, balance, adjustments)
        3. Conditions and warranties (finance, building/pest, cooling-off)
        4. Special conditions and clauses
        5. State-specific requirements ({australian_state})
        
        Return a JSON response with this structure:
        {{
            "validation_score": 0.85,
            "terms_validated": {{
                "parties": true/false,
                "property": true/false,
                "price": true/false,
                "settlement": true/false,
                "conditions": true/false
            }},
            "missing_mandatory_terms": [],
            "incomplete_terms": [],
            "validation_confidence": 0.85,
            "state_specific_requirements": {{}},
            "recommendations": []
        }}
        """

    def _create_final_validation_fallback_prompt(
        self, state: RealEstateAgentState
    ) -> str:
        """Create fallback final validation prompt when template fails"""
        australian_state = state.get("australian_state", "NSW")
        risk_assessment = state.get("risk_analysis", {})
        compliance_check = state.get("compliance_check", {})
        recommendations = state.get("recommendations", [])

        return f"""
        Conduct final validation of complete contract analysis for {australian_state}:
        
        Risk Assessment Results:
        {json.dumps(risk_assessment, indent=2)}
        
        Compliance Check Results:
        {json.dumps(compliance_check, indent=2)}
        
        Recommendations:
        {json.dumps(recommendations, indent=2)}
        
        Validate the analysis across these dimensions:
        1. Completeness - all essential analysis components present
        2. Consistency - internal consistency across analysis components
        3. Accuracy - legal and factual accuracy of analysis
        4. Utility - practical value and actionability for the user
        5. State compliance - adherence to {australian_state} legal requirements
        
        Return a JSON response with this structure:
        {{
            "validation_score": 0.85,
            "validation_passed": true/false,
            "component_validation": {{
                "risk_assessment_quality": 0.85,
                "compliance_analysis_quality": 0.85,
                "recommendations_quality": 0.85,
                "consistency_score": 0.85,
                "completeness_score": 0.85
            }},
            "issues_found": [],
            "consistency_checks": {{
                "risk_recommendation_alignment": true/false,
                "compliance_risk_correlation": true/false,
                "financial_integration": true/false,
                "timeline_coordination": true/false,
                "state_law_consistency": true/false
            }},
            "delivery_assessment": {{
                "ready_for_delivery": true/false,
                "confidence_level": "high/medium/low",
                "recommended_action": "deliver/improve/rework"
            }},
            "validation_summary": "string",
            "improvement_recommendations": []
        }}
        """

    def _create_compliance_fallback_prompt(
        self, contract_terms: Dict[str, Any], australian_state: str
    ) -> str:
        """Create fallback compliance analysis prompt when template fails"""
        return f"""
        Analyze the compliance of this Australian property contract for {australian_state}:
        
        Contract Terms:
        {json.dumps(contract_terms, indent=2)}
        
        Evaluate compliance across these areas:
        1. Cooling-off period compliance
        2. Stamp duty requirements  
        3. Special conditions validity
        4. State-specific requirements
        5. Consumer protection compliance
        
        Return a JSON response with this structure:
        {{
            "state_compliance": true/false,
            "cooling_off_validation": {{
                "compliant": true/false,
                "period_days": 5,
                "warnings": []
            }},
            "stamp_duty_calculation": {{
                "total_duty": 0,
                "calculation_basis": "string",
                "concessions_applied": []
            }},
            "special_conditions_analysis": {{
                "conditions": [],
                "validity": true/false
            }},
            "compliance_issues": [],
            "warnings": [],
            "compliance_confidence": 0.85
        }}
        """

    def _create_document_quality_fallback_prompt(
        self, document_text: str, document_metadata: Dict[str, Any]
    ) -> str:
        """Create fallback document quality validation prompt when template fails"""
        return f"""
        Assess the quality of this document for property contract analysis:
        
        Document Text (first 2000 chars):
        {document_text[:2000]}...
        
        Document Metadata:
        {json.dumps(document_metadata, indent=2)}
        
        Evaluate the document quality across these dimensions:
        1. Text quality (0-1): Clarity, readability, completeness
        2. Completeness (0-1): How complete is the document content  
        3. Readability (0-1): How easy is it to read and understand
        4. Key terms coverage (0-1): Coverage of important contract terms
        5. Extraction confidence (0-1): Confidence in text extraction
        
        Return a JSON response with this structure:
        {{
            "text_quality_score": 0.85,
            "completeness_score": 0.9,
            "readability_score": 0.8,
            "key_terms_coverage": 0.75,
            "extraction_confidence": 0.9,
            "overall_quality_score": 0.82,
            "issues_identified": [
                {{
                    "issue": "specific quality issue",
                    "severity": "critical|major|minor|warning",
                    "description": "detailed explanation"
                }}
            ],
            "improvement_suggestions": ["suggestion 1", "suggestion 2"],
            "suitability_assessment": {{
                "automated_analysis_suitable": true/false,
                "manual_review_required": true/false,
                "confidence_level": "high|medium|low"
            }}
        }}
        """
