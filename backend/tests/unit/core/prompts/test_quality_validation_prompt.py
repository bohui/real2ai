"""
Test for document quality validation prompt rendering without input parameters.
Uses prompt manager output as test data to validate prompt generation.
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

from app.core.prompts.manager import get_prompt_manager
from app.core.prompts.context import PromptContext
from app.models.contract_state import AustralianState, ContractType


@pytest.fixture
def prompt_manager():
    """Get prompt manager instance for testing"""
    return get_prompt_manager()


@pytest.fixture
def sample_document_context():
    """Sample context for document quality validation prompt"""
    return PromptContext(
        document_type="property_contract",
        australian_state=AustralianState.NSW,
        extraction_method="ocr",
        document_text="This is a sample contract text for quality validation testing. " * 50,
        document_metadata={
            "file_size": 1024000,
            "page_count": 3,
            "extraction_confidence": 0.85,
            "processing_time_ms": 2500
        },
        analysis_timestamp=datetime.now(timezone.utc).isoformat()
    )


@pytest.mark.asyncio
async def test_quality_validation_prompt_rendering(prompt_manager, sample_document_context):
    """Test that quality validation prompt renders correctly and contains expected content"""
    
    # Render the quality validation prompt
    rendered_prompt = await prompt_manager.render(
        template_name="validation/document_quality_validation",
        context=sample_document_context,
        service_name="test_service"
    )
    
    # Validate that prompt was rendered
    assert rendered_prompt is not None
    assert len(rendered_prompt) > 0
    
    # Check that key sections are present
    assert "Document Quality Validation" in rendered_prompt
    assert "Australian State" in rendered_prompt
    assert "NSW" in rendered_prompt
    assert "property_contract" in rendered_prompt
    
    # Verify document text is included (truncated to 2000 chars)
    assert "This is a sample contract text" in rendered_prompt
    
    # Check that JSON response format is specified
    assert "text_quality_score" in rendered_prompt
    assert "overall_quality_score" in rendered_prompt
    assert "issues_identified" in rendered_prompt
    
    # Verify response format requirements
    assert "You must respond with a valid JSON object" in rendered_prompt
    assert "Return ONLY the JSON object" in rendered_prompt


@pytest.mark.asyncio
async def test_quality_validation_prompt_token_estimation():
    """Test prompt size estimation for quality validation template"""
    
    prompt_manager = get_prompt_manager()
    
    # Create test context with large document text
    large_context = PromptContext(
        document_type="property_contract",
        australian_state=AustralianState.NSW,
        extraction_method="ocr",
        document_text="Large contract text content. " * 1000,  # ~30KB of text
        document_metadata={
            "file_size": 5000000,
            "page_count": 15,
            "extraction_confidence": 0.75
        },
        analysis_timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    # Render prompt
    rendered_prompt = await prompt_manager.render(
        template_name="validation/document_quality_validation",
        context=large_context,
        service_name="test_service"
    )
    
    # Estimate token count (rough estimation: 1 token ≈ 4 characters)
    char_count = len(rendered_prompt)
    estimated_tokens = char_count // 4
    
    # Document should be truncated to 2000 chars max in template
    # Plus template content, should be well under limits
    assert char_count < 10000, f"Rendered prompt too large: {char_count} chars"
    assert estimated_tokens < 3000, f"Estimated tokens too high: {estimated_tokens}"
    
    # Verify text was properly truncated
    assert rendered_prompt.count("Large contract text content.") <= 80


@pytest.mark.asyncio
async def test_quality_validation_prompt_metadata_rendering():
    """Test that document metadata is properly rendered in the prompt"""
    
    prompt_manager = get_prompt_manager()
    
    # Create context with complex metadata
    context = PromptContext(
        document_type="lease_agreement",
        australian_state=AustralianState.VIC,
        extraction_method="hybrid",
        document_text="Lease agreement text",
        document_metadata={
            "source_format": "PDF",
            "image_quality": "high",
            "pages_processed": 5,
            "extraction_algorithms": ["tesseract", "google_vision"],
            "confidence_scores": [0.95, 0.87, 0.92, 0.88, 0.91]
        },
        analysis_timestamp="2025-01-15T10:30:00Z"
    )
    
    rendered_prompt = await prompt_manager.render(
        template_name="validation/document_quality_validation",
        context=context,
        service_name="test_service"
    )
    
    # Check metadata is properly formatted as JSON
    assert '"source_format": "PDF"' in rendered_prompt
    assert '"image_quality": "high"' in rendered_prompt
    assert '"pages_processed": 5' in rendered_prompt
    assert "lease_agreement" in rendered_prompt
    assert "VIC" in rendered_prompt
    assert "hybrid" in rendered_prompt


@pytest.mark.asyncio
async def test_quality_validation_prompt_without_optional_fields():
    """Test prompt rendering with minimal context (only required fields)"""
    
    prompt_manager = get_prompt_manager()
    
    # Minimal context with defaults
    minimal_context = PromptContext(
        document_text="Minimal contract text for testing"
    )
    
    rendered_prompt = await prompt_manager.render(
        template_name="validation/document_quality_validation", 
        context=minimal_context,
        service_name="test_service"
    )
    
    # Should use template defaults
    assert "property_contract" in rendered_prompt  # default document_type
    assert "ocr" in rendered_prompt  # default extraction_method
    assert "Minimal contract text for testing" in rendered_prompt
    
    # Should still contain all required JSON fields
    assert "overall_quality_score" in rendered_prompt
    assert "suitability_assessment" in rendered_prompt


@pytest.mark.asyncio
async def test_prompt_manager_caching_behavior():
    """Test that prompt manager properly caches rendered prompts"""
    
    prompt_manager = get_prompt_manager()
    
    context = PromptContext(
        document_type="property_contract",
        australian_state=AustralianState.NSW,
        document_text="Test text for caching",
        analysis_timestamp="2025-01-15T10:30:00Z"
    )
    
    # First render
    start_time = datetime.now()
    rendered_1 = await prompt_manager.render(
        template_name="validation/document_quality_validation",
        context=context,
        service_name="test_service"
    )
    first_duration = (datetime.now() - start_time).total_seconds()
    
    # Second render (should use cache)
    start_time = datetime.now()
    rendered_2 = await prompt_manager.render(
        template_name="validation/document_quality_validation",
        context=context,
        service_name="test_service"
    )
    second_duration = (datetime.now() - start_time).total_seconds()
    
    # Results should be identical
    assert rendered_1 == rendered_2
    
    # Second render should be faster (cached)
    assert second_duration <= first_duration