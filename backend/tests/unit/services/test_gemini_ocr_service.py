"""
Test Gemini OCR Service functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, UTC
from typing import Dict, Any, Optional

from fastapi import HTTPException

from app.services.gemini_ocr_service import GeminiOCRService
from app.models.contract_state import ProcessingStatus, AustralianState, ContractType
from app.clients.base.exceptions import (
    ClientError,
    ClientConnectionError, 
    ClientQuotaExceededError,
)


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client"""
    client = AsyncMock()
    client.generate_content_async = AsyncMock()
    client.configure = AsyncMock()
    return client


@pytest.fixture
def mock_user_client():
    """Create a mock user client"""
    client = AsyncMock()
    return client


@pytest.fixture
def gemini_ocr_service(mock_user_client):
    """Create GeminiOCRService instance with mocked dependencies"""
    with patch('app.services.gemini_ocr_service.get_gemini_client') as mock_get_client:
        mock_get_client.return_value = None  # Will be set in tests
        service = GeminiOCRService(user_client=mock_user_client)
        return service


@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "id": "doc-123",
        "filename": "test-contract.pdf", 
        "file_type": "pdf",
        "file_size": 1024 * 1024,  # 1MB
        "storage_path": "documents/test-user/doc-123.pdf",
        "content": b"PDF content bytes",
        "user_id": "test-user-123"
    }


class TestGeminiOCRServiceInitialization:
    """Test GeminiOCRService initialization"""
    
    def test_service_initialization(self, gemini_ocr_service):
        """Test service initializes with correct defaults"""
        assert gemini_ocr_service.max_file_size == 50 * 1024 * 1024  # 50MB
        assert "pdf" in gemini_ocr_service.supported_formats
        assert "png" in gemini_ocr_service.supported_formats
        assert "jpg" in gemini_ocr_service.supported_formats
    
    def test_service_inherits_mixins(self, gemini_ocr_service):
        """Test service properly inherits from required mixins"""
        # Should have PromptEnabledService methods
        assert hasattr(gemini_ocr_service, 'get_prompt')
        assert hasattr(gemini_ocr_service, 'format_prompt')
        
        # Should have UserAwareService methods
        assert hasattr(gemini_ocr_service, 'get_user_context')
        assert hasattr(gemini_ocr_service, 'ensure_user_access')


class TestFileValidation:
    """Test file validation functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_file_valid_pdf(self, gemini_ocr_service, sample_document_data):
        """Test validation of valid PDF file"""
        result = await gemini_ocr_service._validate_file(sample_document_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_file_unsupported_format(self, gemini_ocr_service, sample_document_data):
        """Test validation rejects unsupported file formats"""
        sample_document_data["file_type"] = "doc"
        sample_document_data["filename"] = "test.doc"
        
        with pytest.raises(HTTPException) as exc_info:
            await gemini_ocr_service._validate_file(sample_document_data)
        
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, gemini_ocr_service, sample_document_data):
        """Test validation rejects files that are too large"""
        sample_document_data["file_size"] = 100 * 1024 * 1024  # 100MB
        
        with pytest.raises(HTTPException) as exc_info:
            await gemini_ocr_service._validate_file(sample_document_data)
        
        assert exc_info.value.status_code == 400
        assert "File too large" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_file_zero_size(self, gemini_ocr_service, sample_document_data):
        """Test validation rejects empty files"""
        sample_document_data["file_size"] = 0
        
        with pytest.raises(HTTPException) as exc_info:
            await gemini_ocr_service._validate_file(sample_document_data)
        
        assert exc_info.value.status_code == 400
        assert "Empty file" in str(exc_info.value.detail)


class TestOCRProcessing:
    """Test OCR processing functionality"""
    
    @pytest.mark.asyncio
    async def test_process_document_success(self, gemini_ocr_service, mock_gemini_client, sample_document_data):
        """Test successful document processing"""
        # Setup mocks
        gemini_ocr_service.gemini_client = mock_gemini_client
        
        mock_response = Mock()
        mock_response.text = "Sample extracted text from contract"
        mock_gemini_client.generate_content_async.return_value = mock_response
        
        with patch.object(gemini_ocr_service, '_validate_file', return_value=True):
            with patch.object(gemini_ocr_service, '_prepare_gemini_input') as mock_prepare:
                mock_prepare.return_value = ("prompt", "image_data")
                
                result = await gemini_ocr_service.process_document(sample_document_data)
        
        assert result["status"] == ProcessingStatus.COMPLETED
        assert result["extracted_text"] == "Sample extracted text from contract"
        assert result["character_count"] > 0
        assert result["word_count"] > 0
        assert "processing_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_process_document_gemini_error(self, gemini_ocr_service, mock_gemini_client, sample_document_data):
        """Test handling of Gemini API errors"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        mock_gemini_client.generate_content_async.side_effect = ClientError("API Error")
        
        with patch.object(gemini_ocr_service, '_validate_file', return_value=True):
            with patch.object(gemini_ocr_service, '_prepare_gemini_input') as mock_prepare:
                mock_prepare.return_value = ("prompt", "image_data")
                
                result = await gemini_ocr_service.process_document(sample_document_data)
        
        assert result["status"] == ProcessingStatus.FAILED
        assert "error" in result
        assert "API Error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_document_quota_exceeded(self, gemini_ocr_service, mock_gemini_client, sample_document_data):
        """Test handling of quota exceeded errors"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        mock_gemini_client.generate_content_async.side_effect = ClientQuotaExceededError("Quota exceeded")
        
        with patch.object(gemini_ocr_service, '_validate_file', return_value=True):
            with patch.object(gemini_ocr_service, '_prepare_gemini_input') as mock_prepare:
                mock_prepare.return_value = ("prompt", "image_data")
                
                result = await gemini_ocr_service.process_document(sample_document_data)
        
        assert result["status"] == ProcessingStatus.FAILED
        assert "quota exceeded" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_process_document_connection_error(self, gemini_ocr_service, mock_gemini_client, sample_document_data):
        """Test handling of connection errors with retry"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = "Extracted text after retry"
        
        mock_gemini_client.generate_content_async.side_effect = [
            ClientConnectionError("Connection failed"),
            mock_response
        ]
        
        with patch.object(gemini_ocr_service, '_validate_file', return_value=True):
            with patch.object(gemini_ocr_service, '_prepare_gemini_input') as mock_prepare:
                mock_prepare.return_value = ("prompt", "image_data")
                with patch('asyncio.sleep'):  # Speed up retry delay
                    result = await gemini_ocr_service.process_document(sample_document_data)
        
        assert result["status"] == ProcessingStatus.COMPLETED
        assert result["extracted_text"] == "Extracted text after retry"
        assert mock_gemini_client.generate_content_async.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_document_all_retries_fail(self, gemini_ocr_service, mock_gemini_client, sample_document_data):
        """Test handling when all retries fail"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        mock_gemini_client.generate_content_async.side_effect = ClientConnectionError("Persistent connection failure")
        
        with patch.object(gemini_ocr_service, '_validate_file', return_value=True):
            with patch.object(gemini_ocr_service, '_prepare_gemini_input') as mock_prepare:
                mock_prepare.return_value = ("prompt", "image_data")
                with patch('asyncio.sleep'):  # Speed up retry delays
                    result = await gemini_ocr_service.process_document(sample_document_data)
        
        assert result["status"] == ProcessingStatus.FAILED
        assert "connection failure" in result["error"].lower()


class TestImageSemantics:
    """Test image semantics analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_image_semantics_success(self, gemini_ocr_service, mock_gemini_client):
        """Test successful image semantics analysis"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        
        # Mock structured output from Gemini
        mock_response = Mock()
        mock_response.text = """{
            "image_type": "contract_document",
            "content_structure": {
                "has_header": true,
                "has_signature_blocks": true,
                "has_tables": false,
                "layout_quality": "good"
            },
            "text_regions": [
                {
                    "region_type": "header",
                    "confidence": 0.95,
                    "coordinates": {"x": 0, "y": 0, "width": 100, "height": 10}
                }
            ],
            "quality_metrics": {
                "overall_quality": 0.9,
                "text_clarity": 0.85,
                "image_sharpness": 0.88
            }
        }"""
        mock_gemini_client.generate_content_async.return_value = mock_response
        
        image_data = b"fake image data"
        result = await gemini_ocr_service.analyze_image_semantics(image_data, "pdf")
        
        assert result["image_type"] == "contract_document"
        assert result["content_structure"]["has_header"] == True
        assert len(result["text_regions"]) == 1
        assert result["quality_metrics"]["overall_quality"] == 0.9
    
    @pytest.mark.asyncio
    async def test_analyze_image_semantics_invalid_json(self, gemini_ocr_service, mock_gemini_client):
        """Test handling of invalid JSON response"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        
        mock_response = Mock()
        mock_response.text = "Invalid JSON response"
        mock_gemini_client.generate_content_async.return_value = mock_response
        
        image_data = b"fake image data"
        result = await gemini_ocr_service.analyze_image_semantics(image_data, "pdf")
        
        # Should return default/fallback structure
        assert "error" in result or "image_type" in result
    
    @pytest.mark.asyncio
    async def test_analyze_image_semantics_error_handling(self, gemini_ocr_service, mock_gemini_client):
        """Test error handling in image semantics analysis"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        mock_gemini_client.generate_content_async.side_effect = Exception("Analysis failed")
        
        image_data = b"fake image data"
        result = await gemini_ocr_service.analyze_image_semantics(image_data, "pdf")
        
        assert "error" in result
        assert "Analysis failed" in str(result["error"])


class TestUtilityMethods:
    """Test utility and helper methods"""
    
    @pytest.mark.asyncio
    async def test_prepare_gemini_input_pdf(self, gemini_ocr_service):
        """Test preparing input for PDF files"""
        document_data = {
            "content": b"PDF content",
            "file_type": "pdf",
            "filename": "test.pdf"
        }
        
        with patch.object(gemini_ocr_service, 'get_prompt', return_value="OCR prompt template"):
            prompt, image_data = await gemini_ocr_service._prepare_gemini_input(document_data)
        
        assert "OCR prompt template" in prompt
        assert image_data == b"PDF content"
    
    @pytest.mark.asyncio 
    async def test_prepare_gemini_input_image(self, gemini_ocr_service):
        """Test preparing input for image files"""
        document_data = {
            "content": b"Image content",
            "file_type": "png", 
            "filename": "test.png"
        }
        
        with patch.object(gemini_ocr_service, 'get_prompt', return_value="OCR prompt template"):
            prompt, image_data = await gemini_ocr_service._prepare_gemini_input(document_data)
        
        assert "OCR prompt template" in prompt
        assert image_data == b"Image content"
    
    def test_calculate_confidence_score_high_quality(self, gemini_ocr_service):
        """Test confidence calculation for high quality text"""
        extracted_text = "This is clear, well-formatted text with proper punctuation."
        confidence = gemini_ocr_service._calculate_confidence_score(extracted_text)
        
        assert confidence > 0.8
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    def test_calculate_confidence_score_poor_quality(self, gemini_ocr_service):
        """Test confidence calculation for poor quality text"""
        extracted_text = "th1s 1s p00rly f0rm4tt3d t3xt w1th m4ny 3rr0rs"
        confidence = gemini_ocr_service._calculate_confidence_score(extracted_text)
        
        assert confidence < 0.7
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    def test_calculate_confidence_score_empty_text(self, gemini_ocr_service):
        """Test confidence calculation for empty text"""
        extracted_text = ""
        confidence = gemini_ocr_service._calculate_confidence_score(extracted_text)
        
        assert confidence == 0.0
    
    def test_extract_text_metrics(self, gemini_ocr_service):
        """Test text metrics extraction"""
        text = "This is a sample text with multiple words and characters."
        
        metrics = gemini_ocr_service._extract_text_metrics(text)
        
        assert metrics["character_count"] == len(text)
        assert metrics["word_count"] == len(text.split())
        assert metrics["line_count"] == 1
        assert "average_word_length" in metrics
    
    def test_extract_text_metrics_multiline(self, gemini_ocr_service):
        """Test text metrics for multiline text"""
        text = "First line of text\nSecond line of text\nThird line"
        
        metrics = gemini_ocr_service._extract_text_metrics(text)
        
        assert metrics["line_count"] == 3
        assert metrics["character_count"] == len(text)
        assert metrics["word_count"] == 9  # Total words across all lines


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases"""
    
    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self, gemini_ocr_service, mock_gemini_client, sample_document_data):
        """Test complete processing pipeline"""
        gemini_ocr_service.gemini_client = mock_gemini_client
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.text = "CONTRACT OF SALE\n\nThis agreement is made between..."
        mock_gemini_client.generate_content_async.return_value = mock_response
        
        with patch.object(gemini_ocr_service, '_validate_file', return_value=True):
            with patch.object(gemini_ocr_service, '_prepare_gemini_input') as mock_prepare:
                mock_prepare.return_value = ("OCR prompt", b"document content")
                
                result = await gemini_ocr_service.process_document(sample_document_data)
        
        # Validate complete result structure
        assert result["status"] == ProcessingStatus.COMPLETED
        assert result["extracted_text"] == "CONTRACT OF SALE\n\nThis agreement is made between..."
        assert result["character_count"] > 0
        assert result["word_count"] > 0
        assert result["line_count"] >= 1
        assert result["extraction_confidence"] > 0
        assert "processing_time_ms" in result
        assert isinstance(result["processing_time_ms"], (int, float))
    
    @pytest.mark.asyncio
    async def test_service_with_user_context(self, mock_user_client):
        """Test service operation with user context"""
        with patch('app.services.gemini_ocr_service.get_gemini_client'):
            service = GeminiOCRService(user_client=mock_user_client)
            
            # Should have user context
            assert service.user_client == mock_user_client
            
            # Should be able to get user context
            with patch.object(service, 'get_user_context', return_value={"user_id": "test-user"}):
                context = service.get_user_context()
                assert context["user_id"] == "test-user"