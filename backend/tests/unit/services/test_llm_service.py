"""
Unit tests for LLMService.generate_content focusing on the parsing path
that calls `output_parser.parse_with_retry(response)`.
"""

import json
import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, Field

from app.services.ai.llm_service import LLMService
from app.core.prompts.output_parser import PydanticOutputParser


class _TestModel(BaseModel):
    """Simple model for parser tests."""

    name: str = Field(..., description="Name value")


class _StubOpenAIClient:
    """Minimal stub client exposing an async generate_content compatible with LLMService."""

    def __init__(self, responses: list[str]):
        # Responses to return on successive calls
        self._responses = list(responses)
        self.calls: int = 0

    async def generate_content(self, prompt: str, **kwargs: Any) -> str:
        self.calls += 1
        if not self._responses:
            # If exhausted, keep returning the last entry
            return "{}"
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_generate_content_with_parser_success_single_attempt():
    """Should parse successfully on first attempt and call client once."""

    # Arrange
    valid_response = json.dumps({"name": "alice"})
    client = _StubOpenAIClient([valid_response])

    service = LLMService()
    service._openai_client = client  # Inject stub

    parser = PydanticOutputParser(_TestModel)

    # Act
    result = await service.generate_content(
        prompt="Test prompt",
        model="gpt-4",  # Routes to OpenAI branch
        output_parser=parser,
        parse_generation_max_attempts=1,  # 1 retry -> total attempts = 2 (but success on first)
    )

    # Assert
    assert hasattr(result, "success") and result.success is True
    assert result.parsed_data is not None
    assert result.parsed_data.name == "alice"
    assert client.calls == 1


@pytest.mark.asyncio
async def test_generate_content_with_parser_parsing_fails_then_regenerates_success():
    """First generation is unparseable, second is valid -> should call client twice and succeed."""

    invalid_response = "not valid json"
    valid_response = json.dumps({"name": "bob"})
    client = _StubOpenAIClient([invalid_response, valid_response])

    service = LLMService()
    service._openai_client = client

    parser = PydanticOutputParser(_TestModel)

    result = await service.generate_content(
        prompt="Test prompt",
        model="gpt-4",
        output_parser=parser,
        parse_generation_max_attempts=1,  # total attempts = 2
    )

    assert hasattr(result, "success") and result.success is True
    assert result.parsed_data.name == "bob"
    assert client.calls == 2


@pytest.mark.asyncio
async def test_generate_content_with_parser_all_attempts_fail_returns_last_result():
    """All generations produce invalid output -> should return failed ParsingResult after retries."""

    invalid_response = "still not json"
    client = _StubOpenAIClient([invalid_response, invalid_response, invalid_response])

    service = LLMService()
    service._openai_client = client

    parser = PydanticOutputParser(_TestModel)

    # Set retries so total attempts = parse_generation_max_attempts + 1
    result = await service.generate_content(
        prompt="Test prompt",
        model="gpt-4",
        output_parser=parser,
        parse_generation_max_attempts=2,  # total attempts = 3
    )

    assert hasattr(result, "success") and result.success is False
    assert result.parsed_data is None
    assert client.calls == 3
