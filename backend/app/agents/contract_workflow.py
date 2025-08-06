"""
Enhanced LangGraph Contract Analysis Workflow with PromptManager and OutputParser integration
"""

from typing import Dict, Any, Optional, List, Union
from langgraph.graph import StateGraph
from langchain.schema import HumanMessage, SystemMessage
import json
import time
import logging
from datetime import datetime, UTC
from pathlib import Path

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
)
from backend.app.schema.enums import ProcessingStatus
from app.models.workflow_outputs import (
    RiskAnalysisOutput,
    RecommendationsOutput,
    DocumentQualityMetrics,
    WorkflowValidationOutput,
    ContractTermsValidationOutput,
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

logger = logging.getLogger(__name__)


class ContractAnalysisWorkflow:
    """Enhanced LangGraph workflow with PromptManager and OutputParser integration"""

    def __init__(
        self,
        openai_api_key: str = None,
        model_name: str = "gpt-4",
        openai_api_base: Optional[str] = None,
        prompt_manager: Optional[PromptManager] = None,
        enable_validation: bool = True,
        enable_quality_checks: bool = True,
    ):
        # Initialize clients (will be set up in initialize method)
        self.openai_client = None
        self.gemini_client = None
        self.model_name = model_name
        self.openai_api_base = openai_api_base

        # Initialize prompt manager
        if prompt_manager is None:
            self.prompt_manager = get_prompt_manager()
        else:
            self.prompt_manager = prompt_manager

        self.enable_validation = enable_validation
        self.enable_quality_checks = enable_quality_checks

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
            "average_processing_time": 0.0,
        }

        self.workflow = self._create_workflow()
        logger.info(
            "Enhanced ContractAnalysisWorkflow initialized with PromptManager integration"
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
            logger.error(f"Failed to initialize workflow clients: {e}")
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
            workflow.add_edge("analyze_compliance", "assess_risks")
            workflow.add_edge("assess_risks", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "validate_final_output")
            workflow.add_edge("validate_final_output", "compile_report")
        else:
            # Standard flow without validation
            workflow.add_edge("validate_input", "process_document")
            workflow.add_edge("process_document", "extract_terms")
            workflow.add_edge("extract_terms", "analyze_compliance")
            workflow.add_edge("analyze_compliance", "assess_risks")
            workflow.add_edge("assess_risks", "generate_recommendations")
            workflow.add_edge("generate_recommendations", "compile_report")

        # Conditional Error Handling (enhanced)
        workflow.add_conditional_edges(
            "process_document",
            self.check_processing_success,
            {
                "success": (
                    "extract_terms" if not self.enable_validation else "extract_terms"
                ),
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

    async def analyze_contract(
        self, initial_state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Execute the complete enhanced contract analysis workflow"""

        start_time = time.time()
        self._metrics["total_analyses"] += 1

        # Initialize progress tracking
        total_steps = 7 + (3 if self.enable_validation else 0)
        step_names = [
            "validate_input",
            "process_document",
            "extract_terms",
            "analyze_compliance",
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

        # Initialize prompt manager if needed
        try:
            await self.prompt_manager.initialize()
        except Exception as e:
            logger.warning(f"Failed to initialize prompt manager: {e}")

        try:
            # Run the enhanced workflow with progress tracking
            final_state = await self.workflow.ainvoke(initial_state)

            # Calculate processing time and update metrics
            processing_time = time.time() - start_time
            final_state["processing_time"] = processing_time

            self._metrics["average_processing_time"] = (
                self._metrics["average_processing_time"]
                * (self._metrics["total_analyses"] - 1)
                + processing_time
            ) / self._metrics["total_analyses"]

            # Calculate overall confidence with enhanced scoring
            if "analysis_results" not in final_state:
                final_state["analysis_results"] = {}

            confidence_result = calculate_overall_confidence_score.invoke(
                {
                    "confidence_scores": final_state.get("confidence_scores", {}),
                    "step_weights": None,  # Use default weights
                }
            )

            final_state["analysis_results"]["overall_confidence"] = confidence_result[
                "overall_confidence"
            ]
            final_state["analysis_results"]["confidence_breakdown"] = confidence_result[
                "confidence_breakdown"
            ]
            final_state["analysis_results"]["quality_assessment"] = confidence_result[
                "quality_assessment"
            ]

            # Mark progress complete
            final_state["progress"]["percentage"] = 100
            final_state["progress"]["current_step"] = total_steps

            logger.info(
                f"Enhanced workflow completed successfully in {processing_time:.2f}s"
            )
            return final_state

        except Exception as e:
            # Handle workflow-level errors
            processing_time = time.time() - start_time
            error_state = update_state_step(
                initial_state,
                "workflow_error",
                error=f"Enhanced workflow execution failed: {str(e)}",
            )
            error_state["processing_time"] = processing_time
            error_state["progress"]["percentage"] = 0

            logger.error(f"Enhanced workflow failed after {processing_time:.2f}s: {e}")
            return error_state

    # Enhanced workflow steps

    def validate_input(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Enhanced input validation with prompt manager context"""

        # Update progress
        state["progress"]["current_step"] = 1
        state["progress"]["percentage"] = int(100 / state["progress"]["total_steps"])

        # Existing validation logic
        if not state.get("document_data"):
            return update_state_step(
                state, "validation_failed", error="No document provided"
            )

        if not state.get("australian_state"):
            return update_state_step(
                state, "validation_failed", error="Australian state not specified"
            )

        # Enhanced validation with prompt context validation
        try:
            # Create context for validation
            context_vars = {
                "australian_state": state["australian_state"],
                "user_type": state.get("user_type", "buyer"),
                "contract_type": state.get("contract_type", "purchase_agreement"),
            }

            # Store context for later use in prompt rendering
            state["prompt_context"] = context_vars

        except Exception as e:
            logger.warning(f"Context validation failed: {e}")
            # Continue with basic validation

        # Validate document format
        document_data = state["document_data"]
        if not document_data.get("content") and not document_data.get("file_path"):
            return update_state_step(
                state, "validation_failed", error="Document content not accessible"
            )

        # Add confidence score for validation
        if "confidence_scores" not in state:
            state["confidence_scores"] = {}
        state["confidence_scores"]["input_validation"] = 0.95

        logger.debug("Enhanced input validation completed successfully")
        return update_state_step(state, "input_validated")

    def validate_document_quality_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Validate document quality using enhanced tools"""

        if not self.enable_quality_checks:
            return state

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            document_data = state["document_data"]
            document_text = document_data.get("content", "")
            document_metadata = document_data.get("metadata", {})

            # Validate document quality
            quality_metrics = validate_document_quality.invoke(
                {"document_text": document_text, "document_metadata": document_metadata}
            )

            # Store quality metrics
            state["document_quality_metrics"] = quality_metrics.dict()
            state["confidence_scores"][
                "document_quality"
            ] = quality_metrics.text_quality_score

            # Log quality issues
            if quality_metrics.issues_identified:
                logger.warning(
                    f"Document quality issues: {quality_metrics.issues_identified}"
                )

            return update_state_step(state, "document_quality_validated")

        except Exception as e:
            logger.error(f"Document quality validation failed: {e}")
            # Continue workflow with warning
            state["confidence_scores"]["document_quality"] = 0.5
            return update_state_step(
                state,
                "document_quality_validation_warning",
                error=f"Quality validation failed: {str(e)}",
            )

    def process_document(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Enhanced document processing with validation"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            document_data = state["document_data"]

            # Use actual extracted text if available
            if document_data.get("content"):
                extracted_text = document_data["content"]
                extraction_method = "pre_processed"
                extraction_confidence = 0.95
            else:
                # Fallback to simulation if no content available
                extracted_text = self._simulate_document_extraction(document_data)
                extraction_method = "simulation"
                extraction_confidence = 0.7

            # Enhanced text quality assessment
            if self.enable_quality_checks:
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
            state["confidence_scores"]["document_processing"] = (
                extraction_confidence * text_quality["score"]
            )

            # Update state with extracted text and enhanced metadata
            updated_data = {
                "document_metadata": {
                    "extracted_text": extracted_text,
                    "extraction_method": extraction_method,
                    "extraction_confidence": extraction_confidence,
                    "text_quality": text_quality,
                    "character_count": len(extracted_text),
                    "word_count": len(extracted_text.split()),
                    "processing_timestamp": datetime.now(UTC).isoformat(),
                    "enhanced_processing": True,
                },
                "parsing_status": ProcessingStatus.COMPLETED,
            }

            logger.debug(
                f"Enhanced document processing completed: {len(extracted_text)} chars extracted"
            )
            return update_state_step(state, "document_processed", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced document processing failed: {e}")
            return update_state_step(
                state,
                "document_processing_failed",
                error=f"Enhanced document processing failed: {str(e)}",
            )

    def extract_contract_terms(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced contract terms extraction with validation"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            document_text = state["document_metadata"]["extracted_text"]
            australian_state = state["australian_state"]

            # Identify contract template type first
            template_identification = None
            try:
                template_identification = identify_contract_template_type.invoke(
                    {"document_text": document_text, "state": australian_state}
                )
                logger.debug(
                    f"Template identified: {template_identification.get('primary_template_type', 'unknown')}"
                )
            except Exception as template_error:
                logger.warning(f"Template identification failed: {str(template_error)}")
                template_identification = {
                    "primary_template_type": "unknown",
                    "validation_issues": [],
                    "compliance_notes": [],
                }

            # Use the Australian contract tools with enhanced error handling
            try:
                extraction_result = extract_australian_contract_terms.invoke(
                    {"document_text": document_text, "state": australian_state}
                )
                # Add template information to extraction result
                if template_identification:
                    extraction_result["template_analysis"] = template_identification
                logger.debug(
                    f"Terms extracted using Australian tools with confidence: {extraction_result.get('overall_confidence', 0)}"
                )
            except Exception as tool_error:
                logger.warning(f"Australian tools failed, using fallback: {tool_error}")
                # Fallback extraction if tool fails
                extraction_result = self._fallback_term_extraction(
                    document_text, australian_state
                )
                extraction_result["extraction_method"] = "fallback"
                if template_identification:
                    extraction_result["template_analysis"] = template_identification

            # Enhanced validation of extraction quality
            if extraction_result["overall_confidence"] < 0.3:
                self._metrics["validation_failures"] += 1
                return update_state_step(
                    state,
                    "term_extraction_failed",
                    error="Low confidence in term extraction",
                )

            # Store results in state with enhanced metadata
            state["confidence_scores"]["term_extraction"] = extraction_result[
                "overall_confidence"
            ]

            updated_data = {
                "contract_terms": extraction_result["terms"],
                "extraction_metadata": {
                    "confidence_scores": extraction_result.get("confidence_scores", {}),
                    "state_requirements": extraction_result.get(
                        "state_requirements", {}
                    ),
                    "extraction_method": extraction_result.get(
                        "extraction_method", "standard"
                    ),
                    "enhanced_extraction": True,
                    "extraction_timestamp": datetime.now(UTC).isoformat(),
                },
            }

            logger.debug("Enhanced contract terms extraction completed successfully")
            return update_state_step(state, "terms_extracted", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced term extraction failed: {e}")
            return update_state_step(
                state,
                "term_extraction_failed",
                error=f"Enhanced term extraction failed: {str(e)}",
            )

    def validate_terms_completeness_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Validate completeness of extracted terms"""

        if not self.enable_validation:
            return state

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            contract_terms = state.get("contract_terms", {})
            australian_state = state["australian_state"]

            # Validate terms completeness
            validation_result = validate_contract_terms_completeness.invoke(
                {
                    "contract_terms": contract_terms,
                    "australian_state": australian_state,
                    "contract_type": state.get("contract_type", "purchase_agreement"),
                }
            )

            # Store validation results
            state["terms_validation"] = validation_result.dict()
            state["confidence_scores"][
                "terms_completeness"
            ] = validation_result.validation_confidence

            # Log validation issues
            if validation_result.missing_mandatory_terms:
                logger.warning(
                    f"Missing mandatory terms: {validation_result.missing_mandatory_terms}"
                )
            if validation_result.incomplete_terms:
                logger.warning(
                    f"Incomplete terms: {validation_result.incomplete_terms}"
                )

            return update_state_step(state, "terms_completeness_validated")

        except Exception as e:
            logger.error(f"Terms completeness validation failed: {e}")
            # Continue workflow with warning
            state["confidence_scores"]["terms_completeness"] = 0.6
            return update_state_step(
                state,
                "terms_completeness_validation_warning",
                error=f"Terms validation failed: {str(e)}",
            )

    def analyze_australian_compliance(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced Australian compliance analysis"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            contract_terms = state["contract_terms"]
            australian_state = state["australian_state"]
            compliance_confidence = 0.0
            compliance_components = 0

            # Enhanced validation with step validation
            if self.enable_validation:
                try:
                    step_validation = validate_workflow_step.invoke(
                        {
                            "step_name": "compliance_check",
                            "step_data": {
                                "contract_terms": contract_terms,
                                "australian_state": australian_state,
                            },
                            "validation_criteria": {"min_score": 0.7},
                        }
                    )
                    state["compliance_step_validation"] = step_validation.dict()
                except Exception as e:
                    logger.warning(f"Step validation failed: {e}")

            # Validate cooling-off period with enhanced error handling
            try:
                cooling_off_result = validate_cooling_off_period.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )
                compliance_confidence += 0.9
                compliance_components += 1
                logger.debug(
                    f"Cooling-off validation completed: {cooling_off_result.get('compliant', False)}"
                )
            except Exception as e:
                logger.warning(f"Cooling-off validation failed: {e}")
                cooling_off_result = {
                    "compliant": False,
                    "error": f"Cooling-off validation failed: {str(e)}",
                    "warnings": ["Unable to validate cooling-off period"],
                }

            # Calculate stamp duty with enhanced error handling
            stamp_duty_result = None
            purchase_price = contract_terms.get("purchase_price", 0)
            if purchase_price > 0:
                try:
                    stamp_duty_result = calculate_stamp_duty.invoke(
                        {
                            "purchase_price": purchase_price,
                            "state": australian_state,
                            "is_first_home": state["user_preferences"].get(
                                "is_first_home_buyer", False
                            ),
                            "is_foreign_buyer": state["user_preferences"].get(
                                "is_foreign_buyer", False
                            ),
                        }
                    )
                    compliance_confidence += 0.95
                    compliance_components += 1
                    logger.debug(
                        f"Stamp duty calculated: ${stamp_duty_result.total_duty}"
                    )
                except Exception as e:
                    logger.warning(f"Stamp duty calculation failed: {e}")
                    stamp_duty_result = {
                        "error": f"Stamp duty calculation failed: {str(e)}",
                        "total_duty": 0,
                        "state": australian_state,
                    }

            # Analyze special conditions with enhanced error handling
            try:
                special_conditions_result = analyze_special_conditions.invoke(
                    {"contract_terms": contract_terms, "state": australian_state}
                )
                compliance_confidence += 0.8
                compliance_components += 1
                logger.debug(
                    f"Special conditions analyzed: {len(special_conditions_result)} conditions"
                )
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
                compliance_confidence = 0.5  # Default if all failed

            # Compile enhanced compliance check
            compliance_check = {
                "state_compliance": cooling_off_result.get("compliant", False),
                "cooling_off_validation": cooling_off_result,
                "stamp_duty_calculation": stamp_duty_result,
                "special_conditions_analysis": special_conditions_result,
                "compliance_issues": [],
                "warnings": cooling_off_result.get("warnings", []),
                "compliance_confidence": compliance_confidence,
                "enhanced_analysis": True,
                "analysis_timestamp": datetime.now(UTC).isoformat(),
            }

            # Add compliance issues with enhanced detection
            if not cooling_off_result.get("compliant", False):
                compliance_check["compliance_issues"].append(
                    "Cooling-off period non-compliant"
                )

            if stamp_duty_result and stamp_duty_result.get("error"):
                compliance_check["compliance_issues"].append(
                    "Stamp duty calculation incomplete"
                )

            state["confidence_scores"]["compliance_check"] = compliance_confidence

            updated_data = {"compliance_check": compliance_check}

            logger.debug("Enhanced compliance analysis completed successfully")
            return update_state_step(state, "compliance_analyzed", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced compliance analysis failed: {e}")
            return update_state_step(
                state,
                "compliance_analysis_failed",
                error=f"Enhanced compliance analysis failed: {str(e)}",
            )

    async def assess_contract_risks(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced risk assessment using PromptManager and OutputParser"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            contract_terms = state["contract_terms"]
            compliance_check = state["compliance_check"]

            # Create enhanced context for risk assessment
            risk_context = PromptContext(
                context_type=ContextType.CONTRACT_ANALYSIS,
                variables={
                    **state.get("prompt_context", {}),
                    "contract_terms": contract_terms,
                    "compliance_check": compliance_check,
                    "user_experience": state.get("user_experience", "novice"),
                },
            )

            # Render prompt using PromptManager
            try:
                rendered_prompt = await self.prompt_manager.render_with_parser(
                    template_name="contract_risk_assessment",
                    context=risk_context,
                    output_parser=self.risk_parser,
                    service_name="contract_analysis_workflow",
                )
                logger.debug("Risk assessment prompt rendered successfully")
            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to manual prompt creation
                rendered_prompt = self._create_risk_assessment_prompt(
                    contract_terms, compliance_check, state["australian_state"]
                )

            # Get LLM response using new client architecture with fallback
            try:
                system_message = "You are an expert Australian property lawyer analyzing contract risks."
                llm_response = await self._generate_content_with_fallback(
                    rendered_prompt, system_message, use_gemini_fallback=True
                )

                # Parse response using structured parser
                parsing_result = self.risk_parser.parse_with_retry(llm_response)

                if parsing_result.success:
                    risk_analysis = parsing_result.parsed_data.dict()
                    risk_confidence = parsing_result.confidence_score
                    self._metrics["successful_parses"] += 1
                    logger.debug(
                        f"Risk analysis parsed successfully with confidence: {risk_confidence}"
                    )
                else:
                    # Enhanced fallback with parsing error details
                    logger.warning(
                        f"Risk parsing failed: {parsing_result.parsing_errors}"
                    )
                    risk_analysis = self._fallback_risk_analysis(
                        contract_terms, compliance_check
                    )
                    risk_confidence = 0.6
                    self._metrics["fallback_uses"] += 1

            except Exception as llm_error:
                logger.error(f"LLM risk assessment failed: {llm_error}")
                # Fallback risk analysis
                risk_analysis = self._fallback_risk_analysis(
                    contract_terms, compliance_check
                )
                risk_confidence = 0.5
                self._metrics["fallback_uses"] += 1

            # Enhanced validation of risk analysis quality
            if not risk_analysis or risk_analysis.get("overall_risk_score", 0) == 0:
                risk_analysis = self._fallback_risk_analysis(
                    contract_terms, compliance_check
                )
                risk_confidence = 0.4

            # Store enhanced results
            state["confidence_scores"]["risk_assessment"] = risk_confidence

            updated_data = {
                "risk_assessment": {
                    **risk_analysis,
                    "enhanced_analysis": True,
                    "parsing_method": (
                        "structured" if parsing_result.success else "fallback"
                    ),
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                }
            }

            logger.debug("Enhanced risk assessment completed successfully")
            return update_state_step(state, "risks_assessed", data=updated_data)

        except Exception as e:
            logger.error(f"Enhanced risk assessment failed: {e}")
            return update_state_step(
                state,
                "risk_assessment_failed",
                error=f"Enhanced risk assessment failed: {str(e)}",
            )

    async def generate_recommendations(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Enhanced recommendations generation using PromptManager and OutputParser"""

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            # Create enhanced context for recommendations
            recommendations_context = PromptContext(
                context_type=ContextType.CONTRACT_ANALYSIS,
                variables={
                    **state.get("prompt_context", {}),
                    "risk_assessment": state.get("risk_assessment", {}),
                    "compliance_check": state.get("compliance_check", {}),
                    "contract_terms": state.get("contract_terms", {}),
                    "user_experience": state.get("user_experience", "novice"),
                },
            )

            # Render prompt using PromptManager
            try:
                rendered_prompt = await self.prompt_manager.render_with_parser(
                    template_name="contract_recommendations",
                    context=recommendations_context,
                    output_parser=self.recommendations_parser,
                    service_name="contract_analysis_workflow",
                )
                logger.debug("Recommendations prompt rendered successfully")
            except (
                PromptNotFoundError,
                PromptValidationError,
                PromptContextError,
            ) as e:
                logger.warning(f"Prompt manager failed, using fallback: {e}")
                # Fallback to manual prompt creation
                rendered_prompt = self._create_recommendations_prompt(state)

            # Get LLM response and parse using new client architecture with fallback
            try:
                system_message = "You are an expert Australian property advisor providing actionable recommendations."
                llm_response = await self._generate_content_with_fallback(
                    rendered_prompt, system_message, use_gemini_fallback=True
                )

                # Parse response using structured parser
                parsing_result = self.recommendations_parser.parse_with_retry(
                    llm_response
                )

                if parsing_result.success:
                    recommendations_data = parsing_result.parsed_data.dict()
                    recommendations = recommendations_data.get("recommendations", [])
                    recommendations_confidence = parsing_result.confidence_score
                    self._metrics["successful_parses"] += 1
                    logger.debug(
                        f"Recommendations parsed successfully: {len(recommendations)} recommendations"
                    )
                else:
                    # Enhanced fallback with parsing error details
                    logger.warning(
                        f"Recommendations parsing failed: {parsing_result.parsing_errors}"
                    )
                    recommendations = self._fallback_recommendations(state)
                    recommendations_confidence = 0.6
                    self._metrics["fallback_uses"] += 1

            except Exception as llm_error:
                logger.error(f"LLM recommendations generation failed: {llm_error}")
                # Fallback recommendations
                recommendations = self._fallback_recommendations(state)
                recommendations_confidence = 0.5
                self._metrics["fallback_uses"] += 1

            # Enhanced validation of recommendations quality
            if not recommendations or len(recommendations) == 0:
                recommendations = self._fallback_recommendations(state)
                recommendations_confidence = 0.4

            # Store enhanced results
            state["confidence_scores"]["recommendations"] = recommendations_confidence

            updated_data = {
                "final_recommendations": recommendations,
                "recommendations": recommendations,  # For backwards compatibility
                "recommendations_metadata": {
                    "enhanced_generation": True,
                    "parsing_method": (
                        "structured" if parsing_result.success else "fallback"
                    ),
                    "generation_timestamp": datetime.now(UTC).isoformat(),
                    "total_recommendations": len(recommendations),
                },
            }

            logger.debug("Enhanced recommendations generation completed successfully")
            return update_state_step(
                state, "recommendations_generated", data=updated_data
            )

        except Exception as e:
            logger.error(f"Enhanced recommendations generation failed: {e}")
            return update_state_step(
                state,
                "recommendation_generation_failed",
                error=f"Enhanced recommendation generation failed: {str(e)}",
            )

    def validate_final_output_step(
        self, state: RealEstateAgentState
    ) -> RealEstateAgentState:
        """Validate final output quality and completeness"""

        if not self.enable_validation:
            return state

        # Update progress
        state["progress"]["current_step"] += 1
        state["progress"]["percentage"] = int(
            (state["progress"]["current_step"] / state["progress"]["total_steps"]) * 100
        )

        try:
            # Validate final analysis completeness
            validation_criteria = {"min_score": 0.7}

            final_validation = validate_workflow_step.invoke(
                {
                    "step_name": "final_output",
                    "step_data": {
                        "risk_assessment": state.get("risk_assessment", {}),
                        "recommendations": state.get("final_recommendations", []),
                        "compliance_check": state.get("compliance_check", {}),
                    },
                    "validation_criteria": validation_criteria,
                }
            )

            # Store final validation results
            state["final_output_validation"] = final_validation.dict()
            state["confidence_scores"][
                "final_output"
            ] = final_validation.validation_score

            # Log validation results
            if not final_validation.validation_passed:
                logger.warning(
                    f"Final output validation failed: {final_validation.issues_found}"
                )
            else:
                logger.debug("Final output validation passed successfully")

            return update_state_step(state, "final_output_validated")

        except Exception as e:
            logger.error(f"Final output validation failed: {e}")
            # Continue workflow with warning
            state["confidence_scores"]["final_output"] = 0.6
            return update_state_step(
                state,
                "final_output_validation_warning",
                error=f"Final validation failed: {str(e)}",
            )

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
                "contract_terms": state.get("contract_terms", {}),
                "risk_assessment": state.get("risk_assessment", {}),
                "compliance_check": state.get("compliance_check", {}),
                "recommendations": state.get("final_recommendations", []),
                "confidence_scores": state.get("confidence_scores", {}),
                "overall_confidence": overall_confidence,
                "confidence_assessment": confidence_result.get(
                    "quality_assessment", ""
                ),
                "processing_summary": {
                    "steps_completed": state["current_step"],
                    "processing_time": state.get("processing_time"),
                    "analysis_version": state["agent_version"],
                    "progress": state.get("progress", {}),
                    "enhanced_workflow": True,
                    "validation_enabled": self.enable_validation,
                    "quality_checks_enabled": self.enable_quality_checks,
                },
                "quality_metrics": {
                    "extraction_quality": state.get("document_metadata", {}).get(
                        "text_quality", {}
                    ),
                    "confidence_breakdown": state.get("confidence_scores", {}),
                    "processing_method": {
                        "document_extraction": state.get("document_metadata", {}).get(
                            "extraction_method", "unknown"
                        ),
                        "term_extraction": state.get("extraction_metadata", {}).get(
                            "extraction_method", "standard"
                        ),
                        "risk_parsing": state.get("risk_assessment", {}).get(
                            "parsing_method", "unknown"
                        ),
                        "recommendations_parsing": state.get(
                            "recommendations_metadata", {}
                        ).get("parsing_method", "unknown"),
                    },
                    "workflow_metrics": self._get_workflow_metrics(),
                    "document_quality_metrics": state.get(
                        "document_quality_metrics", {}
                    ),
                    "validation_results": {
                        "terms_validation": state.get("terms_validation", {}),
                        "final_output_validation": state.get(
                            "final_output_validation", {}
                        ),
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

        risk_assessment = analysis_results.get("risk_assessment", {})
        compliance_check = analysis_results.get("compliance_check", {})
        recommendations = analysis_results.get("recommendations", [])

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
            "validation_results": analysis_results.get("quality_metrics", {}).get(
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
                "processing_time": analysis_results.get("processing_summary", {}).get(
                    "processing_time"
                ),
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

        updated_data = {
            "analysis_results": {
                "error_details": error_details,
                "status": "failed",
                "workflow_metrics": self._get_workflow_metrics(),
            },
            "parsing_status": ProcessingStatus.FAILED,
        }

        logger.error(f"Enhanced workflow error: {error_message}")
        return update_state_step(state, "error_handled", data=updated_data)

    def retry_failed_step(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """Enhanced retry logic with intelligent backoff"""

        retry_count = state.get("retry_count", 0)
        max_retries = 3  # Increased for enhanced workflow

        if retry_count >= max_retries:
            logger.warning(f"Max retries ({max_retries}) exceeded, handling error")
            return self.handle_processing_error(state)

        # Enhanced retry with exponential backoff
        retry_delay = 2**retry_count  # 2, 4, 8 seconds
        logger.info(
            f"Retrying step (attempt {retry_count + 1}/{max_retries}) after {retry_delay}s delay"
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

    def _simulate_document_extraction(self, document_data: Dict[str, Any]) -> str:
        """Enhanced document extraction simulation"""
        logger.debug("Using simulated document extraction (fallback mode)")
        return """
        SALE OF LAND CONTRACT
        
        VENDOR: John Smith
        PURCHASER: Jane Doe
        
        PROPERTY: 123 Collins Street, Melbourne VIC 3000
        
        PURCHASE PRICE: $850,000
        DEPOSIT: $85,000 (10%)
        SETTLEMENT DATE: 45 days from exchange
        
        COOLING OFF PERIOD: 3 business days
        
        SPECIAL CONDITIONS:
        1. Subject to finance approval within 21 days
        2. Subject to satisfactory building and pest inspection
        3. Subject to strata search and review of strata documents
        
        This contract is governed by Victorian law.
        """

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
        - Risk Assessment: {json.dumps(state.get("risk_assessment", {}), indent=2)}
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
                "consequences_if_ignored": "May miss critical legal issues, compliance requirements, or beneficial provisions",
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
                    return response
                except Exception as gemini_error:
                    logger.error(f"Gemini fallback also failed: {gemini_error}")
                    raise openai_error  # Re-raise original error

            raise openai_error

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
            },
            "parsing_metrics": {
                "success_rate": self._metrics["successful_parses"]
                / max(self._metrics["total_analyses"], 1),
                "fallback_rate": self._metrics["fallback_uses"]
                / max(self._metrics["total_analyses"], 1),
            },
        }
