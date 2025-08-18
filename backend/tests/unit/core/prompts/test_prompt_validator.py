"""
Unit tests for PromptValidator with configurable limits
"""

import pytest
from unittest.mock import Mock, patch
from app.core.prompts.validator import PromptValidator, ValidationSeverity
from app.core.prompts.template import PromptTemplate, TemplateMetadata
from app.core.prompts.context import PromptContext, ContextType


class MockConfig:
    """Mock configuration for testing"""
    def __init__(self):
        self.max_prompt_length_chars = 65536
        self.max_template_length_chars = 50000
        self.prompt_long_variable_value_threshold_chars = 10000
        self.prompt_quality_sweet_spot_min_chars = 500
        self.prompt_quality_sweet_spot_max_chars = 10000


@pytest.fixture
def mock_config():
    """Provide mock configuration"""
    return MockConfig()


@pytest.fixture
def validator(mock_config):
    """Create validator with mock config"""
    return PromptValidator(config=mock_config)


@pytest.fixture
def sample_template():
    """Create a sample template for testing"""
    metadata = TemplateMetadata(
        name="test_template",
        description="Test template for validation",
        version="1.0.0",
        required_variables=["test_var"],
    )
    
    return PromptTemplate(
        template_content="Test template content with {{test_var}}",
        metadata=metadata
    )


class TestPromptValidatorInitialization:
    """Test validator initialization with configuration"""
    
    def test_validator_uses_config_limits(self, mock_config):
        """Test that validator uses configured limits"""
        validator = PromptValidator(config=mock_config)
        
        assert validator.max_prompt_length == 65536
        assert validator.max_template_length == 50000
        assert validator.long_variable_value_threshold == 10000
        assert validator.prompt_quality_sweet_spot_min == 500
        assert validator.prompt_quality_sweet_spot_max == 10000
    
    @patch('app.core.config.get_settings')
    def test_validator_gets_default_config(self, mock_get_settings):
        """Test that validator gets default config when none provided"""
        mock_get_settings.return_value = MockConfig()
        
        validator = PromptValidator()
        
        mock_get_settings.assert_called_once()
        assert validator.max_prompt_length == 65536


class TestPromptLengthValidation:
    """Test prompt length validation with configurable limits"""
    
    def test_rendered_prompt_within_limits(self, validator):
        """Test validation passes for prompt within limits"""
        # Create a prompt within limits (< 65536 chars)
        prompt = "A" * 1000
        
        result = validator.validate_rendered_prompt(prompt)
        
        assert result.is_valid
        assert not result.has_errors
        assert result.metrics["prompt_length"] == 1000
    
    def test_rendered_prompt_exceeds_limits(self, validator):
        """Test validation fails for prompt exceeding limits"""
        # Create a prompt exceeding limits (> 65536 chars)
        prompt = "A" * 70000
        
        result = validator.validate_rendered_prompt(prompt)
        
        assert not result.is_valid
        assert result.has_errors
        
        # Check for the specific error
        error_issues = [issue for issue in result.issues 
                       if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) > 0
        
        prompt_too_long_errors = [issue for issue in error_issues 
                                 if issue.code == "PROMPT_TOO_LONG"]
        assert len(prompt_too_long_errors) == 1
        
        error_message = prompt_too_long_errors[0].message
        assert "70000" in error_message
        assert "65536" in error_message
    
    def test_template_length_validation(self, validator):
        """Test template content length validation"""
        # Create metadata with required fields
        metadata = TemplateMetadata(
            name="long_template",
            description="Template with very long content",
            version="1.0.0",
            required_variables=[]
        )
        
        # Create template with content exceeding template limit
        long_content = "A" * 60000  # Exceeds 50000 char limit
        template = PromptTemplate(template_content=long_content, metadata=metadata)
        
        result = validator.validate_template(template)
        
        assert not result.is_valid
        assert result.has_errors
        
        # Check for content too long error
        content_errors = [issue for issue in result.issues 
                         if issue.code == "CONTENT_TOO_LONG"]
        assert len(content_errors) == 1


class TestVariableValueValidation:
    """Test validation of variable values"""
    
    def test_long_variable_value_warning(self, validator):
        """Test warning for overly long variable values"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "short_var": "short value",
                "long_var": "A" * 15000  # Exceeds 10000 char threshold
            }
        )
        
        result = validator.validate_context(context, ["short_var", "long_var"])
        
        # Should be valid but have warnings
        assert result.is_valid
        assert result.has_warnings
        
        # Check for long variable warning
        warnings = [issue for issue in result.issues 
                   if issue.severity == ValidationSeverity.WARNING]
        long_var_warnings = [w for w in warnings 
                            if w.code == "LONG_VARIABLE_VALUE"]
        assert len(long_var_warnings) == 1
        assert "long_var" in long_var_warnings[0].message


class TestQualitySweetSpot:
    """Test prompt quality sweet spot scoring"""
    
    def test_prompt_in_sweet_spot_gets_bonus(self, validator):
        """Test that prompts in quality sweet spot get score bonus"""
        # Create prompt in sweet spot (500-10000 chars)
        prompt = "A" * 5000
        
        result = validator.validate_rendered_prompt(prompt)
        
        # Should get bonus for being in sweet spot
        assert result.score > 0.9  # Base score + bonus


class TestModelCompatibility:
    """Test model-specific validation"""
    
    def test_gemini_model_token_validation(self, validator):
        """Test validation against Gemini model limits"""
        # Create prompt that exceeds Gemini token limit
        # Gemini-2.5-flash has max_tokens: 65535 in validator
        prompt = "A" * 300000  # Way over token limit (estimated ~75K tokens)
        
        result = validator.validate_rendered_prompt(prompt, model="gemini-2.5-flash")
        
        assert not result.is_valid
        assert result.has_errors
        
        # Check for model-specific error
        model_errors = [issue for issue in result.issues 
                       if issue.code == "EXCEEDS_MODEL_LIMIT"]
        assert len(model_errors) == 1


class TestConfigurationIntegration:
    """Test integration with different configurations"""
    
    def test_custom_limits_configuration(self):
        """Test validator with custom limit configuration"""
        # Create custom config with different limits
        custom_config = MockConfig()
        custom_config.max_prompt_length_chars = 30000
        custom_config.max_template_length_chars = 20000
        
        validator = PromptValidator(config=custom_config)
        
        # Test with prompt exceeding custom limit but within default
        prompt = "A" * 40000
        result = validator.validate_rendered_prompt(prompt)
        
        assert not result.is_valid
        assert result.has_errors
        
        # Should reference custom limit in error message
        error_message = result.issues[0].message
        assert "30000" in error_message
    
    def test_zero_limits_edge_case(self):
        """Test validator behavior with zero limits"""
        custom_config = MockConfig()
        custom_config.max_prompt_length_chars = 0
        
        validator = PromptValidator(config=custom_config)
        
        # Any non-empty prompt should fail
        result = validator.validate_rendered_prompt("A")
        
        assert not result.is_valid
        assert result.has_errors


@pytest.mark.asyncio
class TestPromptManagerIntegration:
    """Test integration with PromptManager"""
    
    @patch('app.core.config.get_settings')
    def test_prompt_manager_passes_config_to_validator(self, mock_get_settings):
        """Test that PromptManager passes app config to validator"""
        from app.core.prompts.manager import PromptManager, PromptManagerConfig
        from pathlib import Path
        
        # Setup mock
        mock_get_settings.return_value = MockConfig()
        
        # Create prompt manager config
        config = PromptManagerConfig(
            templates_dir=Path("/tmp/templates"),
            validation_enabled=True
        )
        
        # Create manager (should pass config to validator)
        manager = PromptManager(config)
        
        # Validator should have been created with app config
        assert manager.validator is not None
        assert manager.validator.max_prompt_length == 65536
        mock_get_settings.assert_called_once()