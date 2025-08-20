"""Unit tests for FragmentManager covering the recent fixes"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import shutil
import yaml

from app.core.prompts.fragment_manager import (
    FragmentManager,
    Fragment,
)
from app.core.prompts.context import PromptContext


class TestFragment:
    """Test Fragment class fixes"""

    def test_fragment_with_tags(self):
        """Test Fragment creation with tags"""
        fragment = Fragment(
            name="test",
            path=Path("/tmp/test.md"),
            content="test content",
            metadata={"tags": ["tag1", "tag2"]},
            group="shared",
        )
        assert fragment.metadata.get("tags") == ["tag1", "tag2"]

    def test_fragment_without_tags(self):
        """Test Fragment creation without tags (should default to empty list)"""
        fragment = Fragment(
            name="test",
            path=Path("/tmp/test.md"),
            content="test content",
            metadata={},
            group="shared",
        )
        assert fragment.metadata.get("tags", []) == []


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
        # New FragmentManager signature takes only fragments_dir
        return FragmentManager(fragments_dir)

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
        manager = FragmentManager(fragments_dir)

        assert manager.fragments_dir == fragments_dir
        assert manager._fragment_cache == {}
        assert manager._groups_cache == {}

    def test_get_available_groups(self, fragment_manager, temp_dirs):
        fragments_dir, _ = temp_dirs
        (fragments_dir / "state_requirements").mkdir()
        (fragments_dir / "consumer_protection").mkdir()
        groups = fragment_manager.get_available_groups()
        assert "consumer_protection" in groups
        assert "state_requirements" in groups

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

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"test_var": "test_value"}
        )
        result = fragment_manager._evaluate_condition("test_var", context)
        assert result == "test_value"

    def test_evaluate_condition_without_condition(self, fragment_manager):
        """Test condition evaluation when condition is None (fix for optional condition)"""
        from app.core.prompts import ContextType

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"test_var": "test_value"}
        )
        result = fragment_manager._evaluate_condition(None, context)
        assert result is None

    def test_evaluate_condition_condition_not_in_context(self, fragment_manager):
        """Test condition evaluation when condition is not in context"""
        from app.core.prompts import ContextType

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"other_var": "other_value"}
        )
        result = fragment_manager._evaluate_condition("test_var", context)
        assert result is None

    def test_compose_with_folder_fragments_grouping_and_defaults(
        self, fragment_manager, temp_dirs
    ):
        """Test folder-driven composition groups and empty defaults."""
        fragments_dir, _ = temp_dirs

        # Create fragments in nested folders with frontmatter
        (fragments_dir / "state_requirements" / "NSW").mkdir(parents=True)
        (fragments_dir / "consumer_protection" / "cooling_off").mkdir(parents=True)

        (
            fragments_dir / "state_requirements" / "NSW" / "planning_certificates.md"
        ).write_text(
            "---\ncontext: {state: NSW}\npriority: 10\n---\nNSW Planning Certificates"
        )
        (
            fragments_dir / "consumer_protection" / "cooling_off" / "framework.md"
        ).write_text("---\ncontext: {}\npriority: 5\n---\nCooling Off Rights")

        from app.core.prompts import ContextType

        context = PromptContext(
            context_type=ContextType.ANALYSIS,
            variables={"state": "NSW", "contract_type": "purchase"},
        )

        base_template = (
            "State: {{ state_requirements }}\n"
            "State NSW: {{ state_requirements_NSW }}\n"
            "Consumer: {{ consumer_protection }}\n"
            "MissingGroup: {{ analysis_depth }}\n"
        )

        result = fragment_manager.compose_with_folder_fragments(base_template, context)

        assert "NSW Planning Certificates" in result
        assert "Cooling Off Rights" in result
        # Missing groups render as empty string
        assert "MissingGroup: \n" in result


class TestFragmentManagerIntegration:
    """Integration tests for FragmentManager"""

    # Removed orchestrator-based tests; folder-driven system no longer uses external orchestrator configs


class TestComposeWithFolderFragments(TestFragmentManager):
    """Tests for folder-driven composition"""

    def test_custom_filters_are_available(self, fragment_manager, temp_dirs):
        fragments_dir, _ = temp_dirs
        (fragments_dir / "shared").mkdir(parents=True)
        (fragments_dir / "shared" / "money.md").write_text(
            "---\ncontext: {}\n---\nAmount: {{ amount|currency }}"
        )

        from app.core.prompts import ContextType

        context = PromptContext(
            context_type=ContextType.ANALYSIS, variables={"amount": 1234.56}
        )

        base_template = "{{ shared }}"
        result = fragment_manager.compose_with_folder_fragments(base_template, context)
        assert "Amount: $1,234.56" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
