"""
Unified Contract Analysis Service with WebSocket Integration and Enhanced Features
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime, timezone

from app.agents.progress_tracking_workflow import ProgressTrackingWorkflow
from app.core.config import (
    get_enhanced_workflow_config,
    validate_workflow_configuration,
    EnhancedWorkflowConfig,
)
from app.core.prompts import PromptManager
from app.models.contract_state import RealEstateAgentState
from app.schema.enums import AustralianState, ProcessingStatus
from app.schema import (
    ContractAnalysisServiceResponse,
    AnalysisQualityMetrics,
    WorkflowMetadata,
    EnhancementFeaturesStatus,
    StartAnalysisResponse,
    AnalysesSummary,
    ServiceHealthResponse,
    ServiceMetricsResponse,
    ReloadConfigurationResponse,
    AnalysisStatus,
    OperationResponse,
)
from app.services.communication.websocket_service import (
    WebSocketManager,
    WebSocketEvents,
)
from app.clients.supabase.client import SupabaseClient
from app.services.repositories import ContractsRepository, AnalysesRepository
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ContractAnalysisService:
    """
    Unified contract analysis service with real-time progress tracking and enhanced features

    Combines:
    - Real-time WebSocket progress tracking
    - Advanced workflow configuration
    - Integrated PromptManager system
    - Comprehensive validation & quality checks
    - Service health monitoring & metrics
    - Enhanced error handling & fallback mechanisms
    """

    def __init__(
        self,
        websocket_manager: Optional[WebSocketManager] = None,
        openai_api_key: str = None,
        model_name: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        config: Optional[EnhancedWorkflowConfig] = None,
        prompt_manager: Optional[PromptManager] = None,
        enable_websocket_progress: bool = True,
    ):
        self.websocket_manager = websocket_manager
        self.enable_websocket_progress = (
            enable_websocket_progress and websocket_manager is not None
        )
        self.openai_api_key = openai_api_key
        # Resolve model name from environment/config if not explicitly provided
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

        # Initialize configuration
        self.config = config or get_enhanced_workflow_config()

        # Validate configuration
        config_validation = validate_workflow_configuration(self.config)
        if not config_validation["valid"]:
            logger.error(
                f"Configuration validation failed: {config_validation['issues']}"
            )
            raise ValueError(
                f"Invalid configuration: {'; '.join(config_validation['issues'])}"
            )

        if config_validation["warnings"]:
            logger.warning(f"Configuration warnings: {config_validation['warnings']}")

        # Initialize prompt manager
        if prompt_manager is None and self.config.enable_prompt_manager:
            try:
                prompt_manager_config = self.config.to_prompt_manager_config()
                self.prompt_manager = PromptManager(prompt_manager_config)
                logger.info("Prompt manager initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize prompt manager: {e}")
                self.prompt_manager = None
        else:
            self.prompt_manager = prompt_manager

        # Initialize a single progress-tracking workflow instance
        self.workflow = ProgressTrackingWorkflow(
            self,
            openai_api_key=self.openai_api_key,
            model_name=self.model_name,
            openai_api_base=self.openai_api_base,
            prompt_manager=self.prompt_manager,
            enable_validation=self.config.enable_validation,
            enable_quality_checks=self.config.enable_quality_checks,
            enable_fallbacks=getattr(self.config, "enable_fallback_mechanisms", True),
        )

        # Note: Workflow will be initialized lazily when first used
        self._workflow_initialized = False

        # WebSocket progress tracking
        self.active_analyses: Dict[str, Dict[str, Any]] = {}

        # Service metrics
        self._service_metrics = {
            "total_requests": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_processing_time": 0.0,
            "configuration_errors": 0,
            "prompt_manager_errors": 0,
        }

        logger.info(
            f"Unified contract analysis service initialized with config: {config_validation['config_summary']}"
        )

        # PRD step -> base percent mapping (document_processing uses 7 as start of 7-30 range)
        self._step_percent_map = {
            "document_uploaded": 5,
            "validate_input": 7,
            "document_processing": 7,
            "validate_document_quality": 34,
            "extract_terms": 42,
            "validate_terms_completeness": 50,
            "analyze_compliance": 57,
            "assess_risks": 71,
            "generate_recommendations": 85,
            "compile_report": 98,
            "analysis_complete": 100,
        }

    def _percent_for_step(self, step: str) -> int:
        return int(self._step_percent_map.get(step, -1))

    async def _ensure_workflow_initialized(self):
        """Ensure the workflow is initialized before use."""
        if not self._workflow_initialized:
            try:
                await self.workflow.initialize()
                self._workflow_initialized = True
                logger.info("Contract analysis workflow initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize workflow: {e}")
                raise

    async def analyze_contract(
        self,
        document_data: Dict[str, Any],
        user_id: str,
        australian_state: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        contract_type: str = "purchase_agreement",
        user_experience: str = "novice",
        user_type: str = "buyer",
        enable_websocket_progress: Optional[bool] = None,
        progress_callback: Optional[Callable[[str, int, str], Awaitable[None]]] = None,
    ) -> ContractAnalysisServiceResponse:
        """
        Unified contract analysis method with optional WebSocket progress tracking

        Args:
            document_data: Document content and metadata
            user_id: ID of the user requesting analysis
            australian_state: Australian state for compliance
            user_preferences: Optional user preferences
            session_id: Optional session identifier
            contract_type: Type of contract being analyzed
            user_experience: User experience level
            user_type: Type of user (buyer, seller, etc.)
            enable_websocket_progress: Override WebSocket progress setting

        Returns:
            Enhanced analysis results with comprehensive metadata
        """

        start_time = datetime.now(timezone.utc)
        self._service_metrics["total_requests"] += 1

        # Generate session ID if not provided
        if session_id is None:
            session_id = f"analysis_{int(start_time.timestamp())}"

        # Determine if WebSocket progress should be enabled
        use_websocket_progress = (
            enable_websocket_progress
            if enable_websocket_progress is not None
            else self.enable_websocket_progress
        )

        logger.info(f"Starting unified contract analysis for session {session_id}")

        try:
            # Validate inputs
            validation_result = self._validate_analysis_inputs(
                document_data, user_id, australian_state, contract_type
            )

            if not validation_result["valid"]:
                error_msg = (
                    f"Input validation failed: {'; '.join(validation_result['errors'])}"
                )
                logger.error(error_msg)
                return self._create_error_response(error_msg, session_id, start_time)

            # Create initial state
            if hasattr(AustralianState, australian_state.upper()):
                state_enum = AustralianState(australian_state.upper())
            else:
                state_enum = AustralianState(australian_state)

            initial_state = self._create_initial_state(
                document_data=document_data,
                user_id=user_id,
                australian_state=state_enum,
                user_preferences=user_preferences or {},
                session_id=session_id,
                contract_type=contract_type,
                user_experience=user_experience,
                user_type=user_type,
            )

            # Initialize analysis tracking if WebSocket is enabled
            # Resolve contract_id: prefer provided state value, else derive from content_hash, else session_id
            contract_id = initial_state.get("contract_id")
            if not contract_id:
                try:
                    content_hash = (document_data or {}).get("content_hash") or (
                        document_data or {}
                    ).get("content_hmac")
                    if content_hash:
                        contract_id = await ensure_contract(
                            service_client=None,
                            content_hash=content_hash,
                            contract_type=contract_type,
                            australian_state=(
                                state_enum.value
                                if hasattr(state_enum, "value")
                                else str(state_enum)
                            ),
                        )
                except Exception as cid_err:
                    logger.warning(
                        f"Failed to resolve contract_id from content_hash; falling back to session id: {cid_err}"
                    )
                if not contract_id:
                    contract_id = initial_state["session_id"]
            # Store resolved contract_id back into state for downstream consumers
            initial_state["contract_id"] = contract_id
            if use_websocket_progress:
                self.active_analyses[contract_id] = {
                    "start_time": start_time,
                    "user_id": user_id,
                    "session_id": session_id,
                    "status": "starting",
                    "progress": 0,
                }

                # If caller requested a manual force restart, allow restarting from a specific step
                # user_preferences.force_restart: True/False
                # user_preferences.restart_from_step: step key (e.g., "extract_terms")
                if (user_preferences or {}).get("force_restart"):
                    try:
                        restart_from = (user_preferences or {}).get("restart_from_step")
                        restart_percent = (
                            self._percent_for_step(restart_from) if restart_from else -1
                        )
                        # If an explicit step is provided and recognized, set baseline to that step's percent
                        # Otherwise set to -1 to allow full replay from start
                        self.active_analyses[contract_id]["progress"] = (
                            restart_percent if restart_percent >= 0 else -1
                        )
                        self.active_analyses[contract_id]["manual_restart"] = True
                        if restart_from:
                            self.active_analyses[contract_id][
                                "manual_restart_from"
                            ] = restart_from
                    except Exception:
                        pass

                # Send analysis started event
                if self.websocket_manager:
                    await self.websocket_manager.send_message(
                        session_id,
                        WebSocketEvents.analysis_started(contract_id, estimated_time=3),
                    )

                # PRD: Emit 0% immediately when session/analysis initializes
                self._schedule_progress_update(
                    session_id,
                    contract_id,
                    "initialized",
                    0,
                    "Analysis initialized",
                )

            # Initialize prompt manager if needed
            if self.prompt_manager:
                try:
                    await self.prompt_manager.initialize()
                except Exception as e:
                    logger.warning(f"Prompt manager initialization failed: {e}")
                    self._service_metrics["prompt_manager_errors"] += 1

            # Ensure workflow is initialized before use
            await self._ensure_workflow_initialized()

            # Execute analysis with optional progress tracking
            if use_websocket_progress:
                # PRD: Emit 5% just as workflow starts
                self._schedule_progress_update(
                    session_id,
                    contract_id,
                    "document_uploaded",
                    5,
                    "Upload document",
                )

                # Provide a persist-only notify callback; WS will also be emitted inside the workflow
                if progress_callback:

                    async def _notify_progress(step: str, percent: int, desc: str):
                        try:
                            await progress_callback(step, percent, desc)
                        except Exception:
                            pass

                    initial_state["notify_progress"] = _notify_progress

                # Allow resume behavior via state
                resume_from = (user_preferences or {}).get("resume_from_step")
                if resume_from:
                    initial_state["resume_from_step"] = resume_from

            logger.debug(f"Executing workflow for session {session_id}")
            final_state = await self.workflow.analyze_contract(initial_state)

            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Update service metrics
            if final_state.get(
                "parsing_status"
            ) == ProcessingStatus.COMPLETED or not final_state.get("error_state"):
                self._service_metrics["successful_analyses"] += 1
                logger.info(
                    f"Analysis completed successfully in {processing_time:.2f}s"
                )
            else:
                self._service_metrics["failed_analyses"] += 1
                logger.warning(f"Analysis failed after {processing_time:.2f}s")

            # Update average processing time
            self._service_metrics["average_processing_time"] = (
                self._service_metrics["average_processing_time"]
                * (self._service_metrics["total_requests"] - 1)
                + processing_time
            ) / self._service_metrics["total_requests"]

            # Send WebSocket completion events if enabled
            if use_websocket_progress and self.websocket_manager:
                if final_state.get("error_state"):
                    await self.websocket_manager.send_message(
                        session_id,
                        WebSocketEvents.analysis_failed(
                            contract_id,
                            final_state["error_state"],
                            retry_available=True,
                        ),
                    )

                    # Update analysis status
                    if contract_id in self.active_analyses:
                        self.active_analyses[contract_id]["status"] = "failed"
                        self.active_analyses[contract_id]["error"] = final_state[
                            "error_state"
                        ]
                else:
                    # Create analysis summary
                    analysis_results = final_state.get("analysis_results", {})
                    summary = {
                        "overall_confidence": analysis_results.get(
                            "overall_confidence", 0
                        ),
                        "risk_score": analysis_results.get("risk_assessment", {}).get(
                            "overall_risk_score", 0
                        ),
                        "compliance_status": analysis_results.get(
                            "compliance_check", {}
                        ).get("state_compliance", False),
                        "recommendations_count": len(
                            analysis_results.get("recommendations", [])
                        ),
                        "processing_time": processing_time,
                    }

                    await self.websocket_manager.send_message(
                        session_id,
                        WebSocketEvents.analysis_completed(contract_id, summary),
                    )

                    # Update analysis status
                    if contract_id in self.active_analyses:
                        self.active_analyses[contract_id]["status"] = "completed"
                        self.active_analyses[contract_id]["summary"] = summary

            # Create enhanced response
            response = self._create_analysis_response(final_state, processing_time)

            logger.debug(f"Analysis response created for session {session_id}")
            return response

        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._service_metrics["failed_analyses"] += 1

            error_msg = f"Contract analysis failed: {str(e)}"
            logger.error(f"{error_msg} (processing time: {processing_time:.2f}s)")

            # Send WebSocket error event if enabled
            if use_websocket_progress and self.websocket_manager:
                await self.websocket_manager.send_message(
                    session_id,
                    WebSocketEvents.analysis_failed(
                        contract_id,
                        f"Analysis service error: {str(e)}",
                        retry_available=True,
                    ),
                )

            return self._create_error_response(error_msg, session_id, start_time)

    async def start_analysis(
        self,
        user_id: str,
        session_id: str,
        document_data: Dict[str, Any],
        australian_state: AustralianState,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_type: str = "buyer",
        progress_callback: Optional[Callable[[str, int, str], Awaitable[None]]] = None,
    ) -> StartAnalysisResponse:
        """
        Start contract analysis with real-time progress tracking (backward compatibility method)

        This method delegates to analyze_contract with WebSocket progress enabled.
        """

        # Convert AustralianState enum to string if needed
        state_str = (
            australian_state.value
            if hasattr(australian_state, "value")
            else str(australian_state)
        )

        # Delegate to the unified analyze_contract method with WebSocket progress enabled
        result = await self.analyze_contract(
            document_data=document_data,
            user_id=user_id,
            australian_state=state_str,
            user_preferences=user_preferences,
            session_id=session_id,
            user_type=user_type,
            enable_websocket_progress=True,
            progress_callback=progress_callback,
        )

        # Transform response to match original format
        if result.success:
            return StartAnalysisResponse(
                success=True,
                contract_id=result.session_id,
                session_id=result.session_id,
                final_state=result.analysis_results,
                analysis_results=result.analysis_results,
                processing_time=result.processing_time_seconds,
            )
        else:
            return StartAnalysisResponse(
                success=False,
                error=result.error,
                session_id=session_id,
            )

    def _validate_analysis_inputs(
        self,
        document_data: Dict[str, Any],
        user_id: str,
        australian_state: str,
        contract_type: str,
    ) -> Dict[str, Any]:
        """Validate analysis inputs"""

        errors = []
        warnings = []

        # Validate document data
        if not document_data:
            errors.append("Document data is required")
        elif not isinstance(document_data, dict):
            errors.append("Document data must be a dictionary")
        else:
            if not document_data.get("content") and not document_data.get("file_path"):
                errors.append("Document content or file path is required")

        # Validate user ID
        if not user_id or not isinstance(user_id, str):
            errors.append("Valid user ID is required")

        # Validate Australian state
        try:
            AustralianState(australian_state.upper())
        except (ValueError, AttributeError):
            errors.append(f"Invalid Australian state: {australian_state}")

        # Validate contract type
        valid_contract_types = [
            "purchase_agreement",
            "lease_agreement",
            "rental_agreement",
        ]
        if contract_type not in valid_contract_types:
            warnings.append(f"Unrecognized contract type: {contract_type}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _create_initial_state(
        self,
        document_data: Dict[str, Any],
        user_id: str,
        australian_state: AustralianState,
        user_preferences: Dict[str, Any],
        session_id: str,
        contract_type: str,
        user_experience: str,
        user_type: str,
        document_type: str = "contract",
    ) -> RealEstateAgentState:
        """Create initial state for workflow"""

        return {
            "session_id": session_id,
            "user_id": user_id,
            "australian_state": australian_state,
            "document_data": document_data,
            "user_preferences": user_preferences,
            "user_type": user_type,
            "contract_type": contract_type,
            "document_type": document_type,
            "user_experience": user_experience,
            "current_step": [
                "initialized"
            ],  # Use list for Annotated concurrent updates
            "agent_version": "unified_v1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workflow_config": {
                "validation_enabled": self.config.enable_validation,
                "quality_checks_enabled": self.config.enable_quality_checks,
                "prompt_manager_enabled": self.config.enable_prompt_manager,
                "structured_parsing_enabled": self.config.enable_structured_parsing,
            },
            "confidence_scores": {},
            "parsing_status": ProcessingStatus.PENDING,
            # Required fields from TypedDict
            "document_metadata": {},
            "contract_terms": None,
            "risk_assessment": None,
            "compliance_check": None,
            "recommendations": [],
            "property_data": None,
            "market_analysis": None,
            "financial_analysis": None,
            "error_state": None,
            "processing_time": None,
            "progress": None,
            "analysis_results": {},
            "report_data": None,
            "final_recommendations": [],
        }

    def _create_analysis_response(
        self, final_state: RealEstateAgentState, processing_time: float
    ) -> ContractAnalysisServiceResponse:
        """Create enhanced analysis response"""

        # Safely coalesce optional fields that may be present but set to None
        analysis_results = final_state.get("analysis_results") or {}
        report_data = final_state.get("report_data") or {}
        workflow_config = final_state.get("workflow_config") or {}
        progress_info = final_state.get("progress") or {}

        # Create comprehensive response
        response = ContractAnalysisServiceResponse(
            success=(
                final_state.get("parsing_status") == ProcessingStatus.COMPLETED
                and not final_state.get("error_state")
            ),
            session_id=final_state.get("session_id"),
            analysis_timestamp=datetime.now(timezone.utc),
            processing_time_seconds=processing_time,
            workflow_version="unified_v1.0",
            analysis_results=analysis_results,
            report_data=report_data,
            quality_metrics=AnalysisQualityMetrics(
                overall_confidence=analysis_results.get("overall_confidence", 0.0),
                confidence_breakdown=analysis_results.get("confidence_breakdown", {}),
                quality_assessment=analysis_results.get("confidence_assessment", ""),
                processing_quality=analysis_results.get("quality_metrics", {}),
                document_quality=(final_state.get("document_quality_metrics") or {}),
                validation_results=(
                    (final_state.get("quality_metrics") or {}).get(
                        "validation_results", {}
                    )
                ),
            ),
            workflow_metadata=WorkflowMetadata(
                steps_completed=(
                    progress_info.get("current_step", 0)
                    if isinstance(progress_info, dict)
                    else 0
                ),
                total_steps=(
                    progress_info.get("total_steps", 0)
                    if isinstance(progress_info, dict)
                    else 0
                ),
                progress_percentage=(
                    progress_info.get("percentage", 0)
                    if isinstance(progress_info, dict)
                    else 0
                ),
                configuration=workflow_config,
                performance_metrics=(
                    self.workflow.get_workflow_metrics()
                    if hasattr(self.workflow, "get_workflow_metrics")
                    else {}
                ),
                service_metrics=self._service_metrics,
            ),
            error=final_state.get("error_state"),
            warnings=self._extract_warnings_from_state(final_state),
            enhancement_features=EnhancementFeaturesStatus(
                structured_parsing_used=True,
                prompt_manager_used=self.config.enable_prompt_manager,
                validation_performed=self.config.enable_validation,
                quality_checks_performed=self.config.enable_quality_checks,
                enhanced_error_handling=self.config.enable_enhanced_error_handling,
                fallback_mechanisms_available=self.config.enable_fallback_mechanisms,
            ),
        )

        return response

    def _create_error_response(
        self, error_message: str, session_id: str, start_time: datetime
    ) -> ContractAnalysisServiceResponse:
        """Create error response"""

        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        return ContractAnalysisServiceResponse(
            success=False,
            session_id=session_id,
            error=error_message,
            analysis_timestamp=datetime.now(timezone.utc),
            processing_time_seconds=processing_time,
            workflow_version="unified_v1.0",
            analysis_results={},
            report_data={},
            quality_metrics=AnalysisQualityMetrics(),
            workflow_metadata=WorkflowMetadata(
                configuration=(
                    self.config.validate_config()
                    if hasattr(self.config, "validate_config")
                    else {}
                ),
                service_metrics=self._service_metrics,
            ),
            warnings=[],
            enhancement_features=EnhancementFeaturesStatus(
                structured_parsing_used=True,
                prompt_manager_used=self.config.enable_prompt_manager,
                validation_performed=self.config.enable_validation,
                quality_checks_performed=self.config.enable_quality_checks,
                enhanced_error_handling=self.config.enable_enhanced_error_handling,
                fallback_mechanisms_available=self.config.enable_fallback_mechanisms,
            ),
        )

    def _extract_warnings_from_state(self, state: RealEstateAgentState) -> List[str]:
        """Extract warnings from workflow state"""

        warnings = []

        # Document quality warnings
        doc_quality = state.get("document_quality_metrics") or {}
        if doc_quality.get("issues_identified"):
            warnings.extend(doc_quality["issues_identified"])

        # Compliance warnings
        compliance_check = state.get("compliance_check") or {}
        if compliance_check.get("warnings"):
            warnings.extend(compliance_check["warnings"])

        # Terms validation warnings
        terms_validation = state.get("terms_validation") or {}
        if terms_validation.get("missing_mandatory_terms"):
            warnings.append(
                f"Missing mandatory terms: {', '.join(terms_validation['missing_mandatory_terms'])}"
            )

        # Final output validation warnings
        final_validation = state.get("final_output_validation") or {}
        if not final_validation.get("validation_passed", True):
            warnings.append("Final output validation failed")

        return warnings

        # Deprecated: method now unused since we reuse a single workflow; kept for backward compatibility
        # Simply execute using the main workflow
        # await self._ensure_workflow_initialized()
        # return await self.workflow.analyze_contract(initial_state)

    async def _send_progress_update(
        self,
        session_id: str,
        contract_id: str,
        step: str,
        progress_percent: int,
        description: str,
    ):
        """Send progress update via WebSocket"""
        try:
            # Update internal tracking
            if contract_id in self.active_analyses:
                self.active_analyses[contract_id]["progress"] = progress_percent
                self.active_analyses[contract_id]["current_step"] = step

            # Send WebSocket event
            await self.websocket_manager.send_message(
                session_id,
                WebSocketEvents.analysis_progress(
                    contract_id, step, progress_percent, description
                ),
            )
        except Exception as e:
            logger.error(f"Failed to send progress update: {str(e)}")

    def _schedule_progress_update(
        self,
        session_id: str,
        contract_id: str,
        step: str,
        progress_percent: int,
        description: str,
    ) -> None:
        """Schedule a progress update regardless of event loop availability.

        - If an asyncio event loop is running, schedule the coroutine normally.
        - If no loop is running (e.g., inside a Celery worker sync context),
          publish via Redis synchronously so the FastAPI process can fan out to WS.
        """
        # Monotonic guard: skip if not increasing
        try:
            last = None
            manual_restart = False
            if contract_id in self.active_analyses:
                last = self.active_analyses[contract_id].get("progress")
                manual_restart = bool(
                    self.active_analyses[contract_id].get("manual_restart")
                )
            # Enforce monotonicity unless this session is marked as a manual restart
            if (
                not manual_restart
                and last is not None
                and progress_percent <= int(last)
            ):
                return
        except Exception:
            pass

        # Update local tracking immediately
        try:
            if contract_id in self.active_analyses:
                self.active_analyses[contract_id]["progress"] = progress_percent
                self.active_analyses[contract_id]["current_step"] = step
        except Exception:
            pass

        # Publish via Redis to the contract/session channel for UI consumption
        try:
            from app.services.communication.redis_pubsub import publish_progress_sync
            from datetime import datetime

            message = {
                "event_type": "analysis_progress",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "contract_id": contract_id,  # Use actual contract UUID
                    "current_step": step,
                    "progress_percent": progress_percent,
                    "step_description": description,
                },
            }

            # Primary channel: session_id for UI WebSocket subscription
            if session_id:
                publish_progress_sync(session_id, message)

            # Secondary channel: contract_id for contract-specific subscriptions
            if contract_id and contract_id != session_id:
                publish_progress_sync(contract_id, message)
        except Exception as redis_error:
            logger.warning(
                f"Progress update Redis publish failed for {contract_id}: {redis_error}"
            )

        # Additionally attempt direct WS delivery on the session_id (best-effort)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._send_progress_update(
                    session_id, contract_id, step, progress_percent, description
                )
            )
        except Exception as e:
            # Ignore; Redis path is authoritative for fan-out
            logger.debug(
                f"Skipping direct WS schedule for {contract_id}: {e}",
                exc_info=False,
            )

    async def get_analysis_status(self, contract_id: str) -> Optional[AnalysisStatus]:
        """Get current analysis status"""
        info = self.active_analyses.get(contract_id)
        if not info:
            return None
        return AnalysisStatus(**info)

    async def cancel_analysis(self, contract_id: str, session_id: str) -> bool:
        """Cancel ongoing analysis"""
        try:
            if contract_id in self.active_analyses:
                self.active_analyses[contract_id]["status"] = "cancelled"

                # Send cancellation event
                await self.websocket_manager.send_message(
                    session_id,
                    WebSocketEvents.system_notification(
                        f"Analysis {contract_id} has been cancelled",
                        notification_type="info",
                    ),
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cancel analysis {contract_id}: {str(e)}")
            return False

    async def retry_analysis(
        self, contract_id: str, session_id: str, user_id: str
    ) -> OperationResponse:
        """Retry failed analysis"""

        # Get previous analysis data
        analysis_info = self.active_analyses.get(contract_id)
        if not analysis_info:
            return OperationResponse(success=False, error="Analysis not found")

        # Clear error state
        if contract_id in self.active_analyses:
            self.active_analyses[contract_id]["status"] = "retrying"
            self.active_analyses[contract_id].pop("error", None)

        # Send retry notification
        await self.websocket_manager.send_message(
            session_id,
            WebSocketEvents.system_notification(
                f"Retrying analysis {contract_id}", notification_type="info"
            ),
        )

        # Note: In a full implementation, you would need to store and retrieve
        # the original document data and parameters to retry the analysis
        return OperationResponse(success=True, message="Retry initiated")

    def cleanup_completed_analyses(self, max_age_hours: int = 24):
        """Clean up old completed analyses"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)

        to_remove = []
        for contract_id, analysis_info in self.active_analyses.items():
            if analysis_info["start_time"].timestamp() < cutoff_time:
                if analysis_info["status"] in ["completed", "failed", "cancelled"]:
                    to_remove.append(contract_id)

        for contract_id in to_remove:
            del self.active_analyses[contract_id]

        logger.info(f"Cleaned up {len(to_remove)} old analyses")

    def get_active_analyses_count(self) -> int:
        """Get count of active analyses"""
        return len(
            [
                a
                for a in self.active_analyses.values()
                if a["status"] in ["starting", "processing", "retrying"]
            ]
        )

    def get_all_analyses_summary(self) -> AnalysesSummary:
        """Get summary of all analyses"""
        status_counts = {}
        for analysis in self.active_analyses.values():
            status = analysis["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        return AnalysesSummary(
            total_analyses=len(self.active_analyses),
            status_breakdown=status_counts,
            active_count=self.get_active_analyses_count(),
        )

    async def get_service_health(self) -> ServiceHealthResponse:
        """Get service health status"""

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "version": "unified_v1.0",
            "configuration": (
                self.config.validate_config()
                if hasattr(self.config, "validate_config")
                else {}
            ),
            "metrics": self._service_metrics,
            "components": {},
        }

        # Check workflow health
        try:
            workflow_metrics = (
                self.workflow.get_workflow_metrics()
                if hasattr(self.workflow, "get_workflow_metrics")
                else {}
            )
            health_status["components"]["workflow"] = {
                "status": "healthy",
                "metrics": workflow_metrics,
            }
        except Exception as e:
            health_status["components"]["workflow"] = {
                "status": "error",
                "error": str(e),
            }
            health_status["status"] = "degraded"

        # Check prompt manager health
        if self.prompt_manager:
            try:
                pm_health = (
                    await self.prompt_manager.health_check()
                    if hasattr(self.prompt_manager, "health_check")
                    else {"status": "healthy"}
                )
                health_status["components"]["prompt_manager"] = pm_health
                if pm_health.get("status") != "healthy":
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["components"]["prompt_manager"] = {
                    "status": "error",
                    "error": str(e),
                }
                health_status["status"] = "degraded"
        else:
            health_status["components"]["prompt_manager"] = {"status": "disabled"}

        # Check WebSocket manager health
        if self.websocket_manager:
            health_status["components"]["websocket_manager"] = {
                "status": "healthy",
                "progress_tracking_enabled": self.enable_websocket_progress,
            }
        else:
            health_status["components"]["websocket_manager"] = {"status": "disabled"}

        return ServiceHealthResponse(**health_status)

    def get_service_metrics(self) -> ServiceMetricsResponse:
        """Get comprehensive service metrics"""

        metrics = {
            "service_metrics": self._service_metrics,
            "configuration": (
                self.config.validate_config()
                if hasattr(self.config, "validate_config")
                else {}
            ),
            "workflow_metrics": (
                self.workflow.get_workflow_metrics()
                if hasattr(self.workflow, "get_workflow_metrics")
                else {}
            ),
            "websocket_metrics": {
                "active_analyses_count": self.get_active_analyses_count(),
                "total_analyses": len(self.active_analyses),
                "progress_tracking_enabled": self.enable_websocket_progress,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.prompt_manager and hasattr(self.prompt_manager, "get_metrics"):
            try:
                metrics["prompt_manager_metrics"] = self.prompt_manager.get_metrics()
            except Exception as e:
                metrics["prompt_manager_error"] = str(e)

        return ServiceMetricsResponse(**metrics)

    async def reload_configuration(
        self, new_config: Optional[EnhancedWorkflowConfig] = None
    ) -> ReloadConfigurationResponse:
        """Reload service configuration"""

        try:
            if new_config:
                self.config = new_config
            else:
                self.config = get_enhanced_workflow_config()

            # Validate new configuration
            config_validation = validate_workflow_configuration(self.config)
            if not config_validation["valid"]:
                raise ValueError(
                    f"Invalid configuration: {'; '.join(config_validation['issues'])}"
                )

            # Reload prompt manager if enabled
            if (
                self.config.enable_prompt_manager
                and self.prompt_manager
                and hasattr(self.prompt_manager, "reload_templates")
            ):
                await self.prompt_manager.reload_templates()

            logger.info("Service configuration reloaded successfully")

            return ReloadConfigurationResponse(
                success=True,
                message="Configuration reloaded successfully",
                validation=config_validation,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return ReloadConfigurationResponse(
                success=False,
                error=str(e),
                timestamp=datetime.now(timezone.utc),
            )


# Database helpers colocated with analysis service to keep status logic centralized
async def ensure_contract(
    service_client: SupabaseClient,  # Kept for backward compatibility but not used
    *,
    content_hash: str,
    contract_type: str,
    australian_state: str,
) -> str:
    """
    Create or fetch a contract row for a given content hash.

    MIGRATED: Now uses ContractsRepository with service role connection.
    Uses repository pattern for better maintainability and RLS enforcement.
    Returns the contract id.
    """
    settings = get_settings()

    contracts_repo = ContractsRepository()

    try:
        contract = await contracts_repo.upsert_contract_by_content_hash(
            content_hash=content_hash,
            contract_type=contract_type,
            australian_state=australian_state,
        )
        logger.info(f"Repository: Upserted contract record: {contract.id}")
        return str(contract.id)
    except Exception as repo_error:
        logger.error(f"Repository contract upsert failed: {repo_error}", exc_info=True)
        raise ValueError("Failed to create or fetch contract record") from repo_error


async def upsert_contract_analysis(
    user_client: SupabaseClient,  # Kept for backward compatibility but not used
    *,
    content_hash: str,
    agent_version: str = "1.0",
) -> str:
    """
    Create or update an analysis row for the content hash.

    Uses AnalysesRepository with service role connection for shared analyses.
    Returns the analysis id.
    """
    # Use shared analyses repository for contract analyses
    analyses_repo = AnalysesRepository(use_service_role=True)

    try:
        analysis = await analyses_repo.upsert_analysis(
            content_hash=content_hash,
            agent_version=agent_version,
            status="pending",
            result={},
        )
        logger.info(f"Repository: Upserted contract analysis: {analysis.id}")
        return str(analysis.id)
    except Exception as repo_error:
        logger.error(f"Repository analysis upsert failed: {repo_error}", exc_info=True)
        raise ValueError("Failed to create analysis record") from repo_error


# Service factory function
def create_contract_analysis_service(
    websocket_manager: Optional[WebSocketManager] = None,
    openai_api_key: str = None,
    model_name: Optional[str] = None,
    openai_api_base: Optional[str] = None,
    use_environment_config: bool = True,
    enable_websocket_progress: bool = True,
) -> ContractAnalysisService:
    """Create unified contract analysis service with default configuration"""

    config = get_enhanced_workflow_config(use_environment_config)

    return ContractAnalysisService(
        websocket_manager=websocket_manager,
        openai_api_key=openai_api_key,
        model_name=model_name,
        openai_api_base=openai_api_base,
        config=config,
        enable_websocket_progress=enable_websocket_progress,
    )


# Export service and factory
__all__ = ["ContractAnalysisService", "create_contract_analysis_service"]
