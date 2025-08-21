"""
Integration tests for LayoutSummariseNode with font mapping functionality

Tests the complete flow of font layout mapping generation and consistent usage
across document chunks.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from backend.app.agents.nodes.document_processing_subflow.layout_summarise_node_too_slow import (
    LayoutSummariseNode,
)
from app.agents.subflows.document_processing_workflow import DocumentProcessingState
from app.prompts.schema.contract_layout_summary_schema import ContractLayoutSummary
from app.schema.enums import ContractType, AustralianState


class TestLayoutSummariseNodeFontMapping:
    """Test LayoutSummariseNode with font mapping integration."""

    @pytest.fixture
    def node(self):
        """Create a LayoutSummariseNode instance for testing."""
        return LayoutSummariseNode()

    @pytest.fixture
    def sample_state(self):
        """Create a sample DocumentProcessingState for testing."""
        return DocumentProcessingState(
            document_id="test-doc-123",
            australian_state=AustralianState.NSW,
            contract_type=ContractType.PURCHASE_AGREEMENT,
            content_hash="test-hash-123",
            text_extraction_result=MagicMock(
                success=True,
                full_text="""--- Page 1 ---
PURCHASE AGREEMENT[[[24.0]]]
1. GENERAL CONDITIONS[[[18.0]]]
1.1 Definitions[[[16.0]]]
This agreement is made between the parties...[[[12.0]]]
The property address is...[[[12.0]]]

--- Page 2 ---
2. PROPERTY DETAILS[[[18.0]]]
2.1 Location[[[16.0]]]
The property is located at...[[[12.0]]]
2.2 Description[[[16.0]]]
The property consists of...[[[12.0]]]

--- Page 3 ---
Schedule A[[[16.0]]]
Additional terms and conditions...[[[12.0]]]""",
            ),
        )

    @pytest.fixture
    def mock_prompt_manager(self):
        """Mock prompt manager for testing."""
        mock_manager = AsyncMock()
        mock_manager.initialize = AsyncMock()
        mock_manager.render_composed.return_value = {
            "system_prompt": "You are a helpful assistant.",
            "user_prompt": "Process this text: {{ full_text }}",
            "model": "gpt-4",
        }
        return mock_manager

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing."""
        mock_service = AsyncMock()
        mock_service.generate_content.return_value = MagicMock(
            success=True,
            parsed_data=MagicMock(
                raw_text="Cleaned text content",
                contract_type=ContractType.PURCHASE_AGREEMENT,
                purchase_method=None,
                use_category=None,
                australian_state=AustralianState.NSW,
                contract_terms={},
                property_address=None,
                ocr_confidence={"contract_type": 0.9},
            ),
        )
        return mock_service

    @pytest.fixture
    def mock_contracts_repo(self):
        """Mock contracts repository for testing."""
        mock_repo = AsyncMock()
        mock_repo.upsert_contract_by_content_hash = AsyncMock()
        return mock_repo

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_generation_and_usage(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test that font mapping is generated and used consistently across chunks."""
        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Execute the node
        result_state = await node.execute(sample_state)

        # Verify font mapping was generated
        assert result_state.get("layout_format_result") is not None
        summary = result_state.get("layout_format_result")

        # Mapping is not part of the summary anymore
        assert not hasattr(summary, "font_to_layout_mapping")

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_consistency_across_chunks(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test that the same font mapping is used across all document chunks."""
        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Track the context passed to each chunk
        chunk_contexts = []

        async def mock_render_composed(composition_name, context, output_parser):
            chunk_contexts.append(context)
            return {
                "system_prompt": "You are a helpful assistant.",
                "user_prompt": "Process this text: {{ full_text }}",
                "model": "gpt-4",
            }

        mock_prompt_manager.render_composed = mock_render_composed

        # Execute the node
        await node.execute(sample_state)

        # Verify that multiple chunks were processed
        assert len(chunk_contexts) > 1

        # Verify font_to_layout_mapping is passed per chunk and is consistent
        first_chunk_mapping = chunk_contexts[0].get("font_to_layout_mapping")
        assert isinstance(first_chunk_mapping, dict)
        assert len(first_chunk_mapping) > 0
        for i, context in enumerate(chunk_contexts):
            assert context.get("font_to_layout_mapping") == first_chunk_mapping

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_with_no_font_markers(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test behavior when no font markers are present in the text."""
        # Modify state to have text without font markers
        sample_state[
            "text_extraction_result"
        ].full_text = """--- Page 1 ---
PURCHASE AGREEMENT
1. GENERAL CONDITIONS
1.1 Definitions
This agreement is made between the parties...
The property address is..."""

        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Execute the node
        result_state = await node.execute(sample_state)

        # Verify the node handles the case gracefully
        assert result_state.get("layout_format_result") is not None
        summary = result_state.get("layout_format_result")

        # Summary no longer contains mapping
        assert not hasattr(summary, "font_to_layout_mapping")

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_logging(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test that font mapping generation is properly logged."""
        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Mock the logger to capture log calls
        with (
            patch.object(node, "_log_info") as mock_log_info,
            patch.object(node, "_log_warning") as mock_log_warning,
        ):

            # Execute the node
            await node.execute(sample_state)

            # Verify that font mapping generation was logged
            log_calls = [call[0] for call in mock_log_info.call_args_list]
            assert any(
                "Generating font to layout mapping" in call for call in log_calls
            )
            assert any("Generated font layout mapping" in call for call in log_calls)

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_in_final_summary(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test that the final summary includes the generated font mapping."""
        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Execute the node
        result_state = await node.execute(sample_state)

        # Verify the final summary does not include font mapping
        summary = result_state.get("layout_format_result")
        assert summary is not None
        assert not hasattr(summary, "font_to_layout_mapping")

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_error_handling(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test that font mapping errors are handled gracefully."""
        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Mock the font mapper to raise an exception
        with patch.object(
            node.font_mapper,
            "generate_font_layout_mapping",
            side_effect=Exception("Font mapping error"),
        ):

            # Execute the node - should not fail
            result_state = await node.execute(sample_state)

            # Verify the node continues processing
            assert result_state.get("layout_format_result") is not None
            summary = result_state.get("layout_format_result")

            # Summary no longer contains mapping even on failure
            assert not hasattr(summary, "font_to_layout_mapping")

    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_prompt_manager"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.get_llm_service"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.create_parser"
    )
    @patch(
        "app.agents.nodes.document_processing_subflow.layout_summarise_node.ContractsRepository"
    )
    async def test_font_mapping_with_floating_point_sizes(
        self,
        mock_contracts_repo_class,
        mock_create_parser,
        mock_get_llm_service,
        mock_get_prompt_manager,
        node,
        sample_state,
        mock_prompt_manager,
        mock_llm_service,
        mock_contracts_repo,
    ):
        """Test font mapping with floating point font sizes."""
        # Modify state to have text with floating point font sizes
        sample_state[
            "text_extraction_result"
        ].full_text = """--- Page 1 ---
PURCHASE AGREEMENT[[[24.5]]]
1. GENERAL CONDITIONS[[[18.75]]]
1.1 Definitions[[[16.25]]]
This agreement is made between the parties...[[[12.5]]]
The property address is...[[[12.5]]]"""

        # Setup mocks
        mock_get_prompt_manager.return_value = mock_prompt_manager
        mock_get_llm_service.return_value = mock_llm_service
        mock_create_parser.return_value = MagicMock()
        mock_contracts_repo_class.return_value = mock_contracts_repo

        # Execute the node
        result_state = await node.execute(sample_state)

        # Verify the node handles floating point font sizes
        assert result_state.get("layout_format_result") is not None
        summary = result_state.get("layout_format_result")

        # Mapping not present in summary; ensure processing completed
        assert not hasattr(summary, "font_to_layout_mapping")
