"""
Enhanced Contract Analysis Service integrating the new workflow
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from backend.app.agents.contract_workflow import EnhancedContractAnalysisWorkflow
from app.config.enhanced_workflow_config import (
    get_enhanced_workflow_config,
    validate_workflow_configuration,
    EnhancedWorkflowConfig
)
from app.core.prompts import PromptManager, get_prompt_manager
from app.models.contract_state import RealEstateAgentState, AustralianState
from app.model.enums import ProcessingStatus

logger = logging.getLogger(__name__)


class EnhancedContractAnalysisService:
    """Enhanced service for contract analysis with improved workflow"""
    
    def __init__(
        self,
        openai_api_key: str,
        model_name: str = "gpt-4",
        openai_api_base: Optional[str] = None,
        config: Optional[EnhancedWorkflowConfig] = None,
        prompt_manager: Optional[PromptManager] = None
    ):
        """
        Initialize enhanced contract analysis service
        
        Args:
            openai_api_key: OpenAI API key
            model_name: Model to use for analysis
            openai_api_base: Optional custom API base URL
            config: Optional workflow configuration
            prompt_manager: Optional prompt manager instance
        """
        
        self.openai_api_key = openai_api_key
        self.model_name = model_name
        self.openai_api_base = openai_api_base
        
        # Initialize configuration
        self.config = config or get_enhanced_workflow_config()
        
        # Validate configuration
        config_validation = validate_workflow_configuration(self.config)
        if not config_validation["valid"]:
            logger.error(f"Configuration validation failed: {config_validation['issues']}")
            raise ValueError(f"Invalid configuration: {'; '.join(config_validation['issues'])}")
        
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
        
        # Initialize workflow
        self.workflow = EnhancedContractAnalysisWorkflow(
            openai_api_key=self.openai_api_key,
            model_name=self.model_name,
            openai_api_base=self.openai_api_base,
            prompt_manager=self.prompt_manager,
            enable_validation=self.config.enable_validation,
            enable_quality_checks=self.config.enable_quality_checks
        )
        
        # Service metrics
        self._service_metrics = {
            "total_requests": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_processing_time": 0.0,
            "configuration_errors": 0,
            "prompt_manager_errors": 0
        }
        
        logger.info(f"Enhanced contract analysis service initialized with config: {config_validation['config_summary']}")
    
    async def analyze_contract(
        self,
        document_data: Dict[str, Any],
        user_id: str,
        australian_state: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        contract_type: str = "purchase_agreement",
        user_experience: str = "novice"
    ) -> Dict[str, Any]:
        """
        Analyze contract using enhanced workflow
        
        Args:
            document_data: Document content and metadata
            user_id: ID of the user requesting analysis
            australian_state: Australian state for compliance
            user_preferences: Optional user preferences
            session_id: Optional session identifier
            contract_type: Type of contract being analyzed
            user_experience: User experience level
            
        Returns:
            Enhanced analysis results with comprehensive metadata
        """
        
        start_time = datetime.now(UTC)
        self._service_metrics["total_requests"] += 1
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = f"enhanced_analysis_{int(start_time.timestamp())}"
        
        logger.info(f"Starting enhanced contract analysis for session {session_id}")
        
        try:
            # Validate inputs
            validation_result = self._validate_analysis_inputs(
                document_data, user_id, australian_state, contract_type
            )
            
            if not validation_result["valid"]:
                error_msg = f"Input validation failed: {'; '.join(validation_result['errors'])}"
                logger.error(error_msg)
                return self._create_error_response(error_msg, session_id, start_time)
            
            # Create initial state for enhanced workflow
            initial_state = self._create_initial_state(
                document_data=document_data,
                user_id=user_id,
                australian_state=australian_state,
                user_preferences=user_preferences or {},
                session_id=session_id,
                contract_type=contract_type,
                user_experience=user_experience
            )
            
            # Initialize prompt manager if needed
            if self.prompt_manager:
                try:
                    await self.prompt_manager.initialize()
                except Exception as e:
                    logger.warning(f"Prompt manager initialization failed: {e}")
                    self._service_metrics["prompt_manager_errors"] += 1
            
            # Execute enhanced workflow
            logger.debug(f"Executing enhanced workflow for session {session_id}")
            final_state = await self.workflow.analyze_contract(initial_state)
            
            # Calculate processing time
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            
            # Update service metrics
            if final_state.get("parsing_status") == ProcessingStatus.COMPLETED:
                self._service_metrics["successful_analyses"] += 1
                logger.info(f"Enhanced analysis completed successfully in {processing_time:.2f}s")
            else:
                self._service_metrics["failed_analyses"] += 1
                logger.warning(f"Enhanced analysis failed after {processing_time:.2f}s")
            
            # Update average processing time
            self._service_metrics["average_processing_time"] = (
                (self._service_metrics["average_processing_time"] * (self._service_metrics["total_requests"] - 1) + processing_time)
                / self._service_metrics["total_requests"]
            )
            
            # Create enhanced response
            response = self._create_analysis_response(final_state, processing_time)
            
            logger.debug(f"Enhanced analysis response created for session {session_id}")
            return response
            
        except Exception as e:
            processing_time = (datetime.now(UTC) - start_time).total_seconds()
            self._service_metrics["failed_analyses"] += 1
            
            error_msg = f"Enhanced contract analysis failed: {str(e)}"
            logger.error(f"{error_msg} (processing time: {processing_time:.2f}s)")
            
            return self._create_error_response(error_msg, session_id, start_time)
    
    def _validate_analysis_inputs(
        self,
        document_data: Dict[str, Any],
        user_id: str,
        australian_state: str,
        contract_type: str
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
            AustralianState(australian_state)
        except ValueError:
            errors.append(f"Invalid Australian state: {australian_state}")
        
        # Validate contract type
        valid_contract_types = ["purchase_agreement", "lease_agreement", "rental_agreement"]
        if contract_type not in valid_contract_types:
            warnings.append(f"Unrecognized contract type: {contract_type}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _create_initial_state(
        self,
        document_data: Dict[str, Any],
        user_id: str,
        australian_state: str,
        user_preferences: Dict[str, Any],
        session_id: str,
        contract_type: str,
        user_experience: str
    ) -> RealEstateAgentState:
        """Create initial state for enhanced workflow"""
        
        return RealEstateAgentState(
            session_id=session_id,
            user_id=user_id,
            australian_state=australian_state,
            document_data=document_data,
            user_preferences=user_preferences,
            user_type="buyer",  # Default, could be parameterized
            contract_type=contract_type,
            user_experience=user_experience,
            current_step="initialized",
            agent_version="enhanced_v1.0",
            created_at=datetime.now(UTC).isoformat(),
            workflow_config={
                "validation_enabled": self.config.enable_validation,
                "quality_checks_enabled": self.config.enable_quality_checks,
                "prompt_manager_enabled": self.config.enable_prompt_manager,
                "structured_parsing_enabled": self.config.enable_structured_parsing
            },
            confidence_scores={},
            parsing_status=ProcessingStatus.PENDING
        )
    
    def _create_analysis_response(
        self,
        final_state: RealEstateAgentState,
        processing_time: float
    ) -> Dict[str, Any]:
        """Create enhanced analysis response"""
        
        analysis_results = final_state.get("analysis_results", {})
        
        # Extract key components
        risk_assessment = analysis_results.get("risk_assessment", {})
        compliance_check = analysis_results.get("compliance_check", {})
        recommendations = analysis_results.get("recommendations", [])
        
        # Create comprehensive response
        response = {
            "success": final_state.get("parsing_status") == ProcessingStatus.COMPLETED,
            "session_id": final_state.get("session_id"),
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "processing_time_seconds": processing_time,
            "workflow_version": "enhanced_v1.0",
            
            # Core analysis results
            "analysis_results": analysis_results,
            "report_data": final_state.get("report_data", {}),
            
            # Enhanced metadata
            "quality_metrics": {
                "overall_confidence": analysis_results.get("overall_confidence", 0),
                "confidence_breakdown": analysis_results.get("confidence_breakdown", {}),
                "quality_assessment": analysis_results.get("confidence_assessment", ""),
                "processing_quality": analysis_results.get("quality_metrics", {}),
                "document_quality": final_state.get("document_quality_metrics", {}),
                "validation_results": final_state.get("quality_metrics", {}).get("validation_results", {})
            },
            
            # Workflow execution details
            "workflow_metadata": {
                "steps_completed": final_state.get("progress", {}).get("current_step", 0),
                "total_steps": final_state.get("progress", {}).get("total_steps", 0),
                "progress_percentage": final_state.get("progress", {}).get("percentage", 0),
                "configuration": final_state.get("workflow_config", {}),
                "performance_metrics": self.workflow.get_workflow_metrics(),
                "service_metrics": self._service_metrics
            },
            
            # Error information (if any)
            "errors": final_state.get("error_state"),
            "warnings": self._extract_warnings_from_state(final_state),
            
            # Enhanced features status
            "enhancement_features": {
                "structured_parsing_used": True,
                "prompt_manager_used": self.config.enable_prompt_manager,
                "validation_performed": self.config.enable_validation,
                "quality_checks_performed": self.config.enable_quality_checks,
                "enhanced_error_handling": self.config.enable_enhanced_error_handling,
                "fallback_mechanisms_available": self.config.enable_fallback_mechanisms
            }
        }
        
        return response
    
    def _create_error_response(
        self,
        error_message: str,
        session_id: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Create error response"""
        
        processing_time = (datetime.now(UTC) - start_time).total_seconds()
        
        return {
            "success": False,
            "session_id": session_id,
            "error": error_message,
            "analysis_timestamp": datetime.now(UTC).isoformat(),
            "processing_time_seconds": processing_time,
            "workflow_version": "enhanced_v1.0",
            "service_metrics": self._service_metrics,
            "configuration_status": self.config.validate_config()
        }
    
    def _extract_warnings_from_state(self, state: RealEstateAgentState) -> List[str]:
        """Extract warnings from workflow state"""
        
        warnings = []
        
        # Document quality warnings
        doc_quality = state.get("document_quality_metrics", {})
        if doc_quality.get("issues_identified"):
            warnings.extend(doc_quality["issues_identified"])
        
        # Compliance warnings
        compliance_check = state.get("compliance_check", {})
        if compliance_check.get("warnings"):
            warnings.extend(compliance_check["warnings"])
        
        # Terms validation warnings
        terms_validation = state.get("terms_validation", {})
        if terms_validation.get("missing_mandatory_terms"):
            warnings.append(f"Missing mandatory terms: {', '.join(terms_validation['missing_mandatory_terms'])}")
        
        # Final output validation warnings
        final_validation = state.get("final_output_validation", {})
        if not final_validation.get("validation_passed", True):
            warnings.append("Final output validation failed")
        
        return warnings
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status"""
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": "enhanced_v1.0",
            "configuration": self.config.validate_config(),
            "metrics": self._service_metrics,
            "components": {}
        }
        
        # Check workflow health
        try:
            workflow_metrics = self.workflow.get_workflow_metrics()
            health_status["components"]["workflow"] = {
                "status": "healthy",
                "metrics": workflow_metrics
            }
        except Exception as e:
            health_status["components"]["workflow"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check prompt manager health
        if self.prompt_manager:
            try:
                pm_health = await self.prompt_manager.health_check()
                health_status["components"]["prompt_manager"] = pm_health
                if pm_health["status"] != "healthy":
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["components"]["prompt_manager"] = {
                    "status": "error",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        else:
            health_status["components"]["prompt_manager"] = {
                "status": "disabled"
            }
        
        return health_status
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        
        metrics = {
            "service_metrics": self._service_metrics,
            "configuration": self.config.validate_config(),
            "workflow_metrics": self.workflow.get_workflow_metrics() if self.workflow else {},
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        if self.prompt_manager:
            try:
                metrics["prompt_manager_metrics"] = self.prompt_manager.get_metrics()
            except Exception as e:
                metrics["prompt_manager_error"] = str(e)
        
        return metrics
    
    async def reload_configuration(self, new_config: Optional[EnhancedWorkflowConfig] = None) -> Dict[str, Any]:
        """Reload service configuration"""
        
        try:
            if new_config:
                self.config = new_config
            else:
                self.config = get_enhanced_workflow_config()
            
            # Validate new configuration
            config_validation = validate_workflow_configuration(self.config)
            if not config_validation["valid"]:
                raise ValueError(f"Invalid configuration: {'; '.join(config_validation['issues'])}")
            
            # Reload prompt manager if enabled
            if self.config.enable_prompt_manager and self.prompt_manager:
                await self.prompt_manager.reload_templates()
            
            logger.info("Service configuration reloaded successfully")
            
            return {
                "success": True,
                "message": "Configuration reloaded successfully",
                "validation": config_validation,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }


# Service factory function
def create_enhanced_contract_analysis_service(
    openai_api_key: str,
    model_name: str = "gpt-4",
    openai_api_base: Optional[str] = None,
    use_environment_config: bool = True
) -> EnhancedContractAnalysisService:
    """Create enhanced contract analysis service with default configuration"""
    
    config = get_enhanced_workflow_config(use_environment_config)
    
    return EnhancedContractAnalysisService(
        openai_api_key=openai_api_key,
        model_name=model_name,
        openai_api_base=openai_api_base,
        config=config
    )


# Export service and factory
__all__ = [
    'EnhancedContractAnalysisService',
    'create_enhanced_contract_analysis_service'
]