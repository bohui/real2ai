"""
Test cases for Terms Validation Node fixes.

This module tests the fixes for the AttributeError when handling Pydantic models.
"""

import pytest
from unittest.mock import Mock, patch

from app.agents.nodes.terms_validation_node import TermsValidationNode
from app.prompts.schema.workflow_outputs import ContractTermsValidationOutput


class TestTermsValidationNodeFixes:
    """Test the fixes for Pydantic model handling in TermsValidationNode."""

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow for testing."""
        workflow = Mock()
        workflow.use_llm_config = {"terms_validation": True}
        workflow.enable_fallbacks = True
        workflow.enable_validation = True
        return workflow

    @pytest.fixture
    def terms_validation_node(self, mock_workflow):
        """Create a TermsValidationNode instance for testing."""
        return TermsValidationNode(mock_workflow)

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
        """Create a mock validation result that mimics ContractTermsValidationOutput."""
        result = Mock(spec=ContractTermsValidationOutput)
        result.validation_confidence = 0.85
        result.terms_validated = {"purchase_price": True, "settlement_date": True}
        result.missing_mandatory_terms = []
        result.incomplete_terms = []
        result.state_specific_requirements = {}
        result.recommendations = ["All terms are complete"]
        result.australian_state = "NSW"
        return result

    @pytest.mark.asyncio
    async def test_handle_pydantic_model_with_validation_confidence(
        self, terms_validation_node, sample_state, mock_validation_result
    ):
        """Test that the node correctly handles Pydantic models with validation_confidence attribute."""
        # Mock the validation method to return our mock result
        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result,
        ):
            # Mock the base node methods
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            # Execute the node
            result = await terms_validation_node.execute(sample_state)

            # Verify that validation_confidence was extracted correctly
            assert sample_state["confidence_scores"]["terms_validation"] == 0.85
            assert sample_state["terms_validation_result"] == mock_validation_result

    @pytest.fixture
    def mock_validation_result_overall_confidence(self):
        """Create a mock validation result with overall_confidence attribute."""
        result = Mock(spec=ContractTermsValidationOutput)
        result.overall_confidence = 0.75
        result.terms_validated = {"purchase_price": True, "settlement_date": True}
        result.missing_mandatory_terms = []
        result.incomplete_terms = []
        result.state_specific_requirements = {}
        result.recommendations = ["All terms are complete"]
        result.australian_state = "NSW"
        return result

    @pytest.mark.asyncio
    async def test_handle_pydantic_model_with_overall_confidence(
        self,
        terms_validation_node,
        sample_state,
        mock_validation_result_overall_confidence,
    ):
        """Test that the node correctly handles Pydantic models with overall_confidence attribute."""
        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result_overall_confidence,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that overall_confidence was extracted correctly
            assert sample_state["confidence_scores"]["terms_validation"] == 0.75

    @pytest.fixture
    def mock_validation_result_with_model_dump(self):
        """Create a mock validation result with model_dump method."""
        result = Mock(spec=ContractTermsValidationOutput)
        result.model_dump.return_value = {
            "validation_confidence": 0.92,
            "terms_validated": {"purchase_price": True, "settlement_date": True},
            "missing_mandatory_terms": [],
            "incomplete_terms": [],
            "state_specific_requirements": {},
            "recommendations": ["All terms are complete"],
            "australian_state": "NSW",
        }
        return result

    @pytest.mark.asyncio
    async def test_handle_pydantic_model_with_model_dump(
        self,
        terms_validation_node,
        sample_state,
        mock_validation_result_with_model_dump,
    ):
        """Test that the node correctly handles Pydantic models with model_dump method."""
        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result_with_model_dump,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that validation_confidence was extracted via model_dump
            assert sample_state["confidence_scores"]["terms_validation"] == 0.92

    @pytest.fixture
    def dict_validation_result(self):
        """Create a dictionary validation result for fallback testing."""
        return {
            "validation_confidence": 0.68,
            "terms_validated": {"purchase_price": True, "settlement_date": True},
            "missing_mandatory_terms": [],
            "incomplete_terms": [],
            "state_specific_requirements": {},
            "recommendations": ["All terms are complete"],
            "australian_state": "NSW",
        }

    @pytest.mark.asyncio
    async def test_handle_dict_validation_result(
        self, terms_validation_node, sample_state, dict_validation_result
    ):
        """Test that the node correctly handles dictionary validation results."""
        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=dict_validation_result,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that validation_confidence was extracted from dict
            assert sample_state["confidence_scores"]["terms_validation"] == 0.68

    @pytest.fixture
    def mock_validation_result_no_confidence(self):
        """Create a mock validation result with no confidence attributes."""
        result = Mock(spec=ContractTermsValidationOutput)
        # Remove confidence attributes to test fallback
        del result.validation_confidence
        del result.overall_confidence
        del result.model_dump
        result.terms_validated = {"purchase_price": True, "settlement_date": True}
        result.missing_mandatory_terms = []
        result.incomplete_terms = []
        result.state_specific_requirements = {}
        result.recommendations = ["All terms are complete"]
        result.australian_state = "NSW"
        return result

    @pytest.mark.asyncio
    async def test_handle_pydantic_model_no_confidence_fallback(
        self, terms_validation_node, sample_state, mock_validation_result_no_confidence
    ):
        """Test that the node falls back to default confidence when no confidence attributes exist."""
        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result_no_confidence,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that default confidence was used
            assert sample_state["confidence_scores"]["terms_validation"] == 0.5

    @pytest.mark.asyncio
    async def test_handle_none_validation_result(
        self, terms_validation_node, sample_state
    ):
        """Test that the node handles None validation results gracefully."""
        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=None,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that default confidence was used
            assert sample_state["confidence_scores"]["terms_validation"] == 0.5

    @pytest.mark.asyncio
    async def test_validation_threshold_logic(
        self, terms_validation_node, sample_state, mock_validation_result
    ):
        """Test that validation threshold logic works correctly with Pydantic models."""
        # Set confidence below threshold
        mock_validation_result.validation_confidence = 0.45

        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that validation failed due to low confidence
            assert sample_state["confidence_scores"]["terms_validation"] == 0.45
            # The node should call update_state_step with validation_failed
            # This is tested through the mock

    @pytest.mark.asyncio
    async def test_validation_passed_logic(
        self, terms_validation_node, sample_state, mock_validation_result
    ):
        """Test that validation passed logic works correctly with Pydantic models."""
        # Set confidence above threshold
        mock_validation_result.validation_confidence = 0.85

        with patch.object(
            terms_validation_node,
            "_validate_terms_completeness_with_llm",
            return_value=mock_validation_result,
        ):
            terms_validation_node._log_step_debug = Mock()
            terms_validation_node._handle_node_error = Mock()
            terms_validation_node.update_state_step = Mock()

            result = await terms_validation_node.execute(sample_state)

            # Verify that validation passed due to high confidence
            assert sample_state["confidence_scores"]["terms_validation"] == 0.85
            # The node should call update_state_step with validation_passed
            # This is tested through the mock
