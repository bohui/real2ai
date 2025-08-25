"""
Comprehensive unit tests for DocumentService
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from fastapi import UploadFile
from pathlib import Path
import tempfile

from app.services.document_service import DocumentService, create_document_service
from app.services.interfaces import IDocumentProcessor
from app.clients.base.exceptions import ClientConnectionError


class TestDocumentServiceInitialization:
    """Test DocumentService initialization and configuration."""

    @pytest.mark.asyncio
    async def test_document_service_creation(self):
        """Test DocumentService can be created with default settings."""
        service = create_document_service()

        assert service is not None
        assert service.max_file_size_mb == 50
        assert service.use_llm_document_processing is True
        assert service.storage_bucket == "documents"

    @pytest.mark.asyncio
    async def test_document_service_custom_config(self):
        """Test DocumentService with custom configuration."""
        service = create_document_service(
            storage_path="custom/path",
            max_file_size_mb=25,
            use_llm_document_processing=False,
            use_service_role=True,
        )

        assert service.max_file_size_mb == 25
        assert service.use_llm_document_processing is False
        assert service.use_service_role is True
        assert str(service.storage_base_path) == "custom/path"

    @pytest.mark.asyncio
    async def test_storage_directories_created(self):
        """Test that storage directories are created on initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = DocumentService(storage_base_path=temp_dir)

            expected_dirs = [
                Path(temp_dir),
                Path(temp_dir) / "originals",
                Path(temp_dir) / "diagrams",
                Path(temp_dir) / "pages",
                Path(temp_dir) / "temp",
            ]

            for dir_path in expected_dirs:
                assert dir_path.exists()

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_supabase_client, mock_openai_client):
        """Test successful service initialization."""
        service = DocumentService()

        with patch(
            "app.services.document_service.get_supabase_client",
            return_value=mock_supabase_client,
        ):
            with patch(
                "app.services.document_service.get_gemini_client",
                return_value=mock_openai_client,
            ):
                with patch.object(service, "_ensure_bucket_exists") as mock_bucket:
                    mock_bucket.return_value = None

                    await service.initialize()

                    assert service.supabase_client is not None
                    assert service.gemini_client is not None
                    mock_bucket.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """Test initialization handles connection failures gracefully."""
        service = DocumentService()

        with patch(
            "app.services.document_service.get_supabase_client",
            side_effect=ClientConnectionError("Connection failed"),
        ):

            with pytest.raises(Exception) as exc_info:
                await service.initialize()

            assert "Required services unavailable" in str(exc_info.value)


class TestDocumentServiceFileValidation:
    """Test file validation functionality."""

    @pytest.fixture
    def service(self):
        return DocumentService()

    def create_upload_file(
        self, content: bytes, filename: str, content_type: str = "application/pdf"
    ) -> UploadFile:
        """Helper to create UploadFile objects for testing."""
        file_obj = BytesIO(content)
        return UploadFile(filename=filename, file=file_obj, content_type=content_type)

    @pytest.mark.asyncio
    async def test_validate_pdf_file_success(self, service):
        """Test validation of valid PDF file."""
        # PDF header magic bytes
        pdf_content = (
            b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        )
        upload_file = self.create_upload_file(pdf_content, "test.pdf")

        result = await service._validate_uploaded_file(upload_file)

        assert result["valid"] is True
        assert result["file_info"]["file_type"] == "pdf"
        assert result["file_info"]["original_filename"] == "test.pdf"
        assert result["file_info"]["file_size"] == len(pdf_content)

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, service):
        """Test rejection of oversized files."""
        # Create large content
        large_content = b"x" * (service.max_file_size_mb * 1024 * 1024 + 1)
        upload_file = self.create_upload_file(large_content, "large.pdf")

        result = await service._validate_uploaded_file(upload_file)

        assert result["valid"] is False
        assert "File too large" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_unsupported_file_type(self, service):
        """Test rejection of unsupported file types."""
        exe_content = b"MZ\x90\x00"  # PE executable header
        upload_file = self.create_upload_file(exe_content, "malware.exe")

        result = await service._validate_uploaded_file(upload_file)

        assert result["valid"] is False
        assert "Unsupported file type" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_security_concerns(self, service):
        """Test security validation catches malicious files."""
        malicious_content = b"MZ\x90\x00\x03\x00\x00\x00"  # Windows executable
        upload_file = self.create_upload_file(malicious_content, "safe.pdf")

        result = await service._validate_uploaded_file(upload_file)

        assert result["valid"] is False
        assert "security validation" in result["error"]

    @pytest.mark.asyncio
    async def test_detect_file_type_from_magic_bytes(self, service):
        """Test file type detection from magic bytes."""
        test_cases = [
            (b"%PDF-1.4", "test.pdf", "pdf"),
            (b"\x89PNG\r\n\x1a\n", "test.png", "png"),
            (b"\xff\xd8\xff\xe0", "test.jpg", "jpg"),
            (b"PK\x03\x04", "test.docx", "docx"),
        ]

        for header, filename, expected_type in test_cases:
            detected_type = service._detect_file_type(filename, header)
            assert detected_type == expected_type, f"Failed for {filename}"


class TestDocumentServiceTextExtraction:
    """Test text extraction functionality."""

    @pytest.fixture
    def service(self):
        return DocumentService()

    @pytest.mark.asyncio
    async def test_extract_text_pdf_success(self, service, mock_supabase_client):
        """Test successful PDF text extraction."""
        # Mock PDF content
        pdf_content = b"%PDF-1.4\nMock PDF content"
        storage_path = "documents/user/test.pdf"

        # Mock supabase client
        service.supabase_client = mock_supabase_client
        mock_supabase_client.download_file.return_value = pdf_content

        # Mock PDF processing
        with patch.object(service, "_extract_pdf_text_comprehensive") as mock_extract:
            expected_result = {
                "success": True,
                "full_text": "Extracted text content",
                "pages": [{"page_number": 1, "text_content": "Page 1 text"}],
                "extraction_method": "pymupdf",
                "confidence": 0.9,
            }
            mock_extract.return_value = expected_result

            result = await service.extract_text(storage_path, "pdf")

            assert result["success"] is True
            assert result["full_text"] == "Extracted text content"
            mock_supabase_client.download_file.assert_called_once_with(
                bucket="documents", path=storage_path
            )

    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, service, mock_supabase_client):
        """Test text extraction when file doesn't exist."""
        service.supabase_client = mock_supabase_client
        mock_supabase_client.download_file.return_value = None

        result = await service.extract_text("nonexistent/file.pdf", "pdf")

        assert result["success"] is False
        assert "Failed to download file" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_format(self, service, mock_supabase_client):
        """Test text extraction with unsupported file format."""
        service.supabase_client = mock_supabase_client
        mock_supabase_client.download_file.return_value = b"some content"

        result = await service.extract_text("test.xyz", "unknown")

        assert result["success"] is False
        assert "Unsupported file type" in result["error"]


class TestDocumentServiceUpload:
    """Test document upload functionality."""

    @pytest.fixture
    def service(self):
        return DocumentService()

    def create_upload_file(self, content: bytes, filename: str) -> UploadFile:
        file_obj = BytesIO(content)
        return UploadFile(filename=filename, file=file_obj)

    @pytest.mark.asyncio
    async def test_upload_file_success(self, service, mock_supabase_client):
        """Test successful file upload."""
        # Setup
        pdf_content = b"%PDF-1.4\nTest content"
        upload_file = self.create_upload_file(pdf_content, "test.pdf")
        user_id = "test-user-123"

        service.supabase_client = mock_supabase_client

        # Mock successful upload
        mock_supabase_client.upload_file.return_value = {"success": True}
        mock_supabase_client.insert.return_value = {"success": True}

        # Mock validation
        with patch.object(service, "_validate_uploaded_file") as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "file_info": {
                    "original_filename": "test.pdf",
                    "file_type": "pdf",
                    "file_size": len(pdf_content),
                    "content_hash": "mockhash123",
                    "mime_type": "application/pdf",
                },
            }

            result = await service.upload_file(upload_file, user_id)

            assert result["success"] is True
            assert "document_id" in result
            assert "storage_path" in result
            mock_supabase_client.upload_file.assert_called_once()
            mock_supabase_client.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_validation_failure(self, service):
        """Test upload fails when validation fails."""
        upload_file = self.create_upload_file(b"invalid", "bad.exe")

        with patch.object(service, "_validate_uploaded_file") as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Invalid file type"}

            result = await service.upload_file(upload_file, "user123")

            assert result["success"] is False
            assert "Invalid file type" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_file_storage_failure(self, service, mock_supabase_client):
        """Test upload fails when storage upload fails."""
        upload_file = self.create_upload_file(b"%PDF-1.4", "test.pdf")
        service.supabase_client = mock_supabase_client

        # Mock storage failure
        mock_supabase_client.upload_file.return_value = {"success": False}

        with patch.object(service, "_validate_uploaded_file") as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "file_info": {
                    "original_filename": "test.pdf",
                    "file_type": "pdf",
                    "file_size": 8,
                    "content_hash": "hash",
                    "mime_type": "application/pdf",
                },
            }

            result = await service._upload_and_create_document_record(
                upload_file, "user123", mock_validate.return_value["file_info"]
            )

            assert result["success"] is False
            assert "Failed to upload file" in result["error"]


class TestDocumentServiceHealthCheck:
    """Test health check functionality."""

    @pytest.fixture
    def service(self):
        return DocumentService()

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(
        self, service, mock_supabase_client, mock_openai_client
    ):
        """Test health check when all dependencies are healthy."""
        # Setup mocks
        service.supabase_client = mock_supabase_client
        service.gemini_client = mock_openai_client
        service.gemini_ocr_service = MagicMock()

        # Mock health checks
        mock_supabase_client.execute_rpc.return_value = {"status": "ok"}
        mock_openai_client.health_check.return_value = {
            "status": "healthy",
            "model": "gemini-pro",
        }
        service.gemini_ocr_service.health_check = AsyncMock(
            return_value={"status": "healthy"}
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            service.storage_base_path = Path(temp_dir)
            service._setup_storage_directories()

            health = await service.health_check()

            assert health["status"] == "healthy"
            assert health["dependencies"]["supabase"]["status"] == "healthy"
            assert health["dependencies"]["gemini"]["status"] == "healthy"
            assert health["dependencies"]["storage"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_dependencies(
        self, service, mock_supabase_client
    ):
        """Test health check when some dependencies are unavailable."""
        service.supabase_client = mock_supabase_client
        service.gemini_client = None  # Simualte unavailable client

        mock_supabase_client.execute_rpc.side_effect = Exception("Connection failed")

        health = await service.health_check()

        assert health["status"] == "degraded"
        assert health["dependencies"]["supabase"]["status"] == "error"
        assert health["dependencies"]["gemini"]["status"] == "not_initialized"


class TestDocumentServiceUtilities:
    """Test utility methods."""

    @pytest.fixture
    def service(self):
        return DocumentService()

    @pytest.mark.unit
    def test_calculate_hash(self, service):
        """Test content hash calculation."""
        content = b"test content"
        hash_value = service._calculate_hash(content)

        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hex digest length

    @pytest.mark.unit
    def test_has_security_concerns(self, service):
        """Test security concern detection."""
        # Test suspicious extensions
        assert service._has_security_concerns("malware.exe", b"anything") is True
        assert service._has_security_concerns("script.bat", b"anything") is True
        assert service._has_security_concerns("document.pdf", b"%PDF") is False

        # Test executable headers
        assert service._has_security_concerns("file.pdf", b"MZ\x90\x00") is True
        assert service._has_security_concerns("file.pdf", b"%PDF-1.4") is False


class TestDocumentServiceInterfaces:
    """Test service implements interfaces correctly."""

    @pytest.mark.asyncio
    async def test_implements_document_processor_interface(self):
        """Test DocumentService implements IDocumentProcessor interface."""
        service = DocumentService()

        # Check if service implements the protocol
        assert isinstance(service, IDocumentProcessor)

        # Check required methods exist
        assert hasattr(service, "initialize")
        assert hasattr(service, "upload_file")
        assert hasattr(service, "extract_text")
        assert hasattr(service, "get_file_content")

    @pytest.mark.asyncio
    async def test_interface_method_signatures(self):
        """Test method signatures match interface requirements."""
        service = DocumentService()

        # Test initialize method
        await service.initialize()

        # Test method signatures exist (they would fail type checking if wrong)
        upload_file = getattr(service, "upload_file")
        extract_text = getattr(service, "extract_text")
        get_file_content = getattr(service, "get_file_content")

        assert callable(upload_file)
        assert callable(extract_text)
        assert callable(get_file_content)


@pytest.mark.integration
class TestDocumentServiceIntegration:
    """Integration tests requiring external dependencies."""

    @pytest.mark.asyncio
    async def test_end_to_end_document_processing(
        self, mock_supabase_client, mock_openai_client
    ):
        """Test complete document processing workflow."""
        service = DocumentService()

        # Mock all external dependencies
        service.supabase_client = mock_supabase_client
        service.gemini_client = mock_openai_client

        # Mock successful responses
        mock_supabase_client.upload_file.return_value = {"success": True}
        mock_supabase_client.insert.return_value = {"success": True}
        mock_supabase_client.update.return_value = {"success": True}
        mock_supabase_client.download_file.return_value = b"%PDF-1.4\nTest content"

        # Create test file
        pdf_content = b"%PDF-1.4\nTest PDF content for integration test"
        upload_file = UploadFile(
            filename="integration_test.pdf", file=BytesIO(pdf_content)
        )

        # Mock PDF processing
        with patch.object(service, "_extract_pdf_text_comprehensive") as mock_extract:
            mock_extract.return_value = {
                "success": True,
                "full_text": "Integration test content",
                "pages": [{"page_number": 1, "text_content": "Test content"}],
                "total_pages": 1,
                "extraction_methods": ["pymupdf"],
                "total_word_count": 3,
                "overall_confidence": 0.95,
            }

            # Mock other processing steps
            with patch.object(service, "_process_and_analyze_pages") as mock_pages:
                mock_pages.return_value = {"pages": [], "total_analyzed": 1}

                with patch.object(
                    service, "_extract_australian_entities"
                ) as mock_entities:
                    mock_entities.return_value = {
                        "total_entities": 0,
                        "entities_by_type": {},
                    }

                    with patch.object(
                        service, "_detect_and_process_diagrams"
                    ) as mock_diagrams:
                        mock_diagrams.return_value = {
                            "total_diagrams": 0,
                            "diagrams_by_type": {},
                        }

                        with patch.object(
                            service, "_analyze_document_content"
                        ) as mock_analysis:
                            mock_analysis.return_value = {
                                "classification": {},
                                "quality": {},
                            }

                            # Execute integration test
                            result = await service.process_document(
                                upload_file,
                                "integration-user-123",
                                contract_type="purchase_agreement",
                                australian_state="NSW",
                            )

                            # Verify end-to-end success
                            assert result["success"] is True
                            assert "document_id" in result
                            assert result["text_extraction"]["total_pages"] == 1
                            assert result["ready_for_advanced_analysis"] is True
