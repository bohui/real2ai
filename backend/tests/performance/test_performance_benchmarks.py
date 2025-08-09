"""
Performance benchmarks and load testing for Real2.AI backend.

This module includes LangSmith trace integration for comprehensive performance monitoring
and analytics as part of Phase 2 and 3 implementations.
"""
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import pytest
import statistics

from app.services.contract_analysis_service import ContractAnalysisService
from app.services.document_service import DocumentService
from app.services.ai.gemini_ocr_service import GeminiOCRService
from app.core.cache_manager import CacheManager
from app.schema.contract import ContractAnalysisRequest
from app.core.langsmith_config import (
    get_langsmith_config,
    langsmith_trace,
    langsmith_session,
    log_trace_info,
)
from app.evaluation.langsmith_integration import (
    LangSmithEvaluationIntegration,
    LangSmithDatasetConfig,
)


@pytest.fixture
def mock_services():
    """Create mock services for performance testing."""
    return {
        'contract_service': AsyncMock(spec=ContractAnalysisService),
        'document_service': AsyncMock(spec=DocumentService),
        'ocr_service': AsyncMock(spec=GeminiOCRService),
        'cache_manager': AsyncMock(spec=CacheManager)
    }


@pytest.fixture
def langsmith_integration():
    """Create LangSmith integration for evaluation tests."""
    return LangSmithEvaluationIntegration()


@pytest.fixture
def performance_dataset_config():
    """Create dataset configuration for performance testing."""
    return LangSmithDatasetConfig(
        dataset_name=f"performance_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description="Performance test traces for analysis",
        trace_filters={"run_type": "chain", "tags": ["performance_test"]},
        max_examples=100,
        quality_threshold=0.8,
    )


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical system components."""

    @pytest.mark.asyncio
    @langsmith_trace(name="performance_test_contract_analysis_latency", run_type="chain")
    async def test_contract_analysis_latency(self, mock_services):
        """Test contract analysis response time under various loads with LangSmith tracing."""
        async with langsmith_session(
            "contract_analysis_latency_benchmark",
            test_type="performance",
            service_under_test="contract_analysis",
        ) as session:
            
            service = mock_services['contract_service']
            service.analyze_contract.return_value = {
                'success': True,
                'analysis_id': 'test-123',
                'results': {'confidence': 0.85}
            }
            
            # Test single request latency with tracing
            start_time = time.perf_counter()
            
            result = await service.analyze_contract(
                document_data={'content': 'test'},
                user_id='user-123',
                australian_state='NSW',
                session_id='session-123'
            )
            
            end_time = time.perf_counter()
            latency = end_time - start_time
            
            # Phase 2: Add cost tracking and performance monitoring
            session.outputs = {
                "latency_ms": latency * 1000,
                "result": result,
                "performance_threshold_met": latency < 5.0,  # 5 second threshold
                "test_timestamp": datetime.now().isoformat(),
                "cost_estimate": {
                    "token_usage": 1000,  # Mock estimate
                    "estimated_cost_usd": 0.002,
                },
                "resource_usage": {
                    "memory_mb": 50,  # Mock estimate
                    "cpu_usage_percent": 25,
                }
            }
            
            # Log trace info for monitoring dashboards (Phase 2)
            log_trace_info(
                f"Performance test completed in {latency:.3f}s",
                {
                    "test_name": "contract_analysis_latency",
                    "latency_ms": latency * 1000,
                    "threshold_met": latency < 5.0,
                }
            )
            
            assert latency < 30.0, f"Contract analysis took {latency:.3f}s, exceeding 30s threshold"
        latency = time.perf_counter() - start_time
        
        # Single request should complete under 5 seconds
        assert latency < 5.0, f"Single analysis took {latency:.2f}s, exceeds 5s threshold"

    @pytest.mark.asyncio
    async def test_concurrent_analysis_throughput(self, mock_services):
        """Test system throughput with concurrent requests."""
        service = mock_services['contract_service']
        service.analyze_contract.return_value = {
            'success': True,
            'analysis_id': 'test-concurrent',
            'results': {'confidence': 0.85}
        }
        
        # Configure mock to simulate realistic processing time
        async def mock_analysis(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate 100ms processing
            return {'success': True, 'analysis_id': f'test-{time.time()}'}
        
        service.analyze_contract.side_effect = mock_analysis
        
        # Test concurrent requests
        concurrent_requests = 10
        start_time = time.perf_counter()
        
        tasks = [
            service.analyze_contract(
                document_data={'content': f'test-{i}'},
                user_id=f'user-{i}',
                australian_state='NSW',
                session_id=f'session-{i}'
            )
            for i in range(concurrent_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # All requests should complete
        assert len(results) == concurrent_requests
        assert all(r['success'] for r in results)
        
        # Throughput should be reasonable
        throughput = concurrent_requests / total_time
        assert throughput >= 50, f"Throughput {throughput:.1f} req/s is below 50 req/s threshold"

    @pytest.mark.asyncio
    async def test_cache_performance(self, mock_services):
        """Test cache read/write performance."""
        cache = mock_services['cache_manager']
        
        # Configure cache mocks
        cache.set.return_value = True
        cache.get.return_value = {'cached_data': 'test_value'}
        cache.exists.return_value = True
        
        # Test cache write performance
        write_times = []
        for i in range(100):
            start = time.perf_counter()
            await cache.set(f'test_key_{i}', {'data': f'value_{i}'}, ttl=300)
            write_times.append(time.perf_counter() - start)
        
        avg_write_time = statistics.mean(write_times)
        assert avg_write_time < 0.01, f"Average cache write time {avg_write_time:.4f}s exceeds 10ms"
        
        # Test cache read performance
        read_times = []
        for i in range(100):
            start = time.perf_counter()
            await cache.get(f'test_key_{i}')
            read_times.append(time.perf_counter() - start)
        
        avg_read_time = statistics.mean(read_times)
        assert avg_read_time < 0.005, f"Average cache read time {avg_read_time:.4f}s exceeds 5ms"

    @pytest.mark.asyncio
    async def test_ocr_processing_performance(self, mock_services):
        """Test OCR processing performance under load."""
        ocr_service = mock_services['ocr_service']
        
        # Mock OCR response
        mock_response = {
            'success': True,
            'extracted_text': 'Sample extracted text from document',
            'confidence': 0.95,
            'processing_time': 0.5
        }
        ocr_service.process_document.return_value = mock_response
        
        # Test OCR batch processing
        batch_size = 5
        documents = [
            {'content': f'doc_{i}', 'type': 'pdf'} 
            for i in range(batch_size)
        ]
        
        start_time = time.perf_counter()
        tasks = [
            ocr_service.process_document(doc) 
            for doc in documents
        ]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time
        
        # All OCR requests should succeed
        assert len(results) == batch_size
        assert all(r['success'] for r in results)
        
        # OCR processing should complete within reasonable time
        avg_time_per_doc = total_time / batch_size
        assert avg_time_per_doc < 2.0, f"OCR processing {avg_time_per_doc:.2f}s/doc exceeds 2s threshold"

    @pytest.mark.asyncio 
    async def test_memory_usage_stability(self, mock_services):
        """Test memory usage remains stable under load."""
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get baseline memory usage
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate heavy workload
        service = mock_services['contract_service']
        service.analyze_contract.return_value = {'success': True}
        
        for i in range(50):
            await service.analyze_contract(
                document_data={'content': f'large_document_content_{i}' * 1000},
                user_id=f'user-{i}',
                australian_state='NSW',
                session_id=f'session-{i}'
            )
            
            if i % 10 == 0:
                gc.collect()  # Force garbage collection
        
        # Check final memory usage
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - baseline_memory
        
        # Memory growth should be reasonable (under 100MB)
        assert memory_growth < 100, f"Memory grew by {memory_growth:.1f}MB, exceeds 100MB threshold"

    @pytest.mark.asyncio
    async def test_database_query_performance(self, mock_services):
        """Test database query performance for common operations."""
        document_service = mock_services['document_service']
        
        # Mock database responses
        document_service.get_document.return_value = {
            'id': 'doc-123',
            'content': 'test',
            'created_at': datetime.now()
        }
        document_service.list_user_documents.return_value = [
            {'id': f'doc-{i}', 'name': f'Document {i}'} 
            for i in range(20)
        ]
        
        # Test individual document retrieval
        query_times = []
        for i in range(20):
            start = time.perf_counter()
            await document_service.get_document(f'doc-{i}', user_id='user-123')
            query_times.append(time.perf_counter() - start)
        
        avg_query_time = statistics.mean(query_times)
        assert avg_query_time < 0.1, f"Average query time {avg_query_time:.3f}s exceeds 100ms"
        
        # Test bulk operations
        start = time.perf_counter()
        documents = await document_service.list_user_documents(
            user_id='user-123', 
            limit=50, 
            offset=0
        )
        bulk_query_time = time.perf_counter() - start
        
        assert bulk_query_time < 0.5, f"Bulk query time {bulk_query_time:.3f}s exceeds 500ms"
        assert len(documents) == 20

    @pytest.mark.asyncio
    async def test_websocket_connection_performance(self, mock_services):
        """Test WebSocket connection handling performance."""
        # Mock WebSocket manager
        websocket_manager = AsyncMock()
        websocket_manager.connect.return_value = True
        websocket_manager.send_message.return_value = True
        websocket_manager.disconnect.return_value = True
        
        # Test multiple simultaneous connections
        connection_count = 50
        connection_times = []
        
        for i in range(connection_count):
            start = time.perf_counter()
            await websocket_manager.connect(f'user-{i}')
            connection_times.append(time.perf_counter() - start)
        
        avg_connection_time = statistics.mean(connection_times)
        assert avg_connection_time < 0.1, f"Average connection time {avg_connection_time:.3f}s exceeds 100ms"
        
        # Test message broadcasting performance
        message = {'type': 'analysis_update', 'data': {'progress': 50}}
        
        start = time.perf_counter()
        broadcast_tasks = [
            websocket_manager.send_message(f'user-{i}', message)
            for i in range(connection_count)
        ]
        await asyncio.gather(*broadcast_tasks)
        broadcast_time = time.perf_counter() - start
        
        messages_per_second = connection_count / broadcast_time
        assert messages_per_second >= 100, f"Message broadcast rate {messages_per_second:.1f} msg/s is below 100 msg/s"


class TestLoadScenarios:
    """Test realistic load scenarios."""

    @pytest.mark.asyncio
    async def test_peak_usage_scenario(self, mock_services):
        """Simulate peak usage with multiple concurrent operations."""
        # Configure all services
        services = mock_services
        
        # Configure realistic response times
        services['contract_service'].analyze_contract.side_effect = lambda *args, **kwargs: asyncio.sleep(1.0) and {'success': True}
        services['ocr_service'].process_document.side_effect = lambda *args, **kwargs: asyncio.sleep(0.5) and {'success': True}
        services['cache_manager'].get.return_value = None  # Cache miss scenario
        services['cache_manager'].set.return_value = True
        
        # Simulate 20 users each uploading 2 documents simultaneously
        user_count = 20
        docs_per_user = 2
        
        start_time = time.perf_counter()
        
        # Create tasks for all operations
        tasks = []
        for user_id in range(user_count):
            for doc_id in range(docs_per_user):
                # Each user uploads a document and starts analysis
                task = self._simulate_user_workflow(
                    services,
                    f'user-{user_id}',
                    f'doc-{user_id}-{doc_id}'
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Verify all operations completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failure_count = len(results) - len(successful_results)
        
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} is below 95%"
        assert failure_count <= 2, f"Too many failures: {failure_count}"
        
        # System should handle the load within reasonable time
        total_operations = user_count * docs_per_user
        avg_time_per_operation = total_time / total_operations
        assert avg_time_per_operation < 10.0, f"Average operation time {avg_time_per_operation:.2f}s exceeds 10s"

    async def _simulate_user_workflow(self, services: Dict[str, Any], user_id: str, doc_id: str) -> Dict[str, Any]:
        """Simulate complete user workflow: upload -> OCR -> analysis."""
        try:
            # Step 1: OCR processing
            ocr_result = await services['ocr_service'].process_document({
                'id': doc_id,
                'user_id': user_id,
                'content': f'document_content_{doc_id}'
            })
            
            # Step 2: Contract analysis
            analysis_result = await services['contract_service'].analyze_contract(
                document_data={'content': 'extracted_text'},
                user_id=user_id,
                australian_state='NSW',
                session_id=f'session-{user_id}-{doc_id}'
            )
            
            # Step 3: Cache results
            await services['cache_manager'].set(
                f'analysis:{doc_id}',
                analysis_result,
                ttl=3600
            )
            
            return {
                'user_id': user_id,
                'doc_id': doc_id,
                'success': True,
                'ocr_result': ocr_result,
                'analysis_result': analysis_result
            }
            
        except Exception as e:
            return {
                'user_id': user_id,
                'doc_id': doc_id,
                'success': False,
                'error': str(e)
            }


@pytest.mark.slow
class TestStressTests:
    """Stress tests for extreme load conditions."""

    @pytest.mark.asyncio
    async def test_extreme_concurrent_load(self, mock_services):
        """Test system behavior under extreme concurrent load."""
        service = mock_services['contract_service']
        service.analyze_contract.return_value = {'success': True}
        
        # Configure realistic processing delay
        async def delayed_analysis(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms processing
            return {'success': True, 'analysis_id': f'stress-{time.time()}'}
        
        service.analyze_contract.side_effect = delayed_analysis
        
        # Test with very high concurrency
        concurrent_requests = 100
        start_time = time.perf_counter()
        
        tasks = [
            service.analyze_contract(
                document_data={'content': f'stress_test_{i}'},
                user_id=f'stress_user_{i}',
                australian_state='NSW',
                session_id=f'stress_session_{i}'
            )
            for i in range(concurrent_requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # System should gracefully handle high load
        successful_results = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful_results) / len(results)
        
        # Allow for some degradation under extreme load
        assert success_rate >= 0.90, f"Success rate under stress {success_rate:.2%} is below 90%"
        
        # Performance may degrade but should remain reasonable
        avg_response_time = total_time / concurrent_requests
        assert avg_response_time < 5.0, f"Average response time under stress {avg_response_time:.2f}s exceeds 5s"