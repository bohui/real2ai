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
from app.models.workflow_outputs import (
    RiskAnalysisOutput,
    RecommendationsOutput,
    DocumentQualityMetrics,
    WorkflowValidationOutput,
    ContractTermsValidationOutput,
    ContractTermsOutput,
    ComplianceAnalysisOutput,
)

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
from app.core.prompts.output_parser import create_parser

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
    ContractTermsExtractionNode,
    TermsValidationNode,
    # Compliance Analysis
    ComplianceAnalysisNode,
    DiagramAnalysisNode,
    # Risk Assessment
    RiskAssessmentNode,
    RecommendationsGenerationNode,
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

        # No longer using persistent background loops - running everything in current loop

        # Initialize node instances
        self._initialize_nodes()

        # Create LangGraph-compatible node functions
        self._create_node_functions()

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
        self.contract_terms_extraction_node = ContractTermsExtractionNode(self)
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
            "contract_terms_extraction": self.contract_terms_extraction_node,
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
                raise Exception(
                    "No AI clients could be initialized. Both OpenAI and Gemini failed."
                )

            # Set clients in all nodes that need them
            for node_name, node in self.nodes.items():
                if hasattr(node, "openai_client"):
                    node.openai_client = self.openai_client
                if hasattr(node, "gemini_client"):
                    node.gemini_client = self.gemini_client

                # Log client availability for each node
                logger.debug(
                    f"Node {node_name}: OpenAI={self.openai_client is not None}, Gemini={self.gemini_client is not None}"
                )

            logger.info(
                f"Workflow clients initialized successfully - OpenAI: {self.openai_client is not None}, Gemini: {self.gemini_client is not None}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize workflow clients: {e}")
            raise

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with node-based architecture."""
        workflow = StateGraph(RealEstateAgentState)

        # Add all node execution methods to the workflow using standalone functions
        workflow.add_node("validate_input", self._node_functions["validate_input"])
        workflow.add_node("process_document", self._node_functions["process_document"])
        workflow.add_node("extract_terms", self._node_functions["extract_contract_terms"])
        workflow.add_node("analyze_compliance", self._node_functions["analyze_australian_compliance"])
        workflow.add_node("analyze_contract_diagrams", self._node_functions["analyze_contract_diagrams"])
        workflow.add_node("assess_risks", self._node_functions["assess_contract_risks"])
        workflow.add_node("generate_recommendations", self._node_functions["generate_recommendations"])
        workflow.add_node("compile_report", self._node_functions["compile_analysis_report"])

        # Add validation nodes if enabled
        if self.enable_validation:
            workflow.add_node(
                "validate_document_quality", self._node_functions["validate_document_quality_step"]
            )
            workflow.add_node(
                "validate_terms_completeness", self._node_functions["validate_terms_completeness_step"]
            )
            workflow.add_node("validate_final_output", self._node_functions["validate_final_output_step"])

        # Add utility nodes
        workflow.add_node("handle_error", self._node_functions["handle_processing_error"])
        workflow.add_node("retry_processing", self._node_functions["retry_failed_step"])

        # Set entry point
        workflow.set_entry_point("validate_input")

        # Define workflow edges based on validation configuration
        if self.enable_validation:
            # Full validation workflow
            workflow.add_edge("validate_input", "process_document")
            workflow.add_edge("process_document", "validate_document_quality")
            workflow.add_edge("validate_document_quality", "extract_terms")
            workflow.add_edge("extract_terms", "validate_terms_completeness")
            workflow.add_edge("validate_terms_completeness", "analyze_compliance")
            workflow.add_edge("analyze_compliance", "analyze_contract_diagrams")
            workflow.add_edge("analyze_contract_diagrams", "assess_risks")
            workflow.add_edge("assess_risks", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "validate_final_output")
            workflow.add_edge("validate_final_output", "compile_report")
        else:
            # Standard workflow without intermediate validation
            workflow.add_edge("validate_input", "process_document")
            workflow.add_edge("process_document", "extract_terms")
            workflow.add_edge("extract_terms", "analyze_compliance")
            workflow.add_edge("analyze_compliance", "analyze_contract_diagrams")
            workflow.add_edge("analyze_contract_diagrams", "assess_risks")
            workflow.add_edge("assess_risks", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "compile_report")

        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "process_document",
            self.check_processing_success,
            {
                "success": (
                    "validate_document_quality"
                    if self.enable_validation
                    else "extract_terms"
                ),
                "retry": "retry_processing",
                "error": "handle_error",
            },
        )

        if self.enable_validation:
            workflow.add_conditional_edges(
                "validate_document_quality",
                self.check_document_quality,
                {
                    "quality_passed": "extract_terms",
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

        # Terminal conditions
        workflow.add_edge("compile_report", "__end__")
        workflow.add_edge("handle_error", "__end__")

        return workflow.compile()


    # Node execution methods - async functions for LangGraph compatibility
    # We'll run LangGraph directly in the current event loop using our per-loop registry system

    # Create async wrapper functions that LangGraph can call directly
    # These functions will have the correct signature: async def func(state, config=None)
    
    def _create_node_functions(self):
        """Create async functions with correct signatures for LangGraph."""
        
        @langsmith_trace(name="validate_input", run_type="tool")
        async def validate_input(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute input validation node."""
            return await self.input_validation_node.execute(state)

        async def process_document(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute document processing node."""
            return await self.document_processing_node.execute(state)

        @langsmith_trace(name="validate_document_quality", run_type="tool")
        async def validate_document_quality_step(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute document quality validation node."""
            return await self.document_quality_validation_node.execute(state)

        @langsmith_trace(name="extract_contract_terms", run_type="chain")
        async def extract_contract_terms(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute contract terms extraction node."""
            return await self.contract_terms_extraction_node.execute(state)

        @langsmith_trace(name="validate_terms_completeness", run_type="tool")
        async def validate_terms_completeness_step(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute terms validation node."""
            return await self.terms_validation_node.execute(state)

        @langsmith_trace(name="analyze_australian_compliance", run_type="chain")
        async def analyze_australian_compliance(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute compliance analysis node."""
            return await self.compliance_analysis_node.execute(state)

        @langsmith_trace(name="analyze_contract_diagrams", run_type="chain")
        async def analyze_contract_diagrams(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute diagram analysis node."""
            return await self.diagram_analysis_node.execute(state)

        @langsmith_trace(name="assess_contract_risks", run_type="chain")
        async def assess_contract_risks(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute risk assessment node."""
            return await self.risk_assessment_node.execute(state)

        @langsmith_trace(name="generate_recommendations", run_type="chain")
        async def generate_recommendations(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute recommendations generation node."""
            return await self.recommendations_generation_node.execute(state)

        @langsmith_trace(name="validate_final_output", run_type="tool")
        async def validate_final_output_step(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute final validation node."""
            return await self.final_validation_node.execute(state)

        @langsmith_trace(name="compile_analysis_report", run_type="chain")
        async def compile_analysis_report(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute report compilation node."""
            return await self.report_compilation_node.execute(state)

        @langsmith_trace(name="handle_processing_error", run_type="tool")
        async def handle_processing_error(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute error handling node."""
            return await self.error_handling_node.execute(state)

        @langsmith_trace(name="retry_failed_step", run_type="tool")
        async def retry_failed_step(state: RealEstateAgentState, config=None) -> RealEstateAgentState:
            """Execute retry processing node."""
            return await self.retry_processing_node.execute(state)
        
        # Store these functions so we can reference them in workflow creation
        self._node_functions = {
            'validate_input': validate_input,
            'process_document': process_document, 
            'validate_document_quality_step': validate_document_quality_step,
            'extract_contract_terms': extract_contract_terms,
            'validate_terms_completeness_step': validate_terms_completeness_step,
            'analyze_australian_compliance': analyze_australian_compliance,
            'analyze_contract_diagrams': analyze_contract_diagrams,
            'assess_contract_risks': assess_contract_risks,
            'generate_recommendations': generate_recommendations,
            'validate_final_output_step': validate_final_output_step,
            'compile_analysis_report': compile_analysis_report,
            'handle_processing_error': handle_processing_error,
            'retry_failed_step': retry_failed_step,
        }

    # Conditional edge check methods (kept simple for orchestration)
    def check_processing_success(self, state: RealEstateAgentState) -> str:
        """Check if document processing was successful."""
        if state.get("parsing_status") == ProcessingStatus.COMPLETED:
            return "success"
        elif state.get("retry_attempts", 0) < 3:
            return "retry"
        else:
            return "error"

    def check_document_quality(self, state: RealEstateAgentState) -> str:
        """Check document quality validation results."""
        quality_metrics = state.get("document_quality_metrics", {})
        overall_confidence = quality_metrics.get("overall_confidence", 0)

        if overall_confidence >= 0.6:
            return "quality_passed"
        elif state.get("retry_attempts", 0) < 2:
            return "retry"
        else:
            return "error"

    def check_extraction_quality(self, state: RealEstateAgentState) -> str:
        """Check contract terms extraction quality."""
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

    @langsmith_trace(name="contract_analysis_workflow", run_type="chain")
    async def analyze_contract(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """Main analysis method using per-loop registry system for safety."""
        try:
            # Update metrics
            self._metrics["total_analyses"] += 1
            start_time = datetime.now(UTC)

            # Execute LangGraph workflow directly in current event loop
            # Our per-loop registry system and @langgraph_safe_task decorator 
            # provide all the cross-loop protection we need
            logger.info(f"[WORKFLOW] Starting LangGraph workflow execution in current event loop")
            result = await self.workflow.ainvoke(state)
            logger.info(f"[WORKFLOW] LangGraph workflow completed successfully")

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
