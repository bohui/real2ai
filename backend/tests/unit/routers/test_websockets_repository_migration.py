"""
Unit tests for websockets.py repository migration

Tests verify that the migrated websocket handlers use repositories correctly
and maintain the same functionality as before the migration.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.router.websockets import (
    handle_status_request,
    handle_cancellation_request,
    _dispatch_analysis_task,
)
from app.services.repositories.documents_repository import DocumentsRepository
from app.models.supabase_models import Document
from app.services.repositories.contracts_repository import Contract
from app.services.repositories.analyses_repository import Analysis


class TestWebSocketsRepositoryMigration:
    """Test websockets router repository migration"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = str(uuid4())
        self.document_id = str(uuid4())
        self.contract_id = str(uuid4())
        self.content_hash = "test_content_hash_websockets"

        self.mock_document = Document(
            id=UUID(self.document_id),
            user_id=UUID(self.user_id),
            original_filename="test_contract.pdf",
            storage_path="/storage/test_contract.pdf",
            file_type="pdf",
            file_size=2048,
            content_hash=self.content_hash,
            processing_status="processed",
        )

        self.mock_contract = Contract(
            id=UUID(self.contract_id),
            content_hash=self.content_hash,
            property_address="123 Test St",
            file_name="test_contract.pdf",
            file_type="pdf",
            user_id=UUID(self.user_id),
        )

    @pytest.mark.asyncio
    async def test_handle_status_request_success(self):
        """Test successful status request using repositories"""

        # Mock websocket
        mock_websocket = AsyncMock()

        # Mock repositories
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document
        mock_docs_repo.get_user_contract_views.return_value = [{"id": "view_id"}]

        mock_contracts_repo = AsyncMock()
        mock_contracts_repo.get_contracts_by_content_hash.return_value = [
            self.mock_contract
        ]

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_latest_progress.return_value = {
            "current_step": "extracting_text",
            "progress_percent": 50.0,
            "step_description": "Extracting text from document",
            "status": "in_progress",
            "estimated_completion_minutes": 5,
        }

        # Mock AuthContext
        mock_auth_context = AsyncMock()

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch(
                "app.router.websockets.ContractsRepository",
                return_value=mock_contracts_repo,
            ),
            patch(
                "app.router.websockets.AnalysisProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()

            await handle_status_request(
                mock_websocket, self.document_id, self.contract_id, self.user_id
            )

        # Verify repository calls
        mock_docs_repo.get_document.assert_called_once_with(UUID(self.document_id))
        mock_contracts_repo.get_contracts_by_content_hash.assert_called_once_with(
            self.content_hash, limit=1
        )
        mock_docs_repo.get_user_contract_views.assert_called_once_with(
            self.content_hash, self.user_id, limit=1
        )
        mock_progress_repo.get_latest_progress.assert_called_once_with(
            self.content_hash, self.user_id
        )

        # Verify websocket response
        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["event_type"] == "analysis_progress"
        assert call_data["data"]["current_step"] == "extracting_text"
        assert call_data["data"]["progress_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_handle_status_request_document_not_found(self):
        """Test status request when document is not found"""

        mock_websocket = AsyncMock()

        # Mock repository to return None (document not found)
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = None

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()

            await handle_status_request(
                mock_websocket, self.document_id, self.contract_id, self.user_id
            )

        # Verify error response
        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["event_type"] == "error"
        assert "Document" in call_data["data"]["message"]
        assert "not found" in call_data["data"]["message"]

    @pytest.mark.asyncio
    async def test_handle_status_request_contract_resolution(self):
        """Test contract resolution when contract_id is not provided"""

        mock_websocket = AsyncMock()

        # Mock repositories
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document
        mock_docs_repo.get_user_contract_views.return_value = [{"id": "view_id"}]

        mock_contracts_repo = AsyncMock()
        mock_contracts_repo.get_contracts_by_content_hash.return_value = [
            self.mock_contract
        ]

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_latest_progress.return_value = None  # No progress data

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch(
                "app.router.websockets.ContractsRepository",
                return_value=mock_contracts_repo,
            ),
            patch(
                "app.router.websockets.AnalysisProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()

            # Call without contract_id to test resolution
            await handle_status_request(
                mock_websocket, self.document_id, None, self.user_id
            )

        # Verify contract resolution was attempted
        mock_contracts_repo.get_contracts_by_content_hash.assert_called_once_with(
            self.content_hash, limit=1
        )

        # Verify status response
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_cancellation_request_success(self):
        """Test successful cancellation request using repositories"""

        mock_websocket = AsyncMock()

        # Mock repositories
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_progress_records.return_value = [
            {"id": "progress_1", "status": "in_progress"},
            {"id": "progress_2", "status": "in_progress"},
        ]
        mock_progress_repo.update_progress_by_id.return_value = True

        mock_analyses_repo = AsyncMock()

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch(
                "app.router.websockets.AnalysisProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch(
                "app.router.websockets.AnalysesRepository",
                return_value=mock_analyses_repo,
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()

            await handle_cancellation_request(
                mock_websocket, self.document_id, self.contract_id, self.user_id
            )

        # Verify repository calls
        mock_docs_repo.get_document.assert_called_once_with(UUID(self.document_id))
        mock_progress_repo.get_progress_records.assert_called_once()

        # Verify progress records were updated
        assert mock_progress_repo.update_progress_by_id.call_count == 2
        mock_progress_repo.update_progress_by_id.assert_any_call(
            "progress_1",
            {"status": "cancelled", "error_message": "Analysis cancelled by user"},
        )
        mock_progress_repo.update_progress_by_id.assert_any_call(
            "progress_2",
            {"status": "cancelled", "error_message": "Analysis cancelled by user"},
        )

        # Verify success response
        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["event_type"] == "cancellation_success"

    @pytest.mark.asyncio
    async def test_dispatch_analysis_task_success(self):
        """Test successful analysis task dispatch using repositories"""

        # Mock repositories
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document

        analysis_options = {"analysis_type": "comprehensive"}

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
            patch(
                "app.router.websockets.get_service_supabase_client"
            ) as mock_service_client,
            patch(
                "app.services.contract_analysis_service.ensure_contract"
            ) as mock_ensure_contract,
            patch(
                "app.services.backend_token_service.BackendTokenService"
            ) as mock_token_service,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()
            mock_ensure_contract.return_value = self.contract_id

            # Mock token service and task dispatch
            mock_token_service_instance = AsyncMock()
            mock_token_service.return_value = mock_token_service_instance
            mock_token_service_instance.enqueue_contract_analysis_task.return_value = {
                "task_id": "test_task"
            }

            result = await _dispatch_analysis_task(
                self.document_id, self.contract_id, self.user_id, analysis_options
            )

        # Verify repository calls
        mock_docs_repo.get_document.assert_called_once_with(UUID(self.document_id))

        # Verify result contains expected data
        assert "contract_id" in result
        assert "analysis_id" in result or "task_id" in result

    @pytest.mark.asyncio
    async def test_dispatch_analysis_task_document_not_found(self):
        """Test dispatch analysis task when document is not found"""

        # Mock repository to return None
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = None

        analysis_options = {"analysis_type": "comprehensive"}

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()

            with pytest.raises(
                ValueError, match="Document .* not found or access denied"
            ):
                await _dispatch_analysis_task(
                    self.document_id, self.contract_id, self.user_id, analysis_options
                )

    @pytest.mark.asyncio
    async def test_backward_compatibility_dict_format(self):
        """Test that functions still work with dict access patterns for backward compatibility"""

        mock_websocket = AsyncMock()

        # Mock repositories
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document
        mock_docs_repo.get_user_contract_views.return_value = (
            []
        )  # Empty to test user_contract_views creation

        mock_contract_views_repo = AsyncMock()
        mock_contract_views_repo.create_contract_view.return_value = True

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch(
                "app.router.websockets.UserContractViewsRepository",
                return_value=mock_contract_views_repo,
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_user_client = AsyncMock()
            mock_auth_ctx.get_authenticated_client.return_value = mock_user_client

            await handle_status_request(
                mock_websocket, self.document_id, self.contract_id, self.user_id
            )

        # Verify document repository was called
        mock_docs_repo.get_document.assert_called_once_with(UUID(self.document_id))

        # Verify user_contract_views lookup was called
        mock_docs_repo.get_user_contract_views.assert_called_once_with(
            self.content_hash, self.user_id, limit=1
        )

        # Verify contract view creation was called (since we returned empty list)
        mock_contract_views_repo.create_contract_view.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_client_database_usage_eliminated(self):
        """Test that user_client.database usage is completely eliminated"""

        mock_websocket = AsyncMock()

        # Mock repositories
        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document
        mock_docs_repo.get_user_contract_views.return_value = [
            {"id": "view_id"}
        ]  # Existing view

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_latest_progress.return_value = None

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch(
                "app.router.websockets.AnalysisProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_user_client = AsyncMock()
            # Add database mock that should never be called
            mock_user_client.database = Mock()
            mock_auth_ctx.get_authenticated_client.return_value = mock_user_client

            await handle_status_request(
                mock_websocket, self.document_id, self.contract_id, self.user_id
            )

        # Verify repositories were used instead of user_client.database
        mock_docs_repo.get_document.assert_called_once()
        mock_docs_repo.get_user_contract_views.assert_called_once()
        mock_progress_repo.get_latest_progress.assert_called_once()

        # user_client.database should NEVER be called now that migration is complete
        mock_user_client.database.assert_not_called()

    @pytest.mark.asyncio
    async def test_uuid_conversion_handled(self):
        """Test that string IDs are properly converted to UUID for repository calls"""

        mock_websocket = AsyncMock()

        mock_docs_repo = AsyncMock()
        mock_docs_repo.get_document.return_value = self.mock_document
        mock_docs_repo.get_user_contract_views.return_value = [{"id": "view_id"}]

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_latest_progress.return_value = None

        with (
            patch(
                "app.router.websockets.DocumentsRepository", return_value=mock_docs_repo
            ),
            patch(
                "app.router.websockets.AnalysisProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch("app.router.websockets.AuthContext") as mock_auth_ctx,
        ):

            mock_auth_ctx.get_authenticated_client.return_value = AsyncMock()

            await handle_status_request(
                mock_websocket, self.document_id, self.contract_id, self.user_id
            )

        # Verify UUID conversion for document lookup
        doc_call_args = mock_docs_repo.get_document.call_args[0]
        assert isinstance(doc_call_args[0], UUID)
        assert str(doc_call_args[0]) == self.document_id
