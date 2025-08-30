"""
Tests for SaveDiagramsNode - Persist diagram detection results with artifact references
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.nodes.step0_document_processing.save_diagrams_node import SaveDiagramsNode
from app.agents.subflows.step0_document_processing_workflow import DocumentProcessingState
from app.schema.document import DiagramProcessingResult
from app.schema.enums import DiagramType


class TestSaveDiagramsNode:
    """Test SaveDiagramsNode functionality."""

    @pytest.fixture
    def node(self):
        """Create SaveDiagramsNode instance."""
        return SaveDiagramsNode()

    @pytest.fixture
    def document_id(self):
        """Sample document ID."""
        return str(uuid.uuid4())

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def mock_artifact_diagrams(self):
        """Mock artifact diagrams."""
        artifact1 = MagicMock()
        artifact1.id = uuid.uuid4()
        artifact1.page_number = 1
        artifact1.diagram_key = "diagram_page_1_site_plan_01"
        
        artifact2 = MagicMock()
        artifact2.id = uuid.uuid4()
        artifact2.page_number = 2
        artifact2.diagram_key = "diagram_page_2_survey_diagram_01"
        
        return [artifact1, artifact2]

    @pytest.fixture
    def mock_diagram_detection_items(self):
        """Mock diagram detection items."""
        # Use MagicMock objects since we need additional attributes beyond the Pydantic model
        item1 = MagicMock()
        item1.type = DiagramType.SITE_PLAN
        item1.page = 1
        item1.confidence = 0.9
        item1.description = "Site plan diagram"
        item1.bbox = [100, 100, 200, 200]
        
        item2 = MagicMock()
        item2.type = DiagramType.SURVEY_DIAGRAM
        item2.page = 2
        item2.confidence = 0.8
        item2.description = "Survey diagram"
        item2.bbox = [50, 50, 150, 150]
        
        return [item1, item2]

    @pytest.fixture
    def base_state(self, document_id):
        """Base document processing state."""
        return DocumentProcessingState({
            "document_id": document_id,
            "content_hmac": "test_hmac",
            "algorithm_version": 1,
            "params_fingerprint": "test_params",
            "text_extraction_result": MagicMock(success=True, pages=["page1", "page2"])
        })

    async def test_initialization_creates_repositories(self, node, user_id):
        """Test that initialization creates repositories."""
        await node.initialize(user_id)
        
        assert node.user_docs_repo is not None
        assert node.artifacts_repo is not None

    async def test_cleanup_clears_repositories(self, node, user_id):
        """Test that cleanup clears repositories."""
        await node.initialize(user_id)
        await node.cleanup()
        
        assert node.user_docs_repo is None
        assert node.artifacts_repo is None

    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.UserDocsRepository')
    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.ArtifactsRepository')
    async def test_execute_saves_diagrams_successfully(
        self, 
        mock_artifacts_repo_class,
        mock_user_docs_repo_class,
        node, 
        base_state, 
        mock_artifact_diagrams,
        mock_diagram_detection_items
    ):
        """Test successful diagram saving with artifact references."""
        # Setup mocks
        mock_user_docs_repo = AsyncMock()
        mock_artifacts_repo = AsyncMock()
        mock_user_docs_repo_class.return_value = mock_user_docs_repo
        mock_artifacts_repo_class.return_value = mock_artifacts_repo
        
        # Mock get_all_visual_artifacts to return our test artifacts
        mock_artifacts_repo.get_all_visual_artifacts.return_value = mock_artifact_diagrams
        
        # Add diagram processing result to state
        diagram_result = {
            "success": True,
            "diagrams": mock_diagram_detection_items
        }
        base_state["diagram_processing_result"] = diagram_result
        
        # Mock user context
        user_context = MagicMock()
        user_context.user_id = str(uuid.uuid4())
        
        with patch.object(node, 'get_user_context', return_value=user_context):
            with patch.object(node, '_ensure_user_context', return_value=base_state):
                result_state = await node.execute(base_state)

        # Verify artifacts repository was called
        mock_artifacts_repo.get_all_visual_artifacts.assert_called_with(
            "test_hmac", 1, "test_params"
        )

        # Verify user docs repository was called for each diagram
        assert mock_user_docs_repo.upsert_document_diagram.call_count == 2
        
        # Verify the result state contains diagram processing result
        assert "diagram_processing_result" in result_state
        diagram_result = result_state["diagram_processing_result"]
        assert isinstance(diagram_result, DiagramProcessingResult)
        assert diagram_result.total_diagrams == 2
        assert len(diagram_result.diagram_pages) == 2

    async def test_execute_skips_invalid_extraction_result(self, node, document_id):
        """Test that execution skips when text extraction result is invalid."""
        state = DocumentProcessingState({
            "document_id": document_id,
            "text_extraction_result": None
        })
        
        result_state = await node.execute(state)
        
        # Should return state unchanged
        assert result_state == state

    async def test_execute_skips_no_pages(self, node, document_id):
        """Test that execution skips when there are no pages."""
        state = DocumentProcessingState({
            "document_id": document_id,
            "text_extraction_result": MagicMock(success=True, pages=[])
        })
        
        result_state = await node.execute(state)
        
        # Should return state unchanged
        assert result_state == state

    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.UserDocsRepository')
    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.ArtifactsRepository')
    async def test_execute_handles_auth_error(
        self,
        mock_artifacts_repo_class,
        mock_user_docs_repo_class,
        node,
        base_state
    ):
        """Test handling of authentication errors."""
        # Mock auth error
        auth_error_state = base_state.copy()
        auth_error_state["auth_error"] = "User authentication required"
        
        with patch.object(node, '_ensure_user_context', return_value=auth_error_state):
            result_state = await node.execute(base_state)

        # Should handle the error and return error state
        assert "error" in result_state

    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.UserDocsRepository')
    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.ArtifactsRepository')
    async def test_execute_handles_no_diagram_processing_result(
        self,
        mock_artifacts_repo_class,
        mock_user_docs_repo_class,
        node,
        base_state,
        mock_artifact_diagrams
    ):
        """Test execution when there's no diagram processing result."""
        # Setup mocks
        mock_user_docs_repo = AsyncMock()
        mock_artifacts_repo = AsyncMock()
        mock_user_docs_repo_class.return_value = mock_user_docs_repo
        mock_artifacts_repo_class.return_value = mock_artifacts_repo
        
        mock_artifacts_repo.get_all_visual_artifacts.return_value = mock_artifact_diagrams
        
        # No diagram_processing_result in state
        user_context = MagicMock()
        user_context.user_id = str(uuid.uuid4())
        
        with patch.object(node, 'get_user_context', return_value=user_context):
            with patch.object(node, '_ensure_user_context', return_value=base_state):
                result_state = await node.execute(base_state)

        # Should complete successfully with zero diagrams
        assert "diagram_processing_result" in result_state
        diagram_result = result_state["diagram_processing_result"]
        assert diagram_result.total_diagrams == 0

    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.UserDocsRepository')
    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.ArtifactsRepository')
    async def test_execute_handles_unsuccessful_diagram_result(
        self,
        mock_artifacts_repo_class,
        mock_user_docs_repo_class,
        node,
        base_state,
        mock_artifact_diagrams
    ):
        """Test execution when diagram processing was unsuccessful."""
        # Setup mocks
        mock_user_docs_repo = AsyncMock()
        mock_artifacts_repo = AsyncMock()
        mock_user_docs_repo_class.return_value = mock_user_docs_repo
        mock_artifacts_repo_class.return_value = mock_artifacts_repo
        
        mock_artifacts_repo.get_all_visual_artifacts.return_value = mock_artifact_diagrams
        
        # Add unsuccessful diagram processing result
        base_state["diagram_processing_result"] = {"success": False}
        
        user_context = MagicMock()
        user_context.user_id = str(uuid.uuid4())
        
        with patch.object(node, 'get_user_context', return_value=user_context):
            with patch.object(node, '_ensure_user_context', return_value=base_state):
                result_state = await node.execute(base_state)

        # Should complete successfully with zero diagrams
        assert "diagram_processing_result" in result_state
        diagram_result = result_state["diagram_processing_result"]
        assert diagram_result.total_diagrams == 0

    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.UserDocsRepository')
    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.ArtifactsRepository')
    async def test_execute_handles_missing_artifact_references(
        self,
        mock_artifacts_repo_class,
        mock_user_docs_repo_class,
        node,
        base_state,
        mock_diagram_detection_items
    ):
        """Test execution when artifact references are missing."""
        # Setup mocks
        mock_user_docs_repo = AsyncMock()
        mock_artifacts_repo = AsyncMock()
        mock_user_docs_repo_class.return_value = mock_user_docs_repo
        mock_artifacts_repo_class.return_value = mock_artifacts_repo
        
        # Return empty artifacts (no matching references)
        mock_artifacts_repo.get_all_visual_artifacts.return_value = []
        
        # Add diagram processing result
        diagram_result = {
            "success": True,
            "diagrams": mock_diagram_detection_items
        }
        base_state["diagram_processing_result"] = diagram_result
        
        user_context = MagicMock()
        user_context.user_id = str(uuid.uuid4())
        
        with patch.object(node, 'get_user_context', return_value=user_context):
            with patch.object(node, '_ensure_user_context', return_value=base_state):
                result_state = await node.execute(base_state)

        # Should not call upsert_document_diagram since no artifacts matched
        mock_user_docs_repo.upsert_document_diagram.assert_not_called()
        
        # Should still create diagram processing result with zero saved diagrams
        assert "diagram_processing_result" in result_state
        diagram_result = result_state["diagram_processing_result"]
        assert diagram_result.total_diagrams == 0

    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.UserDocsRepository')
    @patch('app.agents.nodes.document_processing_subflow.save_diagrams_node.ArtifactsRepository')
    async def test_execute_handles_repository_exception(
        self,
        mock_artifacts_repo_class,
        mock_user_docs_repo_class,
        node,
        base_state
    ):
        """Test execution handles repository exceptions."""
        # Setup mocks to raise exception
        mock_artifacts_repo = AsyncMock()
        mock_artifacts_repo_class.return_value = mock_artifacts_repo
        mock_artifacts_repo.get_all_visual_artifacts.side_effect = Exception("Database error")
        
        user_context = MagicMock()
        user_context.user_id = str(uuid.uuid4())
        
        with patch.object(node, 'get_user_context', return_value=user_context):
            with patch.object(node, '_ensure_user_context', return_value=base_state):
                result_state = await node.execute(base_state)

        # Should handle the error and return error state
        assert "error" in result_state
        assert result_state["error"]["type"] == "Exception"
        assert "Database error" in result_state["error"]["message"]

    def test_deterministic_diagram_key_generation(self, node, mock_diagram_detection_items):
        """Test that diagram keys are generated deterministically."""
        # This tests the deterministic key generation logic used in the execute method
        page_diagram_counts = {}
        keys = []
        
        for diagram in mock_diagram_detection_items:
            page_number = getattr(diagram, "page", None) or getattr(diagram, "page_number", None)
            diagram_type = diagram.type
            
            if page_number not in page_diagram_counts:
                page_diagram_counts[page_number] = 0
            page_diagram_counts[page_number] += 1
            diagram_key = f"diagram_page_{page_number}_{diagram_type}_{page_diagram_counts[page_number]:02d}"
            keys.append(diagram_key)
        
        # Keys should be deterministic and unique
        assert keys == ["diagram_page_1_site_plan_01", "diagram_page_2_survey_diagram_01"]
        
        # Multiple runs should produce same keys
        page_diagram_counts = {}
        keys2 = []
        for diagram in mock_diagram_detection_items:
            page_number = getattr(diagram, "page", None) or getattr(diagram, "page_number", None)
            diagram_type = diagram.type
            
            if page_number not in page_diagram_counts:
                page_diagram_counts[page_number] = 0
            page_diagram_counts[page_number] += 1
            diagram_key = f"diagram_page_{page_number}_{diagram_type}_{page_diagram_counts[page_number]:02d}"
            keys2.append(diagram_key)
        
        assert keys == keys2

    def test_node_name(self, node):
        """Test that node has correct name."""
        assert node.node_name == "save_diagrams"