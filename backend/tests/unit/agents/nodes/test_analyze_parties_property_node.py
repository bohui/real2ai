"""
Unit tests for PartiesPropertyNode

Tests the refactored functionality that delegates short-circuiting and persistence
to the base ContractLLMNode while maintaining Step 2 state compatibility.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC

from app.agents.nodes.step2_section_analysis.analyze_parties_property_node import (
    PartiesPropertyNode,
)
from app.prompts.schema.step2.parties_property_schema import (
    RiskLevel,
)


class TestPartiesPropertyNode:
    """Test suite for PartiesPropertyNode"""

    @pytest.fixture
    def mock_workflow(self):
        """Mock workflow for testing"""
        workflow = MagicMock()
        workflow.extraction_config = {}
        workflow.use_llm_config = {}
        workflow.enable_validation = True
        workflow.enable_quality_checks = True
        workflow.enable_fallbacks = True
        workflow.prompt_manager = MagicMock()
        workflow.structured_parsers = {}
        return workflow

    @pytest.fixture
    def node(self, mock_workflow):
        """Create PartiesPropertyNode instance for testing"""
        return PartiesPropertyNode(workflow=mock_workflow, progress_range=(2, 12))

    @pytest.fixture
    def sample_state(self):
        """Sample Step 2 analysis state"""
        return {
            "extracted_entity": {
                "content_hash": "test_hash_123",
                "metadata": {
                    "state": "NSW",
                    "contract_type": "purchase_agreement",
                    "use_category": "residential",
                    "property_condition": "existing",
                    "purchase_method": "private_treaty",
                },
                "document": {
                    "content_hash": "fallback_hash_456",
                },
            },
            "australian_state": "NSW",
            "contract_type": "purchase_agreement",
            "use_category": "residential",
            "property_condition": "existing",
            "purchase_method": "private_treaty",
            "legal_requirements_matrix": {"NSW": {"purchase_agreement": {}}},
            "section_seeds": {
                "snippets": {
                    "parties_property": ["clause_1", "clause_2"],
                }
            },
        }

    @pytest.fixture
    def mock_parsed_result(self):
        """Mock parsed analysis result"""
        return MagicMock(
            parties=[
                MagicMock(
                    name="John Smith",
                    role="vendor",
                    verification_status="verified",
                    concerns=[],
                    additional_info={},
                )
            ],
            property_identification=MagicMock(
                street_address="123 Test Street, Sydney NSW 2000",
                lot_number="1",
                plan_number="DP123456",
                title_reference="Vol 1234 Fol 567",
                property_type="residential_house",
                completeness_status="complete",
                verification_issues=[],
            ),
            inclusions_exclusions=MagicMock(
                included_items=["fixtures", "fittings"],
                excluded_items=["furniture"],
                analysis_summary="Standard inclusions/exclusions",
            ),
            risk_indicators=[],
            overall_risk_level=RiskLevel.LOW,
            confidence_score=0.85,
            evidence_references=["clause_1", "clause_2"],
            seed_references=["clause_1", "clause_2"],
            retrieval_expanded=False,
            retrieved_snippets_count=0,
            analysis_notes="Comprehensive analysis completed",
            analyzer_version="1.0",
            analysis_timestamp=datetime.now(UTC).isoformat(),
        )

    def test_node_initialization(self, node):
        """Test node initialization with correct attributes"""
        assert node.node_name == "analyze_parties_property"
        assert node.contract_attribute == "parties_property"
        assert node.state_field == "parties_property_result"
        assert node.progress_range == (2, 12)

    def test_ensure_content_hash_on_state_with_existing_hash(self, node, sample_state):
        """Test content_hash normalization when content_hash already exists"""
        sample_state["content_hash"] = "existing_hash"
        original_hash = sample_state["content_hash"]

        node._ensure_content_hash_on_state(sample_state)

        assert sample_state["content_hash"] == original_hash

    def test_ensure_content_hash_on_state_with_existing_hmac(self, node, sample_state):
        """Test content_hash normalization when content_hmac exists"""
        sample_state["content_hmac"] = "existing_hmac"

        node._ensure_content_hash_on_state(sample_state)

        # Should not override existing content_hmac
        assert sample_state["content_hmac"] == "existing_hmac"
        assert "content_hash" not in sample_state

    def test_ensure_content_hash_on_state_from_entities_extraction(
        self, node, sample_state
    ):
        """Test content_hash normalization from extracted_entity.content_hash"""
        # Remove any existing content_hash
        sample_state.pop("content_hash", None)
        sample_state.pop("content_hmac", None)

        node._ensure_content_hash_on_state(sample_state)

        assert sample_state["content_hash"] == "test_hash_123"

    def test_ensure_content_hash_on_state_from_document_fallback(
        self, node, sample_state
    ):
        """Test content_hash normalization from extracted_entity.document.content_hash fallback"""
        # Remove extracted_entity.content_hash but keep document.content_hash
        sample_state["extracted_entity"].pop("content_hash")
        sample_state.pop("content_hash", None)
        sample_state.pop("content_hmac", None)

        node._ensure_content_hash_on_state(sample_state)

        assert sample_state["content_hash"] == "fallback_hash_456"

    def test_ensure_content_hash_on_state_no_hash_available(self, node, sample_state):
        """Test content_hash normalization when no hash is available"""
        # Remove all hash sources
        sample_state["extracted_entity"].pop("content_hash")
        sample_state["extracted_entity"]["document"].pop("content_hash")
        sample_state.pop("content_hash", None)
        sample_state.pop("content_hmac", None)

        node._ensure_content_hash_on_state(sample_state)

        # Should not add content_hash if none available
        assert "content_hash" not in sample_state

    def test_ensure_content_hash_on_state_exception_handling(self, node, sample_state):
        """Test content_hash normalization handles exceptions gracefully"""
        # Make state access raise an exception
        sample_state["extracted_entity"

        # Should not raise exception
        node._ensure_content_hash_on_state(sample_state)

    @pytest.mark.asyncio
    async def test_short_circuit_check_delegates_to_base(self, node, sample_state):
        """Test that short-circuit check delegates to base class"""
        with patch.object(node, "_ensure_content_hash_on_state") as mock_ensure:
            # Test that content_hash normalization is called
            result = await node._short_circuit_check(sample_state)

            mock_ensure.assert_called_once_with(sample_state)
            # The actual result depends on the base class implementation
            # We're testing that our wrapper method works correctly

    @pytest.mark.asyncio
    async def test_persist_results_delegates_to_base(
        self, node, sample_state, mock_parsed_result
    ):
        """Test that persist_results delegates to base class"""
        with patch.object(node, "_ensure_content_hash_on_state") as mock_ensure:
            # Test that content_hash normalization is called
            await node._persist_results(sample_state, mock_parsed_result)

            mock_ensure.assert_called_once_with(sample_state)
            # The actual persistence depends on the base class implementation
            # We're testing that our wrapper method works correctly

    @pytest.mark.asyncio
    async def test_build_context_and_parser(self, node, sample_state):
        """Test context and parser building"""
        with (
            patch("app.core.prompts.PromptContext") as mock_context_class,
            patch("app.core.prompts.parsers.create_parser") as mock_create_parser,
        ):

            mock_context = MagicMock()
            mock_context_class.return_value = mock_context
            mock_parser = MagicMock()
            mock_create_parser.return_value = mock_parser

            context, parser, prompt_name = await node._build_context_and_parser(
                sample_state
            )

            assert context == mock_context
            assert parser == mock_parser
            assert prompt_name == "step2_parties_property"

            # Verify context was created with correct parameters
            mock_context_class.assert_called_once()
            call_args = mock_context_class.call_args
            # Check the actual enum value, not the string representation
            assert call_args[1]["context_type"].value == "analysis"
            variables = call_args[1]["variables"]
            assert variables["australian_state"] == "NSW"
            assert variables["contract_type"] == "purchase_agreement"
            assert variables["use_category"] == "residential"
            assert variables["property_condition"] == "existing"
            assert variables["purchase_method"] == "private_treaty"
            assert variables["seed_snippets"] == ["clause_1", "clause_2"]

    def test_coerce_to_model_with_model_instance(self, node):
        """Test model coercion with existing model instance"""
        # Create a real instance of the model class
        from app.prompts.schema.step2.parties_property_schema import (
            PartiesPropertyAnalysisResult,
        )

        real_model = MagicMock(spec=PartiesPropertyAnalysisResult)
        result = node._coerce_to_model(real_model)
        assert result == real_model

    def test_coerce_to_model_with_dict_data(self, node):
        """Test model coercion with dictionary data"""
        # Create a mock object with model_validate method
        mock_data = MagicMock()
        mock_data.model_validate.return_value = "validated_model"

        result = node._coerce_to_model(mock_data)

        assert result == "validated_model"
        mock_data.model_validate.assert_called_once()

    def test_coerce_to_model_with_invalid_data(self, node):
        """Test model coercion with invalid data"""
        result = node._coerce_to_model("invalid_data")
        assert result is None

    def test_evaluate_quality_with_valid_result(
        self, node, mock_parsed_result, sample_state
    ):
        """Test quality evaluation with valid result"""
        quality = node._evaluate_quality(mock_parsed_result, sample_state)

        assert quality["ok"] is True
        assert quality["confidence_score"] == 0.85
        assert quality["has_parties"] is True
        assert quality["has_property_identification"] is True

    def test_evaluate_quality_with_low_confidence_but_coverage(
        self, node, sample_state
    ):
        """Test quality evaluation with low confidence but good coverage"""
        mock_result = MagicMock()
        mock_result.confidence_score = 0.6
        mock_result.parties = ["party1"]
        mock_result.property_identification = "property_info"

        quality = node._evaluate_quality(mock_result, sample_state)

        assert quality["ok"] is True
        assert quality["confidence_score"] == 0.6
        assert quality["has_parties"] is True
        assert quality["has_property_identification"] is True

    def test_evaluate_quality_with_high_confidence(self, node, sample_state):
        """Test quality evaluation with high confidence"""
        mock_result = MagicMock()
        mock_result.confidence_score = 0.8
        mock_result.parties = []
        mock_result.property_identification = None

        quality = node._evaluate_quality(mock_result, sample_state)

        assert quality["ok"] is True
        assert quality["confidence_score"] == 0.8
        assert quality["has_parties"] is False
        assert quality["has_property_identification"] is False

    def test_evaluate_quality_with_none_result(self, node, sample_state):
        """Test quality evaluation with None result"""
        quality = node._evaluate_quality(None, sample_state)
        assert quality["ok"] is False

    def test_evaluate_quality_with_exception(self, node, sample_state):
        """Test quality evaluation handles exceptions gracefully"""
        mock_result = MagicMock()
        # Make getattr raise an exception by making the attribute access fail
        mock_result.parties = MagicMock(side_effect=Exception("test error"))

        quality = node._evaluate_quality(mock_result, sample_state)
        assert quality["ok"] is False

    @pytest.mark.asyncio
    async def test_update_state_success(self, node, sample_state, mock_parsed_result):
        """Test successful state update"""
        with patch.object(node, "emit_progress") as mock_emit:
            result = await node._update_state_success(
                sample_state, mock_parsed_result, {"ok": True}
            )

            # Verify state was updated with the parsed result
            # The state should contain the result of model_dump() if available, otherwise the original object
            expected_value = (
                mock_parsed_result.model_dump()
                if hasattr(mock_parsed_result, "model_dump")
                else mock_parsed_result
            )
            assert sample_state["parties_property_result"] == expected_value

            # Verify progress was emitted
            mock_emit.assert_called_once_with(
                sample_state, 12, "Parties and property analysis completed"
            )

            # Verify return value
            assert result == {"parties_property_result": expected_value}

    @pytest.mark.asyncio
    async def test_update_state_success_with_model_dump(self, node, sample_state):
        """Test state update with model that has model_dump method"""
        mock_parsed = MagicMock()
        mock_parsed.model_dump.return_value = {"dumped": "data"}

        result = await node._update_state_success(
            sample_state, mock_parsed, {"ok": True}
        )

        assert sample_state["parties_property_result"] == {"dumped": "data"}
        assert result == {"parties_property_result": {"dumped": "data"}}
        mock_parsed.model_dump.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_state_success_without_model_dump(self, node, sample_state):
        """Test state update with object that doesn't have model_dump method"""
        mock_parsed = {"raw": "data"}

        result = await node._update_state_success(
            sample_state, mock_parsed, {"ok": True}
        )

        assert sample_state["parties_property_result"] == {"raw": "data"}
        assert result == {"parties_property_result": {"raw": "data"}}
