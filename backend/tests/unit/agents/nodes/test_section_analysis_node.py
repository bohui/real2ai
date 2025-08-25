"""
Unit tests for Section Analysis Node (Step 2 Integration)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.nodes.section_analysis_node import SectionAnalysisNode
from app.agents.states.contract_state import RealEstateAgentState


class TestSectionAnalysisNode:
    """Test suite for Section Analysis Node"""

    @pytest.fixture
    def mock_workflow(self):
        """Mock workflow for testing"""
        workflow = MagicMock()
        workflow.config = {"extraction_config": {}, "use_llm_config": {}}
        return workflow

    @pytest.fixture
    def section_node(self, mock_workflow):
        """Create section analysis node for testing"""
        return SectionAnalysisNode(mock_workflow)

    @pytest.fixture
    def sample_state(self):
        """Sample state for testing"""
        return RealEstateAgentState(
            user_id="test-user",
            session_id="test-session",
            agent_version="1.0",
            contract_id="test-contract",
            document_data={"document_id": "test-doc"},
            document_metadata={"full_text": "Sample contract text"},
            parsing_status="complete",
            contract_terms=None,
            risk_assessment=None,
            compliance_check=None,
            recommendations=[],
            property_data=None,
            market_analysis=None,
            financial_analysis=None,
            user_preferences={},
            australian_state="NSW",
            user_type="general",
            contract_type="purchase_agreement",
            document_type="contract",
            current_step=["section_analysis"],
            error_state=None,
            confidence_scores={},
            processing_time=None,
            progress=None,
            notify_progress=None,
            entities_extraction={"property": {"address": "123 Test St"}},
            step2_analysis_result=None,
            analysis_results={},
            report_data=None,
            final_recommendations=[],
        )

    def test_node_initialization(self, section_node):
        """Test node initialization"""
        assert section_node is not None
        assert section_node.step2_workflow is not None
        assert section_node.node_name == "section_analysis"

    @pytest.mark.asyncio
    async def test_execute_with_missing_contract_text(self, section_node, sample_state):
        """Test execution with missing contract text"""
        # Remove contract text
        sample_state["document_metadata"] = {}

        # Mock the workflow execute to not be called
        section_node.step2_workflow.execute = AsyncMock()

        result = await section_node.execute(sample_state)

        # Should handle error gracefully
        assert result is not None
        assert "error_state" in result

        # Workflow should not be called with missing text
        section_node.step2_workflow.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_missing_entities(self, section_node, sample_state):
        """Test execution with missing entity results"""
        # Remove entities
        sample_state["entities_extraction"] = None

        section_node.step2_workflow.execute = AsyncMock()

        result = await section_node.execute(sample_state)

        # Should handle error gracefully
        assert result is not None
        assert "error_state" in result

        # Workflow should not be called with missing entities
        section_node.step2_workflow.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_successful_analysis(self, section_node, sample_state):
        """Test successful Step 2 analysis execution"""

        # Mock successful workflow execution
        mock_step2_result = {
            "success": True,
            "timestamp": "2024-01-15T10:30:00Z",
            "total_duration_seconds": 120.5,
            "section_results": {
                "parties_property": {
                    "analyzer": "parties_property",
                    "status": "completed",
                    "confidence_score": 0.9,
                    "overall_risk_level": "low",
                }
            },
            "cross_section_validation": {"status": "passed"},
            "workflow_metadata": {
                "phases_completed": {"phase1": True, "phase2": True, "phase3": True},
                "processing_errors": [],
                "total_risk_flags": [],
            },
        }

        section_node.step2_workflow.execute = AsyncMock(return_value=mock_step2_result)

        result = await section_node.execute(sample_state)

        # Verify execution
        section_node.step2_workflow.execute.assert_called_once()

        # Check result structure
        assert result is not None
        assert result.get("step2_analysis_result") == mock_step2_result
        assert "analysis_results" in result
        assert "step2" in result["analysis_results"]
        assert "contract_terms" in result  # Backward compatibility
        assert result["confidence_scores"]["step2_analysis"] > 0

    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self, section_node, sample_state):
        """Test handling of Step 2 workflow failure"""

        # Mock workflow failure
        mock_step2_result = {
            "success": False,
            "error": "Mock workflow failure",
            "error_type": "TestError",
            "partial_results": {},
        }

        section_node.step2_workflow.execute = AsyncMock(return_value=mock_step2_result)

        result = await section_node.execute(sample_state)

        # Should handle workflow failure gracefully
        assert result is not None
        assert "error_state" in result

    @pytest.mark.asyncio
    async def test_backward_compatibility_contract_terms(
        self, section_node, sample_state
    ):
        """Test backward compatibility with contract_terms structure"""

        mock_step2_result = {
            "success": True,
            "section_results": {
                "parties_property": {"findings": {"property_address": "123 Test St"}},
                "financial_terms": {"findings": {"purchase_price": 800000}},
            },
            "workflow_metadata": {
                "phases_completed": {"phase1": True, "phase2": True, "phase3": True}
            },
        }

        section_node.step2_workflow.execute = AsyncMock(return_value=mock_step2_result)

        result = await section_node.execute(sample_state)

        # Check backward compatibility
        assert "contract_terms" in result
        contract_terms = result["contract_terms"]
        assert contract_terms["extraction_method"] == "step2_section_analysis"
        assert "step2_metadata" in contract_terms

    def test_calculate_overall_confidence(self, section_node):
        """Test overall confidence calculation"""

        # Test successful completion
        step2_results = {
            "success": True,
            "section_results": {"parties_property": {"status": "completed"}},
            "workflow_metadata": {
                "phases_completed": {"phase1": True, "phase2": True, "phase3": True},
                "processing_errors": [],
            },
        }

        confidence = section_node._calculate_overall_confidence(step2_results)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be relatively high for successful completion

        # Test with errors
        step2_results_with_errors = {
            "success": True,
            "section_results": {"parties_property": {"status": "completed"}},
            "workflow_metadata": {
                "phases_completed": {"phase1": True, "phase2": False, "phase3": False},
                "processing_errors": ["Error 1", "Error 2"],
            },
        }

        confidence_with_errors = section_node._calculate_overall_confidence(
            step2_results_with_errors
        )
        assert confidence_with_errors < confidence  # Should be lower with errors

    @pytest.mark.asyncio
    async def test_get_contract_text_from_metadata(self, section_node, sample_state):
        """Test getting contract text from document metadata"""

        contract_text = await section_node._get_contract_text(sample_state)
        assert contract_text == "Sample contract text"

    @pytest.mark.asyncio
    async def test_get_contract_text_missing(self, section_node, sample_state):
        """Test handling missing contract text"""

        # Remove text from metadata
        sample_state["document_metadata"] = {}
        sample_state["document_data"] = {}

        contract_text = await section_node._get_contract_text(sample_state)
        assert contract_text is None

    def test_get_entities_result(self, section_node, sample_state):
        """Test getting entities extraction result"""

        entities = section_node._get_entities_result(sample_state)
        assert entities == {"property": {"address": "123 Test St"}}

    def test_prepare_additional_context(self, section_node, sample_state):
        """Test preparing additional context for workflow"""

        sample_state["legal_requirements"] = {"NSW": {"disclosure": True}}

        context = section_node._prepare_additional_context(sample_state)

        assert "legal_requirements_matrix" in context
        assert "execution_timestamp" in context
        assert context["legal_requirements_matrix"] == {"NSW": {"disclosure": True}}
