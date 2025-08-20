"""Test cases for RecommendationsGenerationNode."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.nodes.recommendations_generation_node import (
    RecommendationsGenerationNode,
)
from app.models.contract_state import RealEstateAgentState


class TestRecommendationsGenerationNode:
    """Test cases for recommendations generation."""

    @pytest.fixture
    def node(self):
        """Create a test node instance."""
        return RecommendationsGenerationNode()

    @pytest.fixture
    def mock_state(self):
        """Create a mock state with typical data."""
        return RealEstateAgentState(
            {
                "contract_terms": {"purchase_price": 500000},
                "compliance_analysis": {"overall_score": 0.8},
                "risk_assessment": {"overall_risk": "medium"},
                "australian_state": "NSW",
                "contract_type": "purchase_agreement",
                "user_type": "general",
                "user_experience_level": "intermediate",
                "document_metadata": {"full_text": "Sample contract text"},
            }
        )

    @pytest.fixture
    def empty_state(self):
        """Create an empty state to test error handling."""
        return RealEstateAgentState({})

    async def test_execute_with_valid_data(self, node, mock_state):
        """Test successful execution with valid data."""
        with patch.object(node, "_generate_recommendations_with_llm") as mock_llm:
            mock_llm.return_value = {
                "recommendations": [{"priority": "high", "category": "legal"}],
                "overall_confidence": 0.8,
            }

            result = await node.execute(mock_state)

            assert result is not None
            assert "recommendations_generated" in result
            mock_llm.assert_called_once()

    async def test_execute_with_empty_data(self, node, empty_state):
        """Test execution with empty data - should provide defaults."""
        with patch.object(node, "_generate_recommendations_with_llm") as mock_llm:
            mock_llm.return_value = {"recommendations": [], "overall_confidence": 0.5}

            result = await node.execute(empty_state)

            assert result is not None
            # Should have called with empty dicts as defaults
            call_args = mock_llm.call_args[0]
            assert call_args[0] == {}  # contract_terms
            assert call_args[1] == {}  # compliance_analysis
            assert call_args[2] == {}  # risk_assessment

    @patch("app.agents.nodes.recommendations_generation_node.PromptContext")
    async def test_context_variable_mapping(self, mock_context, node):
        """Test that context variables are correctly mapped for template."""
        mock_prompt_manager = AsyncMock()
        mock_prompt_manager.render.return_value = '{"recommendations": []}'
        node.prompt_manager = mock_prompt_manager

        state = RealEstateAgentState(
            {
                "user_experience_level": "novice",
                "australian_state": "VIC",
                "contract_type": "rental_agreement",
            }
        )

        await node._generate_recommendations_with_llm({}, {}, {}, state)

        # Check that PromptContext was called with correct variable mapping
        context_call = mock_context.call_args
        variables = context_call[1]["variables"]

        # Template expects 'user_experience', not 'user_experience_level'
        assert variables["user_experience"] == "novice"
        # Template expects 'compliance_check', not 'compliance_analysis'
        assert "compliance_check" in variables
        # All required variables should have defaults
        assert variables["contract_terms"] == {}
        assert variables["risk_assessment"] == {}
        assert variables["australian_state"] == "VIC"
        assert variables["contract_type"] == "rental_agreement"

    async def test_null_values_handled(self, node):
        """Test that None values are converted to empty dicts."""
        mock_prompt_manager = AsyncMock()
        mock_prompt_manager.render.return_value = '{"recommendations": []}'
        node.prompt_manager = mock_prompt_manager

        with patch(
            "app.agents.nodes.recommendations_generation_node.PromptContext"
        ) as mock_context:
            state = RealEstateAgentState({})

            await node._generate_recommendations_with_llm(None, None, None, state)

            # Check that None values were converted to empty dicts
            variables = mock_context.call_args[1]["variables"]
            assert variables["contract_terms"] == {}
            assert variables["compliance_check"] == {}
            assert variables["risk_assessment"] == {}
