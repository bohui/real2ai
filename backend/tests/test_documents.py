"""
Test document management endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from io import BytesIO


@pytest.mark.api
class TestDocumentUpload:
    """Test document upload functionality"""
    
    def test_upload_document_success(self, client: TestClient, mock_db_client):
        """Test successful document upload"""
        # DocumentService.upload_file is already mocked in conftest.py
        
        # Mock database insertion - it needs to return a result object
        mock_db_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "test-doc-id"}]
        )
        
        # Create test file
        test_file = BytesIO(b"fake pdf content")
        
        # Mock the background task to prevent actual execution
        with patch('app.tasks.background_tasks.process_document_background', new_callable=AsyncMock) as mock_bg_task:
            response = client.post(
                "/api/documents/upload",
                files={"file": ("test-contract.pdf", test_file, "application/pdf")},
                data={
                    "contract_type": "purchase_agreement",
                    "australian_state": "NSW"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == "test-doc-id"
            assert data["filename"] == "test-contract.pdf"
            assert data["upload_status"] == "uploaded"
    
    def test_upload_document_invalid_file_type(self, client: TestClient):
        """Test document upload with invalid file type"""
        test_file = BytesIO(b"fake content")
        
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.exe", test_file, "application/octet-stream")},
            data={
                "contract_type": "purchase_agreement",
                "australian_state": "NSW"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid file type" in data["detail"]
    
    def test_upload_document_file_too_large(self, client: TestClient, test_settings):
        """Test document upload with file too large"""
        # Create large file content
        large_content = b"x" * (test_settings.max_file_size + 1)
        test_file = BytesIO(large_content)
        
        response = client.post(
            "/api/documents/upload",
            files={"file": ("large-contract.pdf", test_file, "application/pdf")},
            data={
                "contract_type": "purchase_agreement",
                "australian_state": "NSW"
            }
        )
        
        assert response.status_code == 413
        data = response.json()
        assert "File too large" in data["detail"]
    
    def test_upload_document_empty_file(self, client: TestClient):
        """Test document upload with empty file"""
        # Create empty file
        empty_file = BytesIO(b"")
        
        response = client.post(
            "/api/documents/upload",
            files={"file": ("empty-contract.pdf", empty_file, "application/pdf")},
            data={
                "contract_type": "purchase_agreement", 
                "australian_state": "NSW"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Empty file uploaded" in data["detail"]
    
    def test_upload_document_no_file(self, client: TestClient):
        """Test document upload without file"""
        response = client.post(
            "/api/documents/upload",
            data={
                "contract_type": "purchase_agreement",
                "australian_state": "NSW"
            }
        )
        
        assert response.status_code == 422  # Validation error


@pytest.mark.api
class TestGetDocument:
    """Test get document functionality"""
    
    def test_get_document_success(self, client: TestClient, mock_db_client, sample_document_data):
        """Test successful document retrieval"""
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document_data]
        )
        
        response = client.get("/api/documents/test-doc-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-doc-id"
        assert data["filename"] == "test-contract.pdf"
        assert data["status"] == "uploaded"
    
    def test_get_document_not_found(self, client: TestClient, mock_db_client):
        """Test document retrieval when document doesn't exist"""
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        response = client.get("/api/documents/nonexistent-doc-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Document not found"
    
    def test_get_document_unauthorized_user(self, client: TestClient, mock_db_client, sample_document_data):
        """Test document retrieval by unauthorized user"""
        # Modify document to belong to different user
        unauthorized_doc = sample_document_data.copy()
        unauthorized_doc["user_id"] = "different-user-id"
        
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]  # No results for this user
        )
        
        response = client.get("/api/documents/test-doc-id")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Document not found"


@pytest.mark.api
class TestDocumentProcessing:
    """Test document processing functionality"""
    
    def test_document_processing_states(self, sample_document_data):
        """Test document processing state transitions"""
        states = ["uploaded", "processing", "processed", "failed"]
        
        for state in states:
            doc = sample_document_data.copy()
            doc["status"] = state
            
            # Validate state is one of expected values
            assert doc["status"] in states
    
    def test_processing_results_structure(self, sample_document_data):
        """Test processing results have expected structure"""
        processing_results = sample_document_data["processing_results"]
        
        required_fields = ["extracted_text", "extraction_confidence", "character_count", "word_count"]
        
        for field in required_fields:
            assert field in processing_results
        
        # Validate data types
        assert isinstance(processing_results["extracted_text"], str)
        assert isinstance(processing_results["extraction_confidence"], (int, float))
        assert isinstance(processing_results["character_count"], int)
        assert isinstance(processing_results["word_count"], int)
        
        # Validate ranges
        assert 0 <= processing_results["extraction_confidence"] <= 1
        assert processing_results["character_count"] >= 0
        assert processing_results["word_count"] >= 0