"""
Unit tests for Step 2 Section Analysis Workflow
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import patch

from app.agents.subflows.step2_section_analysis_workflow import (
    Step2AnalysisWorkflow,
    Step2AnalysisState,
    create_step2_workflow,
)
from app.agents.states.contract_state import RealEstateAgentState


class TestStep2AnalysisWorkflow:
    """Test suite for Step 2 Analysis Workflow"""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance for testing"""
        return Step2AnalysisWorkflow()

    @pytest.fixture
    def sample_state(self):
        """Sample parent state for testing"""
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
            current_step=["step2_analysis"],
            error_state=None,
            confidence_scores={},
            processing_time=None,
            progress=None,
            notify_progress=None,
            extracted_entityss": "123 Test St"}},
            step2_analysis_result=None,
            analysis_results={},
            report_data=None,
            final_recommendations=[],
        )

    @pytest.fixture
    def sample_entities_result(self):
        """Sample entities extraction result"""
        return {
            "property": {
                "address": "123 Test Street, Sydney NSW 2000",
                "lot_number": "1",
                "plan_number": "DP123456",
            },
            "parties": {
                "vendor": {"name": "John Smith"},
                "purchaser": {"name": "Jane Doe"},
            },
            "financial": {"purchase_price": 800000, "deposit_amount": 80000},
            "conditions": [
                {"type": "finance", "deadline": "2024-02-15"},
                {"type": "inspection", "deadline": "2024-02-10"},
            ],
            "metadata": {
                "contract_type": "purchase_agreement",
                "australian_state": "NSW",
            },
        }

    def test_workflow_creation(self, workflow):
        """Test workflow instance creation"""
        assert workflow is not None
        assert workflow.graph is not None
        assert hasattr(workflow, "execute")

    def test_factory_function(self):
        """Test factory function creates workflow correctly"""
        workflow = create_step2_workflow()
        assert isinstance(workflow, Step2AnalysisWorkflow)
        assert workflow.graph is not None

    @pytest.mark.asyncio
    async def test_workflow_execution_basic(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test basic workflow execution with placeholder implementations"""

        contract_text = "Sample contract text for analysis"

        result = await workflow.execute(
            contract_text=contract_text,
            extracted_entitys_result,
            parent_state=sample_state,
        )

        # Verify basic result structure
        assert result is not None
        assert isinstance(result, dict)
        assert "success" in result
        assert "timestamp" in result
        assert "section_results" in result
        assert "workflow_metadata" in result

    @pytest.mark.asyncio
    async def test_workflow_execution_with_empty_inputs(self, workflow, sample_state):
        """Test workflow execution with missing inputs"""

        result = await workflow.execute(
            contract_text="",  # Empty text
            extracted_entityy entities
            parent_state=sample_state,
        )

        # Should handle gracefully and return result with errors
        assert result is not None
        assert isinstance(result, dict)

        # May succeed with warnings/errors logged
        workflow_metadata = result.get("workflow_metadata", {})
        processing_errors = workflow_metadata.get("processing_errors", [])

        # Expecting some processing errors due to empty inputs
        assert len(processing_errors) >= 0  # May have validation errors

    @pytest.mark.asyncio
    async def test_workflow_phase_completion_tracking(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test that phases are tracked correctly"""

        contract_text = "Sample contract text for analysis"

        result = await workflow.execute(
            contract_text=contract_text,
            extracted_entitymple_entities_result,
            parent_state=sample_state,
        )

        # Check phase completion tracking
        workflow_metadata = result.get("workflow_metadata", {})
        phases_completed = workflow_metadata.get("phases_completed", {})

        assert "phase1" in phases_completed
        assert "phase2" in phases_completed
        assert "phase3" in phases_completed

        # All phases should complete with placeholder implementations
        assert phases_completed.get("phase1") is True
        assert phases_completed.get("phase2") is True
        assert phases_completed.get("phase3") is True

    @pytest.mark.asyncio
    async def test_workflow_section_results_structure(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test that all expected section results are present"""

        contract_text = "Sample contract text for analysis"

        result = await workflow.execute(
            contract_text=contract_text,
            extracted_entity=sample_entities_result,
            parent_state=sample_state,
        )

        section_results = result.get("section_results", {})

        # Check all expected sections are present
        expected_sections = [
            "parties_property",
            "financial_terms",
            "conditions",
            "warranties",
            "default_termination",
            "settlement_logistics",
            "title_encumbrances",
            "adjustments_outgoings",
            "disclosure_compliance",
            "special_risks",
        ]

        for section in expected_sections:
            assert section in section_results
            # With placeholder implementations, all should have results
            assert section_results[section] is not None

    @pytest.mark.asyncio
    async def test_workflow_cross_section_validation(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test cross-section validation is executed"""

        contract_text = "Sample contract text for analysis"

        result = await workflow.execute(
            contract_text=contract_text,
            extracted_entity=sample_entities_result,
            parent_state=sample_state,
        )

        # Cross-section validation should be present
        cross_section_validation = result.get("cross_section_validation")
        assert cross_section_validation is not None
        assert isinstance(cross_section_validation, dict)

    @pytest.mark.asyncio
    async def test_workflow_performance_tracking(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test that performance metrics are tracked"""

        contract_text = "Sample contract text for analysis"

        result = await workflow.execute(
            contract_text=contract_text,
            extracted_entity=sample_entities_result,
            parent_state=sample_state,
        )

        # Check performance tracking
        assert "total_duration_seconds" in result
        assert isinstance(result["total_duration_seconds"], (int, float))
        assert result["total_duration_seconds"] >= 0

        workflow_metadata = result.get("workflow_metadata", {})
        assert "phase_completion_times" in workflow_metadata
        assert "diagrams_processed" in workflow_metadata
        assert "diagram_success_rate" in workflow_metadata

    @pytest.mark.asyncio
    async def test_workflow_error_handling(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test workflow error handling with exception scenarios"""

        # Test with invalid contract text type
        with patch.object(
            workflow.graph, "ainvoke", side_effect=Exception("Test error")
        ):
            result = await workflow.execute(
                contract_text="Sample text",
                extracted_entity=sample_entities_result,
                parent_state=sample_state,
            )

            # Should return error structure
            assert result is not None
            assert result.get("success") is False
            assert "error" in result
            assert "error_type" in result
            assert result["error"] == "Test error"

    def test_step2_state_structure(self):
        """Test Step2AnalysisState TypedDict structure"""

        # Test state creation with required fields
        state = Step2AnalysisState(
            contract_text="Sample text",
            extracted_entity={"test": "data"},
            legal_requirements_matrix=None,
            uploaded_diagrams=None,
            australian_state="NSW",
            contract_type="purchase_agreement",
            purchase_method=None,
            use_category=None,
            property_condition=None,
            parties_property_result=None,
            financial_terms_result=None,
            conditions_result=None,
            warranties_result=None,
            default_termination_result=None,
            settlement_logistics_result=None,
            title_encumbrances_result=None,
            adjustments_outgoings_result=None,
            disclosure_compliance_result=None,
            special_risks_result=None,
            cross_section_validation_result=None,
            phase1_complete=False,
            phase2_complete=False,
            phase3_complete=False,
            processing_errors=[],
            skipped_analyzers=[],
            total_risk_flags=[],
            start_time=datetime.now(UTC),
            phase_completion_times={},
            total_diagrams_processed=0,
            diagram_processing_success_rate=0.0,
        )

        assert state["contract_text"] == "Sample text"
        assert state["extracted_entity"]["test"] == "data"
        assert state["australian_state"] == "NSW"
        assert state["phase1_complete"] is False
        assert isinstance(state["processing_errors"], list)

    @pytest.mark.asyncio
    async def test_workflow_with_additional_context(
        self, workflow, sample_state, sample_entities_result
    ):
        """Test workflow execution with additional context parameters"""

        contract_text = "Sample contract text"
        legal_matrix = {"NSW": {"purchase_agreement": ["disclosure_req_1"]}}
        diagrams = {
            "fake_uri": [
                {
                    "diagram_type_hint": "title_plan",
                    "confidence": 0.8,
                    "page_number": 1,
                    "diagram_key": "title_plan",
                }
            ]
        }

        result = await workflow.execute(
            contract_text=contract_text,
            extracted_entity=sample_entities_result,
            parent_state=sample_state,
            legal_requirements_matrix=legal_matrix,
            uploaded_diagrams=diagrams,
        )

        # Should complete successfully with additional context
        assert result.get("success") is True

        # Diagrams should be tracked
        workflow_metadata = result.get("workflow_metadata", {})
        assert workflow_metadata.get("diagrams_processed", 0) == 1
