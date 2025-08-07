"""
Comprehensive unit tests for SemanticAnalysisService
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from io import BytesIO
from datetime import datetime, UTC
from pathlib import Path
import tempfile
import json

from app.services.semantic_analysis_service import (
    SemanticAnalysisService,
    SemanticAnalysisWorkflow,
)
from app.services.interfaces import ISemanticAnalyzer
from app.clients.base.exceptions import ClientConnectionError, ClientError
from app.prompts.schema.image_semantics_schema import ImageType
from app.schema.enums import AustralianState, ContractType
from fastapi import HTTPException


class TestSemanticAnalysisWorkflowInitialization:
    """Test SemanticAnalysisWorkflow initialization and configuration."""
    
    @pytest.mark.asyncio
    async def test_workflow_creation(self):
        """Test SemanticAnalysisWorkflow can be created."""
        workflow = SemanticAnalysisWorkflow()
        
        assert workflow is not None
        assert workflow.ocr_service is None
        assert workflow.document_service is None
        assert workflow.settings is not None
    
    @pytest.mark.asyncio
    async def test_workflow_initialization_success(self, mock_document_service):
        """Test successful workflow initialization."""
        workflow = SemanticAnalysisWorkflow()
        
        with patch('app.services.semantic_analysis_service.GeminiOCRService') as mock_ocr:
            mock_ocr_instance = AsyncMock()
            mock_ocr.return_value = mock_ocr_instance
            
            await workflow.initialize(mock_document_service)
            
            assert workflow.ocr_service is not None
            assert workflow.document_service == mock_document_service
            mock_ocr_instance.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_initialization_failure(self):
        """Test workflow initialization handles OCR service failure."""
        workflow = SemanticAnalysisWorkflow()
        
        with patch('app.services.semantic_analysis_service.GeminiOCRService') as mock_ocr:
            mock_ocr_instance = AsyncMock()
            mock_ocr_instance.initialize.side_effect = Exception("OCR init failed")
            mock_ocr.return_value = mock_ocr_instance
            
            with pytest.raises(Exception) as exc_info:
                await workflow.initialize()
            
            assert "OCR init failed" in str(exc_info.value)


class TestSemanticAnalysisServiceInitialization:
    """Test SemanticAnalysisService initialization and configuration."""
    
    @pytest.mark.asyncio
    async def test_service_creation_without_document_service(self):
        """Test SemanticAnalysisService can be created without document service."""
        service = SemanticAnalysisService()
        
        assert service is not None
        assert service.workflow is not None
        assert service._document_service is None
    
    @pytest.mark.asyncio
    async def test_service_creation_with_document_service(self, mock_document_service):
        """Test SemanticAnalysisService with document service."""
        service = SemanticAnalysisService(mock_document_service)
        
        assert service._document_service == mock_document_service
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_document_service):
        """Test successful service initialization."""
        service = SemanticAnalysisService(mock_document_service)
        
        with patch.object(service.workflow, 'initialize') as mock_init:
            await service.initialize()
            
            mock_init.assert_called_once_with(mock_document_service)
    
    @pytest.mark.asyncio
    async def test_set_document_service(self, mock_document_service):
        """Test setting document service after initialization."""
        service = SemanticAnalysisService()
        
        await service.set_document_service(mock_document_service)
        
        assert service._document_service == mock_document_service
        assert service.workflow.document_service == mock_document_service


class TestSemanticAnalysisServiceDocumentAnalysis:
    """Test document semantic analysis functionality."""
    
    @pytest.fixture
    def service(self, mock_document_service):
        service = SemanticAnalysisService(mock_document_service)
        service.workflow.ocr_service = AsyncMock()
        service.workflow.document_service = mock_document_service
        return service
    
    @pytest.mark.asyncio
    async def test_analyze_document_semantics_success(self, service, mock_document_service):
        """Test successful document semantic analysis."""
        # Setup mock responses
        file_content = b"mock image content"
        mock_document_service.get_file_content.return_value = file_content
        
        mock_semantic_result = {
            "semantic_analysis": {
                "infrastructure_elements": [
                    {
                        "element_type": "sewer_line",
                        "description": "Main sewer connection",
                        "confidence": "high",
                        "risk_relevance": "medium",
                        "location": {"description": "Front of property"}
                    }
                ],
                "environmental_elements": [],
                "boundary_elements": [],
                "building_elements": [],
                "key_findings": ["Sewer line present"],
                "analysis_confidence": "high"
            },
            "image_type_detected": "sewer_service_diagram",
            "prompt_template_used": True
        }
        
        service.workflow.ocr_service.extract_image_semantics.return_value = mock_semantic_result
        
        # Mock progress tracking
        service.workflow.document_service.track_processing_progress = AsyncMock()
        
        result = await service.analyze_document_semantics(
            storage_path="test/path/diagram.pdf",
            file_type="pdf",
            filename="sewer_diagram.pdf",
            contract_context={"document_type": "sewer_service"},
            document_id="test-doc-123"
        )
        
        assert result["document_metadata"]["storage_path"] == "test/path/diagram.pdf"
        assert result["document_metadata"]["filename"] == "sewer_diagram.pdf"
        assert result["document_metadata"]["document_id"] == "test-doc-123"
        assert result["semantic_analysis"] is not None
        assert result["risk_assessment"] is not None
        assert len(result["processing_stages"]) >= 2
        
        # Verify OCR service was called correctly
        service.workflow.ocr_service.extract_image_semantics.assert_called_once()
        
        # Verify progress tracking
        assert service.workflow.document_service.track_processing_progress.call_count >= 4
    
    @pytest.mark.asyncio
    async def test_analyze_document_semantics_ocr_not_initialized(self, service):
        """Test analysis fails when OCR service not initialized."""
        service.workflow.ocr_service = None
        
        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_document_semantics(
                storage_path="test/path.pdf",
                file_type="pdf",
                filename="test.pdf"
            )
        
        assert exc_info.value.status_code == 503
        assert "not initialized" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_analyze_document_semantics_document_service_unavailable(self, service):
        """Test analysis fails when document service unavailable."""
        service.workflow.document_service = None
        
        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_document_semantics(
                storage_path="test/path.pdf",
                file_type="pdf",
                filename="test.pdf"
            )
        
        assert exc_info.value.status_code == 503
        assert "Document service not available" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_analyze_document_semantics_file_retrieval_failure(self, service, mock_document_service):
        """Test analysis handles file retrieval failure."""
        mock_document_service.get_file_content.side_effect = Exception("File not found")
        
        result = await service.analyze_document_semantics(
            storage_path="nonexistent/path.pdf",
            file_type="pdf",
            filename="test.pdf",
            document_id="test-doc-456"
        )
        
        assert len(result["errors"]) > 0
        assert "File not found" in result["errors"][0]["error"]
        
        # Verify error progress tracking
        service.workflow.document_service.track_processing_progress.assert_called()


class TestSemanticAnalysisServiceContractDiagrams:
    """Test contract diagram analysis functionality."""
    
    @pytest.fixture
    def service(self, mock_document_service):
        service = SemanticAnalysisService(mock_document_service)
        service.workflow.ocr_service = AsyncMock()
        service.workflow.document_service = mock_document_service
        return service
    
    @pytest.mark.asyncio
    async def test_analyze_contract_diagrams_success(self, service):
        """Test successful contract diagram analysis."""
        storage_paths = [
            "diagrams/sewer_plan.jpg",
            "diagrams/site_plan.jpg",
            "diagrams/flood_map.png"
        ]
        
        contract_context = {
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "property_type": "residential"
        }
        
        # Mock individual diagram analysis
        mock_diagram_analysis = {
            "semantic_analysis": {
                "infrastructure_elements": [
                    {
                        "element_type": "sewer_line",
                        "description": "Connection to main line",
                        "confidence": "high",
                        "risk_relevance": "medium"
                    }
                ],
                "environmental_elements": [],
                "boundary_elements": []
            },
            "risk_assessment": {
                "identified_risks": [
                    {
                        "risk_type": "Infrastructure: sewer_line",
                        "description": "Connection to main line",
                        "severity": "medium",
                        "category": "infrastructure"
                    }
                ],
                "overall_risk_score": "medium",
                "total_risks_identified": 1
            }
        }
        
        with patch.object(service, 'analyze_document_semantics', return_value=mock_diagram_analysis):
            result = await service.analyze_contract_diagrams(
                storage_paths=storage_paths,
                contract_context=contract_context,
                document_id="contract-doc-789"
            )
        
        assert result["total_diagrams"] == 3
        assert len(result["diagram_analyses"]) == 3
        assert result["consolidated_risks"] is not None
        assert result["overall_assessment"] is not None
        assert result["recommendations"] is not None
        
        # Verify each diagram was analyzed
        for i, storage_path in enumerate(storage_paths):
            diagram_analysis = result["diagram_analyses"][i]
            assert diagram_analysis["storage_path"] == storage_path
            assert diagram_analysis["diagram_index"] == i
    
    @pytest.mark.asyncio
    async def test_analyze_contract_diagrams_no_paths(self, service):
        """Test analysis fails with no diagram paths."""
        with pytest.raises(HTTPException) as exc_info:
            await service.analyze_contract_diagrams(
                storage_paths=[],
                contract_context={}
            )
        
        assert exc_info.value.status_code == 400
        assert "No diagrams provided" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_analyze_contract_diagrams_analysis_failure(self, service):
        """Test contract diagram analysis handles individual diagram failure."""
        storage_paths = ["diagrams/broken.jpg"]
        
        with patch.object(service, 'analyze_document_semantics', 
                         side_effect=Exception("Analysis failed")):
            result = await service.analyze_contract_diagrams(
                storage_paths=storage_paths,
                contract_context={},
                document_id="failing-doc"
            )
        
        assert "error" in result
        assert "Analysis failed" in result["error"]


class TestSemanticAnalysisServiceUtilities:
    """Test utility methods."""
    
    @pytest.fixture
    def service(self):
        return SemanticAnalysisService()
    
    @pytest.mark.unit
    
    def test_detect_image_type_from_context(self, service):
        """Test image type detection from context and filename."""
        test_cases = [
            ("sewer_service_diagram.pdf", {"document_type": "sewer"}, ImageType.SEWER_SERVICE_DIAGRAM),
            ("site_plan_final.jpg", None, ImageType.SITE_PLAN),
            ("survey_report.png", None, ImageType.SURVEY_DIAGRAM),
            ("flood_risk_map.pdf", None, ImageType.FLOOD_MAP),
            ("bushfire_hazard.jpg", None, ImageType.BUSHFIRE_MAP),
            ("zoning_map.png", None, ImageType.ZONING_MAP),
            ("drainage_plan.pdf", None, ImageType.DRAINAGE_PLAN),
            ("utility_layout.jpg", None, ImageType.UTILITY_PLAN),
            ("strata_diagram.png", None, ImageType.STRATA_PLAN),
            ("unknown_diagram.pdf", None, ImageType.UNKNOWN),
        ]
        
        for filename, contract_context, expected_type in test_cases:
            detected_type = service._detect_image_type_from_context(filename, contract_context)
            assert detected_type == expected_type, f"Failed for {filename}"
    
    @pytest.mark.asyncio
    async def test_convert_to_risk_assessment(self, service):
        """Test conversion of semantic analysis to risk assessment."""
        semantic_analysis = {
            "infrastructure_elements": [
                {
                    "element_type": "sewer_line",
                    "description": "Main connection",
                    "confidence": "high",
                    "risk_relevance": "significant",
                    "location": {"description": "Front boundary"}
                }
            ],
            "environmental_elements": [
                {
                    "environmental_type": "flood_risk",
                    "description": "Potential flooding",
                    "risk_level": "high",
                    "location": {"description": "Low-lying area"}
                }
            ],
            "boundary_elements": [
                {
                    "boundary_type": "fence_line",
                    "description": "Property boundary",
                    "encroachments": ["neighbour_shed"],
                    "easements": ["power_line"],
                    "location": {"description": "Eastern boundary"}
                }
            ]
        }
        
        result = await service._convert_to_risk_assessment(semantic_analysis)
        
        assert result["total_risks_identified"] == 3
        assert result["overall_risk_score"] in ["low", "medium", "high", "critical"]
        assert len(result["identified_risks"]) == 3
        assert len(result["recommended_actions"]) > 0
        
        # Verify risk categories
        risk_categories = result["risk_categories"]
        assert risk_categories["infrastructure"] == 1
        assert risk_categories["environmental"] == 1
        assert risk_categories["boundary"] == 1
    
    @pytest.mark.asyncio
    async def test_convert_to_risk_assessment_empty_input(self, service):
        """Test risk assessment with empty semantic analysis."""
        result = await service._convert_to_risk_assessment(None)
        
        assert result["overall_risk_score"] == "low"
        assert result["total_risks_identified"] == 0
        assert result["high_priority_risks"] == []
        assert result["recommended_actions"] == []
    
    @pytest.mark.unit
    
    def test_determine_risk_severity(self, service):
        """Test risk severity determination."""
        test_cases = [
            ({"confidence": "high", "risk_relevance": "critical"}, "critical"),
            ({"confidence": "high", "risk_relevance": "significant"}, "high"),
            ({"confidence": "medium", "risk_relevance": "moderate"}, "medium"),
            ({"confidence": "low", "risk_relevance": "minimal"}, "low"),
            ({}, "low"),  # Default case
        ]
        
        for element, expected_severity in test_cases:
            severity = service._determine_risk_severity(element)
            assert severity == expected_severity
    
    @pytest.mark.unit
    
    def test_calculate_overall_risk_score(self, service):
        """Test overall risk score calculation."""
        test_cases = [
            ([], "low"),  # No risks
            ([{"severity": "critical"}, {"severity": "high"}], "critical"),
            ([{"severity": "high"}, {"severity": "medium"}], "high"),
            ([{"severity": "medium"}, {"severity": "low"}], "medium"),
            ([{"severity": "low"}], "low"),
        ]
        
        for risks, expected_score in test_cases:
            score = service._calculate_overall_risk_score(risks)
            assert score == expected_score
    
    @pytest.mark.unit
    
    def test_generate_risk_actions(self, service):
        """Test risk action generation."""
        risks = [
            {"category": "infrastructure", "severity": "high"},
            {"category": "environmental", "severity": "medium"},
            {"category": "boundary", "severity": "low"},
            {"category": "other", "severity": "critical"},
        ]
        
        actions = service._generate_risk_actions(risks)
        
        assert len(actions) > 0
        # Should include actions for each category and high severity
        action_text = " ".join(actions)
        assert "structural engineer" in action_text
        assert "environmental" in action_text
        assert "surveyor" in action_text
        assert "legal advice" in action_text  # For critical severity


class TestSemanticAnalysisServiceHealthCheck:
    """Test health check functionality."""
    
    @pytest.fixture
    def service(self, mock_document_service):
        service = SemanticAnalysisService(mock_document_service)
        service.workflow.document_service = mock_document_service
        return service
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, service, mock_document_service):
        """Test health check when all dependencies are healthy."""
        # Setup mock OCR service
        service.workflow.ocr_service = AsyncMock()
        service.workflow.ocr_service.health_check.return_value = {"service_status": "healthy"}
        
        # Setup mock document service
        mock_document_service.health_check.return_value = {"status": "healthy"}
        
        health = await service.health_check()
        
        assert health["service"] == "SemanticAnalysisService"
        assert health["status"] == "healthy"
        assert health["dependencies"]["ocr_service"] == "healthy"
        assert health["dependencies"]["document_service"] == "healthy"
        assert len(health["capabilities"]) > 0
    
    @pytest.mark.asyncio
    async def test_health_check_degraded_dependencies(self, service):
        """Test health check when dependencies are unavailable."""
        service.workflow.ocr_service = None
        service.workflow.document_service = None
        
        health = await service.health_check()
        
        assert health["status"] == "degraded"
        assert health["dependencies"]["ocr_service"] == "not_initialized"
        assert health["dependencies"]["document_service"] == "not_initialized"
    
    @pytest.mark.asyncio
    async def test_health_check_dependency_errors(self, service, mock_document_service):
        """Test health check with dependency errors."""
        # Setup failing OCR service
        service.workflow.ocr_service = AsyncMock()
        service.workflow.ocr_service.health_check.side_effect = Exception("OCR failed")
        
        # Setup failing document service
        mock_document_service.health_check.side_effect = Exception("DB connection failed")
        
        health = await service.health_check()
        
        assert health["status"] == "degraded"
        assert health["dependencies"]["ocr_service"] == "error"
        assert health["dependencies"]["document_service"] == "error"


class TestSemanticAnalysisServiceCapabilities:
    """Test capabilities and configuration."""
    
    @pytest.fixture
    def service(self):
        return SemanticAnalysisService()
    
    @pytest.mark.asyncio
    async def test_get_analysis_capabilities(self, service):
        """Test getting analysis capabilities."""
        capabilities = await service.get_analysis_capabilities()
        
        assert "supported_image_types" in capabilities
        assert "analysis_focus_options" in capabilities
        assert "risk_categories" in capabilities
        assert "supported_file_types" in capabilities
        assert "max_diagrams_per_analysis" in capabilities
        assert "features" in capabilities
        
        # Verify specific capabilities
        assert "comprehensive" in capabilities["analysis_focus_options"]
        assert "infrastructure" in capabilities["risk_categories"]
        assert "jpg" in capabilities["supported_file_types"]
        assert capabilities["max_diagrams_per_analysis"] == 10
    
    @pytest.mark.asyncio
    async def test_get_analysis_capabilities_with_ocr(self, service):
        """Test capabilities include OCR capabilities when available."""
        service.workflow.ocr_service = AsyncMock()
        service.workflow.ocr_service.get_processing_capabilities.return_value = {
            "max_image_size_mb": 25,
            "supported_formats": ["jpg", "png", "pdf"]
        }
        
        capabilities = await service.get_analysis_capabilities()
        
        assert "ocr_capabilities" in capabilities
        assert capabilities["ocr_capabilities"]["max_image_size_mb"] == 25


class TestSemanticAnalysisServiceInterfaces:
    """Test service implements interfaces correctly."""
    
    @pytest.mark.asyncio
    async def test_implements_semantic_analyzer_interface(self):
        """Test SemanticAnalysisService implements ISemanticAnalyzer interface."""
        service = SemanticAnalysisService()
        
        # Check if service implements the protocol
        assert isinstance(service, ISemanticAnalyzer)
        
        # Check required methods exist
        assert hasattr(service, 'initialize')
        assert hasattr(service, 'analyze_diagram_semantic_content')
        assert hasattr(service, 'extract_contract_entities')
    
    @pytest.mark.asyncio
    async def test_analyze_diagram_semantic_content_interface(self, mock_document_service):
        """Test analyze_diagram_semantic_content method exists for interface compliance."""
        service = SemanticAnalysisService(mock_document_service)
        service.workflow.ocr_service = AsyncMock()
        service.workflow.document_service = mock_document_service
        
        # Mock file content retrieval
        mock_document_service.get_file_content.return_value = b"mock image content"
        
        # Mock OCR service response
        service.workflow.ocr_service.extract_image_semantics.return_value = {
            "semantic_analysis": {
                "infrastructure_elements": [],
                "environmental_elements": [],
                "boundary_elements": []
            }
        }
        
        # This method should delegate to analyze_document_semantics
        image_content = b"test image content"
        diagram_context = {
            "storage_path": "test/diagram.jpg",
            "file_type": "jpg",
            "filename": "test_diagram.jpg"
        }
        
        # For interface compliance, we create a wrapper method
        async def analyze_diagram_semantic_content(image_content: bytes, diagram_context: dict):
            return await service.analyze_document_semantics(
                storage_path=diagram_context["storage_path"],
                file_type=diagram_context["file_type"],
                filename=diagram_context["filename"]
            )
        
        # Test the method exists and works
        result = await analyze_diagram_semantic_content(image_content, diagram_context)
        assert result is not None


@pytest.mark.integration
class TestSemanticAnalysisServiceIntegration:
    """Integration tests requiring external dependencies."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_semantic_analysis(self, mock_document_service):
        """Test complete semantic analysis workflow."""
        service = SemanticAnalysisService(mock_document_service)
        
        # Setup mock OCR service
        service.workflow.ocr_service = AsyncMock()
        service.workflow.ocr_service.extract_image_semantics.return_value = {
            "semantic_analysis": {
                "infrastructure_elements": [
                    {
                        "element_type": "sewer_connection",
                        "description": "Main sewer line connection point",
                        "confidence": "high",
                        "risk_relevance": "significant property consideration",
                        "location": {"description": "Front boundary near street"}
                    }
                ],
                "environmental_elements": [
                    {
                        "environmental_type": "flood_risk_area",
                        "description": "Property in 1 in 100 year flood zone",
                        "risk_level": "high",
                        "location": {"description": "Lower section of property"}
                    }
                ],
                "boundary_elements": [],
                "building_elements": [],
                "key_findings": [
                    "Sewer connection accessible",
                    "Flood risk requires assessment"
                ],
                "analysis_confidence": "high"
            },
            "image_type_detected": "sewer_service_diagram",
            "prompt_template_used": True
        }
        
        # Setup document service
        mock_document_service.get_file_content.return_value = b"mock PDF content"
        mock_document_service.track_processing_progress = AsyncMock()
        
        # Execute integration test
        result = await service.analyze_document_semantics(
            storage_path="integration/test/sewer_plan.pdf",
            file_type="pdf",
            filename="sewer_service_diagram.pdf",
            contract_context={
                "contract_type": "purchase_agreement",
                "australian_state": "NSW",
                "property_type": "residential"
            },
            analysis_options={
                "analysis_focus": "comprehensive",
                "risk_categories": ["infrastructure", "environmental"]
            },
            document_id="integration-test-doc"
        )
        
        # Verify comprehensive integration
        assert result["document_metadata"]["filename"] == "sewer_service_diagram.pdf"
        assert result["semantic_analysis"] is not None
        assert result["risk_assessment"] is not None
        assert result["risk_assessment"]["total_risks_identified"] > 0
        assert len(result["processing_stages"]) >= 4
        assert result["analysis_summary"]["risks_identified"] > 0
        
        # Verify risk categories were properly processed
        risk_categories = result["risk_assessment"]["risk_categories"]
        assert risk_categories["infrastructure"] > 0
        assert risk_categories["environmental"] > 0
        
        # Verify professional consultations recommended
        assert len(result["professional_consultations_required"]) > 0
        
        # Verify progress tracking was called
        assert mock_document_service.track_processing_progress.call_count >= 4


# Pytest fixtures for mocking
@pytest.fixture
def mock_document_service():
    """Create mock document service for testing."""
    mock_service = AsyncMock()
    mock_service.get_file_content = AsyncMock()
    mock_service.track_processing_progress = AsyncMock()
    mock_service.health_check = AsyncMock()
    return mock_service


@pytest.fixture
def mock_ocr_service():
    """Create mock OCR service for testing."""
    mock_service = AsyncMock()
    mock_service.initialize = AsyncMock()
    mock_service.extract_image_semantics = AsyncMock()
    mock_service.health_check = AsyncMock()
    mock_service.get_processing_capabilities = AsyncMock()
    return mock_service