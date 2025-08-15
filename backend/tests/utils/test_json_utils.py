"""
Tests for JSON utility functions.
"""

import pytest
from app.utils.json_utils import safe_json_loads


class TestSafeJsonLoads:
    """Test cases for safe_json_loads function."""

    def test_none_value_returns_default(self):
        """Test that None values return the default value."""
        assert safe_json_loads(None) is None
        assert safe_json_loads(None, default={}) == {}
        assert safe_json_loads(None, default="fallback") == "fallback"

    def test_dict_value_returns_as_is(self):
        """Test that dict values are returned unchanged."""
        test_dict = {"key": "value", "nested": {"inner": "data"}}
        assert safe_json_loads(test_dict) == test_dict
        assert safe_json_loads(test_dict, default={}) == test_dict

    def test_valid_json_string_parses_correctly(self):
        """Test that valid JSON strings are parsed correctly."""
        json_string = '{"key": "value", "number": 42, "boolean": true}'
        expected = {"key": "value", "number": 42, "boolean": True}
        assert safe_json_loads(json_string) == expected

    def test_empty_json_string_parses_correctly(self):
        """Test that empty JSON objects parse correctly."""
        assert safe_json_loads("{}") == {}
        assert safe_json_loads("[]") == []

    def test_invalid_json_string_returns_default(self):
        """Test that invalid JSON strings return the default value."""
        assert safe_json_loads("{invalid json", default={}) == {}
        assert safe_json_loads("not json at all", default=None) is None
        assert safe_json_loads("", default="empty") == "empty"

    def test_non_string_non_dict_returns_default(self):
        """Test that non-string, non-dict values return the default."""
        assert safe_json_loads(42, default="number") == "number"
        assert safe_json_loads(True, default="boolean") == "boolean"
        assert safe_json_loads([1, 2, 3], default="list") == "list"

    def test_complex_json_parses_correctly(self):
        """Test that complex JSON structures parse correctly."""
        complex_json = '''
        {
            "string": "hello world",
            "number": 3.14159,
            "boolean": false,
            "null": null,
            "array": [1, 2, 3, "string"],
            "object": {
                "nested": "value",
                "deep": {
                    "level": 3
                }
            }
        }
        '''
        result = safe_json_loads(complex_json)
        assert result["string"] == "hello world"
        assert result["number"] == 3.14159
        assert result["boolean"] is False
        assert result["null"] is None
        assert result["array"] == [1, 2, 3, "string"]
        assert result["object"]["deep"]["level"] == 3

    def test_unicode_json_parses_correctly(self):
        """Test that Unicode JSON strings parse correctly."""
        unicode_json = '{"message": "Hello, 世界! 🌍", "emoji": "🚀"}'
        result = safe_json_loads(unicode_json)
        assert result["message"] == "Hello, 世界! 🌍"
        assert result["emoji"] == "🚀"
