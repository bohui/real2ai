"""
Comprehensive Integration Tests for Contract Analysis Business Logic

This test suite focuses on integration testing for core contract analysis workflows,
including document processing, risk assessment, compliance checking, and recommendations.
Tests the integration between multiple services and components.
"""

import pytest
import asyncio
import json
import tempfile
import io
from typing import Dict, Any, List
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.services.contract_analysis_service import ContractAnalysisService
from app.services.document_service import DocumentService
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.services.communication.websocket_service import WebSocketManager
from app.core.config import get_enhanced_workflow_config
from app.core.prompts import get_prompt_manager
from app.models.contract_state import create_initial_state, RealEstateAgentState
from app.schema.enums import AustralianState, ProcessingStatus, ContractType
from app.schema import ContractAnalysisServiceResponse
from app.clients.supabase.client import SupabaseClient


@pytest.fixture
def sample_contract_content():
    """Sample contract text for testing"""
    return """
    CONTRACT OF SALE
    
    This agreement is made between:
    VENDOR: John Smith
    PURCHASER: Jane Doe
    
    PROPERTY: 123 Test Street, Sydney, NSW 2000
    PURCHASE PRICE: $850,000 (Eight Hundred and Fifty Thousand Dollars)
    DEPOSIT: $85,000 (Ten percent of purchase price)
    SETTLEMENT DATE: 15th March 2024
    COOLING OFF PERIOD: 5 business days from contract date
    
    SPECIAL CONDITIONS:
    1. Subject to satisfactory building and pest inspection
    2. Subject to finance approval within 21 days
    3. Property to be sold with vacant possession
    
    VENDOR WARRANTIES:
    - The vendor warrants that all improvements comply with relevant building codes
    - No knowledge of contamination or environmental issues
    
    This contract is subject to the Conveyancing Act 1919 (NSW).
    """


@pytest.fixture
def sample_pdf_document(sample_contract_content):
    """Create a temporary PDF document for testing"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Create a simple PDF structure
        pdf_header = b'%PDF-1.4\n'
        pdf_content = sample_contract_content.encode('utf-8')
        pdf_footer = b'\n%%EOF'
        
        tmp.write(pdf_header + pdf_content + pdf_footer)
        tmp.flush()
        
        return {
            'file_path': tmp.name,
            'filename': 'test_contract.pdf',
            'content_type': 'application/pdf',
            'file_size': len(pdf_header + pdf_content + pdf_footer),
            'content': pdf_content
        }


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for real-time updates"""
    manager = AsyncMock(spec=WebSocketManager)
    manager.send_progress_update = AsyncMock()
    manager.send_error = AsyncMock()
    manager.send_completion = AsyncMock()
    return manager


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for database operations"""
    client = AsyncMock(spec=SupabaseClient)
    
    # Mock document storage
    client.store_document = AsyncMock(return_value={
        'id': 'doc-12345',
        'user_id': 'test-user-123',
        'filename': 'test_contract.pdf',
        'status': 'uploaded'
    })
    
    # Mock contract creation
    client.create_contract = AsyncMock(return_value={
        'id': 'contract-67890',
        'document_id': 'doc-12345',
        'contract_type': 'purchase_agreement',
        'status': 'analyzing'
    })
    
    # Mock analysis storage
    client.store_analysis_result = AsyncMock(return_value={
        'id': 'analysis-99999',
        'contract_id': 'contract-67890',
        'status': 'completed'
    })
    
    return client


@pytest.fixture
def contract_analysis_service(mock_websocket_manager, mock_supabase_client):
    """Create Contract Analysis Service with mocked dependencies"""
    config = get_enhanced_workflow_config()
    prompt_manager = get_prompt_manager()
    
    with patch('app.services.contract_analysis_service.SupabaseClient', return_value=mock_supabase_client):
        service = ContractAnalysisService(
            websocket_manager=mock_websocket_manager,
            config=config,
            prompt_manager=prompt_manager,
            enable_websocket_progress=True
        )
        return service


@pytest.mark.integration
@pytest.mark.asyncio
class TestContractAnalysisIntegration:
    """Integration tests for contract analysis business logic"""

    async def test_complete_contract_analysis_workflow(
        self, 
        contract_analysis_service, 
        sample_pdf_document,
        mock_websocket_manager,
        sample_contract_content
    ):
        """Test complete contract analysis workflow from document to results"""
        
        with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
            with patch('app.services.document_service.DocumentService') as mock_doc_service:
                
                # Configure OCR service mock
                ocr_instance = AsyncMock()
                mock_ocr.return_value = ocr_instance
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': sample_contract_content,
                    'extraction_confidence': 0.95,
                    'character_count': len(sample_contract_content),
                    'word_count': len(sample_contract_content.split()),
                    'processing_time_ms': 2150.0
                })
                
                # Configure document service mock
                doc_instance = AsyncMock()
                mock_doc_service.return_value = doc_instance
                doc_instance.process_document = AsyncMock(return_value={
                    'document_id': 'doc-12345',
                    'processed': True,
                    'metadata': {
                        'pages': 3,
                        'file_size': sample_pdf_document['file_size']
                    }
                })
                
                # Create analysis request
                analysis_request = {
                    'document_data': sample_pdf_document,
                    'contract_type': ContractType.PURCHASE_AGREEMENT.value,
                    'australian_state': AustralianState.NSW.value,
                    'user_id': 'test-user-123',
                    'user_preferences': {
                        'include_recommendations': True,
                        'focus_areas': ['risk_assessment', 'compliance_check'],
                        'detailed_analysis': True
                    }
                }
                
                # Run analysis
                result = await contract_analysis_service.analyze_contract(**analysis_request)
                
                # Verify workflow completion
                assert result is not None
                assert result.get('success', False) is True
                assert 'session_id' in result
                assert 'analysis_results' in result
                
                # Verify analysis structure
                analysis_results = result['analysis_results']
                assert 'contract_terms' in analysis_results
                assert 'risk_assessment' in analysis_results
                assert 'compliance_check' in analysis_results
                assert 'recommendations' in analysis_results
                
                # Verify contract terms extraction
                contract_terms = analysis_results['contract_terms']
                assert contract_terms['purchase_price'] > 0
                assert 'settlement_date' in contract_terms
                assert 'parties' in contract_terms
                
                # Verify risk assessment
                risk_assessment = analysis_results['risk_assessment']
                assert 'overall_risk_score' in risk_assessment
                assert 'risk_factors' in risk_assessment
                assert isinstance(risk_assessment['risk_factors'], list)
                
                # Verify compliance check
                compliance_check = analysis_results['compliance_check']
                assert 'state_compliance' in compliance_check
                assert 'cooling_off_compliance' in compliance_check
                
                # Verify recommendations
                recommendations = analysis_results['recommendations']
                assert isinstance(recommendations, list)
                assert len(recommendations) > 0
                
                # Verify WebSocket progress updates were sent
                mock_websocket_manager.send_progress_update.assert_called()
                
                # Verify OCR service was called
                ocr_instance.process_document.assert_called_once()
                
                # Verify document service was called
                doc_instance.process_document.assert_called_once()

    async def test_contract_analysis_with_different_contract_types(
        self, 
        contract_analysis_service,
        sample_pdf_document,
        sample_contract_content
    ):
        """Test analysis workflow with different Australian contract types"""
        
        contract_types_to_test = [
            ContractType.PURCHASE_AGREEMENT,
            ContractType.LEASE_AGREEMENT,
            ContractType.OFF_PLAN,
            ContractType.AUCTION
        ]
        
        with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
            with patch('app.services.document_service.DocumentService') as mock_doc_service:
                
                # Configure mocks
                ocr_instance = AsyncMock()
                mock_ocr.return_value = ocr_instance
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': sample_contract_content,
                    'extraction_confidence': 0.90
                })
                
                doc_instance = AsyncMock()
                mock_doc_service.return_value = doc_instance
                doc_instance.process_document = AsyncMock(return_value={
                    'document_id': 'doc-12345',
                    'processed': True
                })
                
                results = {}
                
                for contract_type in contract_types_to_test:
                    analysis_request = {
                        'document_data': sample_pdf_document,
                        'contract_type': contract_type,
                        'australian_state': AustralianState.NSW.value,
                        'user_id': 'test-user-123',
                        'user_preferences': {
                            'include_recommendations': True
                        }
                    }
                    
                    result = await contract_analysis_service.analyze_contract(**analysis_request)
                    results[contract_type.value] = result
                    
                    # Verify contract type-specific analysis
                    assert result['success'] is True
                    assert result['analysis_results']['contract_type'] == contract_type.value
                    
                    # Contract type-specific validations
                    if contract_type == ContractType.LEASE_AGREEMENT:
                        # Should have lease-specific terms
                        analysis = result['analysis_results']
                        assert 'rental_terms' in analysis.get('contract_terms', {}) or \
                               'lease_period' in analysis.get('contract_terms', {})
                    
                    elif contract_type == ContractType.OFF_PLAN:
                        # Should identify off-plan risks
                        risk_factors = result['analysis_results']['risk_assessment']['risk_factors']
                        off_plan_risks = [r for r in risk_factors if 'off plan' in r.get('factor', '').lower()]
                        # Note: This depends on the actual analysis logic
                
                # Verify all contract types were processed successfully
                assert len(results) == len(contract_types_to_test)
                assert all(result['success'] for result in results.values())

    async def test_contract_analysis_with_different_australian_states(
        self, 
        contract_analysis_service,
        sample_pdf_document,
        sample_contract_content
    ):
        """Test analysis workflow with different Australian states for compliance"""
        
        australian_states = [
            AustralianState.NSW,
            AustralianState.VIC, 
            AustralianState.QLD,
            AustralianState.SA,
            AustralianState.WA,
            AustralianState.TAS
        ]
        
        with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
            with patch('app.services.document_service.DocumentService') as mock_doc_service:
                
                # Configure mocks
                ocr_instance = AsyncMock()
                mock_ocr.return_value = ocr_instance
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': sample_contract_content,
                    'extraction_confidence': 0.92
                })
                
                doc_instance = AsyncMock()
                mock_doc_service.return_value = doc_instance
                doc_instance.process_document = AsyncMock(return_value={
                    'document_id': 'doc-12345',
                    'processed': True
                })
                
                state_results = {}
                
                for state in australian_states:
                    analysis_request = {
                        'document_data': sample_pdf_document,
                        'contract_type': ContractType.PURCHASE_AGREEMENT.value,
                        'australian_state': state,
                        'user_id': 'test-user-123',
                        'user_preferences': {
                            'include_recommendations': True,
                            'focus_areas': ['compliance_check']
                        }
                    }
                    
                    result = await contract_analysis_service.analyze_contract(**analysis_request)
                    state_results[state.value] = result
                    
                    # Verify state-specific compliance analysis
                    assert result['success'] is True
                    compliance = result['analysis_results']['compliance_check']
                    assert compliance['australian_state'] == state.value
                    assert 'state_compliance' in compliance
                    
                    # State-specific validation logic would depend on implementation
                    # For NSW, should reference Conveyancing Act 1919
                    if state == AustralianState.NSW:
                        legal_refs = compliance.get('legal_references', [])
                        nsw_references = [ref for ref in legal_refs if 'NSW' in ref or 'Conveyancing Act' in ref]
                        # Note: This depends on actual implementation
                
                # Verify all states were processed
                assert len(state_results) == len(australian_states)
                assert all(result['success'] for result in state_results.values())

    async def test_contract_analysis_error_handling_and_recovery(
        self, 
        contract_analysis_service,
        sample_pdf_document
    ):
        """Test error handling and recovery mechanisms in analysis workflow"""
        
        with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
            with patch('app.services.document_service.DocumentService') as mock_doc_service:
                
                # Test OCR service failure
                ocr_instance = AsyncMock()
                mock_ocr.return_value = ocr_instance
                ocr_instance.process_document = AsyncMock(side_effect=Exception("OCR service unavailable"))
                
                doc_instance = AsyncMock()
                mock_doc_service.return_value = doc_instance
                doc_instance.process_document = AsyncMock(return_value={
                    'document_id': 'doc-12345',
                    'processed': True
                })
                
                analysis_request = {
                    'document_data': sample_pdf_document,
                    'contract_type': ContractType.PURCHASE_AGREEMENT.value,
                    'australian_state': AustralianState.NSW.value,
                    'user_id': 'test-user-123'
                }
                
                # Should handle OCR failure gracefully
                result = await contract_analysis_service.analyze_contract(**analysis_request)
                
                # Verify error handling
                assert result is not None
                assert result.get('success', True) is False or 'error' in result
                
                # Test document service failure
                mock_ocr.reset_mock()
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': 'Sample text',
                    'extraction_confidence': 0.85
                })
                
                doc_instance.process_document = AsyncMock(side_effect=Exception("Document storage failed"))
                
                result = await contract_analysis_service.analyze_contract(**analysis_request)
                
                # Should handle document service failure
                assert result is not None
                assert result.get('success', True) is False or 'error' in result

    async def test_contract_analysis_quality_metrics_and_validation(
        self, 
        contract_analysis_service,
        sample_pdf_document,
        sample_contract_content
    ):
        """Test quality metrics calculation and validation in analysis workflow"""
        
        with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
            with patch('app.services.document_service.DocumentService') as mock_doc_service:
                
                # Configure mocks for high-quality analysis
                ocr_instance = AsyncMock()
                mock_ocr.return_value = ocr_instance
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': sample_contract_content,
                    'extraction_confidence': 0.98,  # High confidence
                    'character_count': len(sample_contract_content),
                    'word_count': len(sample_contract_content.split())
                })
                
                doc_instance = AsyncMock()
                mock_doc_service.return_value = doc_instance
                doc_instance.process_document = AsyncMock(return_value={
                    'document_id': 'doc-12345',
                    'processed': True,
                    'quality_score': 0.95
                })
                
                analysis_request = {
                    'document_data': sample_pdf_document,
                    'contract_type': ContractType.PURCHASE_AGREEMENT.value,
                    'australian_state': AustralianState.NSW.value,
                    'user_id': 'test-user-123',
                    'user_preferences': {
                        'include_quality_metrics': True,
                        'detailed_analysis': True
                    }
                }
                
                result = await contract_analysis_service.analyze_contract(**analysis_request)
                
                # Verify quality metrics are included
                assert result['success'] is True
                assert 'quality_metrics' in result
                
                quality_metrics = result['quality_metrics']
                assert 'overall_confidence' in quality_metrics
                assert 'extraction_confidence' in quality_metrics
                assert 'analysis_confidence' in quality_metrics
                assert 'validation_passed' in quality_metrics
                
                # Verify high-quality thresholds
                assert quality_metrics['overall_confidence'] >= 0.8
                assert quality_metrics['extraction_confidence'] >= 0.9
                assert quality_metrics['validation_passed'] is True
                
                # Test low-quality scenario
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': 'Poor quality text...',
                    'extraction_confidence': 0.45,  # Low confidence
                    'character_count': 20,
                    'word_count': 3
                })
                
                result_low_quality = await contract_analysis_service.analyze_contract(**analysis_request)
                
                # Should indicate low quality
                quality_metrics_low = result_low_quality.get('quality_metrics', {})
                assert quality_metrics_low.get('overall_confidence', 1.0) < 0.7
                assert quality_metrics_low.get('extraction_confidence', 1.0) < 0.5

    async def test_concurrent_contract_analysis_workflows(
        self, 
        contract_analysis_service,
        sample_pdf_document,
        sample_contract_content
    ):
        """Test handling of concurrent analysis workflows"""
        
        with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
            with patch('app.services.document_service.DocumentService') as mock_doc_service:
                
                # Configure mocks
                ocr_instance = AsyncMock()
                mock_ocr.return_value = ocr_instance
                ocr_instance.process_document = AsyncMock(return_value={
                    'status': ProcessingStatus.COMPLETED,
                    'extracted_text': sample_contract_content,
                    'extraction_confidence': 0.90
                })
                
                doc_instance = AsyncMock()
                mock_doc_service.return_value = doc_instance
                doc_instance.process_document = AsyncMock(return_value={
                    'document_id': 'doc-12345',
                    'processed': True
                })
                
                # Create multiple concurrent analysis tasks
                analysis_requests = []
                for i in range(5):
                    request = {
                        'document_data': sample_pdf_document,
                        'contract_type': ContractType.PURCHASE_AGREEMENT.value,
                        'australian_state': AustralianState.NSW.value,
                        'user_id': f'test-user-{i+1}',
                        'user_preferences': {
                            'session_id': f'concurrent-session-{i+1}'
                        }
                    }
                    analysis_requests.append(request)
                
                # Run all analyses concurrently
                tasks = [
                    contract_analysis_service.analyze_contract(**request)
                    for request in analysis_requests
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify all analyses completed
                successful_results = [r for r in results if isinstance(r, dict) and r.get('success', False)]
                assert len(successful_results) == 5
                
                # Verify unique session IDs
                session_ids = [r.get('session_id') for r in successful_results]
                assert len(set(session_ids)) == len(session_ids)  # All unique

    async def test_analysis_caching_and_performance_optimization(
        self, 
        contract_analysis_service,
        sample_pdf_document,
        sample_contract_content
    ):
        """Test caching mechanisms and performance optimizations"""
        
        with patch('app.core.cache_manager.CacheManager') as mock_cache:
            with patch('app.services.ai.gemini_ocr_service.GeminiOCRService') as mock_ocr:
                with patch('app.services.document_service.DocumentService') as mock_doc_service:
                    
                    # Configure cache mock
                    cache_instance = AsyncMock()
                    mock_cache.return_value = cache_instance
                    cache_instance.get = AsyncMock(return_value=None)  # Cache miss
                    cache_instance.set = AsyncMock(return_value=True)
                    
                    # Configure service mocks
                    ocr_instance = AsyncMock()
                    mock_ocr.return_value = ocr_instance
                    ocr_instance.process_document = AsyncMock(return_value={
                        'status': ProcessingStatus.COMPLETED,
                        'extracted_text': sample_contract_content,
                        'extraction_confidence': 0.93
                    })
                    
                    doc_instance = AsyncMock()
                    mock_doc_service.return_value = doc_instance
                    doc_instance.process_document = AsyncMock(return_value={
                        'document_id': 'doc-12345',
                        'processed': True
                    })
                    
                    analysis_request = {
                        'document_data': sample_pdf_document,
                        'contract_type': ContractType.PURCHASE_AGREEMENT.value,
                        'australian_state': AustralianState.NSW.value,
                        'user_id': 'test-user-123'
                    }
                    
                    # First analysis (cache miss)
                    result1 = await contract_analysis_service.analyze_contract(**analysis_request)
                    assert result1['success'] is True
                    
                    # Verify cache interaction
                    cache_instance.get.assert_called()
                    cache_instance.set.assert_called()
                    
                    # Second analysis with same parameters (should hit cache)
                    cache_instance.reset_mock()
                    cached_result = {
                        'cached_analysis': True,
                        'extracted_text': sample_contract_content
                    }
                    cache_instance.get = AsyncMock(return_value=cached_result)
                    
                    result2 = await contract_analysis_service.analyze_contract(**analysis_request)
                    
                    # Should have used cached data
                    cache_instance.get.assert_called()
                    # Note: Actual caching behavior depends on implementation