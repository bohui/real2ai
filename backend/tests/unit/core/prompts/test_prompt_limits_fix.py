"""
Integration test for the original prompt length issue fix
Tests the specific scenario that was failing: rendered prompt exceeding 65536 chars
"""

import pytest
from app.core.prompts.validator import PromptValidator, ValidationSeverity
from app.core.prompts.manager import PromptManager, PromptManagerConfig
from app.core.prompts.context import PromptContext, ContextType
from app.core.config import get_settings
from pathlib import Path
import tempfile


class TestPromptLengthIssueFix:
    """Test the specific fix for the original prompt validation error"""
    
    def test_original_error_scenario_fixed(self):
        """Test that the original 157738 char error is now properly handled"""
        # Get actual app settings
        settings = get_settings()
        
        # Create validator with real config
        validator = PromptValidator(config=settings)
        
        # Create a prompt that matches the original error size (157738 chars)
        large_prompt = "A" * 157738
        
        # The original error is now fixed because the limit is configurable
        # and set higher than 157738
        result = validator.validate_rendered_prompt(large_prompt)
        
        if settings.max_prompt_length_chars > 157738:
            # With current config (242144), this should pass
            assert result.is_valid
            assert not result.has_errors
        else:
            # If config was set lower, should fail with proper error message
            assert not result.is_valid
            assert result.has_errors
            
            error_issues = [issue for issue in result.issues 
                           if issue.severity == ValidationSeverity.ERROR 
                           and issue.code == "PROMPT_TOO_LONG"]
            
            assert len(error_issues) == 1
            error_message = error_issues[0].message
            
            # Should mention both the actual length and the configured limit
            assert "157738" in error_message
            assert str(settings.max_prompt_length_chars) in error_message
    
    def test_prompt_under_new_limit_passes(self):
        """Test that prompts under the new limit pass validation"""
        settings = get_settings()
        validator = PromptValidator(config=settings)
        
        # Create prompt just under the limit
        prompt_under_limit = "A" * (settings.max_prompt_length_chars - 1000)
        
        result = validator.validate_rendered_prompt(prompt_under_limit)
        
        assert result.is_valid
        assert not result.has_errors
    
    def test_prompt_just_over_limit_fails(self):
        """Test that prompts just over the limit fail with proper error"""
        settings = get_settings()
        validator = PromptValidator(config=settings)
        
        # Create prompt just over the limit
        prompt_over_limit = "A" * (settings.max_prompt_length_chars + 100)
        
        result = validator.validate_rendered_prompt(prompt_over_limit)
        
        assert not result.is_valid
        assert result.has_errors
        
        # Check error message is informative
        error_issues = [issue for issue in result.issues 
                       if issue.code == "PROMPT_TOO_LONG"]
        assert len(error_issues) == 1
        
        error_message = error_issues[0].message
        assert str(settings.max_prompt_length_chars + 100) in error_message
        assert str(settings.max_prompt_length_chars) in error_message
    
    def test_prompt_manager_uses_configured_limits(self):
        """Test that PromptManager passes the configured limits to validator"""
        # Create a temporary templates directory
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir) / "templates"
            templates_dir.mkdir()
            
            # Create PromptManager
            config = PromptManagerConfig(
                templates_dir=templates_dir,
                validation_enabled=True
            )
            
            manager = PromptManager(config)
            
            # Verify validator has correct limits
            assert manager.validator is not None
            
            settings = get_settings()
            assert manager.validator.max_prompt_length == settings.max_prompt_length_chars
            assert manager.validator.max_template_length == settings.max_template_length_chars
    
    def test_configured_limits_are_reasonable(self):
        """Test that the configured limits are reasonable for the use case"""
        settings = get_settings()
        
        # Check that prompt limit is larger than template limit
        assert settings.max_prompt_length_chars >= settings.max_template_length_chars
        
        # Check that limits are reasonable for LLM use
        assert settings.max_prompt_length_chars >= 50000  # At least 50K chars
        assert settings.max_template_length_chars >= 10000  # At least 10K chars
        
        # Check that the configured limit handles the original error case
        # The fix ensures the limit is configurable and can be set appropriately
        assert settings.max_prompt_length_chars > 100000  # Should be large enough for real use


@pytest.mark.integration
class TestOriginalErrorScenario:
    """Integration test for the exact error that was reported"""
    
    def test_contract_terms_extraction_scenario(self):
        """Simulate the contract terms extraction scenario that was failing"""
        # This test simulates the scenario from the original error:
        # PromptValidationError: Rendered prompt validation failed: 
        # Prompt exceeds maximum length (157738 chars)
        
        settings = get_settings()
        validator = PromptValidator(config=settings)
        
        # Simulate a large contract document that could generate 157738 chars
        large_contract_text = "Contract clause text. " * 7000  # ~154K chars
        
        # Create context similar to contract_terms_extraction
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "full_text": large_contract_text,
                "extraction_method": "llm",
                "contract_type": "purchase_agreement",
                "australian_state": "NSW"
            }
        )
        
        # Create a template that might expand to be very large
        template_content = """
You are analyzing a contract. Here is the full text:

{{full_text}}

Please extract all contract terms systematically:
1. Parties involved
2. Property details
3. Financial terms
4. Settlement conditions
5. Special conditions

State: {{australian_state}}
Contract Type: {{contract_type}}
Method: {{extraction_method}}

Provide a comprehensive analysis...
"""
        
        # Render the template (simulating what PromptManager would do)
        rendered = template_content.replace("{{full_text}}", large_contract_text)
        rendered = rendered.replace("{{australian_state}}", "NSW")
        rendered = rendered.replace("{{contract_type}}", "purchase_agreement")
        rendered = rendered.replace("{{extraction_method}}", "llm")
        
        # The rendered prompt will be very large
        assert len(rendered) > 150000
        
        # Validate it
        result = validator.validate_rendered_prompt(rendered)
        
        # This should now be handled properly with our configuration
        if len(rendered) > settings.max_prompt_length_chars:
            # Should fail but with proper error message
            assert not result.is_valid
            assert result.has_errors
            
            error_messages = [issue.message for issue in result.issues 
                            if issue.code == "PROMPT_TOO_LONG"]
            assert len(error_messages) > 0
            
            # Error should include actual length and configured limit
            error_msg = error_messages[0]
            assert str(len(rendered)) in error_msg
            assert str(settings.max_prompt_length_chars) in error_msg
        else:
            # If under limit, should pass
            assert result.is_valid