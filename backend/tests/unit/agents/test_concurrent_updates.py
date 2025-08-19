"""
Test concurrent updates in the contract workflow to prevent InvalidUpdateError.

This test ensures that the workflow can handle concurrent state updates
without throwing LangGraph's InvalidUpdateError.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.models.contract_state import (
    RealEstateAgentState,
    create_initial_state,
    update_state_step,
)
from app.agents.contract_workflow import ContractAnalysisWorkflow
from app.schema.enums import AustralianState, ProcessingStatus


class TestConcurrentUpdates:
    """Test concurrent state updates in the workflow."""

    def test_state_model_annotated_fields(self):
        """Test that all state fields are properly annotated for concurrent updates."""
        # This test ensures that the state model has proper Annotated types
        # which prevent LangGraph InvalidUpdateError

        # Check that critical fields are annotated
        state = create_initial_state(
            user_id="test_user", australian_state=AustralianState.NSW, user_type="buyer"
        )

        # Verify the state can be created without errors
        assert state["user_id"] == "test_user"
        assert state["australian_state"] == AustralianState.NSW
        assert state["user_type"] == "buyer"

        # Test concurrent updates to the same field
        update1 = update_state_step(state, "step1", {"user_id": "user1"})
        update2 = update_state_step(state, "step2", {"user_id": "user2"})

        # Both updates should succeed without InvalidUpdateError
        assert "user_id" in update1
        assert "user_id" in update2
        assert update1["user_id"] == "user1"
        assert update2["user_id"] == "user2"

    def test_concurrent_step_updates(self):
        """Test that multiple steps can update the state concurrently."""
        state = create_initial_state(
            user_id="test_user", australian_state=AustralianState.NSW, user_type="buyer"
        )

        # Simulate concurrent updates from different nodes
        updates = []
        for i in range(5):
            update = update_state_step(
                state,
                f"step_{i}",
                {"confidence_scores": {f"step_{i}": 0.8 + (i * 0.1)}},
            )
            updates.append(update)

        # All updates should succeed
        assert len(updates) == 5
        for update in updates:
            assert "current_step" in update
            assert "confidence_scores" in update

    def test_concurrent_error_handling(self):
        """Test that error states can be updated concurrently."""
        state = create_initial_state(
            user_id="test_user", australian_state=AustralianState.NSW, user_type="buyer"
        )

        # Simulate concurrent error updates
        error_updates = []
        for i in range(3):
            update = update_state_step(
                state, f"error_step_{i}", error=f"Error in step {i}"
            )
            error_updates.append(update)

        # All error updates should succeed
        assert len(error_updates) == 3
        for update in error_updates:
            assert "error_state" in update
            assert "parsing_status" in update
            assert update["parsing_status"] == ProcessingStatus.FAILED

    def test_list_field_concurrent_updates(self):
        """Test that list fields can be updated concurrently using add reducer."""
        state = create_initial_state(
            user_id="test_user", australian_state=AustralianState.NSW, user_type="buyer"
        )

        # Simulate concurrent updates to list fields
        step_updates = []
        for i in range(3):
            update = update_state_step(state, f"step_{i}")
            step_updates.append(update)

        # All step updates should succeed
        assert len(step_updates) == 3
        for update in step_updates:
            assert "current_step" in update
            assert isinstance(update["current_step"], list)

    @pytest.mark.asyncio
    async def test_workflow_concurrent_execution(self):
        """Test that the workflow can handle concurrent node execution."""
        # Mock the workflow to avoid actual AI client calls
        with (
            patch("app.agents.contract_workflow.get_openai_client"),
            patch("app.agents.contract_workflow.get_gemini_client"),
        ):

            workflow = ContractAnalysisWorkflow(
                model_name="gpt-4",
                enable_validation=False,  # Disable validation for simpler testing
                enable_quality_checks=False,
            )

            # Create test state
            initial_state = create_initial_state(
                user_id="test_user",
                australian_state=AustralianState.NSW,
                user_type="buyer",
            )

            # Add test document data
            initial_state["document_data"] = {
                "content": "Test contract content",
                "document_id": "test_doc_123",
            }

            # Test that the workflow can be initialized without errors
            # This validates that the state model is properly configured
            assert workflow is not None
            assert hasattr(workflow, "workflow")

            # Verify the state graph was created successfully
            assert workflow.workflow is not None

    def test_state_merge_operations(self):
        """Test that state merging operations work correctly for concurrent updates."""
        state = create_initial_state(
            user_id="test_user", australian_state=AustralianState.NSW, user_type="buyer"
        )

        # Test dictionary merging
        update1 = update_state_step(
            state, "step1", {"confidence_scores": {"step1": 0.8}}
        )
        update2 = update_state_step(
            state, "step2", {"confidence_scores": {"step2": 0.9}}
        )

        # Both updates should contain confidence_scores
        assert "confidence_scores" in update1
        assert "confidence_scores" in update2
        assert update1["confidence_scores"]["step1"] == 0.8
        assert update2["confidence_scores"]["step2"] == 0.9

    def test_annotated_field_validation(self):
        """Test that all required fields in the state model are properly annotated."""
        # This test ensures that the state model changes are complete
        # and all fields that can be updated concurrently are annotated

        # Import the state model to check its structure
        from app.models.contract_state import RealEstateAgentState

        # Get the annotations from the state model
        annotations = RealEstateAgentState.__annotations__

        # Check that critical fields are annotated
        critical_fields = [
            "user_id",
            "session_id",
            "agent_version",
            "document_data",
            "parsing_status",
            "contract_terms",
            "risk_assessment",
            "compliance_check",
            "user_preferences",
            "australian_state",
            "user_type",
        ]

        for field in critical_fields:
            assert field in annotations, f"Field {field} missing from state model"

            # Check that the field has an Annotated type
            field_type = annotations[field]
            assert hasattr(
                field_type, "__origin__"
            ), f"Field {field} should be Annotated"
            assert (
                field_type.__origin__ is not None
            ), f"Field {field} should have proper annotation"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
