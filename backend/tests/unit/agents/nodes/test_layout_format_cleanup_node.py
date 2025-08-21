"""
Unit tests for LayoutFormatCleanupNode

Tests the layout format cleanup functionality without LLM processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.agents.nodes.document_processing_subflow.layout_format_cleanup_node import (
    LayoutFormatCleanupNode,
)
from app.agents.subflows.document_processing_workflow import DocumentProcessingState


class TestLayoutFormatCleanupNode:
    """Test LayoutFormatCleanupNode class functionality."""

    @pytest.fixture
    def node(self):
        """Create a LayoutFormatCleanupNode instance."""
        return LayoutFormatCleanupNode(progress_range=(43, 48))

    @pytest.fixture
    def sample_state(self):
        """Create a sample document processing state."""
        return DocumentProcessingState(
            document_id="test-doc-123",
            text_extraction_result=MagicMock(
                success=True,
                full_text="""--- Page 7 ---
55 Roseville Avenue, Roseville NSW 2069[[[37.0]]]
1.[[[12.0]]]""",
            ),
        )

    @pytest.fixture
    def sample_font_mapping(self):
        """Sample font to layout mapping."""
        return {
            "10.0": "body_text",
            "11.0": "body_text",
            "12.0": "section_heading",
            "8.0": "emphasis_text",
            "9.0": "subsection_heading",
            "14.0": "emphasis_text",
            "37.0": "emphasis_text",
            "9.5": "emphasis_text",
        }

    def test_node_initialization(self, node):
        """Test that the node initializes correctly."""
        assert node.node_name == "layout_format_cleanup"
        assert hasattr(node, "font_mapper")
        assert hasattr(node, "_metrics")

    def test_apply_layout_formatting(self, node):
        """Test layout formatting application."""
        # Test main title
        assert (
            node._apply_layout_formatting("Document Title", "main_title")
            == "# Document Title"
        )

        # Test section heading
        assert (
            node._apply_layout_formatting("1. Section", "section_heading")
            == "## 1. Section"
        )

        # Test subsection heading
        assert (
            node._apply_layout_formatting("1.1 Subsection", "subsection_heading")
            == "### 1.1 Subsection"
        )

        # Test emphasis text
        assert (
            node._apply_layout_formatting("Important text", "emphasis_text")
            == "**Important text**"
        )

        # Test body text
        assert (
            node._apply_layout_formatting("Regular text", "body_text") == "Regular text"
        )

        # Test unknown layout element
        assert (
            node._apply_layout_formatting("Unknown text", "unknown") == "Unknown text"
        )

        # Test empty text
        assert node._apply_layout_formatting("", "section_heading") == ""

    def test_format_page_with_mapping(self, node, sample_font_mapping):
        """Test page formatting with font mapping."""
        page_text = """55 Roseville Avenue, Roseville NSW 2069[[[37.0]]]
1.[[[12.0]]]"""

        formatted = node._format_page_with_mapping(page_text, sample_font_mapping)

        # Should have double newlines between elements
        expected_lines = ["**55 Roseville Avenue, Roseville NSW 2069**", "", "## 1."]
        assert formatted.split("\n") == expected_lines

    @pytest.mark.asyncio
    async def test_format_text_with_layout_mapping(self, node, sample_font_mapping):
        """Test full text formatting with font mapping."""
        text = """--- Page 7 ---
55 Roseville Avenue, Roseville NSW 2069[[[37.0]]]
1.[[[12.0]]]"""

        formatted = await node._format_text_with_layout_mapping(
            text, sample_font_mapping
        )

        # Should have double newlines between pages
        expected = """**55 Roseville Avenue, Roseville NSW 2069**

## 1."""
        assert formatted == expected

    @pytest.mark.asyncio
    async def test_format_text_without_font_mapping(self, node):
        """Test text formatting when no font mapping is available."""
        text = """--- Page 7 ---
55 Roseville Avenue, Roseville NSW 2069[[[37.0]]]
1.[[[12.0]]]"""

        formatted = await node._format_text_with_layout_mapping(text, {})

        # Should remove font markers and keep text
        expected = """55 Roseville Avenue, Roseville NSW 2069

1."""
        assert formatted == expected

    def test_remove_font_markers(self, node):
        """Test font marker removal."""
        text = "Text with font[[[12.0]]] and more[[[37.0]]]"
        cleaned = node._remove_font_markers(text)
        assert cleaned == "Text with font and more"

    @patch("app.utils.font_layout_mapper.FontLayoutMapper.generate_font_layout_mapping")
    async def test_execute_success(
        self, mock_generate_mapping, node, sample_state, sample_font_mapping
    ):
        """Test successful execution of the node."""
        # Mock font mapping generation
        mock_generate_mapping.return_value = sample_font_mapping

        # Execute the node
        result_state = await node.execute(sample_state)

        # Verify font mapping was generated
        mock_generate_mapping.assert_called_once_with(
            sample_state.get("text_extraction_result").full_text
        )

        # Verify result state
        assert "layout_format_result" in result_state
        assert "formatted_text" in result_state

        layout_result = result_state["layout_format_result"]
        assert (
            layout_result.raw_text
            == sample_state.get("text_extraction_result").full_text
        )
        assert layout_result.formatted_text == result_state["formatted_text"]
        assert layout_result.font_to_layout_mapping == sample_font_mapping

        # Verify formatted text matches expected
        expected_formatted = """**55 Roseville Avenue, Roseville NSW 2069**

## 1."""
        assert result_state["formatted_text"] == expected_formatted

    async def test_execute_missing_document_id(self, node):
        """Test execution with missing document_id."""
        state = DocumentProcessingState()

        result_state = await node.execute(state)

        assert "error" in result_state
        error = result_state["error"]
        assert error["node"] == "layout_format_cleanup"
        assert "Document ID is required" in error["message"]

    async def test_execute_missing_text_extraction_result(self, node):
        """Test execution with missing text extraction result."""
        state = DocumentProcessingState(document_id="test-doc-123")

        result_state = await node.execute(state)

        assert "error" in result_state
        error = result_state["error"]
        assert error["node"] == "layout_format_cleanup"
        assert "Text extraction result is missing" in error["message"]

    async def test_execute_empty_full_text(self, node):
        """Test execution with empty full_text."""
        state = DocumentProcessingState(
            document_id="test-doc-123",
            text_extraction_result=MagicMock(success=True, full_text=""),
        )

        result_state = await node.execute(state)

        assert "error" in result_state
        error = result_state["error"]
        assert error["node"] == "layout_format_cleanup"
        assert "Full text is empty" in error["message"]

    def test_metrics_tracking(self, node):
        """Test that metrics are properly tracked."""
        # Initial state
        assert node._metrics["executions"] == 0
        assert node._metrics["successes"] == 0
        assert node._metrics["failures"] == 0

        # Record execution
        node._record_execution()
        assert node._metrics["executions"] == 1

        # Record success
        node._record_success(1.5)
        assert node._metrics["successes"] == 1
        assert node._metrics["total_duration"] == 1.5
        assert node._metrics["average_duration"] == 1.5

        # Record another success
        node._record_success(2.5)
        assert node._metrics["successes"] == 2
        assert node._metrics["total_duration"] == 4.0
        assert node._metrics["average_duration"] == 2.0

    def test_logging_methods(self, node, caplog):
        """Test logging methods work correctly."""
        with caplog.at_level("INFO"):
            node._log_info("Test info message", {"key": "value"})
            assert "Test info message - {'key': 'value'}" in caplog.text

        with caplog.at_level("WARNING"):
            node._log_warning("Test warning message")
            assert "Test warning message" in caplog.text

        with caplog.at_level("DEBUG"):
            node._log_debug("Test debug message", {"debug": "info"})
            # Debug logs might not be captured by default, so check if the method works
            # by calling it and ensuring no exception is raised
            try:
                node._log_debug("Test debug message", {"debug": "info"})
            except Exception as e:
                pytest.fail(f"Debug logging failed: {e}")

    @pytest.mark.asyncio
    async def test_edge_cases(self, node):
        """Test edge cases and boundary conditions."""
        # Test empty text
        assert await node._format_text_with_layout_mapping("", {}) == ""
        assert (
            await node._format_text_with_layout_mapping("", {"12.0": "section_heading"}) == ""
        )

        # Test text with only whitespace
        assert await node._format_text_with_layout_mapping("   \n  \n  ", {}) == ""
        assert (
            await node._format_text_with_layout_mapping(
                "   \n  \n  ", {"12.0": "section_heading"}
            )
            == ""
        )

        # Test text with only page delimiters
        page_only_text = """--- Page 1 ---
--- Page 2 ---
--- Page 3 ---"""
        assert await node._format_text_with_layout_mapping(page_only_text, {}) == ""
        assert (
            await node._format_text_with_layout_mapping(
                page_only_text, {"12.0": "section_heading"}
            )
            == ""
        )

        # Test text with mixed content and empty pages
        mixed_text = """--- Page 1 ---
Content here[[[12.0]]]

--- Page 2 ---

--- Page 3 ---
More content[[[14.0]]]"""

        # Without font mapping
        result_no_mapping = await node._format_text_with_layout_mapping(mixed_text, {})
        assert "Content here" in result_no_mapping
        assert "More content" in result_no_mapping
        assert "--- Page" not in result_no_mapping

        # With font mapping
        font_mapping = {"12.0": "section_heading", "14.0": "emphasis_text"}
        result_with_mapping = await node._format_text_with_layout_mapping(
            mixed_text, font_mapping
        )
        assert "## Content here" in result_with_mapping
        assert "**More content**" in result_with_mapping

    @pytest.mark.asyncio
    async def test_font_marker_edge_cases(self, node):
        """Test various font marker formats and edge cases."""
        # Test different font size formats
        text = """Normal text[[[12.0]]]
Decimal font[[[12.5]]]
Large font[[[100]]]
Small font[[[0.5]]]
Invalid font[[[abc]]]
No font marker"""

        font_mapping = {
            "12.0": "section_heading",
            "12.5": "emphasis_text",
            "100": "main_title",
            "0.5": "body_text",
        }
        result = await node._format_text_with_layout_mapping(text, font_mapping)

        # Should format valid font sizes
        assert "## Normal text" in result
        assert "**Decimal font**" in result
        assert "# Large font" in result
        assert "Small font" in result  # 0.5 maps to body_text

        # Should handle invalid font markers gracefully
        assert "Invalid font" in result
        assert "No font marker" in result

        # Should not contain font markers in output
        assert "[[[" not in result
        assert "]]]" not in result

    def test_page_delimiter_edge_cases(self, node):
        """Test various page delimiter formats."""
        # Test different page delimiter formats
        text = """--- Page 1 ---
Content 1

--- Page 2 ---
Content 2

--- Page 10 ---
Content 10

--- Page 999 ---
Content 999

--- Page A ---
Invalid page

--- Page ---
Invalid page 2"""

        font_mapping = {"12.0": "section_heading"}
        result = node._format_text_with_layout_mapping(text, font_mapping)

        # Should remove all page delimiters
        assert "--- Page" not in result

        # Should preserve content
        assert "Content 1" in result
        assert "Content 2" in result
        assert "Content 10" in result
        assert "Content 999" in result
        assert "Invalid page" in result
        assert "Invalid page 2" in result

    def test_layout_formatting_edge_cases(self, node):
        """Test layout formatting with edge cases."""
        # Test empty text
        assert node._apply_layout_formatting("", "section_heading") == ""
        assert node._apply_layout_formatting("", "main_title") == ""

        # Test whitespace-only text
        assert node._apply_layout_formatting("   ", "section_heading") == "##    "
        assert node._apply_layout_formatting("  \n  ", "emphasis_text") == "**  \n  **"

        # Test special characters
        special_text = "Text with @#$%^&*() symbols"
        assert (
            node._apply_layout_formatting(special_text, "section_heading")
            == f"## {special_text}"
        )
        assert (
            node._apply_layout_formatting(special_text, "emphasis_text")
            == f"**{special_text}**"
        )

        # Test newlines in text
        multiline_text = "Line 1\nLine 2\nLine 3"
        assert (
            node._apply_layout_formatting(multiline_text, "section_heading")
            == f"## {multiline_text}"
        )

        # Test unknown layout element
        assert (
            node._apply_layout_formatting("Unknown text", "unknown_element")
            == "Unknown text"
        )
