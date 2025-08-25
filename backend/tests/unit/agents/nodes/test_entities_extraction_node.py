import asyncio
import pytest


@pytest.mark.asyncio
async def test_model_selection_uses_metadata_primary_and_fallbacks(mocker):
    from app.agents.nodes.entities_extraction_node import EntitiesExtractionNode

    # Mock workflow with configs (no magic numbers hard-coded)
    class MockWorkflow:
        extraction_config = {"max_retries": 3, "min_confidence": 0.8}
        use_llm_config = {}
        enable_validation = True
        enable_quality_checks = True
        enable_fallbacks = True
        prompt_manager = mocker.Mock()
        structured_parsers = {"entities_extraction": mocker.Mock()}

    node = EntitiesExtractionNode(MockWorkflow())

    # Prepare composition result with metadata primary/fallbacks
    node.prompt_manager.render_composed = mocker.AsyncMock(
        return_value={
            "user_prompt": "USER_PROMPT",
            "system_prompt": "SYSTEM_PROMPT",
            "metadata": {
                "primary_model": "primary-model",
                "fallback_models": ["fb-1", "fb-2"],
                "model_compatibility": ["primary-model", "fb-1", "fb-2"],
            },
        }
    )

    # Mock llm_service generate_content to fail primary, succeed on first fallback
    class MockParsing:
        def __init__(self, success, parsed_data=None):
            self.success = success
            self.parsed_data = parsed_data

    class Parsed:
        metadata = type("M", (), {"overall_confidence": 0.85})()
        parties = ["A", "B"]
        dates = ["today"]
        financial_amounts = ["$1"]
        property_details = ["addr"]
        legal_references = []

        def model_dump(self):
            return {"metadata": {"overall_confidence": 0.85}}

    llm_service = mocker.Mock()
    llm_service.generate_content = mocker.AsyncMock(
        side_effect=[
            MockParsing(False, None),  # primary fails
            MockParsing(True, Parsed()),  # first fallback succeeds
        ]
    )

    async def fake_get_llm_service():
        return llm_service

    mocker.patch(
        "app.agents.nodes.llm_base.LLMNode._get_llm_service",
        side_effect=fake_get_llm_service,
    )

    # Minimal state
    state = {
        "progress": {"current_step": 0, "total_steps": 10},
        "document_metadata": {"full_text": "some text"},
    }

    result = await node.execute(state)

    # Ensure state update marked as complete and confidence set
    assert result["progress"]["current_step"] == 1
    assert result["progress"]["percentage"] == 10
    assert result["confidence_scores"]["entities_extraction"] == 0.85


@pytest.mark.asyncio
async def test_short_circuit_skips_when_cached(mocker):
    from app.agents.nodes.entities_extraction_node import EntitiesExtractionNode

    class MockWorkflow:
        extraction_config = {"max_retries": 2, "min_confidence": 0.75}
        use_llm_config = {}
        enable_validation = True
        enable_quality_checks = True
        enable_fallbacks = True
        prompt_manager = mocker.Mock()
        structured_parsers = {"entities_extraction": mocker.Mock()}

    node = EntitiesExtractionNode(MockWorkflow())

    # Mock repository returning existing entity
    repo_mock = mocker.AsyncMock()
    repo_mock.get_contract_by_content_hash = mocker.AsyncMock(
        return_value=type(
            "C",
            (),
            {
                "extracted_entity": {"metadata": {"overall_confidence": 0.9}},
            },
        )()
    )
    mocker.patch(
        "app.agents.nodes.entities_extraction_node.ContractsRepository",
        return_value=repo_mock,
    )

    state = {
        "content_hash": "abc",
        "progress": {"current_step": 0, "total_steps": 10},
    }

    result = await node.execute(state)
    assert result.get("entities_extraction") is not None
    assert result["confidence_scores"]["entities_extraction"] == 0.9
    # Step should be marked as skipped
    assert result["progress"]["current_step"] == 1
