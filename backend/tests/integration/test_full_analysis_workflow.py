"""
Integration tests for the full document analysis workflow.
"""
import asyncio
import tempfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.core.auth_context import AuthContext
from app.core.auth import User
from app.schema.contract import ContractAnalysisRequest
from app.schema.enums import AustralianState, ProcessingStatus


@pytest.fixture
def test_user():
    """Create a test user for authentication."""
    return User(
        id="test-user-123",
        email="test@example.com",
        australian_state="NSW",
        user_type="lawyer",
        subscription_status="premium",
        credits_remaining=100,
        preferences={},
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(),
        onboarding_preferences={}
    )


@pytest.fixture
def auth_context(test_user):
    """Set up authenticated context."""
    context = AuthContext()
    context.set_current_user(test_user)
    return context


@pytest.fixture
def sample_document():
    """Create a sample PDF document for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b'%PDF-1.4 Sample contract content for testing')
        return {
            'file': tmp.name,
            'filename': 'test_contract.pdf',
            'content_type': 'application/pdf'
        }


class TestFullAnalysisWorkflow:
    """Test the complete document analysis workflow end-to-end."""

    @pytest.mark.asyncio
    async def test_complete_contract_analysis_workflow(self, auth_context, sample_document):
        """Test the complete workflow from document upload to analysis results."""
        
        with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
            with patch('app.services.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                with patch('app.services.document_service.DocumentService') as mock_doc_service:
                    # Configure mocks
                    await self._configure_workflow_mocks(mock_service, mock_ocr, mock_doc_service)
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        # Step 1: Upload document
                        upload_response = await self._upload_document(client, sample_document)
                        assert upload_response.status_code == 200
                        document_id = upload_response.json()['document_id']
                        
                        # Step 2: Start analysis
                        analysis_response = await self._start_analysis(client, document_id)
                        assert analysis_response.status_code == 200
                        session_id = analysis_response.json()['session_id']
                        
                        # Step 3: Monitor analysis progress
                        progress_complete = await self._monitor_analysis_progress(client, session_id)
                        assert progress_complete is True
                        
                        # Step 4: Get final results
                        results_response = await self._get_analysis_results(client, session_id)
                        assert results_response.status_code == 200
                        
                        # Verify complete workflow results
                        results = results_response.json()
                        assert results['success'] is True
                        assert 'analysis_results' in results
                        assert results['analysis_results']['overall_confidence'] >= 0.8
                        assert len(results['analysis_results']['recommendations']) > 0

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, auth_context, sample_document):
        """Test workflow behavior when errors occur at different stages."""
        
        with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
            with patch('app.services.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                # Configure OCR to fail
                mock_ocr.return_value.process_document.side_effect = Exception("OCR processing failed")
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    # Upload should succeed
                    upload_response = await self._upload_document(client, sample_document)
                    assert upload_response.status_code == 200
                    
                    # Analysis should handle OCR failure gracefully
                    document_id = upload_response.json()['document_id']
                    analysis_response = await self._start_analysis(client, document_id)
                    
                    # Should return error response
                    assert analysis_response.status_code == 422
                    error_data = analysis_response.json()
                    assert 'error' in error_data
                    assert 'OCR processing failed' in error_data['error']

    @pytest.mark.asyncio
    async def test_workflow_with_different_contract_types(self, auth_context, sample_document):
        """Test workflow with different Australian contract types."""
        
        contract_types = [
            'purchase_agreement',
            'lease_agreement', 
            'off_plan',
            'auction'
        ]
        
        for contract_type in contract_types:
            with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
                with patch('app.services.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                    with patch('app.services.document_service.DocumentService') as mock_doc_service:
                        await self._configure_workflow_mocks(mock_service, mock_ocr, mock_doc_service)
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            # Upload document
                            upload_response = await self._upload_document(client, sample_document)
                            document_id = upload_response.json()['document_id']
                            
                            # Start analysis with specific contract type
                            analysis_response = await client.post(
                                "/contracts/analyze",
                                json={
                                    'document_id': document_id,
                                    'contract_type': contract_type,
                                    'australian_state': 'NSW',
                                    'include_recommendations': True
                                },
                                headers={'Authorization': 'Bearer test-token'}
                            )
                            
                            assert analysis_response.status_code == 200
                            results = analysis_response.json()
                            
                            # Verify contract type is handled correctly
                            assert results['contract_type'] == contract_type

    @pytest.mark.asyncio
    async def test_workflow_with_different_states(self, auth_context, sample_document):
        """Test workflow with different Australian states."""
        
        australian_states = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'ACT', 'NT']
        
        for state in australian_states:
            with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
                with patch('app.services.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                    with patch('app.services.document_service.DocumentService') as mock_doc_service:
                        await self._configure_workflow_mocks(mock_service, mock_ocr, mock_doc_service)
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            upload_response = await self._upload_document(client, sample_document)
                            document_id = upload_response.json()['document_id']
                            
                            analysis_response = await client.post(
                                "/contracts/analyze", 
                                json={
                                    'document_id': document_id,
                                    'contract_type': 'purchase_agreement',
                                    'australian_state': state,
                                    'include_recommendations': True
                                },
                                headers={'Authorization': 'Bearer test-token'}
                            )
                            
                            assert analysis_response.status_code == 200
                            results = analysis_response.json()
                            assert results['australian_state'] == state

    @pytest.mark.asyncio
    async def test_concurrent_analysis_workflows(self, auth_context, sample_document):
        """Test multiple concurrent analysis workflows."""
        
        with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
            with patch('app.services.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                with patch('app.services.document_service.DocumentService') as mock_doc_service:
                    await self._configure_workflow_mocks(mock_service, mock_ocr, mock_doc_service)
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        # Create multiple concurrent workflows
                        workflow_tasks = []
                        for i in range(5):
                            task = self._run_single_workflow(client, sample_document, f"session-{i}")
                            workflow_tasks.append(task)
                        
                        # Run all workflows concurrently
                        results = await asyncio.gather(*workflow_tasks)
                        
                        # Verify all workflows completed successfully
                        assert len(results) == 5
                        assert all(result['success'] for result in results)
                        
                        # Verify each workflow has unique session ID
                        session_ids = [result['session_id'] for result in results]
                        assert len(set(session_ids)) == 5

    @pytest.mark.asyncio
    async def test_workflow_caching_behavior(self, auth_context, sample_document):
        """Test caching behavior throughout the workflow."""
        
        with patch('app.core.cache_manager.CacheManager') as mock_cache:
            with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
                with patch('app.services.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                    with patch('app.services.document_service.DocumentService') as mock_doc_service:
                        # Configure cache behavior
                        cache_instance = AsyncMock()
                        mock_cache.return_value = cache_instance
                        cache_instance.get.return_value = None  # Cache miss initially
                        cache_instance.set.return_value = True
                        
                        await self._configure_workflow_mocks(mock_service, mock_ocr, mock_doc_service)
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            # First workflow run
                            result1 = await self._run_single_workflow(client, sample_document, "cache-test-1")
                            
                            # Verify cache was called
                            assert cache_instance.get.called
                            assert cache_instance.set.called
                            
                            # Second workflow run (should benefit from caching)
                            cache_instance.reset_mock()
                            cache_instance.get.return_value = {
                                'cached_ocr_result': 'cached text'
                            }
                            
                            result2 = await self._run_single_workflow(client, sample_document, "cache-test-2")
                            
                            # Verify cache was checked again
                            assert cache_instance.get.called
                            assert result2['success'] is True

    # Helper methods
    
    async def _configure_workflow_mocks(self, mock_service, mock_ocr, mock_doc_service):
        """Configure mocks for successful workflow execution."""
        
        # OCR Service Mock
        ocr_instance = AsyncMock()
        mock_ocr.return_value = ocr_instance
        ocr_instance.process_document.return_value = {
            'success': True,
            'extracted_text': 'Sample contract text extracted from PDF',
            'confidence': 0.95,
            'metadata': {
                'pages': 5,
                'processing_time': 2.1
            }
        }
        
        # Contract Analysis Service Mock
        service_instance = AsyncMock()
        mock_service.return_value = service_instance
        service_instance.analyze_contract.return_value = {
            'success': True,
            'session_id': 'test-session-123',
            'analysis_results': {
                'overall_confidence': 0.87,
                'contract_terms': {
                    'purchase_price': 850000,
                    'settlement_date': '2024-03-15',
                    'cooling_off_period': '5 business days'
                },
                'risk_assessment': {
                    'overall_risk_score': 2.8,
                    'risk_factors': ['High purchase price', 'Short settlement period']
                },
                'recommendations': [
                    'Consider extending settlement period',
                    'Review cooling-off rights carefully'
                ]
            },
            'quality_metrics': {
                'overall_confidence': 0.87,
                'validation_passed': True
            }
        }
        
        # Document Service Mock  
        doc_service_instance = AsyncMock()
        mock_doc_service.return_value = doc_service_instance
        doc_service_instance.store_document.return_value = {
            'document_id': 'doc-123',
            'status': 'stored'
        }
        doc_service_instance.get_document.return_value = {
            'id': 'doc-123',
            'filename': 'test_contract.pdf',
            'content': b'Sample PDF content',
            'metadata': {'size': 1024}
        }

    async def _upload_document(self, client: AsyncClient, sample_document: Dict[str, Any]) -> Any:
        """Upload a document via the API."""
        with open(sample_document['file'], 'rb') as f:
            files = {'file': (sample_document['filename'], f, sample_document['content_type'])}
            response = await client.post(
                "/documents/upload",
                files=files,
                headers={'Authorization': 'Bearer test-token'}
            )
        return response

    async def _start_analysis(self, client: AsyncClient, document_id: str) -> Any:
        """Start contract analysis via the API."""
        return await client.post(
            "/contracts/analyze",
            json={
                'document_id': document_id,
                'contract_type': 'purchase_agreement',
                'australian_state': 'NSW',
                'include_recommendations': True
            },
            headers={'Authorization': 'Bearer test-token'}
        )

    async def _monitor_analysis_progress(self, client: AsyncClient, session_id: str) -> bool:
        """Monitor analysis progress until completion."""
        max_attempts = 10
        for attempt in range(max_attempts):
            response = await client.get(
                f"/contracts/{session_id}/progress",
                headers={'Authorization': 'Bearer test-token'}
            )
            
            if response.status_code == 200:
                progress = response.json()
                if progress.get('status') == 'completed':
                    return True
                elif progress.get('status') == 'failed':
                    return False
                    
            await asyncio.sleep(0.5)  # Wait before next check
            
        return False  # Timeout

    async def _get_analysis_results(self, client: AsyncClient, session_id: str) -> Any:
        """Get final analysis results."""
        return await client.get(
            f"/contracts/{session_id}/analysis",
            headers={'Authorization': 'Bearer test-token'}
        )

    async def _run_single_workflow(self, client: AsyncClient, sample_document: Dict[str, Any], session_suffix: str) -> Dict[str, Any]:
        """Run a complete single workflow and return results."""
        # Upload
        upload_response = await self._upload_document(client, sample_document)
        document_id = upload_response.json()['document_id']
        
        # Analyze
        analysis_response = await self._start_analysis(client, document_id)
        session_id = analysis_response.json()['session_id']
        
        # Wait for completion
        await self._monitor_analysis_progress(client, session_id)
        
        # Get results
        results_response = await self._get_analysis_results(client, session_id)
        results = results_response.json()
        
        return {
            'success': results.get('success', False),
            'session_id': session_id,
            'document_id': document_id,
            'analysis_results': results.get('analysis_results', {})
        }


class TestWorkflowEdgeCases:
    """Test edge cases and error conditions in the workflow."""

    @pytest.mark.asyncio
    async def test_invalid_file_upload(self, auth_context):
        """Test workflow with invalid file types."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try uploading text file as contract
            files = {'file': ('test.txt', b'Invalid contract content', 'text/plain')}
            response = await client.post(
                "/documents/upload",
                files=files,
                headers={'Authorization': 'Bearer test-token'}
            )
            
            # Should reject invalid file type
            assert response.status_code == 422
            error = response.json()
            assert 'file type' in error['detail'].lower()

    @pytest.mark.asyncio
    async def test_corrupted_document_handling(self, auth_context):
        """Test workflow with corrupted PDF files."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'Corrupted PDF content that is not valid')
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                with open(tmp.name, 'rb') as f:
                    files = {'file': ('corrupted.pdf', f, 'application/pdf')}
                    response = await client.post(
                        "/documents/upload",
                        files=files,
                        headers={'Authorization': 'Bearer test-token'}
                    )
                
                # Should handle gracefully
                assert response.status_code in [422, 400]

    @pytest.mark.asyncio
    async def test_network_interruption_resilience(self, auth_context, sample_document):
        """Test workflow resilience to network interruptions."""
        with patch('app.services.contract_analysis_service.ContractAnalysisService') as mock_service:
            # Configure service to fail initially then succeed
            service_instance = AsyncMock()
            mock_service.return_value = service_instance
            
            call_count = 0
            async def flaky_analysis(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("Network timeout")
                return {'success': True, 'session_id': 'resilient-session'}
            
            service_instance.analyze_contract.side_effect = flaky_analysis
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                upload_response = await self._upload_document(client, sample_document)
                document_id = upload_response.json()['document_id']
                
                # Analysis should eventually succeed with retry logic
                analysis_response = await client.post(
                    "/contracts/analyze",
                    json={
                        'document_id': document_id,
                        'contract_type': 'purchase_agreement',
                        'australian_state': 'NSW'
                    },
                    headers={'Authorization': 'Bearer test-token'}
                )
                
                # Should succeed after retries
                assert analysis_response.status_code == 200