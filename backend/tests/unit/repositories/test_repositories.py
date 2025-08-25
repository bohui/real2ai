"""
Unit tests for repository classes
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.repositories.artifacts_repository import (
    ArtifactsRepository,
    FullTextArtifact,
    PageArtifact,
)
from app.services.repositories.user_docs_repository import (
    UserDocsRepository,
    DocumentPage,
)
from app.services.repositories.runs_repository import (
    RunsRepository,
    ProcessingRun,
    ProcessingStep,
    RunStatus,
    StepStatus,
)
from app.services.repositories.analysis_progress_repository import (
    AnalysisProgressRepository,
)
from app.services.repositories.documents_repository import (
    DocumentsRepository,
    Document,
)


class TestArtifactsRepository:
    """Test ArtifactsRepository"""

    def setup_method(self):
        """Setup test fixtures"""
        self.repo = ArtifactsRepository()
        self.content_hmac = "a" * 64
        self.algorithm_version = 1
        self.params_fingerprint = "b" * 64

    @pytest.mark.asyncio
    async def test_get_full_text_artifact_found(self):
        """Test getting existing text artifact"""
        mock_connection = AsyncMock()
        mock_row = {
            'id': uuid4(),
            'content_hmac': self.content_hmac,
            'algorithm_version': self.algorithm_version,
            'params_fingerprint': self.params_fingerprint,
            'full_text_uri': 'https://example.com/text.txt',
            'full_text_sha256': 'c' * 64,
            'total_pages': 10,
            'total_words': 1000,
            'methods': {'ocr': 'gemini'},
            'timings': {'duration': 30},
            'created_at': datetime.utcnow()
        }
        mock_connection.fetchrow.return_value = mock_row
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.get_full_text_artifact(
                self.content_hmac, self.algorithm_version, self.params_fingerprint
            )
            
        assert result is not None
        assert isinstance(result, FullTextArtifact)
        assert result.content_hmac == self.content_hmac
        assert result.total_pages == 10
        assert result.total_words == 1000

    @pytest.mark.asyncio
    async def test_get_full_text_artifact_not_found(self):
        """Test getting non-existent text artifact"""
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.get_full_text_artifact(
                self.content_hmac, self.algorithm_version, self.params_fingerprint
            )
            
        assert result is None

    @pytest.mark.asyncio
    async def test_get_full_text_artifact_invalid_hmac(self):
        """Test getting text artifact with invalid HMAC"""
        with pytest.raises(ValueError, match="Invalid content HMAC"):
            await self.repo.get_full_text_artifact(
                "invalid", self.algorithm_version, self.params_fingerprint
            )

    @pytest.mark.asyncio
    async def test_insert_full_text_artifact_success(self):
        """Test inserting new text artifact"""
        mock_connection = AsyncMock()
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction
        
        artifact_id = uuid4()
        mock_row = {
            'id': artifact_id,
            'content_hmac': self.content_hmac,
            'algorithm_version': self.algorithm_version,
            'params_fingerprint': self.params_fingerprint,
            'full_text_uri': 'https://example.com/text.txt',
            'full_text_sha256': 'c' * 64,
            'total_pages': 10,
            'total_words': 1000,
            'methods': {'ocr': 'gemini'},
            'timings': {'duration': 30},
            'created_at': datetime.utcnow()
        }
        mock_connection.fetchrow.return_value = mock_row
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.insert_full_text_artifact(
                content_hmac=self.content_hmac,
                algorithm_version=self.algorithm_version,
                params_fingerprint=self.params_fingerprint,
                full_text_uri='https://example.com/text.txt',
                full_text_sha256='c' * 64,
                total_pages=10,
                total_words=1000,
                methods={'ocr': 'gemini'},
                timings={'duration': 30}
            )
            
        assert result is not None
        assert isinstance(result, FullTextArtifact)
        assert result.id == artifact_id
        assert result.total_pages == 10

    @pytest.mark.asyncio
    async def test_get_page_artifacts(self):
        """Test getting page artifacts"""
        mock_connection = AsyncMock()
        page_id_1 = uuid4()
        page_id_2 = uuid4()
        mock_rows = [
            {
                'id': page_id_1,
                'content_hmac': self.content_hmac,
                'algorithm_version': self.algorithm_version,
                'params_fingerprint': self.params_fingerprint,
                'page_number': 1,
                'page_text_uri': 'https://example.com/page1.txt',
                'page_text_sha256': 'd' * 64,
                'layout': {'sections': 3},
                'metrics': {'confidence': 0.95},
                'created_at': datetime.utcnow()
            },
            {
                'id': page_id_2,
                'content_hmac': self.content_hmac,
                'algorithm_version': self.algorithm_version,
                'params_fingerprint': self.params_fingerprint,
                'page_number': 2,
                'page_text_uri': 'https://example.com/page2.txt',
                'page_text_sha256': 'e' * 64,
                'layout': {'sections': 2},
                'metrics': {'confidence': 0.92},
                'created_at': datetime.utcnow()
            }
        ]
        mock_connection.fetch.return_value = mock_rows
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.get_page_artifacts(
                self.content_hmac, self.algorithm_version, self.params_fingerprint
            )
            
        assert len(result) == 2
        assert all(isinstance(page, PageArtifact) for page in result)
        assert result[0].page_number == 1
        assert result[1].page_number == 2


class TestUserDocsRepository:
    """Test UserDocsRepository"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = uuid4()
        self.repo = UserDocsRepository(self.user_id)
        self.document_id = uuid4()

    @pytest.mark.asyncio
    async def test_update_document_artifact_reference(self):
        """Test updating document with artifact reference"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.update_document_artifact_reference(
                self.document_id, uuid4(), 10, 1000
            )
            
        assert result is True
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document_processing_status(self):
        """Test updating document processing status"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.update_document_processing_status(
                self.document_id, 
                "basic_complete",
                processing_completed_at=datetime.utcnow()
            )
            
        assert result is True
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_document_page(self):
        """Test upserting document page"""
        mock_connection = AsyncMock()
        page_data = {
            'document_id': self.document_id,
            'page_number': 1,
            'artifact_page_id': uuid4(),
            'annotations': {'highlight': True},
            'flags': {'reviewed': False},
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        mock_connection.fetchrow.return_value = page_data
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.upsert_document_page(
                self.document_id, 1, uuid4(), 
                annotations={'highlight': True},
                flags={'reviewed': False}
            )
            
        assert isinstance(result, DocumentPage)
        assert result.document_id == self.document_id
        assert result.page_number == 1

    @pytest.mark.asyncio
    async def test_get_document_pages(self):
        """Test getting document pages"""
        mock_connection = AsyncMock()
        page_data = [
            {
                'document_id': self.document_id,
                'page_number': 1,
                'artifact_page_id': uuid4(),
                'annotations': None,
                'flags': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'document_id': self.document_id,
                'page_number': 2,
                'artifact_page_id': uuid4(),
                'annotations': None,
                'flags': None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        mock_connection.fetch.return_value = page_data
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.get_document_pages(self.document_id)
            
        assert len(result) == 2
        assert all(isinstance(page, DocumentPage) for page in result)
        assert result[0].page_number == 1
        assert result[1].page_number == 2


class TestRunsRepository:
    """Test RunsRepository"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = uuid4()
        self.repo = RunsRepository(self.user_id)
        self.document_id = uuid4()
        self.run_id = uuid4()

    @pytest.mark.asyncio
    async def test_create_run(self):
        """Test creating processing run"""
        mock_connection = AsyncMock()
        run_data = {
            'run_id': self.run_id,
            'document_id': self.document_id,
            'user_id': self.user_id,
            'status': 'queued',
            'last_step': None,
            'error': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        mock_connection.fetchrow.return_value = run_data
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.create_run(self.document_id, self.run_id)
            
        assert isinstance(result, ProcessingRun)
        assert result.run_id == self.run_id
        assert result.status == RunStatus.QUEUED

    @pytest.mark.asyncio
    async def test_update_run_status(self):
        """Test updating run status"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.update_run_status(
                self.run_id, RunStatus.COMPLETED, "final_step"
            )
            
        assert result is True

    @pytest.mark.asyncio
    async def test_upsert_step_status(self):
        """Test upserting step status"""
        mock_connection = AsyncMock()
        step_data = {
            'run_id': self.run_id,
            'step_name': 'extract_text',
            'status': 'success',
            'state_snapshot': {'progress': 100},
            'error': None,
            'started_at': datetime.utcnow(),
            'completed_at': datetime.utcnow()
        }
        mock_connection.fetchrow.return_value = step_data
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.upsert_step_status(
                self.run_id, 'extract_text', StepStatus.SUCCESS,
                state_snapshot={'progress': 100}
            )
            
        assert isinstance(result, ProcessingStep)
        assert result.step_name == 'extract_text'
        assert result.status == StepStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_get_run_progress(self):
        """Test getting run progress"""
        mock_connection = AsyncMock()
        
        # Mock run data
        run_data = {
            'run_id': self.run_id,
            'document_id': self.document_id,
            'user_id': self.user_id,
            'status': 'in_progress',
            'last_step': 'extract_text',
            'error': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Mock step summary
        step_summary = {
            'total_steps': 5,
            'completed_steps': 2,
            'failed_steps': 0,
            'running_steps': 1,
            'skipped_steps': 0
        }
        
        with patch.object(self.repo, 'get_run') as mock_get_run:
            mock_get_run.return_value = ProcessingRun(
                run_id=run_data['run_id'],
                document_id=run_data['document_id'],
                user_id=run_data['user_id'],
                status=RunStatus(run_data['status']),
                last_step=run_data['last_step'],
                error=run_data['error'],
                created_at=run_data['created_at'],
                updated_at=run_data['updated_at']
            )
            
            with patch.object(self.repo, '_get_connection', return_value=mock_connection):
                mock_connection.fetchrow.return_value = step_summary
                
                result = await self.repo.get_run_progress(self.run_id)
                
        assert result['run_id'] == str(self.run_id)
        assert result['status'] == 'in_progress'
        assert result['steps']['total'] == 5
        assert result['steps']['completed'] == 2


class TestAnalysisProgressRepository:
    """Test AnalysisProgressRepository"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = uuid4()
        self.repo = AnalysisProgressRepository(self.user_id)
        self.content_hash = "test_content_hash_123"
        self.user_id_str = str(uuid4())

    @pytest.mark.asyncio
    async def test_upsert_progress_success(self):
        """Test upserting progress record successfully"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = None  # Successful upsert
        
        progress_data = {
            "current_step": "analysis_start",
            "progress_percent": 25,
            "step_description": "Starting contract analysis",
            "status": "in_progress",
            "estimated_completion_minutes": 2,
        }
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.upsert_progress(
                self.content_hash, self.user_id_str, progress_data
            )
            
        assert result is True
        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_progress_failure(self):
        """Test upsert progress failure"""
        mock_connection = AsyncMock()
        mock_connection.execute.side_effect = Exception("Database error")
        
        progress_data = {
            "current_step": "analysis_start",
            "progress_percent": 25,
            "status": "in_progress",
        }
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.upsert_progress(
                self.content_hash, self.user_id_str, progress_data
            )
            
        assert result is False

    @pytest.mark.asyncio
    async def test_get_latest_progress_found(self):
        """Test getting latest progress record when found"""
        mock_connection = AsyncMock()
        mock_row = {
            "current_step": "analysis_complete",
            "progress_percent": 100,
            "updated_at": datetime.utcnow(),
            "status": "completed",
            "error_message": None,
        }
        mock_connection.fetchrow.return_value = mock_row
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_latest_progress(
                self.content_hash, self.user_id_str
            )
            
        assert result is not None
        assert result["current_step"] == "analysis_complete"
        assert result["progress_percent"] == 100
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_latest_progress_not_found(self):
        """Test getting latest progress when not found"""
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_latest_progress(
                self.content_hash, self.user_id_str
            )
            
        assert result is None

    @pytest.mark.asyncio
    async def test_get_progress_records_with_filters(self):
        """Test getting progress records with filters"""
        mock_connection = AsyncMock()
        mock_rows = [
            {
                "id": uuid4(),
                "content_hash": self.content_hash,
                "user_id": UUID(self.user_id_str),
                "current_step": "queued",
                "progress_percent": 5,
                "status": "in_progress",
                "created_at": datetime.utcnow(),
            },
            {
                "id": uuid4(),
                "content_hash": self.content_hash,
                "user_id": UUID(self.user_id_str),
                "current_step": "analysis_complete",
                "progress_percent": 100,
                "status": "completed",
                "created_at": datetime.utcnow(),
            }
        ]
        mock_connection.fetch.return_value = mock_rows
        
        filters = {"content_hash": self.content_hash, "user_id": self.user_id_str}
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_progress_records(filters)
            
        assert len(result) == 2
        assert all(isinstance(record, dict) for record in result)
        assert result[0]["current_step"] == "queued"
        assert result[1]["current_step"] == "analysis_complete"

    @pytest.mark.asyncio
    async def test_update_progress_status_success(self):
        """Test updating progress status successfully"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.update_progress_status(
                self.content_hash, self.user_id_str, "failed", "Analysis timeout"
            )
            
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_progress_success(self):
        """Test deleting progress record successfully"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "DELETE 1"
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.delete_progress(
                self.content_hash, self.user_id_str
            )
            
        assert result is True

    @pytest.mark.asyncio
    async def test_get_active_analyses(self):
        """Test getting active analyses for user"""
        mock_connection = AsyncMock()
        mock_rows = [
            {
                "id": uuid4(),
                "content_hash": "hash1",
                "user_id": UUID(self.user_id_str),
                "current_step": "in_progress",
                "progress_percent": 50,
                "status": "in_progress",
                "created_at": datetime.utcnow(),
            }
        ]
        mock_connection.fetch.return_value = mock_rows
        
        with patch('app.services.repositories.analysis_progress_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_active_analyses(self.user_id_str)
            
        assert len(result) == 1
        assert result[0]["status"] == "in_progress"
        assert result[0]["progress_percent"] == 50


class TestDocumentsRepositoryExtended:
    """Test extended DocumentsRepository methods"""

    def setup_method(self):
        """Setup test fixtures"""
        self.user_id = uuid4()
        self.repo = DocumentsRepository(self.user_id)
        self.document_id = uuid4()
        self.content_hash = "test_content_hash_456"

    @pytest.mark.asyncio
    async def test_get_documents_by_content_hash_found(self):
        """Test getting documents by content hash when found"""
        mock_connection = AsyncMock()
        mock_rows = [
            {
                "id": self.document_id,
                "user_id": self.user_id,
                "original_filename": "test.pdf",
                "storage_path": "/path/to/test.pdf",
                "file_type": "pdf",
                "file_size": 1024,
                "content_hash": self.content_hash,
                "processing_status": "processed",
                "processing_started_at": None,
                "processing_completed_at": datetime.utcnow(),
                "processing_errors": None,
                "artifact_text_id": None,
                "total_pages": 5,
                "total_word_count": 500,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        ]
        mock_connection.fetch.return_value = mock_rows
        
        with patch('app.services.repositories.documents_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_documents_by_content_hash(
                self.content_hash, str(self.user_id)
            )
            
        assert len(result) == 1
        document = result[0]
        assert isinstance(document, Document)
        assert document.content_hash == self.content_hash
        assert document.original_filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_documents_by_content_hash_partial_columns(self):
        """Test getting documents by content hash with partial columns"""
        mock_connection = AsyncMock()
        mock_rows = [
            {
                "id": self.document_id,
            }
        ]
        mock_connection.fetch.return_value = mock_rows
        
        with patch('app.services.repositories.documents_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_documents_by_content_hash(
                self.content_hash, str(self.user_id), columns="id"
            )
            
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["id"] == self.document_id

    @pytest.mark.asyncio
    async def test_update_processing_results_success(self):
        """Test updating processing results successfully"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        results = {
            "extracted_text": "Sample text",
            "confidence": 0.95,
            "method": "ocr"
        }
        
        with patch('app.services.repositories.documents_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.update_processing_results(
                self.document_id, results
            )
            
        assert result is True

    @pytest.mark.asyncio
    async def test_update_processing_status_and_results_with_results(self):
        """Test updating both status and results"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        results = {"extraction_confidence": 0.9}
        
        with patch('app.services.repositories.documents_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.update_processing_status_and_results(
                self.document_id, "processed", results
            )
            
        assert result is True

    @pytest.mark.asyncio
    async def test_update_processing_status_and_results_status_only(self):
        """Test updating only status without results"""
        mock_connection = AsyncMock()
        mock_connection.execute.return_value = "UPDATE 1"
        
        with patch('app.services.repositories.documents_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.update_processing_status_and_results(
                self.document_id, "failed"
            )
            
        assert result is True

    @pytest.mark.asyncio
    async def test_get_document_with_content_hash(self):
        """Test getting document with content_hash field included"""
        mock_connection = AsyncMock()
        mock_row = {
            "id": self.document_id,
            "user_id": self.user_id,
            "original_filename": "test.pdf",
            "storage_path": "/path/to/test.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "content_hash": self.content_hash,
            "processing_status": "processed",
            "processing_started_at": None,
            "processing_completed_at": datetime.utcnow(),
            "processing_errors": None,
            "artifact_text_id": None,
            "total_pages": 5,
            "total_word_count": 500,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        mock_connection.fetchrow.return_value = mock_row
        
        with patch('app.services.repositories.documents_repository.get_user_connection') as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            
            result = await self.repo.get_document(self.document_id)
            
        assert result is not None
        assert isinstance(result, Document)
        assert result.content_hash == self.content_hash
        assert result.id == self.document_id