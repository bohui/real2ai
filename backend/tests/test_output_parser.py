"""
Comprehensive test suite for output parser functionality
"""

import json
import pytest
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.prompts.output_parser import (
    BaseOutputParser,
    PydanticOutputParser,
    StreamingOutputParser,
    ParsingResult,
    OutputFormat,
    create_parser
)


# Test Pydantic Models
class SimpleTestModel(BaseModel):
    """Simple test model for basic parsing tests"""
    name: str = Field(..., description="Name of the item")
    value: int = Field(..., description="Numeric value")
    active: bool = Field(default=True, description="Whether item is active")


class ComplexTestModel(BaseModel):
    """Complex test model with nested structures"""
    id: str = Field(..., description="Unique identifier")
    metadata: dict = Field(default={}, description="Additional metadata")
    tags: List[str] = Field(default=[], description="List of tags")
    nested_data: Optional['NestedModel'] = Field(None, description="Nested data structure")
    timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class NestedModel(BaseModel):
    """Nested model for complex structures"""
    category: str = Field(..., description="Category name")
    score: float = Field(..., description="Score value")
    details: Optional[dict] = Field(None, description="Additional details")


# Update forward references
ComplexTestModel.model_rebuild()


class TestPydanticOutputParser:
    """Test suite for PydanticOutputParser"""
    
    def test_init(self):
        """Test parser initialization"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        assert parser.pydantic_model == SimpleTestModel
        assert parser.output_format == OutputFormat.JSON
        assert parser.strict_mode == True
        assert parser.retry_on_failure == True
        assert parser.max_retries == 2
    
    def test_get_format_instructions(self):
        """Test format instruction generation"""
        parser = PydanticOutputParser(SimpleTestModel)
        instructions = parser.get_format_instructions()
        
        assert "SimpleTestModel" in instructions
        assert "JSON object" in instructions
        assert "name" in instructions
        assert "value" in instructions
        assert "active" in instructions
        assert "REQUIRED" in instructions
        assert "OPTIONAL" in instructions
    
    def test_format_instructions_caching(self):
        """Test that format instructions are cached"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        # First call should generate and cache
        instructions1 = parser.get_format_instructions()
        
        # Second call should return cached version
        instructions2 = parser.get_format_instructions()
        
        assert instructions1 == instructions2
        assert parser._cached_instructions is not None
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        valid_json = json.dumps({
            "name": "test_item",
            "value": 42,
            "active": True
        })
        
        result = parser.parse(valid_json)
        
        assert result.success == True
        assert result.parsed_data is not None
        assert result.parsed_data.name == "test_item"
        assert result.parsed_data.value == 42
        assert result.parsed_data.active == True
        assert result.confidence_score > 0.8
        assert len(result.parsing_errors) == 0
        assert len(result.validation_errors) == 0
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        markdown_json = '''
        Here's the analysis result:
        
        ```json
        {
            "name": "markdown_test",
            "value": 123,
            "active": false
        }
        ```
        
        This completes the analysis.
        '''
        
        result = parser.parse(markdown_json)
        
        assert result.success == True
        assert result.parsed_data.name == "markdown_test"
        assert result.parsed_data.value == 123
        assert result.parsed_data.active == False
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        invalid_json = '{"name": "test", "value": 42, "active": true'  # Missing closing brace
        
        result = parser.parse(invalid_json)
        
        assert result.success == False
        assert result.parsed_data is None
        assert len(result.parsing_errors) > 0
        assert "JSON" in str(result.parsing_errors)
    
    def test_parse_missing_required_field(self):
        """Test parsing JSON missing required fields"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        incomplete_json = json.dumps({
            "value": 42,
            "active": True
            # Missing required "name" field
        })
        
        result = parser.parse(incomplete_json)
        
        assert result.success == False
        assert result.parsed_data is None
        assert len(result.validation_errors) > 0
        assert any("name" in error for error in result.validation_errors)
    
    def test_parse_with_retry(self):
        """Test parsing with retry mechanism"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        # JSON with common formatting issues
        messy_json = '''
        ```json
        {
            "name": "retry_test",
            "value": 99,
            "active": true,
        }
        ```
        '''
        
        result = parser.parse_with_retry(messy_json)
        
        assert result.success == True
        assert result.parsed_data.name == "retry_test"
    
    def test_non_strict_mode(self):
        """Test parsing in non-strict mode"""
        parser = PydanticOutputParser(SimpleTestModel, strict_mode=False)
        
        # Missing required field
        incomplete_json = json.dumps({
            "value": 42,
            "active": True
        })
        
        result = parser.parse(incomplete_json)
        
        # In non-strict mode, should attempt partial parsing
        # Result depends on implementation of _attempt_partial_parsing
        assert result.raw_output == incomplete_json
    
    def test_confidence_score_calculation(self):
        """Test confidence score calculation"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        # Complete data should have high confidence
        complete_json = json.dumps({
            "name": "confidence_test",
            "value": 100,
            "active": True
        })
        
        result = parser.parse(complete_json)
        assert result.success == True
        assert result.confidence_score >= 0.8
        
        # Partial data should have lower confidence
        # (This would require non-strict mode and successful partial parsing)
    
    def test_complex_model_parsing(self):
        """Test parsing complex nested model"""
        parser = PydanticOutputParser(ComplexTestModel)
        
        complex_json = json.dumps({
            "id": "complex_001",
            "metadata": {"source": "test", "priority": "high"},
            "tags": ["important", "test", "complex"],
            "nested_data": {
                "category": "testing",
                "score": 95.5,
                "details": {"accuracy": 0.95, "speed": "fast"}
            },
            "timestamp": "2024-01-01T00:00:00Z"
        })
        
        result = parser.parse(complex_json)
        
        assert result.success == True
        assert result.parsed_data.id == "complex_001"
        assert len(result.parsed_data.tags) == 3
        assert result.parsed_data.nested_data is not None
        assert result.parsed_data.nested_data.category == "testing"
        assert result.parsed_data.nested_data.score == 95.5


class TestStreamingOutputParser:
    """Test suite for StreamingOutputParser"""
    
    def test_init(self):
        """Test streaming parser initialization"""
        parser = StreamingOutputParser(SimpleTestModel)
        
        assert parser.pydantic_model == SimpleTestModel
        assert parser._buffer == ""
        assert len(parser._partial_results) == 0
    
    def test_parse_chunk(self):
        """Test parsing incremental chunks"""
        parser = StreamingOutputParser(SimpleTestModel)
        
        # Send chunks of JSON
        chunk1 = '{'
        chunk2 = '"name": "streaming_test",'
        chunk3 = '"value": 50,'
        chunk4 = '"active": true'
        chunk5 = '}'
        
        # First chunks shouldn't parse successfully
        result1 = parser.parse_chunk(chunk1)
        assert result1 is None
        
        result2 = parser.parse_chunk(chunk2)
        assert result2 is None
        
        result3 = parser.parse_chunk(chunk3)
        assert result3 is None
        
        result4 = parser.parse_chunk(chunk4)
        assert result4 is None
        
        # Final chunk should complete the JSON
        result5 = parser.parse_chunk(chunk5)
        assert result5 is not None
        assert result5.success == True
        assert result5.parsed_data.name == "streaming_test"
    
    def test_finalize(self):
        """Test finalizing streaming parse"""
        parser = StreamingOutputParser(SimpleTestModel)
        
        # Add complete JSON to buffer
        json_data = '{"name": "finalize_test", "value": 75, "active": false}'
        parser.parse_chunk(json_data)
        
        result = parser.finalize()
        
        assert result.success == True
        assert result.parsed_data.name == "finalize_test"
    
    def test_reset(self):
        """Test resetting parser state"""
        parser = StreamingOutputParser(SimpleTestModel)
        
        # Add some data
        parser.parse_chunk('{"name": "reset_test"}')
        
        assert parser._buffer != ""
        
        # Reset
        parser.reset()
        
        assert parser._buffer == ""
        assert len(parser._partial_results) == 0


class TestParsingResult:
    """Test suite for ParsingResult"""
    
    def test_init_default(self):
        """Test ParsingResult initialization with defaults"""
        result = ParsingResult(success=True)
        
        assert result.success == True
        assert result.parsed_data is None
        assert result.raw_output is None
        assert result.validation_errors == []
        assert result.parsing_errors == []
        assert result.confidence_score == 0.0
    
    def test_init_with_data(self):
        """Test ParsingResult initialization with data"""
        result = ParsingResult(
            success=True,
            parsed_data={"test": "data"},
            raw_output="raw text",
            confidence_score=0.95
        )
        
        assert result.success == True
        assert result.parsed_data == {"test": "data"}
        assert result.raw_output == "raw text"
        assert result.confidence_score == 0.95


class TestFactoryFunction:
    """Test suite for factory functions"""
    
    def test_create_parser_default(self):
        """Test creating parser with defaults"""
        parser = create_parser(SimpleTestModel)
        
        assert isinstance(parser, PydanticOutputParser)
        assert parser.pydantic_model == SimpleTestModel
        assert parser.output_format == OutputFormat.JSON
    
    def test_create_parser_streaming(self):
        """Test creating streaming parser"""
        parser = create_parser(SimpleTestModel, streaming=True)
        
        assert isinstance(parser, StreamingOutputParser)
        assert parser.pydantic_model == SimpleTestModel
    
    def test_create_parser_yaml(self):
        """Test creating parser with YAML format"""
        parser = create_parser(SimpleTestModel, output_format=OutputFormat.YAML)
        
        assert isinstance(parser, PydanticOutputParser)
        assert parser.output_format == OutputFormat.YAML


class TestRealWorldScenarios:
    """Test suite for real-world parsing scenarios"""
    
    def test_ai_response_with_explanation(self):
        """Test parsing AI response with explanation text"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        ai_response = '''
        Based on the analysis, here are the results:
        
        The data shows clear patterns that indicate the following structure:
        
        ```json
        {
            "name": "analysis_result",
            "value": 87,
            "active": true
        }
        ```
        
        This structure represents the key findings from the analysis.
        '''
        
        result = parser.parse(ai_response)
        
        assert result.success == True
        assert result.parsed_data.name == "analysis_result"
        assert result.parsed_data.value == 87
    
    def test_malformed_but_recoverable_json(self):
        """Test parsing malformed but recoverable JSON"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        malformed_json = '''
        {
            "name": "recoverable_test",
            "value": 42,
            "active": true,
        }
        '''
        
        result = parser.parse_with_retry(malformed_json)
        
        # Should recover from trailing comma
        assert result.success == True
        assert result.parsed_data.name == "recoverable_test"
    
    def test_multiple_json_blocks(self):
        """Test parsing response with multiple JSON blocks"""
        parser = PydanticOutputParser(SimpleTestModel)
        
        multi_json_response = '''
        First, let me show an example:
        ```json
        {"example": "data"}
        ```
        
        And here's the actual result:
        ```json
        {
            "name": "multi_json_test",
            "value": 999,
            "active": false
        }
        ```
        '''
        
        result = parser.parse(multi_json_response)
        
        # Should find and parse the valid JSON for our model
        assert result.success == True
        assert result.parsed_data.name == "multi_json_test"


# Integration test fixtures
@pytest.fixture
def simple_parser():
    """Fixture for simple parser"""
    return PydanticOutputParser(SimpleTestModel)


@pytest.fixture
def complex_parser():
    """Fixture for complex parser"""
    return PydanticOutputParser(ComplexTestModel)


@pytest.fixture
def streaming_parser():
    """Fixture for streaming parser"""
    return StreamingOutputParser(SimpleTestModel)


# Performance tests
class TestPerformance:
    """Performance tests for output parsers"""
    
    def test_format_instruction_generation_performance(self, simple_parser):
        """Test format instruction generation performance"""
        import time
        
        start_time = time.time()
        instructions = simple_parser.get_format_instructions()
        end_time = time.time()
        
        assert len(instructions) > 0
        assert (end_time - start_time) < 0.1  # Should be very fast
    
    def test_parsing_performance(self, simple_parser):
        """Test parsing performance"""
        import time
        
        json_data = json.dumps({
            "name": "performance_test",
            "value": 123,
            "active": True
        })
        
        start_time = time.time()
        result = simple_parser.parse(json_data)
        end_time = time.time()
        
        assert result.success == True
        assert (end_time - start_time) < 0.01  # Should be very fast


if __name__ == "__main__":
    pytest.main([__file__, "-v"])