"""
Integration tests for PromptManager + Output Parser system
"""

import json
import pytest
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.prompts.manager import PromptManager, PromptManagerConfig
from app.core.prompts.template import PromptTemplate, TemplateMetadata
from app.core.prompts.context import PromptContext, ContextType
from app.core.prompts.parsers import (
    RetryingPydanticOutputParser as PydanticOutputParser,
    create_parser,
)
from app.core.prompts.service_mixin import PromptEnabledService


# Test models
class TestRiskAssessment(BaseModel):
    """Test model for risk assessment"""

    property_id: str = Field(..., description="Property identifier")
    risk_level: str = Field(..., description="Overall risk level")
    risks_identified: List[str] = Field(
        default=[], description="List of identified risks"
    )
    recommendations: List[str] = Field(default=[], description="Recommended actions")
    confidence_score: float = Field(..., description="Analysis confidence score")
    analysis_date: datetime = Field(
        default_factory=datetime.now, description="Date of analysis"
    )


class TestServiceWithParser(PromptEnabledService):
    """Test service that uses output parsers"""

    async def analyze_risk_structured(
        self, document_content: str, analysis_focus: str = "general"
    ) -> dict:
        """Test method that uses structured output parsing"""

        # Create parser
        parser = create_parser(TestRiskAssessment)

        # Create context
        context = self.create_context(
            document_content=document_content, analysis_focus=analysis_focus
        )

        # Render prompt with parser
        prompt = await self.render(
            template_name="risk_analysis_structured",
            context=context,
            output_parser=parser,
        )

        # Simulate AI response (in real usage, this would come from AI model)
        simulated_response = {
            "property_id": "TEST-001",
            "risk_level": "MEDIUM",
            "risks_identified": [
                "Potential boundary encroachment",
                "Sewer line proximity to building area",
            ],
            "recommendations": [
                "Conduct boundary survey",
                "Verify sewer easement requirements",
            ],
            "confidence_score": 0.85,
            "analysis_date": datetime.now().isoformat(),
        }

        ai_response_text = f"""
        Based on the analysis, here are the structured results:
        
        ```json
        {json.dumps(simulated_response, indent=2)}
        ```
        
        This completes the risk assessment analysis.
        """

        # Parse AI response
        parsing_result = await self.parse_ai_response(
            template_name="risk_analysis_structured",
            ai_response=ai_response_text,
            output_parser=parser,
        )

        return {
            "prompt_generated": prompt,
            "parsing_result": parsing_result,
            "structured_data": (
                parsing_result.parsed_data if parsing_result.success else None
            ),
        }


@pytest.fixture
def temp_templates_dir(tmp_path):
    """Create temporary templates directory"""
    templates_dir = tmp_path / "templates" / "analysis"
    templates_dir.mkdir(parents=True)

    # Create test template file
    template_content = """---
name: "risk_analysis_structured"
version: "2.0"
description: "Test structured risk analysis template"
required_variables: ["document_content", "analysis_focus"]
optional_variables: ["service_name"]
tags: ["test", "risk", "structured"]
---

# Risk Analysis - {{ analysis_focus | title }}

Analyze the following document for {{ analysis_focus }} risks:

```
{{ document_content }}
```



Provide a comprehensive analysis following the specified format.
"""

    template_file = templates_dir / "risk_analysis_structured.md"
    template_file.write_text(template_content)

    return tmp_path / "templates"


@pytest.fixture
def prompt_manager(temp_templates_dir):
    """Create PromptManager with test templates"""
    config = PromptManagerConfig(
        templates_dir=temp_templates_dir, cache_enabled=True, validation_enabled=True
    )
    return PromptManager(config)


@pytest.fixture
def test_service(prompt_manager):
    """Create test service"""
    service = TestServiceWithParser()
    service.prompt_manager = prompt_manager
    return service


class TestPromptManagerParserIntegration:
    """Integration tests for PromptManager with parsers"""

    @pytest.mark.asyncio
    async def test_render_with_output_parser(self, prompt_manager):
        """Test rendering prompt with output parser"""
        parser = create_parser(TestRiskAssessment)

        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "document_content": "Test property contract with sewer easement",
                "analysis_focus": "infrastructure",
            },
        )

        rendered = await prompt_manager.render(
            template_name="risk_analysis_structured",
            context=context,
            output_parser=parser,
        )

        # Should contain format instructions
        assert "# Output Format Instructions" in rendered
        assert "TestRiskAssessment" in rendered
        assert "property_id" in rendered
        assert "risk_level" in rendered
        assert "JSON object" in rendered

    @pytest.mark.asyncio
    async def test_parse_ai_response(self, prompt_manager):
        """Test parsing AI response through PromptManager"""
        parser = create_parser(TestRiskAssessment)

        ai_response = """
        Here's my analysis:
        
        ```json
        {
            "property_id": "PROP-123",
            "risk_level": "HIGH",
            "risks_identified": ["Flood zone", "Unstable soil"],
            "recommendations": ["Get flood insurance", "Soil stability report"],
            "confidence_score": 0.92,
            "analysis_date": "2024-01-01T00:00:00Z"
        }
        ```
        """

        result = await prompt_manager.parse_ai_response(
            template_name="risk_analysis_structured",
            ai_response=ai_response,
            output_parser=parser,
        )

        assert result.success == True
        assert result.parsed_data is not None
        assert result.parsed_data.property_id == "PROP-123"
        assert result.parsed_data.risk_level == "HIGH"
        assert len(result.parsed_data.risks_identified) == 2
        assert result.confidence_score > 0.8

    @pytest.mark.asyncio
    async def test_template_with_parser_integration(self, temp_templates_dir):
        """Test PromptTemplate with output parser integration"""
        # Create template metadata
        metadata = TemplateMetadata(
            name="test_template",
            version="1.0",
            description="Test template",
            required_variables=["test_var"],
        )

        # Create template with parser
        parser = create_parser(TestRiskAssessment)
        template = PromptTemplate(
            template_content="Test: {{ test_var }}\n\n{{ format_instructions }}",
            metadata=metadata,
            output_parser=parser,
        )

        # Create context
        context = PromptContext(
            context_type=ContextType.USER, variables={"test_var": "example"}
        )

        # Render
        rendered = template.render(context)

        # Should contain injected format instructions
        assert "Test: example" in rendered
        assert "# Output Format Instructions" in rendered
        assert "TestRiskAssessment" in rendered

        # Test parsing
        test_response = """
        ```json
        {
            "property_id": "TEST-456",
            "risk_level": "LOW",
            "risks_identified": [],
            "recommendations": ["Regular maintenance"],
            "confidence_score": 0.95,
            "analysis_date": "2024-01-01T00:00:00Z"
        }
        ```
        """

        parse_result = template.parse_output(test_response)

        assert parse_result.success == True
        assert parse_result.parsed_data.property_id == "TEST-456"
        assert parse_result.parsed_data.risk_level == "LOW"


class TestServiceMixinIntegration:
    """Integration tests for service mixin with parsers"""

    @pytest.mark.asyncio
    async def test_service_structured_analysis(self, test_service):
        """Test service method using structured output"""
        result = await test_service.analyze_risk_structured(
            document_content="Test contract with infrastructure concerns",
            analysis_focus="infrastructure",
        )

        # Check prompt generation
        assert "prompt_generated" in result
        assert "# Output Format Instructions" in result["prompt_generated"]
        assert "TestRiskAssessment" in result["prompt_generated"]

        # Check parsing result
        assert "parsing_result" in result
        assert result["parsing_result"].success == True

        # Check structured data
        assert "structured_data" in result
        assert result["structured_data"] is not None
        assert result["structured_data"].property_id == "TEST-001"
        assert result["structured_data"].risk_level == "MEDIUM"
        assert len(result["structured_data"].risks_identified) == 2

    @pytest.mark.asyncio
    async def test_render_and_expect_structured(self, test_service):
        """Test convenience method for structured output"""
        context = test_service.create_context(
            document_content="Test document content", analysis_focus="compliance"
        )

        prompt = await test_service.render_and_expect_structured(
            template_name="risk_analysis_structured",
            context=context,
            pydantic_model=TestRiskAssessment,
        )

        # Should contain format instructions automatically
        assert "# Output Format Instructions" in prompt
        assert "TestRiskAssessment" in prompt
        assert "property_id" in prompt
        assert "compliance" in prompt


class TestErrorHandling:
    """Test error handling in parser integration"""

    @pytest.mark.asyncio
    async def test_invalid_ai_response(self, prompt_manager):
        """Test handling of invalid AI response"""
        parser = create_parser(TestRiskAssessment)

        invalid_response = "This is not JSON at all!"

        result = await prompt_manager.parse_ai_response(
            template_name="risk_analysis_structured",
            ai_response=invalid_response,
            output_parser=parser,
        )

        assert result.success == False
        assert len(result.parsing_errors) > 0
        assert result.raw_output == invalid_response

    @pytest.mark.asyncio
    async def test_malformed_json_recovery(self, prompt_manager):
        """Test recovery from malformed JSON"""
        parser = create_parser(TestRiskAssessment)

        malformed_response = """
        ```json
        {
            "property_id": "RECOVER-001",
            "risk_level": "MEDIUM",
            "risks_identified": ["Test risk"],
            "recommendations": ["Test recommendation"],
            "confidence_score": 0.8,
            "analysis_date": "2024-01-01T00:00:00Z",
        }
        ```
        """

        result = await prompt_manager.parse_ai_response(
            template_name="risk_analysis_structured",
            ai_response=malformed_response,
            output_parser=parser,
            use_retry=True,
        )

        # Should recover from trailing comma
        assert result.success == True
        assert result.parsed_data.property_id == "RECOVER-001"


class TestPerformanceIntegration:
    """Performance tests for integrated system"""

    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, test_service):
        """Test end-to-end performance"""
        import time

        start_time = time.time()

        result = await test_service.analyze_risk_structured(
            document_content="Performance test document", analysis_focus="performance"
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete quickly
        assert execution_time < 1.0  # 1 second max
        assert result["parsing_result"].success == True

    @pytest.mark.asyncio
    async def test_format_instruction_caching(self, prompt_manager):
        """Test that format instructions are cached for performance"""
        parser = create_parser(TestRiskAssessment)

        context = PromptContext(
            context_type=ContextType.USER,
            variables={"document_content": "Test content", "analysis_focus": "test"},
        )

        # First render - should generate instructions
        start_time = time.time()
        await prompt_manager.render(
            template_name="risk_analysis_structured",
            context=context,
            output_parser=parser,
        )
        first_time = time.time() - start_time

        # Second render - should use cached instructions
        start_time = time.time()
        await prompt_manager.render(
            template_name="risk_analysis_structured",
            context=context,
            output_parser=parser,
        )
        second_time = time.time() - start_time

        # Second render should be faster (cached instructions)
        assert second_time <= first_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
