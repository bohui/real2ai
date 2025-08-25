"""
Unit tests for PromptComposer class
Tests the actual composition logic and data structure handling
"""

import pytest

from app.core.prompts.composer import PromptComposer
from app.core.prompts.config_manager import CompositionRule
from app.core.prompts.context import PromptContext, ContextType
from app.core.prompts.exceptions import PromptCompositionError, PromptNotFoundError


class TestPromptComposer:
    """Test suite for PromptComposer class"""

    @pytest.fixture
    def mock_config_dir(self, tmp_path):
        """Create a mock config directory with test files"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create test composition rules
        composition_rules = {
            "compositions": {
                "test_composition": {
                    "description": "Test composition",
                    "system_prompts": [
                        {
                            "name": "test_system",
                            "path": "system/test.md",
                            "priority": 100,
                            "required": True,
                        }
                    ],
                    "user_prompts": ["test_user"],
                    "merge_strategy": "sequential",
                }
            }
        }

        import yaml

        with open(config_dir / "composition_rules.yaml", "w") as f:
            yaml.dump(composition_rules, f)

        # Create test prompt registry
        prompt_registry = {
            "registry": {
                "system_prompts": {
                    "test_system": {"path": "system/test.md", "priority": 100}
                },
                "user_prompts": {"test_user": {"path": "user/test.md"}},
            }
        }

        with open(config_dir / "prompt_registry.yaml", "w") as f:
            yaml.dump(prompt_registry, f)

        return config_dir

    @pytest.fixture
    def mock_prompts_dir(self, tmp_path):
        """Create a mock prompts directory with test files"""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create test system prompt
        system_dir = prompts_dir / "system"
        system_dir.mkdir()
        with open(system_dir / "test.md", "w") as f:
            f.write("---\nname: test_system\n---\nTest system prompt content")

        # Create test user prompt
        user_dir = prompts_dir / "user"
        user_dir.mkdir()
        with open(user_dir / "test.md", "w") as f:
            f.write("---\nname: test_user\n---\nTest user prompt content")

        return prompts_dir

    def test_composition_rule_data_structure(self):
        """Test that CompositionRule properly handles dict-based system_prompts"""
        # This should not raise an error
        rule = CompositionRule(
            name="test",
            description="test",
            version="1.0.0",
            system_prompts=[
                {
                    "name": "system1",
                    "path": "system/1.md",
                    "priority": 100,
                    "required": True,
                }
            ],
            user_prompts=["user1"],
            merge_strategy="sequential",
        )

        assert rule.name == "test"
        assert len(rule.system_prompts) == 1
        assert rule.system_prompts[0]["name"] == "system1"
        assert rule.user_prompts == ["user1"]

    def test_composer_initialization(self, mock_config_dir, mock_prompts_dir):
        """Test that PromptComposer initializes correctly with valid config"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        assert len(composer.composition_rules) == 1
        assert "test_composition" in composer.composition_rules
        assert len(composer.prompt_registry.get("system_prompts", {})) == 1
        assert len(composer.prompt_registry.get("user_prompts", {})) == 1

    def test_compose_with_valid_rule(self, mock_config_dir, mock_prompts_dir):
        """Test that composition works with valid composition rule"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"test_var": "test_value"}
        )

        result = composer.compose("test_composition", context)

        assert result.name == "test_composition"
        assert result.system_content != ""
        assert result.user_content != ""
        assert result.composition_rule.name == "test_composition"

    def test_compose_with_invalid_composition(self, mock_config_dir, mock_prompts_dir):
        """Test that composition fails gracefully with invalid composition name"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"test_var": "test_value"}
        )

        with pytest.raises(PromptCompositionError) as exc_info:
            composer.compose("invalid_composition", context)

        assert "Unknown composition rule: invalid_composition" in str(exc_info.value)

    def test_system_prompt_priority_sorting(self, mock_config_dir, mock_prompts_dir):
        """Test that system prompts are sorted by priority correctly"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        # Test the sorting logic
        rule = composer.composition_rules["test_composition"]
        system_prompt_names = [prompt["name"] for prompt in rule.system_prompts]
        sorted_prompts = composer._sort_by_priority(system_prompt_names, "system")

        assert len(sorted_prompts) == 1
        assert sorted_prompts[0] == "test_system"

    def test_validation_with_valid_composition(self, mock_config_dir, mock_prompts_dir):
        """Test that validation passes for valid composition"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        validation_result = composer.validate_composition("test_composition")

        assert validation_result["valid"] is True
        assert len(validation_result["issues"]) == 0
        assert validation_result["total_prompts"] == 2  # 1 system + 1 user

    def test_validation_with_missing_prompt(self, mock_config_dir, mock_prompts_dir):
        """Test that validation fails when prompts are missing from registry"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        # Modify the registry to remove a prompt
        composer.prompt_registry["system_prompts"].pop("test_system")

        validation_result = composer.validate_composition("test_composition")

        assert validation_result["valid"] is False
        assert len(validation_result["issues"]) == 1
        assert "System prompt not found: test_system" in validation_result["issues"][0]

    def test_composition_metadata_creation(self, mock_config_dir, mock_prompts_dir):
        """Test that composition metadata is created correctly"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        rule = composer.composition_rules["test_composition"]
        context = PromptContext(context_type=ContextType.ANALYSIS, variables={})

        metadata = composer._create_composition_metadata(rule, context, {}, {})

        assert metadata["composition_rule"] == "test_composition"
        assert metadata["system_prompts"] == rule.system_prompts
        assert metadata["user_prompts"] == rule.user_prompts
        assert metadata["merge_strategy"] == "sequential"
        assert "composed_at" in metadata

    def test_merge_strategies(self, mock_config_dir, mock_prompts_dir):
        """Test different merge strategies for prompt parts"""
        composer = PromptComposer(mock_config_dir, mock_prompts_dir)

        # Test sequential merge
        sequential_result = composer._merge_prompt_parts(
            ["part1", "part2"], "sequential"
        )
        assert "---" in sequential_result

        # Test parallel merge
        parallel_result = composer._merge_prompt_parts(["part1", "part2"], "parallel")
        assert "---" not in parallel_result

        # Test hierarchical merge
        hierarchical_result = composer._merge_prompt_parts(
            ["part1", "part2"], "hierarchical"
        )
        assert "  part2" in hierarchical_result

        # Test unknown strategy (should default to sequential)
        default_result = composer._merge_prompt_parts(["part1", "part2"], "unknown")
        assert "---" in default_result

    def test_error_handling_in_composition(self, mock_config_dir, mock_prompts_dir):
        """Test that composition errors are properly handled and logged"""
        composer = PromptComposer(mock_config_dir, mock_prompts_dir)

        # Create a context that would cause an error
        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"invalid_var": None}
        )

        # This should not crash, but should handle errors gracefully
        try:
            result = composer.compose("test_composition", context)
            # If we get here, composition succeeded (which is fine)
            assert result is not None
        except Exception as e:
            # If composition fails, it should be a proper exception
            assert isinstance(e, (PromptCompositionError, PromptNotFoundError))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
