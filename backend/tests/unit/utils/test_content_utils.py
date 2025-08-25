"""
Tests for content processing utilities

Tests the HMAC computation, parameter fingerprinting, and validation functions
used in the document processing artifacts system.
"""

import hashlib
import hmac
import pytest
from unittest.mock import Mock, patch

from app.utils.content_utils import (
    compute_content_hmac,
    compute_params_fingerprint,
    get_artifact_key,
    validate_content_hmac,
    validate_params_fingerprint,
)


class TestComputeContentHmac:
    """Test HMAC computation functionality"""

    def test_compute_hmac_with_provided_secret(self):
        """Test HMAC computation with explicitly provided secret"""
        file_bytes = b"test document content"
        secret_key = "test_secret_key"
        
        result = compute_content_hmac(file_bytes, secret_key)
        
        # Verify result is valid hex string of correct length (SHA256 = 64 chars)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)
        
        # Verify it matches direct HMAC computation
        expected = hmac.new(
            secret_key.encode('utf-8'),
            file_bytes,
            hashlib.sha256
        ).hexdigest()
        assert result == expected

    @patch('app.utils.content_utils.get_settings')
    def test_compute_hmac_with_config_secret(self, mock_get_settings):
        """Test HMAC computation using configured secret"""
        file_bytes = b"test document content"
        secret_key = "configured_secret"
        
        # Mock settings to return the secret
        mock_settings = Mock()
        mock_settings.document_hmac_secret = secret_key
        mock_get_settings.return_value = mock_settings
        
        result = compute_content_hmac(file_bytes)
        
        # Verify result matches expected HMAC
        expected = hmac.new(
            secret_key.encode('utf-8'),
            file_bytes,
            hashlib.sha256
        ).hexdigest()
        assert result == expected

    @patch('app.utils.content_utils.get_settings')
    def test_compute_hmac_no_secret_configured(self, mock_get_settings):
        """Test error when no secret is configured"""
        file_bytes = b"test document content"
        
        # Mock settings with no secret
        mock_settings = Mock()
        mock_settings.document_hmac_secret = None
        mock_get_settings.return_value = mock_settings
        
        with pytest.raises(ValueError, match="Document HMAC secret not configured"):
            compute_content_hmac(file_bytes)

    def test_compute_hmac_empty_secret(self):
        """Test error with empty secret string"""
        file_bytes = b"test document content"
        
        with pytest.raises(ValueError, match="Document HMAC secret not configured"):
            compute_content_hmac(file_bytes, "")

    def test_compute_hmac_different_content_different_hash(self):
        """Test that different content produces different hashes"""
        secret_key = "test_secret"
        content1 = b"document content 1"
        content2 = b"document content 2"
        
        hash1 = compute_content_hmac(content1, secret_key)
        hash2 = compute_content_hmac(content2, secret_key)
        
        assert hash1 != hash2

    def test_compute_hmac_same_content_same_hash(self):
        """Test that same content produces same hash"""
        secret_key = "test_secret"
        content = b"document content"
        
        hash1 = compute_content_hmac(content, secret_key)
        hash2 = compute_content_hmac(content, secret_key)
        
        assert hash1 == hash2

    def test_compute_hmac_different_secrets_different_hash(self):
        """Test that different secrets produce different hashes"""
        content = b"document content"
        
        hash1 = compute_content_hmac(content, "secret1")
        hash2 = compute_content_hmac(content, "secret2")
        
        assert hash1 != hash2


class TestComputeParamsFingerprint:
    """Test parameter fingerprinting functionality"""

    def test_simple_params(self):
        """Test fingerprinting of simple parameters"""
        params = {"key1": "value1", "key2": "value2"}
        
        result = compute_params_fingerprint(params)
        
        # Should be 64 character hex string (SHA256)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_nested_params(self):
        """Test fingerprinting of nested parameters"""
        params = {
            "outer_key": {
                "inner_key": "inner_value",
                "nested_list": [1, 2, 3]
            },
            "simple_key": "simple_value"
        }
        
        result = compute_params_fingerprint(params)
        assert len(result) == 64

    def test_key_order_independence(self):
        """Test that parameter order doesn't affect fingerprint"""
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "a": 1, "b": 2}
        
        hash1 = compute_params_fingerprint(params1)
        hash2 = compute_params_fingerprint(params2)
        
        assert hash1 == hash2

    def test_list_order_matters(self):
        """Test that list order affects fingerprint"""
        params1 = {"list": [1, 2, 3]}
        params2 = {"list": [3, 2, 1]}
        
        hash1 = compute_params_fingerprint(params1)
        hash2 = compute_params_fingerprint(params2)
        
        assert hash1 != hash2

    def test_nested_key_order_independence(self):
        """Test order independence in nested dictionaries"""
        params1 = {
            "outer": {"z": 1, "a": 2},
            "simple": "value"
        }
        params2 = {
            "simple": "value",
            "outer": {"a": 2, "z": 1}
        }
        
        hash1 = compute_params_fingerprint(params1)
        hash2 = compute_params_fingerprint(params2)
        
        assert hash1 == hash2

    def test_empty_params(self):
        """Test fingerprinting of empty parameters"""
        result = compute_params_fingerprint({})
        assert len(result) == 64

    def test_same_params_same_fingerprint(self):
        """Test deterministic fingerprinting"""
        params = {"key": "value", "number": 42}
        
        hash1 = compute_params_fingerprint(params)
        hash2 = compute_params_fingerprint(params)
        
        assert hash1 == hash2

    def test_different_params_different_fingerprint(self):
        """Test that different parameters produce different fingerprints"""
        params1 = {"key": "value1"}
        params2 = {"key": "value2"}
        
        hash1 = compute_params_fingerprint(params1)
        hash2 = compute_params_fingerprint(params2)
        
        assert hash1 != hash2

    def test_complex_params_realistic(self):
        """Test with realistic document processing parameters"""
        params = {
            "file_type": "application/pdf",
            "use_llm": True,
            "ocr_zoom": 2.0,
            "min_text_len_for_ocr": 60,
            "diagram_keywords": [
                "diagram", "plan", "map", "layout", "site plan"
            ]
        }
        
        result = compute_params_fingerprint(params)
        assert len(result) == 64

    def test_verify_json_serialization_deterministic(self):
        """Test that JSON serialization is deterministic"""
        params = {"b": 2, "a": 1, "c": {"z": 1, "y": 2}}
        
        # Manually compute what the fingerprint should be
        sorted_params = {"a": 1, "b": 2, "c": {"y": 2, "z": 1}}
        expected_json = '{"a":1,"b":2,"c":{"y":2,"z":1}}'
        expected_hash = hashlib.sha256(expected_json.encode('utf-8')).hexdigest()
        
        result = compute_params_fingerprint(params)
        assert result == expected_hash


class TestGetArtifactKey:
    """Test artifact key tuple creation"""

    def test_get_artifact_key(self):
        """Test artifact key tuple creation"""
        content_hmac = "abcd1234" * 8  # 64 chars
        algorithm_version = 1
        params_fingerprint = "efgh5678" * 8  # 64 chars
        
        result = get_artifact_key(content_hmac, algorithm_version, params_fingerprint)
        
        assert result == (content_hmac, algorithm_version, params_fingerprint)
        assert isinstance(result, tuple)
        assert len(result) == 3


class TestValidateContentHmac:
    """Test HMAC validation functionality"""

    def test_valid_hmac(self):
        """Test validation of valid HMAC"""
        valid_hmac = "a" * 64  # 64 character hex string
        assert validate_content_hmac(valid_hmac) is True

    def test_valid_hmac_mixed_case(self):
        """Test validation of mixed case HMAC"""
        valid_hmac = "AbCdEf" + "1234567890" * 5 + "abcdef12"  # 64 chars
        assert validate_content_hmac(valid_hmac) is True

    def test_invalid_hmac_wrong_length(self):
        """Test rejection of wrong length HMAC"""
        # Too short
        assert validate_content_hmac("a" * 63) is False
        # Too long
        assert validate_content_hmac("a" * 65) is False

    def test_invalid_hmac_non_hex_chars(self):
        """Test rejection of non-hexadecimal characters"""
        invalid_hmac = "g" * 64  # 'g' is not a valid hex character
        assert validate_content_hmac(invalid_hmac) is False

    def test_invalid_hmac_empty_string(self):
        """Test rejection of empty string"""
        assert validate_content_hmac("") is False

    def test_invalid_hmac_none(self):
        """Test rejection of None"""
        assert validate_content_hmac(None) is False

    def test_invalid_hmac_non_string(self):
        """Test rejection of non-string input"""
        assert validate_content_hmac(12345) is False
        assert validate_content_hmac([]) is False

    def test_valid_hmac_all_digits(self):
        """Test validation of all-digit HMAC"""
        valid_hmac = "1234567890" * 6 + "1234"  # 64 digits
        assert validate_content_hmac(valid_hmac) is True

    def test_valid_hmac_all_letters(self):
        """Test validation of all-letter HMAC"""
        valid_hmac = "abcdef" * 10 + "abcd"  # 64 hex letters
        assert validate_content_hmac(valid_hmac) is True


class TestValidateParamsFingerprint:
    """Test parameter fingerprint validation functionality"""

    def test_valid_fingerprint(self):
        """Test validation of valid fingerprint"""
        valid_fingerprint = "b" * 64  # 64 character hex string
        assert validate_params_fingerprint(valid_fingerprint) is True

    def test_valid_fingerprint_mixed_case(self):
        """Test validation of mixed case fingerprint"""
        valid_fingerprint = "FeDcBa" + "9876543210" * 5 + "fedcba98"  # 64 chars
        assert validate_params_fingerprint(valid_fingerprint) is True

    def test_invalid_fingerprint_wrong_length(self):
        """Test rejection of wrong length fingerprint"""
        # Too short
        assert validate_params_fingerprint("b" * 63) is False
        # Too long
        assert validate_params_fingerprint("b" * 65) is False

    def test_invalid_fingerprint_non_hex_chars(self):
        """Test rejection of non-hexadecimal characters"""
        invalid_fingerprint = "z" * 64  # 'z' is not a valid hex character
        assert validate_params_fingerprint(invalid_fingerprint) is False

    def test_invalid_fingerprint_empty_string(self):
        """Test rejection of empty string"""
        assert validate_params_fingerprint("") is False

    def test_invalid_fingerprint_none(self):
        """Test rejection of None"""
        assert validate_params_fingerprint(None) is False

    def test_invalid_fingerprint_non_string(self):
        """Test rejection of non-string input"""
        assert validate_params_fingerprint(67890) is False
        assert validate_params_fingerprint({}) is False


class TestIntegration:
    """Integration tests combining multiple functions"""

    def test_full_workflow(self):
        """Test complete artifact key generation workflow"""
        # Sample document content and parameters
        file_bytes = b"PDF document content here..."
        secret_key = "integration_test_secret"
        params = {
            "file_type": "application/pdf",
            "use_llm": True,
            "processing_version": 1
        }
        
        # Compute HMAC and fingerprint
        content_hmac = compute_content_hmac(file_bytes, secret_key)
        params_fingerprint = compute_params_fingerprint(params)
        algorithm_version = 1
        
        # Validate results
        assert validate_content_hmac(content_hmac)
        assert validate_params_fingerprint(params_fingerprint)
        
        # Create artifact key
        artifact_key = get_artifact_key(content_hmac, algorithm_version, params_fingerprint)
        assert len(artifact_key) == 3
        assert artifact_key[0] == content_hmac
        assert artifact_key[1] == algorithm_version
        assert artifact_key[2] == params_fingerprint

    def test_deterministic_across_calls(self):
        """Test that the same input always produces the same output"""
        file_bytes = b"consistent document content"
        secret_key = "consistent_secret"
        params = {"param1": "value1", "param2": [1, 2, 3]}
        
        # Compute multiple times
        hmac1 = compute_content_hmac(file_bytes, secret_key)
        hmac2 = compute_content_hmac(file_bytes, secret_key)
        
        fingerprint1 = compute_params_fingerprint(params)
        fingerprint2 = compute_params_fingerprint(params)
        
        # Should be identical
        assert hmac1 == hmac2
        assert fingerprint1 == fingerprint2

    def test_sensitivity_to_changes(self):
        """Test that small changes produce different results"""
        base_content = b"document content"
        base_secret = "secret_key"
        base_params = {"key": "value"}
        
        # Base results
        base_hmac = compute_content_hmac(base_content, base_secret)
        base_fingerprint = compute_params_fingerprint(base_params)
        
        # Change content
        changed_hmac = compute_content_hmac(b"document content!", base_secret)
        assert changed_hmac != base_hmac
        
        # Change secret
        secret_hmac = compute_content_hmac(base_content, "different_secret")
        assert secret_hmac != base_hmac
        
        # Change params
        params_fingerprint = compute_params_fingerprint({"key": "different_value"})
        assert params_fingerprint != base_fingerprint