"""
Unit tests for PromptContext with type validation
"""

from unittest.mock import patch
from app.core.prompts.context import (
    PromptContext,
    ContextType,
    ContextBuilder,
    ContextPresets,
)


class TestPromptContextInitialization:
    """Test PromptContext initialization and type validation"""

    def test_valid_initialization(self):
        """Test normal initialization with valid types"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables={"key": "value"},
            metadata={"source": "test"},
            ocr_processing={"doc_id": "123"},
            focus_areas=["quality", "performance"],
        )

        assert context.context_type == ContextType.USER
        assert context.variables == {"key": "value"}
        assert context.metadata == {"source": "test"}
        assert context.ocr_processing == {"doc_id": "123"}
        assert context.focus_areas == ["quality", "performance"]

    def test_default_initialization(self):
        """Test initialization with defaults"""
        context = PromptContext(context_type=ContextType.SYSTEM)

        assert context.context_type == ContextType.SYSTEM
        assert context.variables == {}
        assert context.metadata == {}
        assert context.ocr_processing == {}
        assert context.focus_areas == []

    @patch("app.core.prompts.context.logger")
    def test_variables_type_correction(self, mock_logger):
        """Test that non-dict variables get converted to empty dict"""
        context = PromptContext(
            context_type=ContextType.USER, variables="invalid_string"  # Wrong type
        )

        assert context.variables == {}
        mock_logger.warning.assert_called_once()
        assert "variables expected dict" in mock_logger.warning.call_args[0][0]

    @patch("app.core.prompts.context.logger")
    def test_metadata_type_correction(self, mock_logger):
        """Test that non-dict metadata gets converted to empty dict"""
        context = PromptContext(
            context_type=ContextType.USER,
            metadata=["list", "instead", "of", "dict"],  # Wrong type
        )

        assert context.metadata == {}
        mock_logger.warning.assert_called_once()
        assert "metadata expected dict" in mock_logger.warning.call_args[0][0]

    @patch("app.core.prompts.context.logger")
    def test_document_metadata_type_correction(self, mock_logger):
        """Test that non-dict ocr_processing gets converted to empty dict"""
        context = PromptContext(
            context_type=ContextType.USER, ocr_processing=42  # Wrong type
        )

        assert context.ocr_processing == {}
        mock_logger.warning.assert_called_once()
        assert "ocr_processing expected dict" in mock_logger.warning.call_args[0][0]

    @patch("app.core.prompts.context.logger")
    def test_focus_areas_type_correction(self, mock_logger):
        """Test that non-list focus_areas gets converted to empty list"""
        context = PromptContext(
            context_type=ContextType.USER,
            focus_areas="string_instead_of_list",  # Wrong type
        )

        assert context.focus_areas == []
        mock_logger.warning.assert_called_once()
        assert "focus_areas expected list" in mock_logger.warning.call_args[0][0]

    @patch("app.core.prompts.context.logger")
    def test_multiple_type_corrections(self, mock_logger):
        """Test multiple type corrections in single initialization"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables="wrong",
            metadata=123,
            ocr_processing=None,
            focus_areas="also_wrong",
        )

        assert context.variables == {}
        assert context.metadata == {}
        assert context.ocr_processing == {}
        assert context.focus_areas == []

        # Should log 4 warnings (one for each incorrect type)
        assert mock_logger.warning.call_count == 4

    def test_none_values_get_converted(self):
        """Test that None values get converted to appropriate defaults"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables=None,
            metadata=None,
            ocr_processing=None,
            focus_areas=None,
        )

        assert context.variables == {}
        assert context.metadata == {}
        assert context.ocr_processing == {}
        assert context.focus_areas == []


class TestPromptContextDotNotation:
    """Test dot notation functionality in PromptContext"""

    def test_get_nested_value(self):
        """Test getting nested values with dot notation"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "user": {"name": "John", "profile": {"age": 30}},
                "settings": {"theme": "dark"},
            },
        )

        assert context.get("user.name") == "John"
        assert context.get("user.profile.age") == 30
        assert context.get("settings.theme") == "dark"
        assert context.get("nonexistent.key", "default") == "default"

    def test_set_nested_value(self):
        """Test setting nested values with dot notation"""
        context = PromptContext(context_type=ContextType.USER)

        context.set("user.name", "Alice")
        context.set("user.profile.age", 25)

        assert context.variables["user"]["name"] == "Alice"
        assert context.variables["user"]["profile"]["age"] == 25

    def test_has_nested_key(self):
        """Test checking for nested keys with dot notation"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables={"level1": {"level2": {"level3": "value"}}},
        )

        assert context.has("level1.level2.level3")
        assert not context.has("level1.level2.level4")
        assert not context.has("nonexistent.key")


class TestPromptContextMerging:
    """Test context merging functionality"""

    def test_merge_contexts(self):
        """Test merging two contexts"""
        context1 = PromptContext(
            context_type=ContextType.USER,
            variables={"a": 1, "b": 2},
            metadata={"source": "test1"},
        )

        context2 = PromptContext(
            context_type=ContextType.USER,
            variables={"b": 3, "c": 4},
            metadata={"version": "1.0"},
        )

        merged = context1.merge(context2)

        # Variables should be merged (context2 takes precedence)
        assert merged.variables == {"a": 1, "b": 3, "c": 4}

        # Metadata should be merged
        assert merged.metadata == {"source": "test1", "version": "1.0"}

    def test_merge_with_type_safety(self):
        """Test that merge maintains type safety"""
        context1 = PromptContext(
            context_type=ContextType.USER, variables={"valid": "dict"}
        )

        # Create context2 with invalid types (should be corrected in __post_init__)
        context2 = PromptContext(
            context_type=ContextType.USER,
            variables="invalid_type",  # Will be corrected to {}
        )

        merged = context1.merge(context2)

        # Should preserve valid variables from context1
        assert merged.variables == {"valid": "dict"}


class TestContextBuilder:
    """Test ContextBuilder functionality"""

    def test_create_user_context(self):
        """Test creating user context through builder"""
        context = (
            ContextBuilder()
            .user()
            .variables({"name": "test"})
            .metadata({"source": "builder"})
            .build()
        )

        assert context.context_type == ContextType.USER
        assert context.variables == {"name": "test"}
        assert context.metadata == {"source": "builder"}

    def test_create_system_context(self):
        """Test creating system context through builder"""
        context = ContextBuilder().system().variables({"mode": "production"}).build()

        assert context.context_type == ContextType.SYSTEM
        assert context.variables == {"mode": "production"}


class TestContextPresets:
    """Test context presets functionality"""

    def test_development_preset(self):
        """Test development context preset"""
        context = ContextPresets.development()

        assert context.context_type == ContextType.SYSTEM
        assert "environment" in context.variables
        assert context.variables["environment"] == "development"

    def test_production_preset(self):
        """Test production context preset"""
        context = ContextPresets.production()

        assert context.context_type == ContextType.SYSTEM
        assert "environment" in context.variables
        assert context.variables["environment"] == "production"

    def test_testing_preset(self):
        """Test testing context preset"""
        context = ContextPresets.testing()

        assert context.context_type == ContextType.SYSTEM
        assert "environment" in context.variables
        assert context.variables["environment"] == "testing"


class TestPromptContextEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_string_variables(self):
        """Test handling of empty string in variables"""
        context = PromptContext(
            context_type=ContextType.USER, variables=""  # Empty string, not dict
        )

        assert context.variables == {}

    def test_complex_nested_structure(self):
        """Test with complex nested data structures"""
        complex_data = {
            "level1": {
                "level2": {
                    "array": [1, 2, {"nested": "value"}],
                    "null_value": None,
                    "boolean": True,
                }
            }
        }

        context = PromptContext(context_type=ContextType.USER, variables=complex_data)

        assert context.get("level1.level2.array") == [1, 2, {"nested": "value"}]
        assert context.get("level1.level2.null_value") is None
        assert context.get("level1.level2.boolean") is True

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        context = PromptContext(
            context_type=ContextType.USER,
            variables={
                "unicode": "🚀 Test with emoji",
                "special_chars": "Test with special chars: äöü ñ 中文",
                "escaped": "Test with \"quotes\" and 'apostrophes'",
            },
        )

        assert context.get("unicode") == "🚀 Test with emoji"
        assert context.get("special_chars") == "Test with special chars: äöü ñ 中文"
        assert context.get("escaped") == "Test with \"quotes\" and 'apostrophes'"
