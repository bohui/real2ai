"""
Comprehensive Integration Tests for Document Processing Business Logic

This test suite focuses on integration testing for core document processing workflows,
including document upload, text extraction, OCR processing, metadata extraction,
and storage operations. Tests the integration between multiple document services.
"""

import pytest
import asyncio
import json
import tempfile
import io
import os
from typing import Dict, Any, List, Optional, BinaryIO
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from app.services.document_service import DocumentService
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.core.auth import User
from app.models.supabase_models import Document
from app.schema.enums import ProcessingStatus
from app.prompts.schema.entity_extraction_schema import AustralianState, ContractType
from app.clients.supabase.client import SupabaseClient
from app.core.auth_context import AuthContext


@pytest.fixture
def test_user():
    """Create a test user for document operations"""
    return User(
        id="test-user-123",
        email="test@example.com",
        australian_state="NSW",
        user_type="buyer",
        subscription_status="premium",
        credits_remaining=50,
        preferences={},
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(timezone.utc),
        onboarding_preferences={},
    )


@pytest.fixture
def auth_context(test_user):
    """Set up authenticated context for user operations"""
    context = AuthContext()
    context.set_current_user(test_user)
    return context


@pytest.fixture
def sample_contract_pdf_content():
    """Sample PDF content for testing"""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(CONTRACT OF SALE - Test Document) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000015 00000 n 
0000000074 00000 n 
0000000120 00000 n 
0000000216 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
309
%%EOF"""


@pytest.fixture
def sample_contract_images():
    """Sample image files for OCR testing"""
    # Create simple test images
    images = []
    for i in range(3):
        # Simple bitmap data representing a contract page
        img_data = (
            b"\x89PNG\r\n\x1a\n"
            + b"Test contract page "
            + str(i).encode()
            + b" content"
        )
        images.append(
            {
                "filename": f"contract_page_{i+1}.png",
                "content": img_data,
                "content_type": "image/png",
            }
        )
    return images


@pytest.fixture
def sample_documents_various_formats():
    """Sample documents in various supported formats"""
    return {
        "pdf": {
            "filename": "contract.pdf",
            "content": b"%PDF-1.4 Sample PDF contract content",
            "content_type": "application/pdf",
        },
        "docx": {
            "filename": "contract.docx",
            "content": b"PK\x03\x04" + b"Sample DOCX contract content",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        "image": {
            "filename": "contract_scan.jpg",
            "content": b"\xff\xd8\xff\xe0" + b"Sample JPEG contract scan",
            "content_type": "image/jpeg",
        },
        "txt": {
            "filename": "contract.txt",
            "content": b"Plain text contract content for testing",
            "content_type": "text/plain",
        },
    }


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for document storage operations"""
    client = AsyncMock(spec=SupabaseClient)

    # Mock document operations
    client.create_document = AsyncMock(
        return_value={
            "id": "doc-12345",
            "user_id": "test-user-123",
            "filename": "test_contract.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "status": "uploaded",
            "content_type": "application/pdf",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    client.update_document_status = AsyncMock()
    client.store_document_content = AsyncMock()
    client.get_document = AsyncMock()
    client.store_extracted_entities = AsyncMock()
    client.create_document_pages = AsyncMock()

    return client


@pytest.fixture
def document_service(auth_context, mock_supabase_client):
    """Create DocumentService with mocked dependencies"""
    with patch(
        "app.services.document_service.SupabaseClient",
        return_value=mock_supabase_client,
    ):
        service = DocumentService(user_client=mock_supabase_client)
        # Set the auth context
        with patch("app.core.auth_context.get_auth_context", return_value=auth_context):
            return service


@pytest.mark.integration
@pytest.mark.asyncio
class TestDocumentProcessingIntegration:
    """Integration tests for document processing business logic"""

    async def test_complete_pdf_document_processing_workflow(
        self,
        document_service,
        sample_contract_pdf_content,
        auth_context,
        mock_supabase_client,
    ):
        """Test complete PDF document processing from upload to analysis"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            # Configure OCR service mock
            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "CONTRACT OF SALE\n\nVendor: John Smith\nPurchaser: Jane Doe\nProperty: 123 Test St\nPrice: $500,000",
                    "extraction_confidence": 0.95,
                    "character_count": 89,
                    "word_count": 15,
                    "processing_time_ms": 1500.0,
                }
            )

            # Entity extraction now handled elsewhere; remove SemanticAnalysisService mocking

            # Create document data
            document_data = {
                "filename": "test_contract.pdf",
                "content": sample_contract_pdf_content,
                "content_type": "application/pdf",
                "file_size": len(sample_contract_pdf_content),
            }

            # Process document
            result = await document_service.process_document_complete(
                document_data,
                include_ocr=True,
                include_entity_extraction=True,
                include_semantic_analysis=True,
            )

            # Verify processing completed successfully
            assert result is not None
            assert result["success"] is True
            assert "document_id" in result
            assert "processing_results" in result

            processing_results = result["processing_results"]

            # Verify OCR results
            assert "ocr_results" in processing_results
            ocr_results = processing_results["ocr_results"]
            assert ocr_results["status"] == ProcessingStatus.COMPLETED
            assert ocr_results["extraction_confidence"] >= 0.9
            assert len(ocr_results["extracted_text"]) > 0

            # Verify entity extraction
            assert "entity_extraction" in processing_results
            entities = processing_results["entity_extraction"]["entities"]
            assert len(entities) > 0

            # Verify extracted entities
            person_entities = [e for e in entities if e["type"] == "PERSON"]
            money_entities = [e for e in entities if e["type"] == "MONEY"]
            assert len(person_entities) >= 2  # Vendor and purchaser
            assert len(money_entities) >= 1  # Purchase price

            # Verify document was stored
            mock_supabase_client.create_document.assert_called_once()
            mock_supabase_client.store_document_content.assert_called_once()
            mock_supabase_client.store_extracted_entities.assert_called_once()

            # Verify OCR was called
            ocr_instance.process_document.assert_called_once()

    async def test_multi_page_document_processing(
        self, document_service, auth_context, mock_supabase_client
    ):
        """Test processing of multi-page documents"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            # Create multi-page document content
            multi_page_content = b"%PDF-1.4 Multi-page contract content"

            # Configure OCR to return page-by-page results
            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "Full document text from all pages",
                    "page_results": [
                        {
                            "page_number": 1,
                            "text": "Page 1: CONTRACT OF SALE header and parties",
                            "confidence": 0.96,
                        },
                        {
                            "page_number": 2,
                            "text": "Page 2: Property details and conditions",
                            "confidence": 0.94,
                        },
                        {
                            "page_number": 3,
                            "text": "Page 3: Signatures and legal clauses",
                            "confidence": 0.93,
                        },
                    ],
                    "total_pages": 3,
                    "extraction_confidence": 0.94,
                }
            )

            # Mock document page storage
            mock_supabase_client.create_document_pages = AsyncMock(
                return_value=[
                    {"id": "page-1", "page_number": 1},
                    {"id": "page-2", "page_number": 2},
                    {"id": "page-3", "page_number": 3},
                ]
            )

            document_data = {
                "filename": "multi_page_contract.pdf",
                "content": multi_page_content,
                "content_type": "application/pdf",
                "file_size": len(multi_page_content),
            }

            # Process multi-page document
            result = await document_service.process_document_complete(
                document_data, include_ocr=True, include_page_extraction=True
            )

            # Verify multi-page processing
            assert result["success"] is True
            ocr_results = result["processing_results"]["ocr_results"]

            assert "page_results" in ocr_results
            assert ocr_results["total_pages"] == 3
            assert len(ocr_results["page_results"]) == 3

            # Verify page-specific results
            for i, page_result in enumerate(ocr_results["page_results"]):
                assert page_result["page_number"] == i + 1
                assert len(page_result["text"]) > 0
                assert page_result["confidence"] > 0.9

            # Verify page storage was called
            mock_supabase_client.create_document_pages.assert_called_once()

    async def test_document_processing_various_file_formats(
        self,
        document_service,
        sample_documents_various_formats,
        auth_context,
        mock_supabase_client,
    ):
        """Test processing of various document formats"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance

            # Test each format
            format_results = {}

            for format_name, document_data in sample_documents_various_formats.items():

                # Configure OCR response based on format
                if format_name == "pdf":
                    ocr_response = {
                        "status": ProcessingStatus.COMPLETED,
                        "extracted_text": "PDF contract text extracted successfully",
                        "extraction_confidence": 0.95,
                    }
                elif format_name == "image":
                    ocr_response = {
                        "status": ProcessingStatus.COMPLETED,
                        "extracted_text": "Image OCR text extracted from scan",
                        "extraction_confidence": 0.87,  # Typically lower for images
                    }
                elif format_name == "docx":
                    ocr_response = {
                        "status": ProcessingStatus.COMPLETED,
                        "extracted_text": "DOCX document text extracted",
                        "extraction_confidence": 0.98,  # High for structured documents
                    }
                else:  # txt
                    ocr_response = {
                        "status": ProcessingStatus.COMPLETED,
                        "extracted_text": "Plain text content",
                        "extraction_confidence": 1.0,  # Perfect for plain text
                    }

                ocr_instance.process_document = AsyncMock(return_value=ocr_response)

                # Process document
                result = await document_service.process_document_complete(
                    document_data, include_ocr=True
                )

                format_results[format_name] = result

                # Verify format-specific processing
                assert result["success"] is True
                ocr_results = result["processing_results"]["ocr_results"]
                assert ocr_results["status"] == ProcessingStatus.COMPLETED

                # Format-specific validations
                if format_name == "image":
                    # Images typically have lower confidence
                    assert ocr_results["extraction_confidence"] >= 0.8
                elif format_name == "txt":
                    # Plain text should have perfect confidence
                    assert ocr_results["extraction_confidence"] == 1.0
                else:
                    # PDF and DOCX should have high confidence
                    assert ocr_results["extraction_confidence"] >= 0.9

            # Verify all formats were processed successfully
            assert len(format_results) == len(sample_documents_various_formats)
            assert all(result["success"] for result in format_results.values())

    async def test_document_processing_error_handling_and_recovery(
        self,
        document_service,
        sample_contract_pdf_content,
        auth_context,
        mock_supabase_client,
    ):
        """Test error handling and recovery in document processing"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            # Test OCR service failure
            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance
            ocr_instance.process_document = AsyncMock(
                side_effect=Exception("OCR service unavailable")
            )

            document_data = {
                "filename": "test_contract.pdf",
                "content": sample_contract_pdf_content,
                "content_type": "application/pdf",
                "file_size": len(sample_contract_pdf_content),
            }

            # Should handle OCR failure gracefully
            result = await document_service.process_document_complete(
                document_data, include_ocr=True
            )

            # Verify error handling
            assert "error" in result or result.get("success", True) is False

            # Test database storage failure
            mock_supabase_client.create_document = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            result = await document_service.process_document_complete(document_data)

            # Should handle database failure
            assert "error" in result or result.get("success", True) is False

            # Test partial failure recovery
            mock_supabase_client.create_document = AsyncMock(
                return_value={"id": "doc-12345"}
            )
            mock_supabase_client.store_document_content = AsyncMock(
                side_effect=Exception("Storage failed")
            )

            # Should create document but fail on content storage
            result = await document_service.process_document_complete(document_data)

            # Verify partial completion handling
            assert "document_id" in result
            assert "error" in result or "warnings" in result

    async def test_document_quality_validation_and_metrics(
        self, document_service, auth_context, mock_supabase_client
    ):
        """Test document quality validation and metrics calculation"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance

            # Test high-quality document
            high_quality_content = b"%PDF-1.4 High quality contract with clear text"
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "Clear, well-formatted contract text with all details",
                    "extraction_confidence": 0.98,
                    "character_count": 1500,
                    "word_count": 250,
                    "quality_metrics": {
                        "text_clarity": 0.97,
                        "image_sharpness": 0.95,
                        "overall_quality": 0.96,
                    },
                }
            )

            document_data = {
                "filename": "high_quality_contract.pdf",
                "content": high_quality_content,
                "content_type": "application/pdf",
                "file_size": len(high_quality_content),
            }

            result = await document_service.process_document_complete(
                document_data, include_ocr=True, include_quality_metrics=True
            )

            # Verify high-quality metrics
            assert result["success"] is True
            quality_metrics = result["processing_results"].get("quality_metrics", {})
            assert quality_metrics.get("overall_quality", 0) >= 0.95
            assert quality_metrics.get("extraction_confidence", 0) >= 0.95

            # Test low-quality document
            low_quality_content = b"%PDF-1.4 Poor quality scanned document"
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "Poor qu4lity t3xt w1th err0rs",
                    "extraction_confidence": 0.45,
                    "character_count": 30,
                    "word_count": 6,
                    "quality_metrics": {
                        "text_clarity": 0.3,
                        "image_sharpness": 0.2,
                        "overall_quality": 0.25,
                    },
                }
            )

            document_data["content"] = low_quality_content

            result_low = await document_service.process_document_complete(
                document_data, include_ocr=True, include_quality_metrics=True
            )

            # Should identify low quality
            quality_metrics_low = result_low["processing_results"].get(
                "quality_metrics", {}
            )
            assert quality_metrics_low.get("overall_quality", 1.0) < 0.5
            assert quality_metrics_low.get("extraction_confidence", 1.0) < 0.5

            # Should include quality warnings
            assert "quality_warnings" in result_low["processing_results"]

    async def test_concurrent_document_processing(
        self,
        document_service,
        sample_contract_pdf_content,
        auth_context,
        mock_supabase_client,
    ):
        """Test handling of concurrent document processing requests"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "Contract text extracted successfully",
                    "extraction_confidence": 0.92,
                }
            )

            # Create multiple document processing tasks
            document_tasks = []
            for i in range(5):
                document_data = {
                    "filename": f"contract_{i+1}.pdf",
                    "content": sample_contract_pdf_content,
                    "content_type": "application/pdf",
                    "file_size": len(sample_contract_pdf_content),
                }

                task = document_service.process_document_complete(
                    document_data, include_ocr=True
                )
                document_tasks.append(task)

            # Process all documents concurrently
            results = await asyncio.gather(*document_tasks, return_exceptions=True)

            # Verify all processing completed
            successful_results = [
                r for r in results if isinstance(r, dict) and r.get("success", False)
            ]
            assert len(successful_results) == 5

            # Verify unique document IDs
            document_ids = [r.get("document_id") for r in successful_results]
            assert len(set(document_ids)) == len(document_ids)

            # Verify OCR was called for each document
            assert ocr_instance.process_document.call_count == 5

    async def test_document_metadata_extraction_and_storage(
        self,
        document_service,
        sample_contract_pdf_content,
        auth_context,
        mock_supabase_client,
    ):
        """Test metadata extraction and storage during document processing"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            # Configure OCR mock
            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "CONTRACT OF SALE Property: 123 Main St Price: $750,000",
                    "extraction_confidence": 0.94,
                    "metadata": {
                        "creation_date": "2024-01-15",
                        "modification_date": "2024-01-16",
                        "author": "Legal Document System",
                        "title": "Purchase Agreement",
                    },
                }
            )

            # Removed SemanticAnalysisService mocking

            document_data = {
                "filename": "detailed_contract.pdf",
                "content": sample_contract_pdf_content,
                "content_type": "application/pdf",
                "file_size": len(sample_contract_pdf_content),
            }

            result = await document_service.process_document_complete(
                document_data,
                include_ocr=True,
                include_metadata_extraction=True,
                include_semantic_analysis=True,
            )

            # Verify metadata extraction
            assert result["success"] is True
            processing_results = result["processing_results"]

            # Verify document metadata
            assert "document_metadata" in processing_results
            metadata = processing_results["document_metadata"]
            assert "creation_date" in metadata
            assert "author" in metadata
            assert "title" in metadata

            # Verify semantic analysis results
            assert "semantic_analysis" in processing_results
            semantic_results = processing_results["semantic_analysis"]
            assert semantic_results["document_type"] == "contract"
            assert semantic_results["contract_type"] == ContractType.PURCHASE_AGREEMENT
            assert semantic_results["australian_state"] == AustralianState.NSW
            assert len(semantic_results["key_sections"]) > 0

            # Verify completeness assessment
            assert semantic_results["completeness_score"] > 0.8

            # Verify storage operations
            mock_supabase_client.create_document.assert_called_once()

            # Verify services were called
            ocr_instance.process_document.assert_called_once()

    async def test_document_processing_performance_benchmarks(
        self,
        document_service,
        sample_contract_pdf_content,
        auth_context,
        mock_supabase_client,
    ):
        """Test document processing performance and benchmark tracking"""

        with patch("app.services.ai.gemini_ocr_service.GeminiOCRService") as mock_ocr:

            ocr_instance = AsyncMock()
            mock_ocr.return_value = ocr_instance
            ocr_instance.process_document = AsyncMock(
                return_value={
                    "status": ProcessingStatus.COMPLETED,
                    "extracted_text": "Performance test contract text",
                    "extraction_confidence": 0.90,
                    "processing_time_ms": 1250.0,  # Track processing time
                    "performance_metrics": {
                        "ocr_time_ms": 800.0,
                        "text_processing_time_ms": 350.0,
                        "validation_time_ms": 100.0,
                    },
                }
            )

            document_data = {
                "filename": "performance_test_contract.pdf",
                "content": sample_contract_pdf_content,
                "content_type": "application/pdf",
                "file_size": len(sample_contract_pdf_content),
            }

            # Track processing start time
            start_time = datetime.now(timezone.utc)

            result = await document_service.process_document_complete(
                document_data, include_ocr=True, include_performance_metrics=True
            )

            end_time = datetime.now(timezone.utc)
            total_processing_time = (end_time - start_time).total_seconds() * 1000

            # Verify performance tracking
            assert result["success"] is True
            assert "performance_metrics" in result["processing_results"]

            performance_metrics = result["processing_results"]["performance_metrics"]
            assert "total_processing_time_ms" in performance_metrics
            assert "ocr_processing_time_ms" in performance_metrics

            # Verify processing times are reasonable
            assert performance_metrics["total_processing_time_ms"] > 0
            assert (
                performance_metrics["total_processing_time_ms"]
                <= total_processing_time + 1000
            )  # Allow buffer

            # Performance benchmarks (adjust based on requirements)
            assert (
                performance_metrics["ocr_processing_time_ms"] < 5000
            )  # Should complete within 5 seconds

            # Verify performance is logged for monitoring
            assert "benchmark_data" in result["processing_results"]
