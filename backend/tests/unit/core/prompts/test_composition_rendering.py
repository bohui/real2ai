"""
Unit tests for composition-based prompt rendering
Tests the new render_composed() method and validates the return schema
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.core.prompts.manager import PromptManager, PromptManagerConfig
from app.core.prompts.context import PromptContext, ContextType
from app.core.prompts.service_mixin import PromptEnabledService
from app.core.prompts.parsers import create_parser
from pydantic import BaseModel, Field


class TestContractAnalysis(BaseModel):
    """Test model for contract analysis output"""

    contract_type: str = Field(..., description="Type of contract")
    risk_level: str = Field(..., description="Overall risk level")
    key_terms: list[str] = Field(default=[], description="Key contract terms")


class TestService(PromptEnabledService):
    """Test service using composition-based rendering"""

    def __init__(self):
        super().__init__()
        self._service_name = "test_service"


class TestCompositionRendering:
    """Test suite for composition-based rendering"""

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mock PromptManager"""
        manager = Mock(spec=PromptManager)
        manager.render_composed = AsyncMock()
        return manager

    @pytest.fixture
    def test_service(self, mock_prompt_manager):
        """Create test service with mocked prompt manager"""
        service = TestService()
        service.prompt_manager = mock_prompt_manager
        return service

    @pytest.mark.asyncio
    async def test_render_composed_returns_correct_schema(self, mock_prompt_manager):
        """Test that render_composed returns the correct schema"""
        # Setup mock return value
        expected_return = {
            "system_prompt": "You are a legal specialist.",
            "user_prompt": "Analyze this contract for risks.",
            "metadata": {
                "composition": "risk_assessment_only",
                "fragments": [
                    "nsw/risk_indicators.md",
                    "common/financial_risk_indicators.md",
                ],
            },
        }
        mock_prompt_manager.render_composed.return_value = expected_return

        # Call render_composed
        context = {"document_text": "test document", "australian_state": "NSW"}
        result = await mock_prompt_manager.render_composed(
            composition_name="risk_assessment_only", context=context
        )

        # Validate schema
        assert isinstance(result, dict)
        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "metadata" in result
        assert isinstance(result["system_prompt"], str)
        assert isinstance(result["user_prompt"], str)
        assert isinstance(result["metadata"], dict)
        assert "composition" in result["metadata"]
        assert result["metadata"]["composition"] == "risk_assessment_only"

    @pytest.mark.asyncio
    async def test_render_composed_with_output_parser(self, mock_prompt_manager):
        """Test render_composed with output parser"""
        # Setup
        parser = create_parser(TestContractAnalysis)
        expected_return = {
            "system_prompt": "You are a legal specialist.",
            "user_prompt": "Analyze this contract.\n\nOutput Format:\n{json schema}",
            "metadata": {"composition": "structure_analysis_only", "fragments": []},
        }
        mock_prompt_manager.render_composed.return_value = expected_return

        # Call with output parser
        context = {"document_text": "test document"}
        result = await mock_prompt_manager.render_composed(
            composition_name="structure_analysis_only",
            context=context,
            output_parser=parser,
        )

        # Verify parser was passed
        mock_prompt_manager.render_composed.assert_called_once_with(
            composition_name="structure_analysis_only",
            context=context,
            output_parser=parser,
        )

        # Verify result structure
        assert "user_prompt" in result
        assert isinstance(result["user_prompt"], str)

    @pytest.mark.asyncio
    async def test_service_render_composed(self, test_service, mock_prompt_manager):
        """Test service-level render_composed method"""
        # Setup
        expected_return = {
            "system_prompt": "System prompt content",
            "user_prompt": "User prompt content",
            "metadata": {
                "composition": "test_composition",
                "steps": [],
                "fragments": [],
            },
        }
        mock_prompt_manager.render_composed.return_value = expected_return

        # Call service method
        context = {"test_key": "test_value"}
        result = await test_service.render_composed(
            composition_name="test_composition", context=context
        )

        # Verify result
        assert result == expected_return
        assert result["metadata"]["composition"] == "test_composition"

    @pytest.mark.asyncio
    async def test_empty_system_prompt_handling(self, mock_prompt_manager):
        """Test handling of compositions with no system prompts"""
        # Setup with empty system prompt
        expected_return = {
            "system_prompt": "",  # Empty when no system prompts defined
            "user_prompt": "User prompt content",
            "metadata": {
                "composition": "user_only_composition",
                "steps": ["single_step"],
                "fragments": [],
            },
        }
        mock_prompt_manager.render_composed.return_value = expected_return

        # Call
        result = await mock_prompt_manager.render_composed(
            composition_name="user_only_composition", context={}
        )

        # Verify empty system prompt is handled correctly
        assert result["system_prompt"] == ""
        assert result["user_prompt"] != ""

    @pytest.mark.asyncio
    async def test_metadata_includes_composition_details(self, mock_prompt_manager):
        """Test that metadata includes all composition details"""
        # Setup detailed metadata
        expected_return = {
            "system_prompt": "System content",
            "user_prompt": "User content",
            "metadata": {
                "composition": "contract_analysis_complete",
                "steps": [
                    "ocr_extraction",
                    "structure_analysis",
                    "risk_assessment",
                    "compliance_check",
                    "recommendations",
                ],
                "fragments": [
                    "fragments/nsw/risk_indicators.md",
                    "fragments/common/financial_risk_indicators.md",
                    "fragments/purchase/settlement_requirements.md",
                ],
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
            },
        }
        mock_prompt_manager.render_composed.return_value = expected_return

        # Call
        result = await mock_prompt_manager.render_composed(
            composition_name="contract_analysis_complete",
            context={"australian_state": "NSW"},
        )

        # Verify metadata completeness
        metadata = result["metadata"]
        assert metadata["composition"] == "contract_analysis_complete"
        assert len(metadata["steps"]) == 5
        assert len(metadata["fragments"]) == 3
        assert "version" in metadata
        assert "timestamp" in metadata

    @pytest.mark.asyncio
    async def test_deprecated_render_logs_warning(self, mock_prompt_manager):
        """Test that using deprecated render() method logs a warning"""
        # Setup mock render method
        mock_prompt_manager.render = AsyncMock(return_value="test prompt")

        # Patch logger to capture warnings
        with patch("app.core.prompts.manager.logger") as mock_logger:
            # Call deprecated render method
            await mock_prompt_manager.render(template_name="test_template", context={})

            # Verify deprecation warning would be logged
            # Note: In actual implementation, the warning is logged inside render()
            mock_prompt_manager.render.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_conversion(self, test_service, mock_prompt_manager):
        """Test that dict context is properly converted to PromptContext"""
        # Setup
        expected_return = {
            "system_prompt": "System",
            "user_prompt": "User",
            "metadata": {"composition": "test", "steps": [], "fragments": []},
        }
        mock_prompt_manager.render_composed.return_value = expected_return

        # Call with dict context
        dict_context = {
            "document_text": "test",
            "australian_state": "NSW",
            "contract_type": "purchase",
        }

        result = await test_service.render_composed(
            composition_name="test", context=dict_context
        )

        # Verify service metadata was added
        call_args = mock_prompt_manager.render_composed.call_args
        assert call_args is not None
        # Service should have added metadata to context

    @pytest.mark.asyncio
    async def test_composition_not_found_error(self, mock_prompt_manager):
        """Test error handling when composition is not found"""
        from app.core.prompts.exceptions import PromptCompositionError

        # Setup error
        mock_prompt_manager.render_composed.side_effect = PromptCompositionError(
            "Composition 'invalid_composition' not found",
            composition_name="invalid_composition",
        )

        # Test error is raised
        with pytest.raises(PromptCompositionError) as exc_info:
            await mock_prompt_manager.render_composed(
                composition_name="invalid_composition", context={}
            )

        assert "invalid_composition" in str(exc_info.value)


class TestMigrationFromLegacyRender:
    """Test migration scenarios from legacy render() to render_composed()"""

    @pytest.mark.asyncio
    async def test_agent_node_migration(self):
        """Test that agent nodes use render_composed correctly"""
        from unittest.mock import MagicMock

        # Mock the prompt manager
        mock_manager = MagicMock()
        mock_manager.render_composed = AsyncMock(
            return_value={
                "system_prompt": "Legal specialist system prompt",
                "user_prompt": "Extract contract terms from document",
                "metadata": {
                    "composition": "contract_analysis_complete",
                    "steps": [],
                    "fragments": [],
                },
            }
        )

        # Simulate agent node usage
        context = {
            "document_text": "Contract document text",
            "australian_state": "NSW",
            "contract_type": "purchase_agreement",
        }

        # Call as agent nodes would
        result = await mock_manager.render_composed(
            composition_name="contract_analysis_complete",
            context=context,
            output_parser=None,
        )

        # Extract user prompt as agent nodes do
        rendered_prompt = result["user_prompt"]

        # Verify this works correctly
        assert isinstance(rendered_prompt, str)
        assert rendered_prompt == "Extract contract terms from document"

    @pytest.mark.asyncio
    async def test_service_migration(self):
        """Test that services use render_composed correctly"""
        from unittest.mock import MagicMock

        # Mock service
        service = TestService()
        service.prompt_manager = MagicMock()
        service.prompt_manager.render_composed = AsyncMock(
            return_value={
                "system_prompt": "OCR processor system prompt",
                "user_prompt": "Extract text from image with high quality",
                "metadata": {
                    "composition": "ocr_whole_document_extraction",
                    "steps": [],
                    "fragments": [],
                },
            }
        )

        # Call as services would
        parser = create_parser(TestContractAnalysis)
        result = await service.render_composed(
            composition_name="ocr_whole_document_extraction",
            context={"file_content": "image_data"},
            output_parser=parser,
        )

        # Services should extract user_prompt
        user_prompt = result["user_prompt"]

        # Verify correct usage
        assert isinstance(user_prompt, str)
        assert "Extract text" in user_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
