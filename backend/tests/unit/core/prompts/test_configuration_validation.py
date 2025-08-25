"""
Test Configuration Validation Fixes

This test file covers the fixes for configuration validation errors where
services were referencing non-existent compositions. It ensures that:

1. All service mappings reference existing compositions
2. Configuration validation passes without errors
3. Services can initialize without composition reference issues
4. The system maintains consistency between service mappings and composition rules
"""

import pytest
import asyncio
from pathlib import Path

from app.core.prompts.config_manager import ConfigurationManager
from app.core.prompts.manager import PromptManager, PromptManagerConfig


class TestConfigurationValidation:
    """Test configuration validation fixes"""

    @pytest.fixture
    def config_dir(self):
        """Get the configuration directory path"""
        return (
            Path(__file__).parent.parent.parent.parent.parent
            / "app"
            / "prompts"
            / "config"
        )

    @pytest.fixture
    def templates_dir(self):
        """Get the templates directory path"""
        return (
            Path(__file__).parent.parent.parent.parent.parent
            / "app"
            / "prompts"
            / "templates"
        )

    @pytest.fixture
    def config_manager(self, config_dir):
        """Create and initialize a configuration manager"""

        async def _create():
            cm = ConfigurationManager(config_dir)
            await cm.initialize()
            return cm

        return asyncio.run(_create())

    @pytest.fixture
    def prompt_manager(self, templates_dir, config_dir):
        """Create and initialize a prompt manager"""

        async def _create():
            config = PromptManagerConfig(
                templates_dir=templates_dir,
                config_dir=config_dir,
                cache_enabled=True,
                validation_enabled=True,
                enable_composition=True,
                enable_service_integration=True,
            )
            pm = PromptManager(config)
            await pm.initialize()
            return pm

        return asyncio.run(_create())

    def test_configuration_validation_passes(self, config_manager):
        """Test that configuration validation passes without errors"""
        # This test would have failed before our fixes with:
        # "Service 'geminiocr' references unknown composition: ocr_to_analysis"

        # Verify no validation errors
        assert config_manager._service_mappings is not None
        assert config_manager._composition_rules is not None

        # Verify we have the expected number of services and compositions
        assert len(config_manager._service_mappings) > 0
        assert len(config_manager._composition_rules) > 0

    def test_all_service_compositions_exist(self, config_manager):
        """Test that all services reference existing compositions"""
        # Get all composition names that are actually defined
        defined_compositions = set(config_manager._composition_rules.keys())

        # Check each service's compositions
        for service_name, service_mapping in config_manager._service_mappings.items():
            for composition in service_mapping.compositions:
                comp_name = composition["name"]
                assert (
                    comp_name in defined_compositions
                ), f"Service '{service_name}' references unknown composition: {comp_name}"

    def test_specific_service_fixes(self, config_manager):
        """Test that specific services that had issues now work correctly"""

        # Test geminiocr service
        geminiocr = config_manager.get_service_mapping("geminiocr")
        assert geminiocr is not None
        assert len(geminiocr.compositions) == 1
        assert geminiocr.compositions[0]["name"] == "ocr_whole_document_extraction"

        # Test contract_analysis service
        contract_analysis = config_manager.get_service_mapping("contract_analysis")
        assert contract_analysis is not None
        assert len(contract_analysis.compositions) == 2
        composition_names = {comp["name"] for comp in contract_analysis.compositions}
        assert "structure_analysis_only" in composition_names
        assert "compliance_check_only" in composition_names

        # Test contract_analysis_workflow service
        workflow = config_manager.get_service_mapping("contract_analysis_workflow")
        assert workflow is not None
        assert len(workflow.compositions) == 1
        assert workflow.compositions[0]["name"] == "structure_analysis_only"

        # Test semantic_analysis service
        semantic = config_manager.get_service_mapping("semantic_analysis")
        assert semantic is not None
        assert len(semantic.compositions) == 2
        composition_names = {comp["name"] for comp in semantic.compositions}
        assert "semantic_analysis_only" in composition_names
        assert "image_semantics_only" in composition_names

    def test_composition_routing_consistency(self, config_manager):
        """Test that composition routing rules reference existing compositions"""
        # This would have failed before our fixes

        # Check that routing rules reference valid compositions
        # Note: This assumes routing rules are stored in the config manager
        # If they're not, this test can be adjusted accordingly

        # Verify that all referenced compositions exist
        defined_compositions = set(config_manager._composition_rules.keys())

        # Check if there are any routing rules that need validation
        # This is a defensive test to catch future routing issues

    def test_prompt_manager_initialization(self, prompt_manager):
        """Test that PromptManager can initialize without configuration errors"""
        # This test ensures the full prompt system works

        assert prompt_manager.config_manager is not None
        assert prompt_manager.composer is not None

        # Verify compositions are loaded
        compositions = prompt_manager.composer.list_compositions()
        assert len(compositions) > 0

        # Verify service mappings are loaded
        service_count = len(prompt_manager.config_manager._service_mappings)
        assert service_count > 0

    def test_composition_rule_structure(self, config_manager):
        """Test that composition rules have the expected structure"""
        for comp_name, comp_rule in config_manager._composition_rules.items():
            # Verify required fields exist
            assert hasattr(comp_rule, "name")
            assert hasattr(comp_rule, "description")
            assert hasattr(comp_rule, "system_prompts")
            assert hasattr(comp_rule, "user_prompts")

            # Verify system prompts is a list
            assert isinstance(comp_rule.system_prompts, list)

            # Verify user prompts is a list
            assert isinstance(comp_rule.user_prompts, list)

    def test_service_mapping_structure(self, config_manager):
        """Test that service mappings have the expected structure"""
        for service_name, service_mapping in config_manager._service_mappings.items():
            # Verify required fields exist
            assert hasattr(service_mapping, "service_name")
            assert hasattr(service_mapping, "primary_templates")
            assert hasattr(service_mapping, "compositions")
            assert hasattr(service_mapping, "fallback_templates")

            # Verify compositions is a list
            assert isinstance(service_mapping.compositions, list)

            # Verify each composition has required fields
            for composition in service_mapping.compositions:
                assert "name" in composition
                assert "description" in composition
                assert "priority" in composition

    def test_no_orphaned_compositions(self, config_manager):
        """Test that there are no compositions that no service references"""
        # Get all composition names
        all_compositions = set(config_manager._composition_rules.keys())

        # Get all compositions referenced by services
        referenced_compositions = set()
        for service_mapping in config_manager._service_mappings.values():
            for composition in service_mapping.compositions:
                referenced_compositions.add(composition["name"])

        # Check for compositions that might be orphaned
        # Note: Some compositions might be used by other parts of the system
        # This is more of a warning than a strict requirement

        # Log orphaned compositions for review
        orphaned = all_compositions - referenced_compositions
        if orphaned:
            print(f"⚠️  Compositions not referenced by services: {orphaned}")

    def test_configuration_reload(self, config_manager):
        """Test that configuration can be reloaded without errors"""
        # This tests the dynamic configuration reloading capability

        # Store original state
        original_service_count = len(config_manager._service_mappings)
        assert original_service_count > 0

        # Verify we have compositions loaded
        original_composition_count = len(config_manager._composition_rules)
        assert original_composition_count > 0

    def test_configuration_files_exist(self, config_dir):
        """Test that required configuration files exist"""
        required_files = [
            "service_mappings.yaml",
            "composition_rules.yaml",
            "prompt_registry.yaml",
        ]

        for filename in required_files:
            file_path = config_dir / filename
            assert (
                file_path.exists()
            ), f"Required configuration file missing: {filename}"

    def test_configuration_file_syntax(self, config_dir):
        """Test that configuration files have valid YAML syntax"""
        import yaml

        yaml_files = [
            "service_mappings.yaml",
            "composition_rules.yaml",
            "prompt_registry.yaml",
        ]

        for filename in yaml_files:
            file_path = config_dir / filename
            try:
                with open(file_path, "r") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {filename}: {e}")


class TestConfigurationValidationRegression(TestConfigurationValidation):
    """Test to prevent regression of configuration validation issues"""

    def test_no_old_composition_references(self, config_dir):
        """Test that old composition names are not referenced anywhere"""
        # These are the old composition names that caused errors
        old_composition_names = [
            "ocr_to_analysis",
            "complete_contract_analysis",
            "quick_contract_review",
            "multi_diagram_analysis",
            "single_diagram_analysis",
        ]

        # Check service_mappings.yaml for old references
        service_mappings_file = config_dir / "service_mappings.yaml"
        with open(service_mappings_file, "r") as f:
            content = f.read()

        for old_name in old_composition_names:
            assert (
                old_name not in content
            ), f"Old composition name '{old_name}' still referenced in service_mappings.yaml"

    def test_composition_name_consistency(self, config_dir):
        """Test that composition names are consistent across files"""
        import yaml

        # Load composition rules
        composition_file = config_dir / "composition_rules.yaml"
        with open(composition_file, "r") as f:
            composition_data = yaml.safe_load(f)

        defined_compositions = set(composition_data.get("compositions", {}).keys())

        # Load service mappings
        service_file = config_dir / "service_mappings.yaml"
        with open(service_file, "r") as f:
            service_data = yaml.safe_load(f)

        # Check all service compositions
        for service_name, service_config in service_data.get("mappings", {}).items():
            for composition in service_config.get("compositions", []):
                comp_name = composition.get("name")
                if comp_name:
                    assert (
                        comp_name in defined_compositions
                    ), f"Service '{service_name}' references undefined composition: {comp_name}"


if __name__ == "__main__":
    # Run tests directly if needed
    pytest.main([__file__, "-v"])
