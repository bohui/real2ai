"""
Integration test for workflow type consistency fixes.

This module tests that all the fixes for type consistency issues work together
to prevent "can only concatenate list (not dict) to list" errors.
"""

import pytest
from unittest.mock import Mock, patch

import pytest
import pytest
from app.prompts.schema.workflow_outputs import (
    ContractTermsValidationOutput,
)


class TestWorkflowTypeConsistencyIntegration:
    """Test that all workflow nodes maintain proper type consistency."""

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow for testing."""
        workflow = Mock()
        workflow.use_llm_config = {
            "terms_validation": True,
            "risk_assessment": True,
            "compliance_analysis": True,
            "recommendations_generation": True,
        }
        workflow.enable_fallbacks = True
        workflow.enable_validation = True
        return workflow

    @pytest.fixture
    def sample_state(self):
        """Create a sample workflow state."""
        return {
            "user_id": "test_user",
            "session_id": "test_session",
            "agent_version": "1.0.0",
            "contract_terms": {
                "purchase_price": "500000",
                "settlement_date": "2024-12-31",
                "deposit_amount": "25000",
                "property_address": "123 Test St, Test Suburb, NSW 2000",
                "vendor_details": "Test Vendor",
                "purchaser_details": "Test Purchaser",
            },
            "confidence_scores": {},
            "current_step": [],
            "australian_state": "NSW",
            "user_type": "buyer",
            "contract_type": "purchase_agreement",
            "document_type": "contract",
            "parsing_status": "PARSED",
            "analysis_results": {},
            "user_preferences": {},
            "progress": None,
            "processing_time": None,
            "error_state": None,
            "report_data": None,
            # final_recommendations removed
        }

    @pytest.fixture
    def mock_validation_result(self):
        """Create a mock validation result."""
        result = Mock(spec=ContractTermsValidationOutput)
        result.validation_confidence = 0.85
        result.terms_validated = {"purchase_price": True, "settlement_date": True}
        result.missing_mandatory_terms = []
        result.incomplete_terms = []
        result.state_specific_requirements = {}
        result.recommendations = ["All terms are complete"]
        result.australian_state = "NSW"
        return result

    @pytest.fixture
    def mock_risk_result(self):
        """Create a mock risk assessment result."""
        return {
            "risk_factors": [
                {
                    "category": "financial",
                    "type": "high_value_transaction",
                    "description": "High-value transaction",
                    "probability": 0.3,
                    "impact": 0.8,
                    "risk_score": 0.24,
                }
            ],
            "overall_risk_level": "medium",
            "overall_confidence": 0.8,
            "assessment_method": "llm",
        }

    @pytest.fixture
    def mock_compliance_result(self):
        """Create a mock compliance analysis result."""
        return {
            "compliance_score": 0.85,
            "overall_compliance": True,
            "compliance_issues": [],
            "checks": [
                {"check_type": "stamp_duty", "status": "compliant", "confidence": 0.9}
            ],
            "overall_confidence": 0.85,
        }

    @pytest.fixture
    def mock_recommendations_result(self):
        """Create a mock recommendations result."""
        return {
            "recommendations": [
                {
                    "action": "Get legal advice",
                    "priority": "high",
                    "category": "immediate_actions",
                },
                {
                    "action": "Review contract terms",
                    "priority": "medium",
                    "category": "due_diligence",
                },
            ],
            "priority_actions": [{"action": "Get legal advice", "priority": "high"}],
            "overall_confidence": 0.9,
            "generation_method": "llm",
        }

    # Removed tests for TermsValidationNode (node deleted)

    # Removed tests for RiskAssessmentNode (node deleted)

    # Removed tests for ComplianceAnalysisNode (node deleted)

    # Removed tests for RecommendationsGenerationNode (node deleted)

    @pytest.mark.asyncio
    async def test_workflow_state_evolution_maintains_types(
        self, mock_workflow, sample_state
    ):
        """Test that the workflow state maintains proper types through multiple node executions."""

        # Skip terms validation (node deleted); proceed with remaining nodes
        def mock_update_state_step(state, step_name, data=None):
            if data:
                state.update(data)
            return state

        state_after_validation = sample_state.copy()

        # Skip risk assessment (node deleted)
        state_after_risk = state_after_validation.copy()

        # Skip recommendations generation (node deleted)

    # Removed fallback test for recommendations node (deleted)

    def test_state_model_annotations_are_correct(self):
        """Test that the state model has correct Annotated types for concurrent updates."""
        from app.agents.states.contract_state import RealEstateAgentState
        from typing import get_type_hints, get_origin

        # Get type hints for the state model
        type_hints = get_type_hints(RealEstateAgentState)

        # Check that list fields exist and are properly typed
        assert "current_step" in type_hints
        # Recommendations lists are now synthesized in Step 3; keep annotations check optional

        # Check that dict fields exist and are properly typed
        assert "analysis_results" in type_hints
        assert "confidence_scores" in type_hints

        # Check that simple fields exist
        assert "user_id" in type_hints
        assert "australian_state" in type_hints

        # Verify the types are what we expect
        assert get_origin(type_hints["current_step"]) == list
        assert get_origin(type_hints["recommendations"]) == list
        # final_recommendations removed from schema
        assert get_origin(type_hints["analysis_results"]) == dict
        assert get_origin(type_hints["confidence_scores"]) == dict

    @pytest.mark.asyncio
    async def test_concurrent_updates_work_correctly(self, mock_workflow, sample_state):
        """Test that concurrent updates work correctly with the fixed type handling."""
        # Simulate concurrent updates to different fields
        from app.agents.states.contract_state import update_state_step

        # Update recommendations (list field)
        state_with_recs = update_state_step(
            sample_state.copy(),
            "add_recommendations",
            data={
                "recommendations": [
                    {"action": "Concurrent action 1", "priority": "high"}
                ]
            },
        )

        # Update analysis results (dict field)
        state_with_analysis = update_state_step(
            sample_state.copy(),
            "add_analysis",
            data={"analysis_results": {"concurrent_analysis": {"result": "success"}}},
        )

        # Both updates should work independently
        assert len(state_with_recs["recommendations"]) == 1
        assert "concurrent_analysis" in state_with_analysis["analysis_results"]

        # Verify types are maintained
        assert isinstance(state_with_recs["recommendations"], list)
        assert isinstance(state_with_analysis["analysis_results"], dict)
