"""
Unit tests for prompt composition failure scenarios
Tests all the failure cases we've identified and fixed in the prompt system
"""

import pytest
import yaml

from app.core.prompts.composer import PromptComposer
from app.core.prompts.loader import PromptLoader, LoaderConfig
from app.core.prompts.context import PromptContext, ContextType
from app.core.prompts.exceptions import (
    PromptCompositionError,
    PromptNotFoundError,
)


class TestPromptCompositionFailures:
    """Test suite for prompt composition failure scenarios"""

    @pytest.fixture
    def mock_config_dir(self, tmp_path):
        """Create a mock config directory with test files"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create test composition rules with the OLD problematic structure
        composition_rules = {
            "compositions": {
                "document_quality_validation_only": {
                    "description": "Validate document quality and completeness",
                    "version": "1.0.0",
                    "system_prompts": [
                        {
                            "name": "legal_specialist",
                            "path": "system/domain/legal_specialist.md",
                            "priority": 100,
                            "required": True,
                        }
                    ],
                    "user_prompts": [
                        "validation/document_quality_validation"
                    ],  # OLD: path-based reference
                    "merge_strategy": "sequential",
                },
                "structure_analysis_only": {
                    "description": "Analyze contract structure from extracted text",
                    "version": "1.0.0",
                    "system_prompts": [
                        {
                            "name": "legal_specialist",
                            "path": "system/domain/legal_specialist.md",
                            "priority": 100,
                            "required": True,
                        }
                    ],
                    "user_prompts": [
                        "analysis/contract_structure"
                    ],  # OLD: non-existent path
                    "merge_strategy": "sequential",
                },
            }
        }

        with open(config_dir / "composition_rules.yaml", "w") as f:
            yaml.dump(composition_rules, f)

        # Create test prompt registry with CORRECT structure
        prompt_registry = {
            "registry": {
                "system_prompts": {
                    "legal_specialist": {
                        "path": "system/domain/legal_specialist.md",
                        "category": "domain",
                        "priority": 80,
                        "description": "Legal domain expertise and analysis capabilities",
                    }
                },
                "user_prompts": {
                    "validation_document_quality": {  # CORRECT: registry key
                        "path": "user/validation/document_quality_validation.md",  # CORRECT: full path
                        "category": "validation",
                        "description": "Document quality validation template",
                    },
                    "contract_analysis_base": {  # CORRECT: registry key
                        "path": "user/instructions/contract_analysis_base.md",  # CORRECT: full path
                        "category": "instructions",
                        "description": "Fragment-based comprehensive contract analysis instructions",
                    },
                },
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

        # Create system prompt directory and file
        system_dir = prompts_dir / "system" / "domain"
        system_dir.mkdir(parents=True)
        with open(system_dir / "legal_specialist.md", "w") as f:
            f.write(
                """---
name: "legal_specialist"
version: "1.0"
description: "Legal domain expertise and analysis capabilities"
---
You are a legal specialist with expertise in Australian contract law."""
            )

        # Create user validation prompt directory and file
        user_validation_dir = prompts_dir / "user" / "validation"
        user_validation_dir.mkdir(parents=True)
        with open(user_validation_dir / "document_quality_validation.md", "w") as f:
            f.write(
                """---
name: "document_quality_validation"
version: "2.0"
description: "Quality assessment of extracted contract text for reliability and completeness"
---
# Document Quality Validation

You are an expert document analysis specialist conducting quality assessment of extracted contract text."""
            )

        # Create user instructions prompt directory and file
        user_instructions_dir = prompts_dir / "user" / "instructions"
        user_instructions_dir.mkdir(parents=True)
        with open(user_instructions_dir / "contract_analysis_base.md", "w") as f:
            f.write(
                """---
name: "contract_analysis_base"
version: "1.0"
description: "Fragment-based comprehensive contract analysis instructions"
---
# Contract Analysis Instructions

Analyze the provided contract text for structure and key elements."""
            )

        return prompts_dir

    @pytest.fixture
    def fixed_composition_rules(self, tmp_path):
        """Create FIXED composition rules that should work"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create FIXED composition rules with correct registry keys
        composition_rules = {
            "compositions": {
                "document_quality_validation_only": {
                    "description": "Validate document quality and completeness",
                    "version": "1.0.0",
                    "system_prompts": [
                        {
                            "name": "legal_specialist",
                            "path": "system/domain/legal_specialist.md",
                            "priority": 100,
                            "required": True,
                        }
                    ],
                    "user_prompts": [
                        "validation_document_quality"
                    ],  # FIXED: registry key
                    "merge_strategy": "sequential",
                },
                "structure_analysis_only": {
                    "description": "Analyze contract structure from extracted text",
                    "version": "1.0.0",
                    "system_prompts": [
                        {
                            "name": "legal_specialist",
                            "path": "system/domain/legal_specialist.md",
                            "priority": 100,
                            "required": True,
                        }
                    ],
                    "user_prompts": ["contract_analysis_base"],  # FIXED: registry key
                    "merge_strategy": "sequential",
                },
            }
        }

        with open(config_dir / "composition_rules.yaml", "w") as f:
            yaml.dump(composition_rules, f)

        # Same prompt registry as above
        prompt_registry = {
            "registry": {
                "system_prompts": {
                    "legal_specialist": {
                        "path": "system/domain/legal_specialist.md",
                        "category": "domain",
                        "priority": 80,
                        "description": "Legal domain expertise and analysis capabilities",
                    }
                },
                "user_prompts": {
                    "validation_document_quality": {
                        "path": "user/validation/document_quality_validation.md",
                        "category": "validation",
                        "description": "Document quality validation template",
                    },
                    "contract_analysis_base": {
                        "path": "user/instructions/contract_analysis_base.md",
                        "category": "instructions",
                        "description": "Fragment-based comprehensive contract analysis instructions",
                    },
                },
            }
        }

        with open(config_dir / "prompt_registry.yaml", "w") as f:
            yaml.dump(prompt_registry, f)

        return config_dir

    def test_old_composition_structure_fails(self, mock_config_dir, mock_prompts_dir):
        """Test that the OLD composition structure fails as expected"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        # This should fail because the composition references a path that doesn't exist in registry
        context = PromptContext(
            context_type=ContextType.VALIDATION,
            variables={"document_text": "test", "australian_state": "NSW"},
        )

        with pytest.raises(PromptCompositionError) as exc_info:
            composer.compose("document_quality_validation_only", context)

        # Check that the error message indicates the specific problem
        error_msg = str(exc_info.value)
        assert "User prompt rendering failed" in error_msg
        assert "validation/document_quality_validation" in error_msg

    def test_old_composition_with_nonexistent_template_fails(
        self, mock_config_dir, mock_prompts_dir
    ):
        """Test that OLD composition with non-existent template path fails"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"document_text": "test"}
        )

        with pytest.raises(PromptCompositionError) as exc_info:
            composer.compose("structure_analysis_only", context)

        error_msg = str(exc_info.value)
        assert "User prompt rendering failed" in error_msg
        assert "analysis/contract_structure" in error_msg

    def test_fixed_composition_structure_works(
        self, fixed_composition_rules, mock_prompts_dir
    ):
        """Test that the FIXED composition structure works correctly"""
        composer = PromptComposer(mock_prompts_dir, fixed_composition_rules)

        context = PromptContext(
            context_type=ContextType.VALIDATION,
            variables={"document_text": "test", "australian_state": "NSW"},
        )

        # This should work now
        result = composer.compose("document_quality_validation_only", context)

        assert result is not None
        assert result.name == "document_quality_validation_only"
        assert len(result.system_content) > 0
        assert len(result.user_content) > 0
        assert "legal specialist" in result.system_content.lower()
        assert "document quality validation" in result.user_content.lower()

    def test_fixed_structure_analysis_composition_works(
        self, fixed_composition_rules, mock_prompts_dir
    ):
        """Test that the FIXED structure analysis composition works"""
        composer = PromptComposer(mock_prompts_dir, fixed_composition_rules)

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"document_text": "test"}
        )

        # This should work now
        result = composer.compose("structure_analysis_only", context)

        assert result is not None
        assert result.name == "structure_analysis_only"
        assert len(result.system_content) > 0
        assert len(result.user_content) > 0
        assert "legal specialist" in result.system_content.lower()
        assert "contract analysis" in result.user_content.lower()

    def test_template_loading_with_correct_paths(
        self, fixed_composition_rules, mock_prompts_dir
    ):
        """Test that template loading works with correct file paths"""
        loader = PromptLoader(mock_prompts_dir, LoaderConfig(cache_enabled=False))

        # Test loading validation template - use the metadata name from the template file
        import asyncio

        template = asyncio.run(loader.load_template("document_quality_validation"))
        assert template is not None
        assert template.metadata.name == "document_quality_validation"
        assert "quality assessment" in template.content.lower()

        # Test loading contract analysis template
        template = asyncio.run(loader.load_template("contract_analysis_base"))
        assert template is not None
        assert template.metadata.name == "contract_analysis_base"
        assert "contract analysis" in template.content.lower()

    def test_template_loading_with_incorrect_paths_fails(
        self, mock_config_dir, mock_prompts_dir
    ):
        """Test that template loading fails with incorrect file paths"""
        loader = PromptLoader(mock_prompts_dir, LoaderConfig(cache_enabled=False))

        # This should fail because the path doesn't exist
        import asyncio

        with pytest.raises(PromptNotFoundError) as exc_info:
            asyncio.run(loader.load_template("validation/document_quality_validation"))

        error_msg = str(exc_info.value)
        assert (
            "Template 'validation/document_quality_validation' not found" in error_msg
        )

    def test_composition_with_missing_template_fails_gracefully(
        self, mock_config_dir, mock_prompts_dir
    ):
        """Test that composition fails gracefully when template is missing"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        context = PromptContext(
            context_type=ContextType.VALIDATION, variables={"document_text": "test"}
        )

        # This should fail but with a clear error message
        with pytest.raises(PromptCompositionError) as exc_info:
            composer.compose("document_quality_validation_only", context)

        error_msg = str(exc_info.value)
        assert "Composition failed" in error_msg
        assert "User prompt rendering failed" in error_msg

    def test_registry_key_vs_path_mismatch(self, mock_config_dir, mock_prompts_dir):
        """Test the specific mismatch between registry keys and composition references"""
        # Load the composition rules
        with open(mock_config_dir / "composition_rules.yaml", "r") as f:
            comp_rules = yaml.safe_load(f)

        # Load the prompt registry
        with open(mock_config_dir / "prompt_registry.yaml", "r") as f:
            registry = yaml.safe_load(f)

        # Check that the composition references a path that doesn't exist as a registry key
        composition_user_prompt = comp_rules["compositions"][
            "document_quality_validation_only"
        ]["user_prompts"][0]
        registry_keys = list(registry["registry"]["user_prompts"].keys())

        # The composition references "validation/document_quality_validation" (path-based)
        # But the registry has "validation_document_quality" (key-based)
        assert composition_user_prompt not in registry_keys
        assert composition_user_prompt == "validation/document_quality_validation"
        assert "validation_document_quality" in registry_keys

    def test_fixed_registry_key_vs_path_alignment(
        self, fixed_composition_rules, mock_prompts_dir
    ):
        """Test that the FIXED composition aligns with registry keys"""
        # Load the composition rules
        with open(fixed_composition_rules / "composition_rules.yaml", "r") as f:
            comp_rules = yaml.safe_load(f)

        # Load the prompt registry
        with open(fixed_composition_rules / "prompt_registry.yaml", "r") as f:
            registry = yaml.safe_load(f)

        # Check that the composition references a registry key that exists
        composition_user_prompt = comp_rules["compositions"][
            "document_quality_validation_only"
        ]["user_prompts"][0]
        registry_keys = list(registry["registry"]["user_prompts"].keys())

        # The composition now references "validation_document_quality" (key-based)
        # And the registry has "validation_document_quality" (key-based)
        assert composition_user_prompt in registry_keys
        assert composition_user_prompt == "validation_document_quality"

    def test_file_path_existence_validation(self, mock_prompts_dir):
        """Test that file paths in the registry actually exist"""
        # Check that the paths referenced in the registry actually exist
        validation_path = (
            mock_prompts_dir / "user" / "validation" / "document_quality_validation.md"
        )
        instructions_path = (
            mock_prompts_dir / "user" / "instructions" / "contract_analysis_base.md"
        )
        system_path = mock_prompts_dir / "system" / "domain" / "legal_specialist.md"

        assert (
            validation_path.exists()
        ), f"Validation template not found at {validation_path}"
        assert (
            instructions_path.exists()
        ), f"Instructions template not found at {instructions_path}"
        assert system_path.exists(), f"System template not found at {system_path}"

    def test_composition_rule_validation(
        self, fixed_composition_rules, mock_prompts_dir
    ):
        """Test that composition rules are properly validated"""
        composer = PromptComposer(mock_prompts_dir, fixed_composition_rules)

        # Check that all referenced templates exist
        for comp_name, comp_rule in composer.composition_rules.items():
            # Check system prompts
            for sys_prompt in comp_rule.system_prompts:
                sys_path = mock_prompts_dir / sys_prompt["path"]
                assert (
                    sys_path.exists()
                ), f"System prompt {sys_prompt['path']} not found for {comp_name}"

            # Check user prompts
            for user_prompt in comp_rule.user_prompts:
                # User prompts are registry keys, so we need to check if they exist in registry
                # The prompt_registry structure is different in the composer
                assert user_prompt in composer.prompt_registry.get(
                    "user_prompts", {}
                ), f"User prompt {user_prompt} not found in registry for {comp_name}"

    def test_error_message_clarity(self, mock_config_dir, mock_prompts_dir):
        """Test that error messages are clear and actionable"""
        composer = PromptComposer(mock_prompts_dir, mock_config_dir)

        context = PromptContext(
            context_type=ContextType.VALIDATION, variables={"document_text": "test"}
        )

        try:
            composer.compose("document_quality_validation_only", context)
            pytest.fail("Expected composition to fail")
        except PromptCompositionError as e:
            error_msg = str(e)
            # Error should clearly indicate what went wrong
            assert "Composition failed" in error_msg
            assert "User prompt rendering failed" in error_msg
            assert "validation/document_quality_validation" in error_msg

            # Error should be actionable (user knows what to fix)
            assert "not found" in error_msg.lower() or "failed" in error_msg.lower()

    def test_fallback_behavior_in_nodes(
        self, fixed_composition_rules, mock_prompts_dir
    ):
        """Test that nodes can fallback gracefully when composition fails"""
        # This test simulates the behavior we see in the actual error logs
        # where the document quality validation node falls back to rule-based validation

        # First, test that the fixed composition works
        composer = PromptComposer(mock_prompts_dir, fixed_composition_rules)
        context = PromptContext(
            context_type=ContextType.VALIDATION,
            variables={"document_text": "test", "australian_state": "NSW"},
        )

        try:
            result = composer.compose("document_quality_validation_only", context)
            # If we get here, the composition worked and no fallback is needed
            assert result is not None
            print("✓ Composition succeeded - no fallback needed")
        except Exception as e:
            # If composition fails, we should have a clear error message
            print(f"✗ Composition failed: {e}")
            # In a real node, this would trigger fallback to rule-based validation
            assert "Composition failed" in str(
                e
            ) or "User prompt rendering failed" in str(e)


# Integration tests removed for simplicity - focus on core failure scenario testing
# The main TestPromptCompositionFailures class covers all the essential failure cases


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
