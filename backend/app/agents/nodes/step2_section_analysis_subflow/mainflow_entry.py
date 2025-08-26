"""
Section Analysis Node for Step 2 Contract Analysis

This node replaces ContractTermsExtractionNode with the comprehensive Step 2
section-by-section analysis workflow using LangGraph orchestration.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from app.agents.states.contract_state import RealEstateAgentState
from app.agents.subflows.step2_section_analysis_workflow import Step2AnalysisWorkflow
from ..base import BaseNode

logger = logging.getLogger(__name__)


class SectionAnalysisNode(BaseNode):
    """
    Node that executes Step 2 section-by-section contract analysis.

    This node orchestrates the comprehensive analysis workflow with:
    - Phase 1: Foundation analysis (parallel execution)
    - Phase 2: Dependent analysis (sequential with dependencies)
    - Phase 3: Synthesis analysis (sequential)
    - Cross-section validation and consistency checks

    Replaces ContractTermsExtractionNode with enhanced analysis capabilities.
    """

    def __init__(self, workflow):
        super().__init__(workflow, "section_analysis")
        self.step2_workflow = Step2AnalysisWorkflow()

    async def execute(self, state: RealEstateAgentState) -> RealEstateAgentState:
        """
        Execute Step 2 section-by-section analysis workflow.

        Args:
            state: Current workflow state with processed document and entities

        Returns:
            Updated state with comprehensive Step 2 analysis results
        """
        # Update progress
        progress_update = self._get_progress_update(state)
        state.update(progress_update)

        try:
            self._log_step_debug("Starting Step 2 section analysis", state)

            # Get required inputs
            contract_text = await self._get_contract_text(state)
            entities_result = self._get_entities_result(state)

            # Validate required inputs
            if not contract_text:
                return self._handle_node_error(
                    state,
                    Exception("No contract text available for section analysis"),
                    "Contract text is required for Step 2 analysis",
                    {"document_data_keys": list(state.get("document_data", {}).keys())},
                )

            if not entities_result:
                return self._handle_node_error(
                    state,
                    Exception("No entity extraction results available"),
                    "Entity extraction results are required for Step 2 analysis",
                    {"state_keys": list(state.keys())},
                )

            # Prepare additional context
            additional_context = self._prepare_additional_context(state)

            # Execute Step 2 workflow
            step2_results = await self.step2_workflow.execute(
                contract_text=contract_text,
                entities_extraction=entities_result,
                parent_state=state,
                **additional_context,
            )

            # Validate results
            if not step2_results or not step2_results.get("success", False):
                error_msg = step2_results.get("error", "Unknown Step 2 workflow error")
                return self._handle_node_error(
                    state,
                    Exception(error_msg),
                    "Step 2 workflow execution failed",
                    {
                        "error_type": step2_results.get("error_type"),
                        "partial_results": bool(step2_results.get("partial_results")),
                    },
                )

            # Store Step 2 results in state
            state["step2_analysis_result"] = step2_results

            # Update analysis_results for backward compatibility
            self._update_analysis_results(state, step2_results)

            # Maintain backward compatibility with contract_terms
            self._maintain_backward_compatibility(state, step2_results)

            # Calculate confidence score for the overall analysis
            confidence_score = self._calculate_overall_confidence(step2_results)
            state.setdefault("confidence_scores", {})[
                "step2_analysis"
            ] = confidence_score

            # Prepare execution data for logging
            execution_data = {
                "step2_results": step2_results,
                "total_duration": step2_results.get("total_duration_seconds", 0),
                "sections_analyzed": len(
                    [
                        v
                        for v in step2_results.get("section_results", {}).values()
                        if v is not None
                    ]
                ),
                "workflow_metadata": step2_results.get("workflow_metadata", {}),
                "confidence_score": confidence_score,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            self._log_step_debug(
                f"Step 2 section analysis completed successfully in {step2_results.get('total_duration_seconds', 0):.1f}s",
                state,
                {
                    "sections_completed": len(
                        [
                            v
                            for v in step2_results.get("section_results", {}).values()
                            if v is not None
                        ]
                    ),
                    "confidence_score": confidence_score,
                    "phases_completed": step2_results.get("workflow_metadata", {}).get(
                        "phases_completed", {}
                    ),
                },
            )

            return self.update_state_step(
                state, "section_analysis_complete", data=execution_data
            )

        except Exception as e:
            return self._handle_node_error(
                state,
                e,
                f"Section analysis failed: {str(e)}",
                {"node": "section_analysis", "step": "step2_workflow_execution"},
            )

    async def _get_contract_text(self, state: RealEstateAgentState) -> Optional[str]:
        """
        Get contract text from state or repository.

        Reuses logic from ContractTermsExtractionNode for consistency.
        """
        # Check document metadata first
        document_metadata = state.get("document_metadata", {})
        full_text = document_metadata.get("full_text", "")

        if full_text:
            return full_text

        # Fall back to repository access (same logic as original node)
        try:
            document_data = state.get("document_data", {})
            document_id = document_data.get("document_id")

            if not document_id:
                logger.warning("No document_id available for repository access")
                return None

            # Import repositories and services
            from app.services.repositories.documents_repository import (
                DocumentsRepository,
            )
            from app.services.repositories.artifacts_repository import (
                ArtifactsRepository,
            )
            from app.utils.storage_utils import ArtifactStorageService
            from app.core.auth_context import AuthContext

            # Get user ID
            user_id = AuthContext.get_user_id() or state.get("user_id")
            if not user_id:
                logger.warning("No user_id available for repository access")
                return None

            # Get document and retrieve text
            documents_repo = DocumentsRepository(user_id=user_id)
            document = await documents_repo.get_document(document_id)

            if not document or not document.artifact_text_id:
                logger.warning(f"Document or text artifact not found: {document_id}")
                return None

            # Get full text artifact
            artifacts_repo = ArtifactsRepository()
            full_text_artifact = await artifacts_repo.get_full_text_artifact_by_id(
                document.artifact_text_id
            )

            if not full_text_artifact:
                logger.warning(
                    f"Full text artifact not found: {document.artifact_text_id}"
                )
                return None

            # Download text content
            storage_service = ArtifactStorageService()
            full_text = await storage_service.download_text_blob(
                full_text_artifact.full_text_uri
            )

            self._log_step_debug(
                "Successfully retrieved contract text from artifact storage",
                state,
                {
                    "document_id": document_id,
                    "text_length": len(full_text),
                    "total_pages": full_text_artifact.total_pages,
                },
            )

            return full_text

        except Exception as e:
            logger.error(f"Failed to retrieve contract text from repository: {str(e)}")
            return None

    def _get_entities_result(
        self, state: RealEstateAgentState
    ) -> Optional[Dict[str, Any]]:
        """Get entities extraction result from state"""
        return state.get("entities_extraction") or state.get("entities_result")

    def _prepare_additional_context(
        self, state: RealEstateAgentState
    ) -> Dict[str, Any]:
        """Prepare additional context for Step 2 workflow execution"""
        context = {}

        # Add legal requirements matrix if available
        legal_requirements = state.get("legal_requirements")
        if legal_requirements:
            context["legal_requirements_matrix"] = legal_requirements

        # Add uploaded diagrams if available (future enhancement)
        # context["uploaded_diagrams"] = state.get("uploaded_diagrams")

        # Add any other relevant context
        context["execution_timestamp"] = datetime.now(UTC).isoformat()

        return context

    def _update_analysis_results(
        self, state: RealEstateAgentState, step2_results: Dict[str, Any]
    ) -> None:
        """Update analysis_results structure with Step 2 data"""
        if "analysis_results" not in state:
            state["analysis_results"] = {}

        # Add Step 2 specific results to analysis_results
        state["analysis_results"]["step2"] = {
            "section_results": step2_results.get("section_results", {}),
            "cross_section_validation": step2_results.get(
                "cross_section_validation", {}
            ),
            "workflow_metadata": step2_results.get("workflow_metadata", {}),
            "timestamp": step2_results.get("timestamp"),
            "total_duration_seconds": step2_results.get("total_duration_seconds", 0),
        }

    def _maintain_backward_compatibility(
        self, state: RealEstateAgentState, step2_results: Dict[str, Any]
    ) -> None:
        """
        Maintain backward compatibility by populating contract_terms structure.

        This ensures existing consumers of contract_terms continue to work
        while transitioning to the new Step 2 structure.
        """
        try:
            section_results = step2_results.get("section_results", {})

            # Extract key data from section results for contract_terms compatibility
            parties_result = section_results.get("parties_property", {})
            financial_result = section_results.get("financial_terms", {})
            conditions_result = section_results.get("conditions", {})

            # Build backward-compatible contract_terms structure
            contract_terms = {
                "extraction_method": "step2_section_analysis",
                "confidence": self._calculate_overall_confidence(step2_results),
                "timestamp": datetime.now(UTC).isoformat(),
                # Extract data from section results (placeholder until sections implemented)
                "purchase_price": self._extract_field(
                    financial_result, "purchase_price"
                ),
                "deposit_amount": self._extract_field(
                    financial_result, "deposit_amount"
                ),
                "settlement_date": self._extract_field(
                    financial_result, "settlement_date"
                ),
                "property_address": self._extract_field(
                    parties_result, "property_address"
                ),
                "vendor_details": self._extract_field(
                    parties_result, "vendor_details", {}
                ),
                "purchaser_details": self._extract_field(
                    parties_result, "purchaser_details", {}
                ),
                "special_conditions": self._extract_field(
                    conditions_result, "special_conditions", []
                ),
                # Metadata about Step 2 analysis
                "step2_metadata": {
                    "total_sections_analyzed": len(
                        [v for v in section_results.values() if v is not None]
                    ),
                    "phases_completed": step2_results.get("workflow_metadata", {}).get(
                        "phases_completed", {}
                    ),
                    "processing_errors": step2_results.get("workflow_metadata", {}).get(
                        "processing_errors", []
                    ),
                },
            }

            state["contract_terms"] = contract_terms

        except Exception as e:
            logger.warning(
                f"Failed to maintain backward compatibility for contract_terms: {str(e)}"
            )
            # Fallback minimal structure
            state["contract_terms"] = {
                "extraction_method": "step2_section_analysis",
                "confidence": 0.5,
                "error": "Backward compatibility extraction failed",
                "step2_available": True,
            }

    def _extract_field(
        self, section_result: Dict[str, Any], field_name: str, default_value: Any = None
    ) -> Any:
        """
        Extract a field from section result data.

        This is a placeholder that will be refined as section implementations are completed.
        """
        if not section_result or section_result.get("status") == "placeholder":
            return default_value

        return section_result.get("findings", {}).get(field_name, default_value)

    def _calculate_overall_confidence(self, step2_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score for Step 2 analysis"""
        try:
            section_results = step2_results.get("section_results", {})
            workflow_metadata = step2_results.get("workflow_metadata", {})

            # Base confidence from successful completion
            base_confidence = 0.8 if step2_results.get("success") else 0.3

            # Adjust for completed phases
            phases_completed = workflow_metadata.get("phases_completed", {})
            phase_completion_score = sum(
                [
                    0.3 if phases_completed.get("phase1") else 0,
                    0.3 if phases_completed.get("phase2") else 0,
                    0.4 if phases_completed.get("phase3") else 0,
                ]
            )

            # Adjust for sections with actual results (vs placeholders)
            completed_sections = len(
                [
                    v
                    for v in section_results.values()
                    if v is not None and v.get("status") != "placeholder"
                ]
            )
            total_sections = len(section_results)
            section_completion_score = (
                (completed_sections / max(total_sections, 1)) * 0.2
                if total_sections > 0
                else 0
            )

            # Adjust for errors
            error_count = len(workflow_metadata.get("processing_errors", []))
            error_penalty = min(error_count * 0.1, 0.3)

            # Final confidence calculation
            final_confidence = (
                base_confidence * 0.4
                + phase_completion_score * 0.4
                + section_completion_score * 0.2
                - error_penalty
            )

            return max(0.0, min(1.0, final_confidence))

        except Exception as e:
            logger.warning(f"Failed to calculate overall confidence: {str(e)}")
            return 0.5
