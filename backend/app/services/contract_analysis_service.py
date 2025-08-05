"""
Enhanced Contract Analysis Service with WebSocket Integration
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, UTC

from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.models.contract_state import create_initial_state, RealEstateAgentState
from app.model.enums import AustralianState, ProcessingStatus
from app.services.websocket_service import WebSocketManager, WebSocketEvents

logger = logging.getLogger(__name__)


class ContractAnalysisService:
    """
    Enhanced contract analysis service with real-time progress tracking
    """

    def __init__(
        self,
        websocket_manager: WebSocketManager,
        openai_api_key: str,
        model_name: str = "gpt-4"
    ):
        self.websocket_manager = websocket_manager
        self.workflow = ContractAnalysisWorkflow(
            openai_api_key=openai_api_key,
            model_name=model_name
        )
        self.active_analyses: Dict[str, Dict[str, Any]] = {}

    async def start_analysis(
        self,
        user_id: str,
        session_id: str,
        document_data: Dict[str, Any],
        australian_state: AustralianState,
        user_preferences: Optional[Dict[str, Any]] = None,
        user_type: str = "buyer"
    ) -> Dict[str, Any]:
        """
        Start contract analysis with real-time progress tracking
        """
        
        try:
            # Create initial state
            initial_state = create_initial_state(
                user_id=user_id,
                australian_state=australian_state,
                user_type=user_type,
                user_preferences=user_preferences or {}
            )
            
            # Override session_id if provided
            initial_state["session_id"] = session_id
            initial_state["document_data"] = document_data
            
            # Store analysis info
            contract_id = initial_state["session_id"]
            self.active_analyses[contract_id] = {
                "start_time": datetime.now(UTC),
                "user_id": user_id,
                "session_id": session_id,
                "status": "starting",
                "progress": 0
            }
            
            # Send analysis started event
            await self.websocket_manager.send_message(
                session_id,
                WebSocketEvents.analysis_started(contract_id, estimated_time=3)
            )
            
            # Execute analysis with progress tracking
            final_state = await self._execute_with_progress_tracking(
                initial_state, session_id, contract_id
            )
            
            # Send completion event
            if final_state.get("error_state"):
                await self.websocket_manager.send_message(
                    session_id,
                    WebSocketEvents.analysis_failed(
                        contract_id,
                        final_state["error_state"],
                        retry_available=True
                    )
                )
                
                # Update analysis status
                self.active_analyses[contract_id]["status"] = "failed"
                self.active_analyses[contract_id]["error"] = final_state["error_state"]
                
            else:
                # Create analysis summary
                analysis_results = final_state.get("analysis_results", {})
                summary = {
                    "overall_confidence": analysis_results.get("overall_confidence", 0),
                    "risk_score": analysis_results.get("risk_assessment", {}).get("overall_risk_score", 0),
                    "compliance_status": analysis_results.get("compliance_check", {}).get("state_compliance", False),
                    "recommendations_count": len(analysis_results.get("recommendations", [])),
                    "processing_time": final_state.get("processing_time", 0)
                }
                
                await self.websocket_manager.send_message(
                    session_id,
                    WebSocketEvents.analysis_completed(contract_id, summary)
                )
                
                # Update analysis status
                self.active_analyses[contract_id]["status"] = "completed"
                self.active_analyses[contract_id]["summary"] = summary
            
            return {
                "success": True,
                "contract_id": contract_id,
                "session_id": session_id,
                "final_state": final_state,
                "analysis_results": final_state.get("analysis_results", {}),
                "processing_time": final_state.get("processing_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Analysis failed for session {session_id}: {str(e)}")
            
            # Send error event
            if session_id:
                await self.websocket_manager.send_message(
                    session_id,
                    WebSocketEvents.analysis_failed(
                        session_id,
                        f"Analysis service error: {str(e)}",
                        retry_available=True
                    )
                )
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }

    async def _execute_with_progress_tracking(
        self,
        initial_state: RealEstateAgentState,
        session_id: str,
        contract_id: str
    ) -> RealEstateAgentState:
        """
        Execute workflow with real-time progress updates
        """
        
        # Create a custom workflow that sends progress updates
        class ProgressTrackingWorkflow(ContractAnalysisWorkflow):
            def __init__(self, parent_service, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.parent_service = parent_service
                self.session_id = session_id
                self.contract_id = contract_id
            
            def validate_input(self, state):
                # Send progress update
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "validate_input", 14,
                    "Validating document and input parameters"
                ))
                return super().validate_input(state)
            
            def process_document(self, state):
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "process_document", 28,
                    "Processing document and extracting text content"
                ))
                return super().process_document(state)
            
            def extract_contract_terms(self, state):
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "extract_terms", 42,
                    "Extracting key contract terms using Australian tools"
                ))
                return super().extract_contract_terms(state)
            
            def analyze_australian_compliance(self, state):
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "analyze_compliance", 57,
                    "Analyzing compliance with Australian property laws"
                ))
                return super().analyze_australian_compliance(state)
            
            def assess_contract_risks(self, state):
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "assess_risks", 71,
                    "Assessing contract risks and potential issues"
                ))
                return super().assess_contract_risks(state)
            
            def generate_recommendations(self, state):
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "generate_recommendations", 85,
                    "Generating actionable recommendations"
                ))
                return super().generate_recommendations(state)
            
            def compile_analysis_report(self, state):
                asyncio.create_task(self.parent_service._send_progress_update(
                    self.session_id, self.contract_id, "compile_report", 100,
                    "Compiling final analysis report"
                ))
                return super().compile_analysis_report(state)
        
        # Create progress-tracking workflow
        progress_workflow = ProgressTrackingWorkflow(
            self,
            openai_api_key=self.workflow.llm.openai_api_key,
            model_name=self.workflow.llm.model_name
        )
        
        # Execute the workflow
        return await progress_workflow.analyze_contract(initial_state)

    async def _send_progress_update(
        self,
        session_id: str,
        contract_id: str,
        step: str,
        progress_percent: int,
        description: str
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
                )
            )
        except Exception as e:
            logger.error(f"Failed to send progress update: {str(e)}")

    async def get_analysis_status(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get current analysis status"""
        return self.active_analyses.get(contract_id)

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
                        notification_type="info"
                    )
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cancel analysis {contract_id}: {str(e)}")
            return False

    async def retry_analysis(
        self,
        contract_id: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Retry failed analysis"""
        
        # Get previous analysis data
        analysis_info = self.active_analyses.get(contract_id)
        if not analysis_info:
            return {
                "success": False,
                "error": "Analysis not found"
            }
        
        # Clear error state
        if contract_id in self.active_analyses:
            self.active_analyses[contract_id]["status"] = "retrying"
            self.active_analyses[contract_id].pop("error", None)
        
        # Send retry notification
        await self.websocket_manager.send_message(
            session_id,
            WebSocketEvents.system_notification(
                f"Retrying analysis {contract_id}",
                notification_type="info"
            )
        )
        
        # Note: In a full implementation, you would need to store and retrieve
        # the original document data and parameters to retry the analysis
        return {
            "success": True,
            "message": "Retry initiated"
        }

    def cleanup_completed_analyses(self, max_age_hours: int = 24):
        """Clean up old completed analyses"""
        cutoff_time = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
        
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
        return len([
            a for a in self.active_analyses.values()
            if a["status"] in ["starting", "processing", "retrying"]
        ])

    def get_all_analyses_summary(self) -> Dict[str, Any]:
        """Get summary of all analyses"""
        status_counts = {}
        for analysis in self.active_analyses.values():
            status = analysis["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_analyses": len(self.active_analyses),
            "status_breakdown": status_counts,
            "active_count": self.get_active_analyses_count()
        }