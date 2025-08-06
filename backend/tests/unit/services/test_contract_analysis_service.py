"""
Comprehensive unit tests for ContractAnalysisService
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, UTC
from typing import Dict, Any

from app.services.contract_analysis_service import (
    ContractAnalysisService,
    create_contract_analysis_service,
)
from app.services.interfaces import IContractAnalyzer
from app.schema.enums import AustralianState, ProcessingStatus
from app.models.contract_state import RealEstateAgentState
from app.config.enhanced_workflow_config import EnhancedWorkflowConfig
from app.clients.base.exceptions import ClientError


class TestContractAnalysisServiceInitialization:
    """Test ContractAnalysisService initialization and configuration."""
    
    def test_service_creation_basic(self):
        """Test ContractAnalysisService can be created with basic configuration."""
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            service = ContractAnalysisService()
            
            assert service is not None
            assert service.websocket_manager is None
            assert service.enable_websocket_progress is False
            assert service.workflow is not None
            assert service._service_metrics is not None
    
    def test_service_creation_with_websocket(self, mock_websocket_manager):
        """Test service creation with WebSocket manager."""
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            service = ContractAnalysisService(
                websocket_manager=mock_websocket_manager,
                enable_websocket_progress=True
            )
            
            assert service.websocket_manager == mock_websocket_manager
            assert service.enable_websocket_progress is True
    
    def test_service_creation_with_custom_config(self):
        """Test service creation with custom configuration."""
        custom_config = self._create_mock_config(
            enable_validation=False,
            enable_quality_checks=False
        )
        
        with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "issues": [],
                "warnings": [],
                "config_summary": "custom config"
            }
            
            service = ContractAnalysisService(
                config=custom_config,
                openai_api_key="test-key",
                model_name="gpt-3.5-turbo"
            )
            
            assert service.config == custom_config
            assert service.openai_api_key == "test-key"
            assert service.model_name == "gpt-3.5-turbo"
    
    def test_service_creation_invalid_config(self):
        """Test service creation fails with invalid configuration."""
        invalid_config = self._create_mock_config()
        
        with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "issues": ["Invalid configuration parameter"],
                "warnings": [],
                "config_summary": "invalid"
            }
            
            with pytest.raises(ValueError) as exc_info:
                ContractAnalysisService(config=invalid_config)
            
            assert "Invalid configuration" in str(exc_info.value)
    
    def test_factory_function(self, mock_websocket_manager):
        """Test service factory function."""
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            service = create_contract_analysis_service(
                websocket_manager=mock_websocket_manager,
                openai_api_key="factory-test-key",
                enable_websocket_progress=True
            )
            
            assert isinstance(service, ContractAnalysisService)
            assert service.websocket_manager == mock_websocket_manager
            assert service.openai_api_key == "factory-test-key"
    
    def _create_mock_config(self, **kwargs):
        """Create mock configuration for testing."""
        defaults = {
            'enable_validation': True,
            'enable_quality_checks': True,
            'enable_prompt_manager': False,
            'enable_structured_parsing': True,
            'enable_enhanced_error_handling': True,
            'enable_fallback_mechanisms': True,
        }
        defaults.update(kwargs)
        
        mock_config = Mock(spec=EnhancedWorkflowConfig)
        for key, value in defaults.items():
            setattr(mock_config, key, value)
        
        mock_config.to_prompt_manager_config.return_value = {}
        mock_config.validate_config.return_value = {"status": "valid"}
        
        return mock_config


class TestContractAnalysisServiceAnalysis:
    """Test contract analysis functionality."""
    
    @pytest.fixture
    def service(self, mock_websocket_manager):
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "test config"
                }
                
                service = ContractAnalysisService(
                    websocket_manager=mock_websocket_manager,
                    enable_websocket_progress=True
                )
                
                # Mock workflow
                service.workflow = AsyncMock()
                
                return service
    
    def _create_mock_config(self, **kwargs):
        """Create mock configuration for testing."""
        defaults = {
            'enable_validation': True,
            'enable_quality_checks': True,
            'enable_prompt_manager': False,
            'enable_structured_parsing': True,
            'enable_enhanced_error_handling': True,
            'enable_fallback_mechanisms': True,
        }
        defaults.update(kwargs)
        
        mock_config = Mock(spec=EnhancedWorkflowConfig)
        for key, value in defaults.items():
            setattr(mock_config, key, value)
        
        mock_config.to_prompt_manager_config.return_value = {}
        mock_config.validate_config.return_value = {"status": "valid"}
        
        return mock_config
    
    @pytest.mark.asyncio
    async def test_analyze_contract_success(self, service, mock_websocket_manager):
        """Test successful contract analysis."""
        # Setup mock workflow response
        mock_final_state = {
            "session_id": "test-session-123",
            "parsing_status": ProcessingStatus.COMPLETED,
            "analysis_results": {
                "overall_confidence": 0.85,
                "risk_assessment": {
                    "overall_risk_score": 3
                },
                "compliance_check": {
                    "state_compliance": True
                },
                "recommendations": [
                    "Review clause 5.1 for clarity",
                    "Consider legal advice for clause 7.3"
                ]
            },
            "report_data": {
                "summary": "Contract analysis complete"
            },
            "quality_metrics": {
                "validation_results": {
                    "passed": True
                }
            },
            "progress": {
                "current_step": 6,
                "total_steps": 6,
                "percentage": 100
            },
            "workflow_config": {
                "validation_enabled": True
            }
        }
        
        service.workflow.analyze_contract.return_value = mock_final_state
        service.workflow.get_workflow_metrics.return_value = {
            "execution_time": 2.5,
            "steps_completed": 6
        }
        
        # Test data
        document_data = {
            "content": "Test contract content",
            "file_type": "pdf",
            "metadata": {"pages": 10}
        }
        
        result = await service.analyze_contract(
            document_data=document_data,
            user_id="user-123",
            australian_state="NSW",
            session_id="test-session-123",
            contract_type="purchase_agreement"
        )
        
        # Verify results
        assert result["success"] is True
        assert result["session_id"] == "test-session-123"
        assert result["analysis_results"]["overall_confidence"] == 0.85
        assert len(result["analysis_results"]["recommendations"]) == 2
        assert result["quality_metrics"]["overall_confidence"] == 0.85
        assert result["workflow_metadata"]["steps_completed"] == 6
        assert result["enhancement_features"]["structured_parsing_used"] is True
        
        # Verify WebSocket messages were sent
        assert mock_websocket_manager.send_message.call_count >= 2  # Started and completed
    
    @pytest.mark.asyncio
    async def test_analyze_contract_validation_failure(self, service):
        """Test contract analysis with input validation failure."""
        result = await service.analyze_contract(
            document_data={},  # Invalid - no content
            user_id="",  # Invalid - empty user ID
            australian_state="INVALID_STATE",  # Invalid state
            contract_type="purchase_agreement"
        )
        
        assert result["success"] is False
        assert "Input validation failed" in result["error"]
        assert "Document content or file path is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_analyze_contract_workflow_failure(self, service, mock_websocket_manager):
        """Test contract analysis with workflow failure."""
        service.workflow.analyze_contract.side_effect = Exception("Workflow processing failed")
        
        document_data = {
            "content": "Test contract content",
            "file_type": "pdf"
        }
        
        result = await service.analyze_contract(
            document_data=document_data,
            user_id="user-123",
            australian_state="NSW",
            session_id="test-failure"
        )
        
        assert result["success"] is False
        assert "Contract analysis failed" in result["error"]
        assert "Workflow processing failed" in result["error"]
        
        # Verify error WebSocket message was sent
        mock_websocket_manager.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_analyze_contract_without_websocket(self, service):
        """Test contract analysis without WebSocket progress tracking."""
        service.enable_websocket_progress = False
        service.websocket_manager = None
        
        mock_final_state = {
            "session_id": "no-websocket-test",
            "parsing_status": ProcessingStatus.COMPLETED,
            "analysis_results": {
                "overall_confidence": 0.75
            }
        }
        
        service.workflow.analyze_contract.return_value = mock_final_state
        
        document_data = {"content": "Test contract"}
        
        result = await service.analyze_contract(
            document_data=document_data,
            user_id="user-123",
            australian_state="VIC",
            enable_websocket_progress=False
        )
        
        assert result["success"] is True
        assert result["session_id"] == "no-websocket-test"
    
    @pytest.mark.asyncio
    async def test_start_analysis_backward_compatibility(self, service, mock_websocket_manager):
        """Test backward compatibility start_analysis method."""
        mock_final_state = {
            "session_id": "compat-test",
            "parsing_status": ProcessingStatus.COMPLETED,
            "analysis_results": {
                "overall_confidence": 0.80,
                "recommendations": []
            }
        }
        
        service.workflow.analyze_contract.return_value = mock_final_state
        
        document_data = {"content": "Compatibility test contract"}
        
        result = await service.start_analysis(
            user_id="compat-user",
            session_id="compat-test",
            document_data=document_data,
            australian_state=AustralianState.NSW,
            user_type="buyer"
        )
        
        assert result["success"] is True
        assert result["contract_id"] == "compat-test"
        assert result["session_id"] == "compat-test"
        assert "analysis_results" in result


class TestContractAnalysisServiceValidation:
    """Test input validation functionality."""
    
    @pytest.fixture
    def service(self):
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "test config"
                }
                
                return ContractAnalysisService()
    
    def _create_mock_config(self):
        mock_config = Mock(spec=EnhancedWorkflowConfig)
        mock_config.enable_validation = True
        mock_config.enable_quality_checks = True
        mock_config.enable_prompt_manager = False
        mock_config.enable_structured_parsing = True
        mock_config.enable_enhanced_error_handling = True
        mock_config.enable_fallback_mechanisms = True
        mock_config.to_prompt_manager_config.return_value = {}
        mock_config.validate_config.return_value = {"status": "valid"}
        return mock_config
    
    def test_validate_analysis_inputs_success(self, service):
        """Test successful input validation."""
        validation_result = service._validate_analysis_inputs(
            document_data={"content": "Valid contract content"},
            user_id="valid-user-123",
            australian_state="NSW",
            contract_type="purchase_agreement"
        )
        
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
    
    def test_validate_analysis_inputs_missing_document(self, service):
        """Test validation with missing document data."""
        validation_result = service._validate_analysis_inputs(
            document_data={},
            user_id="user-123",
            australian_state="NSW",
            contract_type="purchase_agreement"
        )
        
        assert validation_result["valid"] is False
        assert "Document content or file path is required" in validation_result["errors"]
    
    def test_validate_analysis_inputs_invalid_user_id(self, service):
        """Test validation with invalid user ID."""
        validation_result = service._validate_analysis_inputs(
            document_data={"content": "Valid content"},
            user_id="",
            australian_state="NSW",
            contract_type="purchase_agreement"
        )
        
        assert validation_result["valid"] is False
        assert "Valid user ID is required" in validation_result["errors"]
    
    def test_validate_analysis_inputs_invalid_state(self, service):
        """Test validation with invalid Australian state."""
        validation_result = service._validate_analysis_inputs(
            document_data={"content": "Valid content"},
            user_id="user-123",
            australian_state="INVALID",
            contract_type="purchase_agreement"
        )
        
        assert validation_result["valid"] is False
        assert "Invalid Australian state: INVALID" in validation_result["errors"]
    
    def test_validate_analysis_inputs_unrecognized_contract_type(self, service):
        """Test validation with unrecognized contract type."""
        validation_result = service._validate_analysis_inputs(
            document_data={"content": "Valid content"},
            user_id="user-123",
            australian_state="NSW",
            contract_type="unknown_contract_type"
        )
        
        assert validation_result["valid"] is True  # Warnings don't fail validation
        assert "Unrecognized contract type: unknown_contract_type" in validation_result["warnings"]


class TestContractAnalysisServiceProgressTracking:
    """Test progress tracking and WebSocket functionality."""
    
    @pytest.fixture
    def service(self, mock_websocket_manager):
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "test config"
                }
                
                return ContractAnalysisService(
                    websocket_manager=mock_websocket_manager,
                    enable_websocket_progress=True
                )
    
    def _create_mock_config(self):
        mock_config = Mock(spec=EnhancedWorkflowConfig)
        mock_config.enable_validation = True
        mock_config.enable_quality_checks = True
        mock_config.enable_prompt_manager = False
        mock_config.enable_structured_parsing = True
        mock_config.enable_enhanced_error_handling = True
        mock_config.enable_fallback_mechanisms = True
        mock_config.to_prompt_manager_config.return_value = {}
        mock_config.validate_config.return_value = {"status": "valid"}
        return mock_config
    
    @pytest.mark.asyncio
    async def test_send_progress_update(self, service, mock_websocket_manager):
        """Test sending progress updates via WebSocket."""
        session_id = "progress-test"
        contract_id = "contract-123"
        
        # Initialize analysis tracking
        service.active_analyses[contract_id] = {
            "status": "processing",
            "progress": 0
        }
        
        await service._send_progress_update(
            session_id=session_id,
            contract_id=contract_id,
            step="validate_input",
            progress_percent=25,
            description="Validating contract terms"
        )
        
        # Verify internal tracking was updated
        assert service.active_analyses[contract_id]["progress"] == 25
        assert service.active_analyses[contract_id]["current_step"] == "validate_input"
        
        # Verify WebSocket message was sent
        mock_websocket_manager.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_analysis_status(self, service):
        """Test getting analysis status."""
        contract_id = "status-test"
        service.active_analyses[contract_id] = {
            "status": "processing",
            "progress": 50,
            "current_step": "analyze_compliance"
        }
        
        status = await service.get_analysis_status(contract_id)
        
        assert status is not None
        assert status["status"] == "processing"
        assert status["progress"] == 50
        assert status["current_step"] == "analyze_compliance"
    
    @pytest.mark.asyncio
    async def test_cancel_analysis(self, service, mock_websocket_manager):
        """Test cancelling an ongoing analysis."""
        contract_id = "cancel-test"
        session_id = "cancel-session"
        
        service.active_analyses[contract_id] = {
            "status": "processing",
            "progress": 30
        }
        
        result = await service.cancel_analysis(contract_id, session_id)
        
        assert result is True
        assert service.active_analyses[contract_id]["status"] == "cancelled"
        mock_websocket_manager.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_analysis(self, service):
        """Test cancelling a non-existent analysis."""
        result = await service.cancel_analysis("nonexistent", "session")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_retry_analysis(self, service, mock_websocket_manager):
        """Test retrying a failed analysis."""
        contract_id = "retry-test"
        session_id = "retry-session"
        
        service.active_analyses[contract_id] = {
            "status": "failed",
            "error": "Previous error"
        }
        
        result = await service.retry_analysis(contract_id, session_id, "user-123")
        
        assert result["success"] is True
        assert service.active_analyses[contract_id]["status"] == "retrying"
        assert "error" not in service.active_analyses[contract_id]
        mock_websocket_manager.send_message.assert_called_once()
    
    def test_cleanup_completed_analyses(self, service):
        """Test cleaning up old completed analyses."""
        old_time = datetime.now(UTC).timestamp() - (25 * 3600)  # 25 hours ago
        recent_time = datetime.now(UTC).timestamp() - 3600  # 1 hour ago
        
        service.active_analyses = {
            "old_completed": {
                "status": "completed",
                "start_time": datetime.fromtimestamp(old_time, UTC)
            },
            "old_failed": {
                "status": "failed",
                "start_time": datetime.fromtimestamp(old_time, UTC)
            },
            "recent_completed": {
                "status": "completed",
                "start_time": datetime.fromtimestamp(recent_time, UTC)
            },
            "current_processing": {
                "status": "processing",
                "start_time": datetime.fromtimestamp(old_time, UTC)
            }
        }
        
        service.cleanup_completed_analyses(max_age_hours=24)
        
        # Only old completed/failed analyses should be removed
        assert "old_completed" not in service.active_analyses
        assert "old_failed" not in service.active_analyses
        assert "recent_completed" in service.active_analyses
        assert "current_processing" in service.active_analyses
    
    def test_get_active_analyses_count(self, service):
        """Test getting count of active analyses."""
        service.active_analyses = {
            "processing1": {"status": "processing"},
            "processing2": {"status": "starting"},
            "completed1": {"status": "completed"},
            "failed1": {"status": "failed"},
            "retrying1": {"status": "retrying"},
        }
        
        count = service.get_active_analyses_count()
        assert count == 3  # processing, starting, retrying
    
    def test_get_all_analyses_summary(self, service):
        """Test getting summary of all analyses."""
        service.active_analyses = {
            "processing1": {"status": "processing"},
            "processing2": {"status": "processing"},
            "completed1": {"status": "completed"},
            "failed1": {"status": "failed"},
        }
        
        summary = service.get_all_analyses_summary()
        
        assert summary["total_analyses"] == 4
        assert summary["status_breakdown"]["processing"] == 2
        assert summary["status_breakdown"]["completed"] == 1
        assert summary["status_breakdown"]["failed"] == 1
        assert summary["active_count"] == 2


class TestContractAnalysisServiceHealthAndMetrics:
    """Test health check and metrics functionality."""
    
    @pytest.fixture
    def service(self, mock_websocket_manager):
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "test config"
                }
                
                service = ContractAnalysisService(
                    websocket_manager=mock_websocket_manager
                )
                
                # Mock workflow
                service.workflow = Mock()
                service.workflow.get_workflow_metrics.return_value = {
                    "total_executions": 10,
                    "average_execution_time": 2.5
                }
                
                return service
    
    def _create_mock_config(self):
        mock_config = Mock(spec=EnhancedWorkflowConfig)
        mock_config.enable_validation = True
        mock_config.enable_quality_checks = True
        mock_config.enable_prompt_manager = False
        mock_config.enable_structured_parsing = True
        mock_config.enable_enhanced_error_handling = True
        mock_config.enable_fallback_mechanisms = True
        mock_config.to_prompt_manager_config.return_value = {}
        mock_config.validate_config.return_value = {"status": "valid"}
        return mock_config
    
    @pytest.mark.asyncio
    async def test_get_service_health_healthy(self, service):
        """Test service health check when all components are healthy."""
        health = await service.get_service_health()
        
        assert health["status"] == "healthy"
        assert health["version"] == "unified_v1.0"
        assert "components" in health
        assert "workflow" in health["components"]
        assert "websocket_manager" in health["components"]
        assert health["components"]["workflow"]["status"] == "healthy"
        assert health["components"]["websocket_manager"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_get_service_health_degraded(self, service):
        """Test service health check when components have issues."""
        service.workflow.get_workflow_metrics.side_effect = Exception("Workflow error")
        
        health = await service.get_service_health()
        
        assert health["status"] == "degraded"
        assert health["components"]["workflow"]["status"] == "error"
        assert "error" in health["components"]["workflow"]
    
    @pytest.mark.asyncio
    async def test_get_service_health_prompt_manager(self, service):
        """Test health check with prompt manager."""
        service.prompt_manager = Mock()
        service.prompt_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        
        health = await service.get_service_health()
        
        assert health["components"]["prompt_manager"]["status"] == "healthy"
    
    def test_get_service_metrics(self, service):
        """Test getting comprehensive service metrics."""
        service._service_metrics["total_requests"] = 50
        service._service_metrics["successful_analyses"] = 45
        service._service_metrics["failed_analyses"] = 5
        
        metrics = service.get_service_metrics()
        
        assert metrics["service_metrics"]["total_requests"] == 50
        assert metrics["service_metrics"]["successful_analyses"] == 45
        assert metrics["workflow_metrics"]["total_executions"] == 10
        assert metrics["websocket_metrics"]["progress_tracking_enabled"] is False
        assert "timestamp" in metrics
    
    @pytest.mark.asyncio
    async def test_reload_configuration_success(self, service):
        """Test successful configuration reload."""
        new_config = self._create_mock_config()
        
        with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "issues": [],
                "warnings": []
            }
            
            result = await service.reload_configuration(new_config)
            
            assert result["success"] is True
            assert service.config == new_config
    
    @pytest.mark.asyncio
    async def test_reload_configuration_failure(self, service):
        """Test configuration reload failure."""
        invalid_config = self._create_mock_config()
        
        with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "issues": ["Configuration error"],
                "warnings": []
            }
            
            result = await service.reload_configuration(invalid_config)
            
            assert result["success"] is False
            assert "Configuration error" in result["error"]


class TestContractAnalysisServiceUtilities:
    """Test utility methods."""
    
    @pytest.fixture
    def service(self):
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = self._create_mock_config()
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "test config"
                }
                
                return ContractAnalysisService()
    
    def _create_mock_config(self):
        mock_config = Mock(spec=EnhancedWorkflowConfig)
        mock_config.enable_validation = True
        mock_config.enable_quality_checks = True
        mock_config.enable_prompt_manager = False
        mock_config.enable_structured_parsing = True
        mock_config.enable_enhanced_error_handling = True
        mock_config.enable_fallback_mechanisms = True
        mock_config.to_prompt_manager_config.return_value = {}
        mock_config.validate_config.return_value = {"status": "valid"}
        return mock_config
    
    def test_create_initial_state(self, service):
        """Test creating initial state for workflow."""
        document_data = {"content": "Test contract"}
        user_preferences = {"language": "en", "detailed_analysis": True}
        
        initial_state = service._create_initial_state(
            document_data=document_data,
            user_id="user-123",
            australian_state=AustralianState.NSW,
            user_preferences=user_preferences,
            session_id="test-session",
            contract_type="purchase_agreement",
            user_experience="intermediate",
            user_type="buyer"
        )
        
        assert initial_state["session_id"] == "test-session"
        assert initial_state["user_id"] == "user-123"
        assert initial_state["australian_state"] == AustralianState.NSW
        assert initial_state["document_data"] == document_data
        assert initial_state["user_preferences"] == user_preferences
        assert initial_state["contract_type"] == "purchase_agreement"
        assert initial_state["user_experience"] == "intermediate"
        assert initial_state["user_type"] == "buyer"
        assert initial_state["current_step"] == "initialized"
        assert initial_state["parsing_status"] == ProcessingStatus.PENDING
    
    def test_create_analysis_response_success(self, service):
        """Test creating successful analysis response."""
        final_state = {
            "session_id": "response-test",
            "parsing_status": ProcessingStatus.COMPLETED,
            "analysis_results": {
                "overall_confidence": 0.92,
                "confidence_breakdown": {
                    "terms_extraction": 0.95,
                    "risk_assessment": 0.88
                },
                "recommendations": ["Review clause 3.2"]
            },
            "report_data": {"summary": "Analysis complete"},
            "progress": {
                "current_step": 6,
                "total_steps": 6,
                "percentage": 100
            },
            "workflow_config": {
                "validation_enabled": True
            }
        }
        
        service.workflow = Mock()
        service.workflow.get_workflow_metrics.return_value = {
            "execution_time": 3.2
        }
        
        response = service._create_analysis_response(final_state, 3.2)
        
        assert response["success"] is True
        assert response["session_id"] == "response-test"
        assert response["processing_time_seconds"] == 3.2
        assert response["workflow_version"] == "unified_v1.0"
        assert response["quality_metrics"]["overall_confidence"] == 0.92
        assert response["workflow_metadata"]["steps_completed"] == 6
        assert response["enhancement_features"]["structured_parsing_used"] is True
    
    def test_create_error_response(self, service):
        """Test creating error response."""
        start_time = datetime.now(UTC)
        
        response = service._create_error_response(
            error_message="Test error occurred",
            session_id="error-session",
            start_time=start_time
        )
        
        assert response["success"] is False
        assert response["session_id"] == "error-session"
        assert response["error"] == "Test error occurred"
        assert response["workflow_version"] == "unified_v1.0"
        assert "processing_time_seconds" in response
        assert "service_metrics" in response
    
    def test_extract_warnings_from_state(self, service):
        """Test extracting warnings from workflow state."""
        state = {
            "document_quality_metrics": {
                "issues_identified": ["Poor image quality", "Text extraction partial"]
            },
            "compliance_check": {
                "warnings": ["Non-standard clause format"]
            },
            "terms_validation": {
                "missing_mandatory_terms": ["deposit_amount", "settlement_date"]
            },
            "final_output_validation": {
                "validation_passed": False
            }
        }
        
        warnings = service._extract_warnings_from_state(state)
        
        assert "Poor image quality" in warnings
        assert "Text extraction partial" in warnings
        assert "Non-standard clause format" in warnings
        assert "Missing mandatory terms: deposit_amount, settlement_date" in warnings
        assert "Final output validation failed" in warnings


class TestContractAnalysisServiceInterfaces:
    """Test service implements interfaces correctly."""
    
    @pytest.mark.asyncio
    async def test_implements_contract_analyzer_interface(self):
        """Test ContractAnalysisService implements IContractAnalyzer interface."""
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = Mock(
                enable_validation=True,
                enable_quality_checks=True,
                enable_prompt_manager=False,
                enable_structured_parsing=True,
                enable_enhanced_error_handling=True,
                enable_fallback_mechanisms=True,
                to_prompt_manager_config=Mock(return_value={}),
                validate_config=Mock(return_value={"status": "valid"})
            )
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "test config"
                }
                
                service = ContractAnalysisService()
        
        # Check if service implements the protocol
        assert isinstance(service, IContractAnalyzer)
        
        # Check required methods exist
        assert hasattr(service, 'initialize')
        assert hasattr(service, 'analyze_contract')
        assert hasattr(service, 'get_analysis_status')


# Pytest fixtures for mocking
@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager for testing."""
    mock_manager = AsyncMock()
    mock_manager.send_message = AsyncMock()
    return mock_manager


@pytest.fixture
def mock_workflow():
    """Create mock workflow for testing."""
    mock_workflow = AsyncMock()
    mock_workflow.analyze_contract = AsyncMock()
    mock_workflow.get_workflow_metrics = Mock(return_value={})
    return mock_workflow


@pytest.fixture
def mock_prompt_manager():
    """Create mock prompt manager for testing."""
    mock_pm = AsyncMock()
    mock_pm.initialize = AsyncMock()
    mock_pm.health_check = AsyncMock(return_value={"status": "healthy"})
    mock_pm.get_metrics = Mock(return_value={})
    mock_pm.reload_templates = AsyncMock()
    return mock_pm


@pytest.mark.integration
class TestContractAnalysisServiceIntegration:
    """Integration tests requiring external dependencies."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_contract_analysis(self, mock_websocket_manager):
        """Test complete contract analysis workflow."""
        with patch('app.services.contract_analysis_service.get_enhanced_workflow_config') as mock_config:
            mock_config.return_value = Mock(
                enable_validation=True,
                enable_quality_checks=True,
                enable_prompt_manager=False,
                enable_structured_parsing=True,
                enable_enhanced_error_handling=True,
                enable_fallback_mechanisms=True,
                to_prompt_manager_config=Mock(return_value={}),
                validate_config=Mock(return_value={"status": "valid"})
            )
            
            with patch('app.services.contract_analysis_service.validate_workflow_configuration') as mock_validate:
                mock_validate.return_value = {
                    "valid": True,
                    "issues": [],
                    "warnings": [],
                    "config_summary": "integration test config"
                }
                
                service = ContractAnalysisService(
                    websocket_manager=mock_websocket_manager,
                    openai_api_key="test-integration-key",
                    model_name="gpt-4",
                    enable_websocket_progress=True
                )
        
        # Mock comprehensive workflow response
        comprehensive_final_state = {
            "session_id": "integration-test-123",
            "parsing_status": ProcessingStatus.COMPLETED,
            "analysis_results": {
                "overall_confidence": 0.88,
                "confidence_breakdown": {
                    "document_processing": 0.95,
                    "terms_extraction": 0.90,
                    "compliance_analysis": 0.85,
                    "risk_assessment": 0.82,
                    "recommendations_generation": 0.88
                },
                "risk_assessment": {
                    "overall_risk_score": 2.5,
                    "risk_categories": {
                        "legal_compliance": "low",
                        "financial_terms": "medium",
                        "settlement_conditions": "low"
                    }
                },
                "compliance_check": {
                    "state_compliance": True,
                    "compliance_score": 0.92,
                    "required_disclosures": ["cooling_off_period", "pest_inspection"]
                },
                "recommendations": [
                    {
                        "priority": "high",
                        "category": "legal_review",
                        "description": "Consider legal review of clause 7.3 regarding settlement extensions"
                    },
                    {
                        "priority": "medium", 
                        "category": "financial_terms",
                        "description": "Verify deposit protection arrangements"
                    }
                ]
            },
            "report_data": {
                "executive_summary": "Purchase agreement analysis completed with medium-low risk profile",
                "key_findings": [
                    "Contract complies with NSW property law requirements",
                    "Standard terms with minor customizations detected",
                    "No critical risk factors identified"
                ],
                "detailed_sections": {
                    "terms_analysis": {"parties": "valid", "property_description": "complete"},
                    "compliance_analysis": {"mandatory_clauses": "present", "disclosures": "adequate"},
                    "risk_analysis": {"legal_risks": "low", "financial_risks": "medium"}
                }
            },
            "quality_metrics": {
                "validation_results": {
                    "input_validation": {"passed": True, "score": 1.0},
                    "document_quality": {"passed": True, "score": 0.95},
                    "analysis_consistency": {"passed": True, "score": 0.88},
                    "output_completeness": {"passed": True, "score": 0.92}
                }
            },
            "progress": {
                "current_step": 6,
                "total_steps": 6,
                "percentage": 100
            },
            "workflow_config": {
                "validation_enabled": True,
                "quality_checks_enabled": True,
                "structured_parsing_enabled": True
            },
            "document_quality_metrics": {
                "text_extraction_quality": 0.95,
                "structure_recognition": 0.88,
                "issues_identified": []
            }
        }
        
        service.workflow.analyze_contract = AsyncMock(return_value=comprehensive_final_state)
        service.workflow.get_workflow_metrics = Mock(return_value={
            "total_executions": 1,
            "successful_executions": 1,
            "average_execution_time": 4.2,
            "steps_completed": 6
        })
        
        # Execute integration test
        document_data = {
            "content": "PURCHASE AGREEMENT\n\nThis agreement is made between...\n[Comprehensive contract content]",
            "file_type": "pdf",
            "metadata": {
                "pages": 15,
                "word_count": 8500,
                "file_size": "2.5MB"
            }
        }
        
        result = await service.analyze_contract(
            document_data=document_data,
            user_id="integration-user-456",
            australian_state="NSW",
            user_preferences={
                "analysis_depth": "comprehensive",
                "risk_tolerance": "conservative",
                "user_experience_level": "intermediate"
            },
            session_id="integration-session-789",
            contract_type="purchase_agreement",
            user_experience="intermediate",
            user_type="buyer",
            enable_websocket_progress=True
        )
        
        # Verify comprehensive integration results
        assert result["success"] is True
        assert result["session_id"] == "integration-test-123"
        assert result["workflow_version"] == "unified_v1.0"
        
        # Verify analysis quality
        assert result["quality_metrics"]["overall_confidence"] == 0.88
        assert result["quality_metrics"]["confidence_breakdown"]["terms_extraction"] == 0.90
        assert result["quality_metrics"]["validation_results"]["input_validation"]["passed"] is True
        
        # Verify analysis results completeness
        analysis_results = result["analysis_results"]
        assert analysis_results["risk_assessment"]["overall_risk_score"] == 2.5
        assert analysis_results["compliance_check"]["state_compliance"] is True
        assert len(analysis_results["recommendations"]) == 2
        
        # Verify workflow metadata
        workflow_metadata = result["workflow_metadata"]
        assert workflow_metadata["steps_completed"] == 6
        assert workflow_metadata["total_steps"] == 6
        assert workflow_metadata["progress_percentage"] == 100
        assert workflow_metadata["configuration"]["validation_enabled"] is True
        
        # Verify enhancement features
        enhancement_features = result["enhancement_features"]
        assert enhancement_features["structured_parsing_used"] is True
        assert enhancement_features["validation_performed"] is True
        assert enhancement_features["quality_checks_performed"] is True
        
        # Verify WebSocket interactions
        assert mock_websocket_manager.send_message.call_count >= 2  # Started + completed events
        
        # Verify service metrics were updated
        assert service._service_metrics["total_requests"] == 1
        assert service._service_metrics["successful_analyses"] == 1
        assert service._service_metrics["average_processing_time"] > 0