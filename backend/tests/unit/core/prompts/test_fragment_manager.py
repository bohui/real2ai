"""Unit tests for FragmentManager covering the recent fixes"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import shutil
import yaml

from app.core.prompts.fragment_manager import (
    FragmentManager,
    FragmentRule,
    Fragment,
    PromptCompositionError,
)
from app.core.prompts.context import PromptContext


class TestFragmentRule:
    """Test FragmentRule class fixes"""

    def test_fragment_rule_with_condition(self):
        """Test FragmentRule creation with condition"""
        rule = FragmentRule(
            condition="test_condition", mappings={"value": ["test.md"]}, priority=80
        )
        assert rule.condition == "test_condition"
        assert rule.mappings == {"value": ["test.md"]}
        assert rule.priority == 80
        assert rule.composition == "replace"
        assert rule.always_include == []

    def test_fragment_rule_without_condition(self):
        """Test FragmentRule creation without condition (fix for consumer_protection)"""
        rule = FragmentRule(always_include=["common.md"], priority=90)
        assert rule.condition is None
        assert rule.always_include == ["common.md"]
        assert rule.priority == 90
        assert rule.mappings == {}
        assert rule.composition == "replace"

    def test_fragment_rule_defaults(self):
        """Test FragmentRule default values are properly set"""
        rule = FragmentRule()
        assert rule.condition is None
        assert rule.composition == "replace"
        assert rule.mappings == {}
        assert rule.always_include == []
        assert rule.priority == 50


class TestFragment:
    """Test Fragment class fixes"""

    def test_fragment_with_tags(self):
        """Test Fragment creation with tags"""
        fragment = Fragment(
            name="test",
            path=Path("/tmp/test.md"),
            content="test content",
            metadata={},
            tags=["tag1", "tag2"],
        )
        assert fragment.tags == ["tag1", "tag2"]

    def test_fragment_without_tags(self):
        """Test Fragment creation without tags (should default to empty list)"""
        fragment = Fragment(
            name="test", path=Path("/tmp/test.md"), content="test content", metadata={}
        )
        assert fragment.tags == []


class TestFragmentManager:
    """Test FragmentManager class fixes"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        temp_dir = tempfile.mkdtemp()
        fragments_dir = Path(temp_dir) / "fragments"
        config_dir = Path(temp_dir) / "config"
        fragments_dir.mkdir()
        config_dir.mkdir()

        yield fragments_dir, config_dir

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def fragment_manager(self, temp_dirs):
        """Create FragmentManager instance for testing"""
        fragments_dir, config_dir = temp_dirs
        return FragmentManager(fragments_dir, config_dir)

    @pytest.fixture
    def sample_orchestration_config(self):
        """Sample orchestration configuration for testing"""
        return {
            "fragments": {
                "state_legal_requirements": {
                    "condition": "australian_state",
                    "composition": "replace",
                    "priority": 80,
                    "mappings": {"NSW": ["fragments/nsw/planning_certificates.md"]},
                },
                "consumer_protection": {
                    "always_include": ["fragments/common/cooling_off_framework.md"],
                    "priority": 90,
                },
                "contract_type_specific": {
                    "condition": "contract_type",
                    "mappings": {
                        "PURCHASE_AGREEMENT": [
                            "fragments/purchase/settlement_requirements.md"
                        ]
                    },
                },
            }
        }

    def test_fragment_manager_initialization(self, temp_dirs):
        """Test FragmentManager initialization"""
        fragments_dir, config_dir = temp_dirs
        manager = FragmentManager(fragments_dir, config_dir)

        assert manager.fragments_dir == fragments_dir
        assert manager.config_dir == config_dir
        assert manager._fragment_cache == {}
        assert manager._orchestration_configs == {}

    def test_load_orchestration_config_success(self, fragment_manager, temp_dirs):
        """Test successful orchestration config loading"""
        _, config_dir = temp_dirs
        config_file = config_dir / "test_orchestrator.yaml"

        config_content = yaml.dump({"test": "config"})
        with open(config_file, "w") as f:
            f.write(config_content)

        result = fragment_manager._load_orchestration_config("test")
        assert result == {"test": "config"}

    def test_load_orchestration_config_not_found(self, fragment_manager):
        """Test orchestration config not found error"""
        with pytest.raises(PromptCompositionError) as exc_info:
            fragment_manager._load_orchestration_config("nonexistent")

        assert "Orchestration config not found" in str(exc_info.value)

    def test_load_fragment_path_stripping(self, fragment_manager, temp_dirs):
        """Test fragment path stripping (fix for double fragments/ issue)"""
        fragments_dir, _ = temp_dirs

        # Create a test fragment file
        test_file = fragments_dir / "nsw" / "planning_certificates.md"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("test content")

        # Test with path that starts with "fragments/"
        fragment = fragment_manager._load_fragment(
            "fragments/nsw/planning_certificates.md"
        )

        assert fragment is not None
        assert fragment.name == "fragments/nsw/planning_certificates.md"
        assert fragment.content == "test content"

    def test_load_fragment_path_no_stripping(self, fragment_manager, temp_dirs):
        """Test fragment loading without path stripping"""
        fragments_dir, _ = temp_dirs

        # Create a test fragment file
        test_file = fragments_dir / "nsw" / "planning_certificates.md"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("test content")

        # Test with path that doesn't start with "fragments/"
        fragment = fragment_manager._load_fragment("nsw/planning_certificates.md")

        assert fragment is not None
        assert fragment.name == "nsw/planning_certificates.md"
        assert fragment.content == "test content"

    def test_load_fragment_not_found(self, fragment_manager):
        """Test fragment loading when file doesn't exist"""
        fragment = fragment_manager._load_fragment("nonexistent.md")
        assert fragment is None

    def test_evaluate_condition_with_condition(self, fragment_manager):
        """Test condition evaluation when condition exists"""
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={"test_var": "test_value"})
        result = fragment_manager._evaluate_condition("test_var", context)
        assert result == "test_value"

    def test_evaluate_condition_without_condition(self, fragment_manager):
        """Test condition evaluation when condition is None (fix for optional condition)"""
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={"test_var": "test_value"})
        result = fragment_manager._evaluate_condition(None, context)
        assert result is None

    def test_evaluate_condition_condition_not_in_context(self, fragment_manager):
        """Test condition evaluation when condition is not in context"""
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={"other_var": "other_value"})
        result = fragment_manager._evaluate_condition("test_var", context)
        assert result is None

    @patch("app.core.prompts.fragment_manager.yaml.safe_load")
    def test_resolve_fragments_with_condition(
        self, mock_yaml_load, fragment_manager, temp_dirs
    ):
        """Test fragment resolution with conditional fragments"""
        _, config_dir = temp_dirs

        # Mock the orchestration config
        mock_yaml_load.return_value = {
            "fragments": {
                "state_legal_requirements": {
                    "condition": "australian_state",
                    "mappings": {"NSW": ["fragments/nsw/planning_certificates.md"]},
                }
            }
        }

        # Create test fragment
        fragments_dir, _ = temp_dirs
        test_file = fragments_dir / "nsw" / "planning_certificates.md"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("test content")

        # Create context with the required variable
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={"australian_state": "NSW"})

        # Mock the config file loading
        with patch("builtins.open", mock_open(read_data="test")):
            with patch("pathlib.Path.exists", return_value=True):
                fragments = fragment_manager.resolve_fragments("test", context)

        assert len(fragments) == 1
        assert fragments[0].content == "test content"

    @patch("app.core.prompts.fragment_manager.yaml.safe_load")
    def test_resolve_fragments_without_condition(
        self, mock_yaml_load, fragment_manager, temp_dirs
    ):
        """Test fragment resolution without condition (fix for consumer_protection)"""
        _, config_dir = temp_dirs

        # Mock the orchestration config
        mock_yaml_load.return_value = {
            "fragments": {
                "consumer_protection": {
                    "always_include": ["fragments/common/cooling_off_framework.md"],
                    "priority": 90,
                }
            }
        }

        # Create test fragment
        fragments_dir, _ = temp_dirs
        test_file = fragments_dir / "common" / "cooling_off_framework.md"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("cooling off content")

        # Create context
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={})

        # Mock the config file loading
        with patch("builtins.open", mock_open(read_data="test")):
            with patch("pathlib.Path.exists", return_value=True):
                fragments = fragment_manager.resolve_fragments("test", context)

        assert len(fragments) == 1
        assert fragments[0].content == "cooling off content"

    @patch("app.core.prompts.fragment_manager.yaml.safe_load")
    def test_resolve_fragments_mixed_rules(
        self, mock_yaml_load, fragment_manager, temp_dirs
    ):
        """Test fragment resolution with both conditional and always-include rules"""
        _, config_dir = temp_dirs

        # Mock the orchestration config with mixed rules
        mock_yaml_load.return_value = {
            "fragments": {
                "state_legal_requirements": {
                    "condition": "australian_state",
                    "mappings": {"NSW": ["fragments/nsw/planning_certificates.md"]},
                },
                "consumer_protection": {
                    "always_include": ["fragments/common/cooling_off_framework.md"],
                    "priority": 90,
                },
            }
        }

        # Create test fragments
        fragments_dir, _ = temp_dirs
        nsw_file = fragments_dir / "nsw" / "planning_certificates.md"
        nsw_file.parent.mkdir(exist_ok=True)
        nsw_file.write_text("nsw content")

        common_file = fragments_dir / "common" / "cooling_off_framework.md"
        common_file.parent.mkdir(exist_ok=True)
        common_file.write_text("common content")

        # Create context with the required variable
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={"australian_state": "NSW"})

        # Mock the config file loading
        with patch("builtins.open", mock_open(read_data="test")):
            with patch("pathlib.Path.exists", return_value=True):
                fragments = fragment_manager.resolve_fragments("test", context)

        assert len(fragments) == 2
        # Check that both fragments are loaded
        fragment_contents = [f.content for f in fragments]
        assert "nsw content" in fragment_contents
        assert "common content" in fragment_contents

    def test_resolve_fragments_handles_missing_fragments_gracefully(
        self, fragment_manager, temp_dirs
    ):
        """Test that missing fragments don't crash the system"""
        _, config_dir = temp_dirs

        # Create a config file that references non-existent fragments
        config_file = config_dir / "test_orchestrator.yaml"
        config_content = yaml.dump(
            {
                "fragments": {
                    "test_rule": {
                        "always_include": ["fragments/nonexistent/fragment.md"]
                    }
                }
            }
        )

        with open(config_file, "w") as f:
            f.write(config_content)

        # This should not crash, just log warnings
        from app.core.prompts import ContextType
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={})
        fragments = fragment_manager.resolve_fragments("test", context)

        # Should return empty list when no fragments can be loaded
        assert fragments == []


class TestFragmentManagerIntegration:
    """Integration tests for FragmentManager"""

    @pytest.fixture
    def real_fragment_manager(self):
        """Create FragmentManager with real paths for integration testing"""
        from app.core.prompts.manager import get_prompt_manager

        # Get the real prompt manager to test with actual configuration
        try:
            prompt_manager = get_prompt_manager()
            return prompt_manager.composer.fragment_manager
        except Exception:
            # If we can't get the real one, skip integration tests
            pytest.skip("Real FragmentManager not available for integration testing")

    def test_contract_analysis_orchestration_loading(self, real_fragment_manager):
        """Test that contract_analysis orchestration can be loaded without errors"""
        # This test verifies our fix for the KeyError: 'condition' issue
        try:
            # Try to load the orchestration config
            config = real_fragment_manager._load_orchestration_config(
                "contract_analysis"
            )
            assert config is not None
            assert "fragments" in config

            # Verify that consumer_protection rule exists and has no condition
            consumer_protection = config["fragments"].get("consumer_protection")
            assert consumer_protection is not None
            assert "condition" not in consumer_protection
            assert "always_include" in consumer_protection

        except Exception as e:
            pytest.fail(f"Contract analysis orchestration loading failed: {e}")

    def test_fragment_rule_creation_from_config(self, real_fragment_manager):
        """Test that FragmentRule can be created from real config without errors"""
        try:
            config = real_fragment_manager._load_orchestration_config(
                "contract_analysis"
            )

            # Test creating FragmentRule from consumer_protection (which has no condition)
            consumer_protection_config = config["fragments"]["consumer_protection"]

            rule = FragmentRule(
                condition=consumer_protection_config.get("condition"),
                composition=consumer_protection_config.get("composition", "replace"),
                mappings=consumer_protection_config.get("mappings", {}),
                always_include=consumer_protection_config.get("always_include", []),
                priority=consumer_protection_config.get("priority", 50),
            )

            assert rule.condition is None
            assert rule.always_include is not None
            assert len(rule.always_include) > 0

        except Exception as e:
            pytest.fail(f"FragmentRule creation from real config failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
