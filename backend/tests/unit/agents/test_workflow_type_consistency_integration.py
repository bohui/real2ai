"""
Integration test for workflow type consistency fixes.

This module tests that all the fixes for type consistency issues work together
to prevent "can only concatenate list (not dict) to list" errors.
"""

import pytest
from unittest.mock import Mock, patch

from app.agents.nodes.terms_validation_node import TermsValidationNode
from app.agents.nodes.recommendations_generation_node import (
    RecommendationsGenerationNode,
)
from app.agents.nodes.risk_assessment_node import RiskAssessmentNode
from app.agents.nodes.compliance_analysis_node import ComplianceAnalysisNode
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
            "final_recommendations": [],
            "property_data": None,
            "market_analysis": None,
            "financial_analysis": None,
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

    @pytest.mark.asyncio
    async def test_terms_validation_maintains_type_consistency(
        self, mock_workflow, sample_state, mock_validation_result
    ):
        """Test that terms validation node maintains proper type consistency."""
        node = TermsValidationNode(mock_workflow)

        # Mock the validation method
        with patch.object(
            node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result,
        ):
            node._log_step_debug = Mock()
            node._handle_node_error = Mock()
            node.update_state_step = Mock()

            # Execute the node
            result = await node.execute(sample_state)

            # Verify that validation_result is assigned correctly (should be the Pydantic model)
            assert sample_state["terms_validation_result"] == mock_validation_result
            # Verify that confidence_scores is updated with a float
            assert isinstance(
                sample_state["confidence_scores"]["terms_validation"], float
            )

    @pytest.mark.asyncio
    async def test_risk_assessment_maintains_type_consistency(
        self, mock_workflow, sample_state, mock_risk_result
    ):
        """Test that risk assessment node maintains proper type consistency."""
        node = RiskAssessmentNode(mock_workflow)

        # Mock the risk assessment method
        with patch.object(
            node, "_assess_risks_with_llm", return_value=mock_risk_result
        ):
            node._log_step_debug = Mock()
            node._handle_node_error = Mock()
            node.update_state_step = Mock()

            # Execute the node
            result = await node.execute(sample_state)

            # Verify that risk_assessment is assigned correctly (should be a dict)
            assert sample_state["risk_assessment"] == mock_risk_result
            # Verify that confidence_scores is updated with a float
            assert isinstance(
                sample_state["confidence_scores"]["risk_assessment"], float
            )
            # Verify that overall_risk_score is added
            assert "overall_risk_score" in sample_state

    @pytest.mark.asyncio
    async def test_compliance_analysis_maintains_type_consistency(
        self, mock_workflow, sample_state, mock_compliance_result
    ):
        """Test that compliance analysis node maintains proper type consistency."""
        node = ComplianceAnalysisNode(mock_workflow)

        # Mock the compliance analysis method
        with patch.object(
            node, "_analyze_compliance_with_llm", return_value=mock_compliance_result
        ):
            node._log_step_debug = Mock()
            node._handle_node_error = Mock()
            node.update_state_step = Mock()

            # Execute the node
            result = await node.execute(sample_state)

            # Verify that compliance_analysis is assigned correctly (should be a dict)
            assert sample_state["compliance_analysis"] == mock_compliance_result
            # Verify that confidence_scores is updated with a float
            assert isinstance(
                sample_state["confidence_scores"]["compliance_analysis"], float
            )

    @pytest.mark.asyncio
    async def test_recommendations_generation_maintains_type_consistency(
        self, mock_workflow, sample_state, mock_recommendations_result
    ):
        """Test that recommendations generation node maintains proper type consistency."""
        node = RecommendationsGenerationNode(mock_workflow)

        # Mock the recommendations generation method
        with patch.object(
            node,
            "_generate_recommendations_with_llm",
            return_value=mock_recommendations_result,
        ):
            node._log_step_debug = Mock()
            node._handle_node_error = Mock()
            node.update_state_step = Mock()

            # Execute the node
            result = await node.execute(sample_state)

            # Verify that recommendations is assigned correctly (should be a list)
            assert isinstance(sample_state["recommendations"], list)
            assert len(sample_state["recommendations"]) == 2
            # Verify that confidence_scores is updated with a float
            assert isinstance(
                sample_state["confidence_scores"]["recommendations"], float
            )

    @pytest.mark.asyncio
    async def test_workflow_state_evolution_maintains_types(
        self, mock_workflow, sample_state
    ):
        """Test that the workflow state maintains proper types through multiple node executions."""
        # Execute terms validation
        terms_node = TermsValidationNode(mock_workflow)
        mock_validation_result = Mock(spec=ContractTermsValidationOutput)
        mock_validation_result.validation_confidence = 0.85

        # Mock the update_state_step method to return the modified state
        def mock_update_state_step(state, step_name, data=None):
            if data:
                state.update(data)
            return state

        with patch.object(
            terms_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result,
        ):
            terms_node._log_step_debug = Mock()
            terms_node._handle_node_error = Mock()
            terms_node.update_state_step = Mock(side_effect=mock_update_state_step)

            state_after_validation = await terms_node.execute(sample_state.copy())

            # Verify types after terms validation
            assert isinstance(state_after_validation["terms_validation_result"], Mock)
            assert isinstance(
                state_after_validation["confidence_scores"]["terms_validation"], float
            )

        # Execute risk assessment
        risk_node = RiskAssessmentNode(mock_workflow)
        mock_risk_result = {
            "risk_factors": [],
            "overall_risk_level": "low",
            "overall_confidence": 0.8,
        }

        with patch.object(
            risk_node, "_assess_risks_with_llm", return_value=mock_risk_result
        ):
            risk_node._log_step_debug = Mock()
            risk_node._handle_node_error = Mock()
            risk_node.update_state_step = Mock(side_effect=mock_update_state_step)

            state_after_risk = await risk_node.execute(state_after_validation.copy())

            # Verify types after risk assessment
            assert isinstance(state_after_risk["risk_assessment"], dict)
            assert isinstance(
                state_after_risk["confidence_scores"]["risk_assessment"], float
            )

        # Execute recommendations generation
        rec_node = RecommendationsGenerationNode(mock_workflow)
        mock_rec_result = {
            "recommendations": [{"action": "Test action", "priority": "high"}],
            "overall_confidence": 0.9,
        }

        with patch.object(
            rec_node, "_generate_recommendations_with_llm", return_value=mock_rec_result
        ):
            rec_node._log_step_debug = Mock()
            rec_node._handle_node_error = Mock()
            rec_node.update_state_step = Mock(side_effect=mock_update_state_step)

            state_after_recs = await rec_node.execute(state_after_risk.copy())

            # Verify types after recommendations generation
            assert isinstance(state_after_recs["recommendations"], list)
            assert len(state_after_recs["recommendations"]) == 1
            assert isinstance(
                state_after_recs["confidence_scores"]["recommendations"], float
            )

    @pytest.mark.asyncio
    async def test_fallback_handling_maintains_type_consistency(
        self, mock_workflow, sample_state
    ):
        """Test that fallback handling maintains proper type consistency."""
        # Test recommendations generation with fallback
        node = RecommendationsGenerationNode(mock_workflow)

        # Mock LLM failure to trigger fallback
        with patch.object(
            node,
            "_generate_recommendations_with_llm",
            side_effect=Exception("LLM failed"),
        ):
            node._log_step_debug = Mock()
            node._handle_node_error = Mock()
            node.update_state_step = Mock()

            # Execute the node (should use fallback)
            result = await node.execute(sample_state)

            # Verify that fallback still maintains proper types
            assert isinstance(sample_state["recommendations"], list)
            assert isinstance(
                sample_state["confidence_scores"]["recommendations"], float
            )

    def test_state_model_annotations_are_correct(self):
        """Test that the state model has correct Annotated types for concurrent updates."""
        from app.agents.states.contract_state import RealEstateAgentState
        from typing import get_type_hints, get_origin

        # Get type hints for the state model
        type_hints = get_type_hints(RealEstateAgentState)

        # Check that list fields exist and are properly typed
        assert "current_step" in type_hints
        assert "recommendations" in type_hints
        assert "final_recommendations" in type_hints

        # Check that dict fields exist and are properly typed
        assert "analysis_results" in type_hints
        assert "confidence_scores" in type_hints

        # Check that simple fields exist
        assert "user_id" in type_hints
        assert "australian_state" in type_hints

        # Verify the types are what we expect
        assert get_origin(type_hints["current_step"]) == list
        assert get_origin(type_hints["recommendations"]) == list
        assert get_origin(type_hints["final_recommendations"]) == list
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
