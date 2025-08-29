"""
Unit tests for ErrorHandlingNode in contract analysis workflow.

This module tests the ErrorHandlingNode class that handles workflow errors
and failures in the contract analysis workflow.
"""

import pytest
from unittest.mock import Mock, patch

from app.agents.nodes.error_handling_node import ErrorHandlingNode
from app.agents.states.contract_state import RealEstateAgentState
from app.schema.enums import ProcessingStatus


class TestErrorHandlingNode:
    """Test cases for ErrorHandlingNode in contract analysis workflow."""

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow for testing."""
        workflow = Mock()
        workflow.config = Mock()
        return workflow

    @pytest.fixture
    def error_handling_node(self, mock_workflow):
        """Create ErrorHandlingNode instance for testing."""
        return ErrorHandlingNode(mock_workflow)

    @pytest.fixture
    def sample_state(self) -> RealEstateAgentState:
        """Create a sample state with error information."""
        return {
            "session_id": "test-session-123",
            "user_id": "test-user-456",
            "australian_state": "NSW",
            "user_type": "buyer",
            "contract_type": "purchase_agreement",
            "document_data": {"content": "test content"},
            "current_step": ["initialized"],
            "agent_version": "1.0",
            "parsing_status": ProcessingStatus.PENDING,
            "contract_terms": None,
            "risk_assessment": None,
            "compliance_check": None,
            "recommendations": [],
            "user_preferences": {},
            "error_state": None,
            "confidence_scores": {},
            "processing_time": None,
            "progress": {
                "percentage": 50,
                "step": "processing",
                "step_history": [
                    {"step": "extract_terms", "status": "completed"},
                    {
                        "step": "analyze_risk",
                        "status": "failed",
                        "error": "API timeout",
                    },
                ],
            },
            "report_data": None,
            "final_recommendations": [],
            "ocr_processing": {},
        }

    @pytest.fixture
    def state_with_none_progress(self) -> RealEstateAgentState:
        """Create a state where progress is None - this tests the bug scenario."""
        return {
            "session_id": "test-session-456",
            "user_id": "test-user-789",
            "australian_state": "VIC",
            "user_type": "investor",
            "contract_type": "lease_agreement",
            "document_data": {"content": "test content"},
            "current_step": ["initialized"],
            "agent_version": "1.0",
            "parsing_status": ProcessingStatus.PENDING,
            "contract_terms": None,
            "risk_assessment": None,
            "compliance_check": None,
            "recommendations": [],
            "user_preferences": {},
            "error_state": None,
            "confidence_scores": {},
            "processing_time": None,
            "progress": None,  # This is the bug scenario
            "report_data": None,
            "final_recommendations": [],
            "ocr_processing": {},
        }

    @pytest.fixture
    def state_with_empty_progress(self) -> RealEstateAgentState:
        """Create a state with empty progress dictionary."""
        return {
            "session_id": "test-session-789",
            "user_id": "test-user-012",
            "australian_state": "QLD",
            "user_type": "agent",
            "contract_type": "purchase_agreement",
            "document_data": {"content": "test content"},
            "current_step": ["initialized"],
            "agent_version": "1.0",
            "parsing_status": ProcessingStatus.PENDING,
            "contract_terms": None,
            "risk_assessment": None,
            "compliance_check": None,
            "recommendations": [],
            "user_preferences": {},
            "error_state": None,
            "confidence_scores": {},
            "processing_time": None,
            "progress": {},  # Empty progress
            "report_data": None,
            "final_recommendations": [],
            "ocr_processing": {},
        }

    @pytest.fixture
    def state_with_error(self) -> RealEstateAgentState:
        """Create a state with explicit error information."""
        return {
            "session_id": "test-session-error",
            "user_id": "test-user-error",
            "australian_state": "WA",
            "user_type": "buyer",
            "contract_type": "purchase_agreement",
            "document_data": {"content": "test content"},
            "current_step": ["initialized"],
            "agent_version": "1.0",
            "parsing_status": ProcessingStatus.PENDING,
            "contract_terms": None,
            "risk_assessment": None,
            "compliance_check": None,
            "recommendations": [],
            "user_preferences": {},
            "error_state": None,
            "confidence_scores": {},
            "processing_time": None,
            "progress": {
                "percentage": 75,
                "step": "validation",
                "step_history": [
                    {"step": "extract_terms", "status": "completed"},
                    {"step": "analyze_risk", "status": "completed"},
                    {
                        "step": "validation",
                        "status": "failed",
                        "error": "Validation failed",
                    },
                ],
            },
            "error": "Contract validation error",  # Explicit error field
            "report_data": None,
            "final_recommendations": [],
            "ocr_processing": {},
        }

    @pytest.mark.asyncio
    async def test_execute_successful_error_handling(
        self, error_handling_node, sample_state
    ):
        """Test successful error handling execution."""
        # Act
        result = await error_handling_node.execute(sample_state)

        # Assert
        assert "error_report" in result
        assert result["processing_status"] == ProcessingStatus.FAILED
        assert (
            result["error_report"]["error_category"] == "api_error"
        )  # "API timeout" should categorize as api_error
        assert result["error_report"]["recoverable"] is True
        assert len(result["error_report"]["recovery_options"]) > 0

    @pytest.mark.asyncio
    async def test_execute_with_none_progress(
        self, error_handling_node, state_with_none_progress
    ):
        """Test error handling when progress is None - this tests the bug fix."""
        # Act
        result = await error_handling_node.execute(state_with_none_progress)

        # Assert - should not crash, should handle gracefully
        assert "error_report" in result
        assert result["processing_status"] == ProcessingStatus.FAILED
        assert (
            result["error_report"]["error_category"] == "system_error"
        )  # Default category
        assert (
            result["error_report"]["recoverable"] is True
        )  # Has recovery options (contact_support + manual_review)

    @pytest.mark.asyncio
    async def test_execute_with_empty_progress(
        self, error_handling_node, state_with_empty_progress
    ):
        """Test error handling when progress is empty dictionary."""
        # Act
        result = await error_handling_node.execute(state_with_empty_progress)

        # Assert
        assert "error_report" in result
        assert result["processing_status"] == ProcessingStatus.FAILED
        assert result["error_report"]["error_category"] == "system_error"
        assert result["error_report"]["recoverable"] is True

    @pytest.mark.asyncio
    async def test_execute_with_explicit_error(
        self, error_handling_node, state_with_error
    ):
        """Test error handling when state has explicit error field."""
        # Act
        result = await error_handling_node.execute(state_with_error)

        # Assert
        assert "error_report" in result
        assert result["processing_status"] == ProcessingStatus.FAILED
        assert result["error_report"]["error_category"] == "validation_error"
        assert result["error_report"]["recoverable"] is True
        assert (
            "Contract validation error"
            in result["error_report"]["error_info"]["error_message"]
        )

    @pytest.mark.asyncio
    async def test_extract_error_info_with_none_progress(
        self, error_handling_node, state_with_none_progress
    ):
        """Test _extract_error_info method with None progress - critical bug test."""
        # Act
        error_info = error_handling_node._extract_error_info(state_with_none_progress)

        # Assert - should not crash, should return default error info
        assert error_info["error_message"] == "Unknown error"
        assert error_info["error_step"] == "unknown"
        assert error_info["error_type"] == "system_error"
        assert error_info["session_id"] == "test-session-456"

    @pytest.mark.asyncio
    async def test_extract_error_info_with_empty_progress(
        self, error_handling_node, state_with_empty_progress
    ):
        """Test _extract_error_info method with empty progress."""
        # Act
        error_info = error_handling_node._extract_error_info(state_with_empty_progress)

        # Assert
        assert error_info["error_message"] == "Unknown error"
        assert error_info["error_step"] == "unknown"
        assert error_info["error_type"] == "system_error"

    @pytest.mark.asyncio
    async def test_extract_error_info_with_step_history(
        self, error_handling_node, sample_state
    ):
        """Test _extract_error_info method with step history containing errors."""
        # Act
        error_info = error_handling_node._extract_error_info(sample_state)

        # Assert
        assert error_info["error_message"] == "API timeout"
        assert error_info["error_step"] == "analyze_risk"
        assert error_info["error_type"] == "system_error"

    @pytest.mark.asyncio
    async def test_extract_error_info_with_explicit_error(
        self, error_handling_node, state_with_error
    ):
        """Test _extract_error_info method with explicit error field."""
        # Act
        error_info = error_handling_node._extract_error_info(state_with_error)

        # Assert
        assert error_info["error_message"] == "Contract validation error"
        assert error_info["error_step"] == "validation"
        assert error_info["error_type"] == "system_error"

    def test_categorize_error_document_errors(self, error_handling_node):
        """Test error categorization for document-related errors."""
        # Test missing document
        error_info = {
            "error_message": "Document not found",
            "error_step": "document_processing",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "missing_document"

        # Test document processing error
        error_info = {
            "error_message": "Document processing failed",
            "error_step": "extract_text",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "document_processing_error"

        # Test general document error
        error_info = {
            "error_message": "Document format invalid",
            "error_step": "validation",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "document_error"

    def test_categorize_error_api_errors(self, error_handling_node):
        """Test error categorization for API-related errors."""
        # Test OpenAI API error
        error_info = {
            "error_message": "OpenAI API rate limit exceeded",
            "error_step": "llm_call",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "api_error"

        # Test Gemini API error
        error_info = {
            "error_message": "Gemini API timeout",
            "error_step": "extract_terms",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "api_error"

        # Test general LLM error
        error_info = {
            "error_message": "LLM processing failed",
            "error_step": "analysis",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "api_error"

    def test_categorize_error_validation_errors(self, error_handling_node):
        """Test error categorization for validation errors."""
        error_info = {
            "error_message": "Contract validation failed",
            "error_step": "validation",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "validation_error"

    def test_categorize_error_extraction_errors(self, error_handling_node):
        """Test error categorization for extraction errors."""
        error_info = {
            "error_message": "Failed to extract contract terms",
            "error_step": "extraction",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "extraction_error"

    def test_categorize_error_configuration_errors(self, error_handling_node):
        """Test error categorization for configuration errors."""
        error_info = {
            "error_message": "Missing configuration",
            "error_step": "initialization",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "configuration_error"

    def test_categorize_error_default_category(self, error_handling_node):
        """Test error categorization defaults to system_error."""
        error_info = {
            "error_message": "Unknown error occurred",
            "error_step": "unknown",
        }
        category = error_handling_node._categorize_error(error_info)
        assert category == "system_error"

    def test_determine_recovery_options_missing_document(self, error_handling_node):
        """Test recovery options for missing document errors."""
        error_info = {
            "error_message": "Document not found",
            "error_step": "document_processing",
        }
        error_category = "missing_document"

        recovery_options = error_handling_node._determine_recovery_options(
            error_info, error_category
        )

        assert len(recovery_options) == 3  # 2 specific + 1 general manual_review
        assert any(
            opt["option"] == "request_document_reupload" for opt in recovery_options
        )
        assert any(opt["option"] == "check_document_id" for opt in recovery_options)
        assert any(opt["option"] == "manual_review" for opt in recovery_options)

    def test_determine_recovery_options_api_error(self, error_handling_node):
        """Test recovery options for API errors."""
        error_info = {"error_message": "API timeout", "error_step": "llm_call"}
        error_category = "api_error"

        recovery_options = error_handling_node._determine_recovery_options(
            error_info, error_category
        )

        assert len(recovery_options) == 3  # 2 specific + 1 general manual_review
        assert any(opt["option"] == "retry_with_backoff" for opt in recovery_options)
        assert any(
            opt["option"] == "fallback_to_rule_based" for opt in recovery_options
        )
        assert any(opt["option"] == "manual_review" for opt in recovery_options)

    def test_determine_recovery_options_validation_error(self, error_handling_node):
        """Test recovery options for validation errors."""
        error_info = {"error_message": "Validation failed", "error_step": "validation"}
        error_category = "validation_error"

        recovery_options = error_handling_node._determine_recovery_options(
            error_info, error_category
        )

        assert len(recovery_options) == 3  # 2 specific + 1 general manual_review
        assert any(opt["option"] == "skip_validation" for opt in recovery_options)
        assert any(opt["option"] == "manual_validation" for opt in recovery_options)
        assert any(opt["option"] == "manual_review" for opt in recovery_options)

    def test_determine_recovery_options_system_error(self, error_handling_node):
        """Test recovery options for system errors."""
        error_info = {"error_message": "Unknown system error", "error_step": "unknown"}
        error_category = "system_error"

        recovery_options = error_handling_node._determine_recovery_options(
            error_info, error_category
        )

        assert len(recovery_options) == 2  # 1 specific + 1 general manual_review
        assert any(opt["option"] == "contact_support" for opt in recovery_options)
        assert any(opt["option"] == "manual_review" for opt in recovery_options)

    @pytest.mark.asyncio
    async def test_execute_critical_error_handling(
        self, error_handling_node, sample_state
    ):
        """Test error handling when the error handling itself fails."""
        # Mock _extract_error_info to raise an exception
        with patch.object(
            error_handling_node,
            "_extract_error_info",
            side_effect=Exception("Critical failure"),
        ):
            # Act
            result = await error_handling_node.execute(sample_state)

            # Assert - should handle critical errors gracefully
            assert "error_handling_error" in result.get("current_step", [])
            assert result.get("error_state") is not None
            assert "Critical failure" in str(result.get("error_state", ""))

    @pytest.mark.asyncio
    async def test_execute_with_missing_session_id(self, error_handling_node):
        """Test error handling when session_id is missing."""
        state = {
            "user_id": "test-user",
            "australian_state": "NSW",
            "user_type": "buyer",
            "contract_type": "purchase_agreement",
            "document_data": {"content": "test content"},
            "current_step": ["initialized"],
            "agent_version": "1.0",
            "parsing_status": ProcessingStatus.PENDING,
            "contract_terms": None,
            "risk_assessment": None,
            "compliance_check": None,
            "recommendations": [],
            "user_preferences": {},
            "error_state": None,
            "confidence_scores": {},
            "processing_time": None,
            "progress": None,
            "report_data": None,
            "final_recommendations": [],
            "document_metadata": {},
        }

        # Act
        result = await error_handling_node.execute(state)

        # Assert - should handle missing session_id gracefully
        assert "error_report" in result
        assert result["error_report"]["error_info"]["session_id"] == "unknown"

    def test_error_handling_node_initialization(self, mock_workflow):
        """Test ErrorHandlingNode initialization."""
        node = ErrorHandlingNode(mock_workflow)
        assert node.node_name == "error_handling"
        assert node.workflow == mock_workflow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
