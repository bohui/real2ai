"""
Unit tests for repository classes
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID
from datetime import datetime
import json

from app.services.repositories.artifacts_repository import (
    ArtifactsRepository,
    TextExtractionArtifact,
    PageArtifact,
    DiagramArtifact,
    ParagraphArtifact,
)
from app.services.repositories.user_docs_repository import (
    UserDocsRepository,
    DocumentPage,
    DocumentDiagram,
    DocumentParagraph,
)
from app.services.repositories.runs_repository import (
    RunsRepository,
    ProcessingRun,
    ProcessingStep,
    RunStatus,
    StepStatus,
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
    async def test_get_text_artifact_found(self):
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
            result = await self.repo.get_text_artifact(
                self.content_hmac, self.algorithm_version, self.params_fingerprint
            )
            
        assert result is not None
        assert isinstance(result, TextExtractionArtifact)
        assert result.content_hmac == self.content_hmac
        assert result.total_pages == 10
        assert result.total_words == 1000

    @pytest.mark.asyncio
    async def test_get_text_artifact_not_found(self):
        """Test getting non-existent text artifact"""
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        
        with patch.object(self.repo, '_get_connection', return_value=mock_connection):
            result = await self.repo.get_text_artifact(
                self.content_hmac, self.algorithm_version, self.params_fingerprint
            )
            
        assert result is None

    @pytest.mark.asyncio
    async def test_get_text_artifact_invalid_hmac(self):
        """Test getting text artifact with invalid HMAC"""
        with pytest.raises(ValueError, match="Invalid content HMAC"):
            await self.repo.get_text_artifact(
                "invalid", self.algorithm_version, self.params_fingerprint
            )

    @pytest.mark.asyncio
    async def test_insert_text_artifact_success(self):
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
            result = await self.repo.insert_text_artifact(
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
        assert isinstance(result, TextExtractionArtifact)
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