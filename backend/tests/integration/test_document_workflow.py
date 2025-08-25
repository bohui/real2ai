"""
Integration tests for document upload and analysis workflow
"""

import pytest
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app


@pytest.fixture
def authenticated_client():
    """Create test client with mocked authentication"""
    client = TestClient(app)
    
    # Mock authentication middleware
    with patch('app.core.auth.get_current_user') as mock_auth:
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        mock_user.australian_state = "NSW"
        mock_user.user_type = "buyer"
        mock_user.subscription_status = "premium"
        mock_user.credits_remaining = 10
        mock_auth.return_value = mock_user
        yield client


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing"""
    pdf_content = b"%PDF-1.4\n%Test PDF content for integration testing"
    return ("test-contract.pdf", io.BytesIO(pdf_content), "application/pdf")


@pytest.fixture
def mock_document_service():
    """Mock document service with successful responses"""
    with patch('app.router.documents.DocumentService') as mock_service:
        service_instance = AsyncMock()
        
        # Mock successful upload
        service_instance.upload_document.return_value = {
            "id": "doc-12345",
            "filename": "test-contract.pdf",
            "file_type": "pdf",
            "file_size": 1024,
            "status": "uploaded",
            "storage_path": "documents/test-user-id/doc-12345.pdf",
            "processing_results": {
                "extracted_text": "Sample contract text",
                "extraction_confidence": 0.95
            }
        }
        
        # Mock document retrieval
        service_instance.get_document.return_value = {
            "id": "doc-12345",
            "filename": "test-contract.pdf",
            "upload_date": "2024-01-01T00:00:00Z",
            "status": "processed"
        }
        
        mock_service.return_value = service_instance
        yield service_instance


@pytest.fixture  
def mock_analysis_service():
    """Mock contract analysis service"""
    with patch('app.router.contracts.ContractAnalysisService') as mock_service:
        service_instance = AsyncMock()
        
        # Mock successful analysis start
        service_instance.start_analysis.return_value = {
            "analysis_id": "analysis-67890", 
            "contract_id": "doc-12345",
            "status": "processing",
            "estimated_completion": "2024-01-01T00:05:00Z"
        }
        
        # Mock analysis result
        service_instance.get_analysis_result.return_value = {
            "analysis_id": "analysis-67890",
            "contract_id": "doc-12345", 
            "status": "completed",
            "analysis_result": {
                "contract_terms": {
                    "parties": ["John Buyer", "Jane Seller"],
                    "property_address": "123 Test St, Sydney NSW",
                    "purchase_price": 750000,
                    "settlement_date": "2024-02-01"
                },
                "risk_assessment": {
                    "overall_risk_score": 3.2,
                    "risk_factors": [
                        {
                            "category": "financial",
                            "severity": "medium", 
                            "description": "Settlement period is shorter than recommended"
                        }
                    ]
                },
                "compliance_check": {
                    "state_compliance": True,
                    "compliance_issues": [],
                    "cooling_off_compliance": True
                },
                "recommendations": [
                    "Consider extending settlement period",
                    "Obtain pre-approval for financing"
                ]
            },
            "processing_time": 145.2
        }
        
        mock_service.return_value = service_instance
        yield service_instance


@pytest.mark.integration
class TestDocumentUpload:
    """Integration tests for document upload functionality"""
    
    def test_upload_document_success(self, authenticated_client, mock_document_service, sample_pdf_file):
        """Test successful document upload"""
        filename, file_content, content_type = sample_pdf_file
        
        files = {"file": (filename, file_content, content_type)}
        data = {"contract_type": "purchase_agreement"}
        
        response = authenticated_client.post("/api/documents/upload", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == "doc-12345"
        assert result["filename"] == "test-contract.pdf"
        assert result["status"] == "uploaded"
        assert "processing_results" in result
    
    def test_upload_document_invalid_file_type(self, authenticated_client, mock_document_service):
        """Test upload with invalid file type"""
        invalid_file = ("test.txt", io.BytesIO(b"Plain text content"), "text/plain")
        
        files = {"file": invalid_file}
        data = {"contract_type": "purchase_agreement"}
        
        response = authenticated_client.post("/api/documents/upload", files=files, data=data)
        
        # Should reject invalid file types
        assert response.status_code in [400, 422]
    
    def test_upload_document_too_large(self, authenticated_client, mock_document_service):
        """Test upload with file too large"""
        # Create a large file (simulate > 50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        large_file = ("large.pdf", io.BytesIO(large_content), "application/pdf")
        
        files = {"file": large_file}
        data = {"contract_type": "purchase_agreement"}
        
        response = authenticated_client.post("/api/documents/upload", files=files, data=data)
        
        # Should reject files that are too large
        assert response.status_code in [400, 413]
    
    def test_upload_document_missing_file(self, authenticated_client):
        """Test upload without file"""
        data = {"contract_type": "purchase_agreement"}
        
        response = authenticated_client.post("/api/documents/upload", data=data)
        
        assert response.status_code == 422
    
    def test_upload_document_service_error(self, authenticated_client, sample_pdf_file):
        """Test upload when document service fails"""
        filename, file_content, content_type = sample_pdf_file
        
        with patch('app.router.documents.DocumentService') as mock_service:
            service_instance = AsyncMock()
            service_instance.upload_document.side_effect = Exception("Storage service unavailable")
            mock_service.return_value = service_instance
            
            files = {"file": (filename, file_content, content_type)}
            data = {"contract_type": "purchase_agreement"}
            
            response = authenticated_client.post("/api/documents/upload", files=files, data=data)
        
        assert response.status_code == 500
    
    def test_get_document_details(self, authenticated_client, mock_document_service):
        """Test retrieving document details"""
        response = authenticated_client.get("/api/documents/doc-12345")
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == "doc-12345"
        assert result["filename"] == "test-contract.pdf"
    
    def test_get_document_not_found(self, authenticated_client, mock_document_service):
        """Test retrieving non-existent document"""
        mock_document_service.get_document.side_effect = Exception("Document not found")
        
        response = authenticated_client.get("/api/documents/nonexistent")
        
        assert response.status_code in [404, 500]


@pytest.mark.integration
class TestContractAnalysis:
    """Integration tests for contract analysis functionality"""
    
    def test_start_analysis_success(self, authenticated_client, mock_analysis_service):
        """Test starting contract analysis"""
        analysis_request = {
            "document_id": "doc-12345",
            "contract_type": "purchase_agreement", 
            "australian_state": "NSW",
            "analysis_preferences": {
                "focus_areas": ["risk_assessment", "compliance_check"],
                "include_recommendations": True
            }
        }
        
        response = authenticated_client.post("/api/contracts/analyze", json=analysis_request)
        
        assert response.status_code == 200
        result = response.json()
        assert result["analysis_id"] == "analysis-67890"
        assert result["status"] == "processing"
    
    def test_start_analysis_invalid_document(self, authenticated_client, mock_analysis_service):
        """Test analysis with invalid document ID"""
        mock_analysis_service.start_analysis.side_effect = Exception("Document not found")
        
        analysis_request = {
            "document_id": "invalid-doc-id",
            "contract_type": "purchase_agreement",
            "australian_state": "NSW"
        }
        
        response = authenticated_client.post("/api/contracts/analyze", json=analysis_request)
        
        assert response.status_code in [400, 404, 500]
    
    def test_start_analysis_missing_required_fields(self, authenticated_client):
        """Test analysis with missing required fields"""
        incomplete_request = {
            "document_id": "doc-12345"
            # Missing contract_type and australian_state
        }
        
        response = authenticated_client.post("/api/contracts/analyze", json=incomplete_request)
        
        assert response.status_code == 422
    
    def test_get_analysis_result_completed(self, authenticated_client, mock_analysis_service):
        """Test retrieving completed analysis result"""
        response = authenticated_client.get("/api/contracts/doc-12345/analysis")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert "analysis_result" in result
        assert "contract_terms" in result["analysis_result"]
        assert "risk_assessment" in result["analysis_result"]
        assert "compliance_check" in result["analysis_result"]
    
    def test_get_analysis_result_processing(self, authenticated_client, mock_analysis_service):
        """Test retrieving analysis result while still processing"""
        # Mock processing state
        mock_analysis_service.get_analysis_result.return_value = {
            "analysis_id": "analysis-67890",
            "contract_id": "doc-12345",
            "status": "processing",
            "progress": 0.65,
            "estimated_completion": "2024-01-01T00:03:00Z"
        }
        
        response = authenticated_client.get("/api/contracts/doc-12345/analysis")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "processing"
        assert result["progress"] == 0.65
    
    def test_get_analysis_result_failed(self, authenticated_client, mock_analysis_service):
        """Test retrieving failed analysis result"""
        # Mock failed analysis
        mock_analysis_service.get_analysis_result.return_value = {
            "analysis_id": "analysis-67890",
            "contract_id": "doc-12345",
            "status": "failed",
            "error": "Unable to extract text from document",
            "error_code": "EXTRACTION_FAILED"
        }
        
        response = authenticated_client.get("/api/contracts/doc-12345/analysis")
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "failed"
        assert "error" in result


@pytest.mark.integration
class TestCompleteWorkflow:
    """Integration tests for complete document analysis workflow"""
    
    def test_full_upload_and_analysis_workflow(self, authenticated_client, mock_document_service, mock_analysis_service, sample_pdf_file):
        """Test complete workflow from upload to analysis"""
        filename, file_content, content_type = sample_pdf_file
        
        # Step 1: Upload document
        files = {"file": (filename, file_content, content_type)}
        upload_data = {"contract_type": "purchase_agreement"}
        
        upload_response = authenticated_client.post("/api/documents/upload", files=files, data=upload_data)
        assert upload_response.status_code == 200
        
        upload_result = upload_response.json()
        document_id = upload_result["id"]
        
        # Step 2: Start analysis
        analysis_request = {
            "document_id": document_id,
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "analysis_preferences": {
                "focus_areas": ["risk_assessment"],
                "include_recommendations": True
            }
        }
        
        analysis_response = authenticated_client.post("/api/contracts/analyze", json=analysis_request)
        assert analysis_response.status_code == 200
        
        analysis_result = analysis_response.json()
        analysis_id = analysis_result["analysis_id"]
        
        # Step 3: Check analysis result
        result_response = authenticated_client.get(f"/api/contracts/{document_id}/analysis")
        assert result_response.status_code == 200
        
        final_result = result_response.json()
        assert final_result["status"] == "completed"
        assert final_result["contract_id"] == document_id
        
        # Verify analysis contains expected sections
        analysis_data = final_result["analysis_result"]
        assert "contract_terms" in analysis_data
        assert "risk_assessment" in analysis_data
        assert "compliance_check" in analysis_data
        assert "recommendations" in analysis_data
    
    def test_workflow_with_analysis_failure(self, authenticated_client, mock_document_service, sample_pdf_file):
        """Test workflow when analysis fails"""
        filename, file_content, content_type = sample_pdf_file
        
        # Step 1: Upload document successfully
        files = {"file": (filename, file_content, content_type)}
        upload_data = {"contract_type": "purchase_agreement"}
        
        upload_response = authenticated_client.post("/api/documents/upload", files=files, data=upload_data)
        assert upload_response.status_code == 200
        
        document_id = upload_response.json()["id"]
        
        # Step 2: Analysis fails
        with patch('app.router.contracts.ContractAnalysisService') as mock_service:
            service_instance = AsyncMock()
            service_instance.start_analysis.side_effect = Exception("Analysis service unavailable")
            mock_service.return_value = service_instance
            
            analysis_request = {
                "document_id": document_id,
                "contract_type": "purchase_agreement",
                "australian_state": "NSW"
            }
            
            analysis_response = authenticated_client.post("/api/contracts/analyze", json=analysis_request)
            assert analysis_response.status_code in [400, 500]
    
    def test_concurrent_analysis_requests(self, authenticated_client, mock_document_service, mock_analysis_service, sample_pdf_file):
        """Test handling concurrent analysis requests for same document"""
        filename, file_content, content_type = sample_pdf_file
        
        # Upload document first
        files = {"file": (filename, file_content, content_type)}
        upload_data = {"contract_type": "purchase_agreement"}
        
        upload_response = authenticated_client.post("/api/documents/upload", files=files, data=upload_data)
        document_id = upload_response.json()["id"]
        
        # Make multiple concurrent analysis requests
        analysis_request = {
            "document_id": document_id,
            "contract_type": "purchase_agreement",
            "australian_state": "NSW"
        }
        
        responses = []
        for _ in range(3):
            response = authenticated_client.post("/api/contracts/analyze", json=analysis_request)
            responses.append(response)
        
        # Should handle gracefully - either succeed with different analysis IDs
        # or reject duplicates appropriately
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1  # At least one should succeed
    
    def test_workflow_with_authentication_issues(self, sample_pdf_file):
        """Test workflow behavior with authentication issues"""
        unauthenticated_client = TestClient(app)
        filename, file_content, content_type = sample_pdf_file
        
        # Try to upload without authentication
        files = {"file": (filename, file_content, content_type)}
        upload_data = {"contract_type": "purchase_agreement"}
        
        response = unauthenticated_client.post("/api/documents/upload", files=files, data=upload_data)
        
        # Should require authentication
        assert response.status_code in [401, 403]


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling scenarios"""
    
    def test_database_connection_failure(self, authenticated_client, sample_pdf_file):
        """Test handling database connection failures"""
        filename, file_content, content_type = sample_pdf_file
        
        with patch('app.clients.factory.get_supabase_client') as mock_client:
            mock_client.side_effect = Exception("Database connection failed")
            
            files = {"file": (filename, file_content, content_type)}
            upload_data = {"contract_type": "purchase_agreement"}
            
            response = authenticated_client.post("/api/documents/upload", files=files, data=upload_data)
            
            assert response.status_code == 500
    
    def test_storage_service_failure(self, authenticated_client, sample_pdf_file):
        """Test handling storage service failures"""
        filename, file_content, content_type = sample_pdf_file
        
        with patch('app.router.documents.DocumentService') as mock_service:
            service_instance = AsyncMock()
            service_instance.upload_document.side_effect = Exception("Storage service unavailable")
            mock_service.return_value = service_instance
            
            files = {"file": (filename, file_content, content_type)}
            upload_data = {"contract_type": "purchase_agreement"}
            
            response = authenticated_client.post("/api/documents/upload", files=files, data=upload_data)
            
            assert response.status_code == 500
            result = response.json()
            assert "detail" in result
    
    def test_malformed_request_handling(self, authenticated_client):
        """Test handling malformed requests"""
        # Send invalid JSON
        response = authenticated_client.post(
            "/api/contracts/analyze",
            data="invalid json data",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422