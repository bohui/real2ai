"""Tests for folder-based fragment management"""

import pytest
import tempfile
import shutil
from pathlib import Path
from app.core.prompts.fragment_manager import FragmentManager


class TestFragmentManagerFolderDriven:
    """Test the unified folder-structure-driven fragment manager"""

    def setup_method(self):
        """Set up test fixtures with temporary directory structure"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create test folder structure
        (self.temp_dir / "state_requirements" / "NSW").mkdir(parents=True)
        (self.temp_dir / "state_requirements" / "VIC").mkdir(parents=True)
        (self.temp_dir / "contract_types" / "purchase").mkdir(parents=True)
        (self.temp_dir / "contract_types" / "lease").mkdir(parents=True)
        (self.temp_dir / "user_experience").mkdir(parents=True)

        # Create test fragments
        self._create_test_fragment(
            "state_requirements/NSW/planning.md",
            {
                "category": "legal_requirement",
                "context": {"state": "NSW", "contract_type": "*"},
                "priority": 80,
            },
            "NSW planning requirements",
        )

        self._create_test_fragment(
            "state_requirements/VIC/vendor_statement.md",
            {
                "category": "legal_requirement",
                "context": {"state": "VIC", "contract_type": "*"},
                "priority": 85,
            },
            "VIC vendor statement requirements",
        )

        self._create_test_fragment(
            "contract_types/purchase/settlement.md",
            {
                "category": "contract_specific",
                "context": {"state": "*", "contract_type": "purchase"},
                "priority": 70,
            },
            "Purchase settlement requirements",
        )

        self._create_test_fragment(
            "contract_types/lease/rental.md",
            {
                "category": "contract_specific",
                "context": {"state": "*", "contract_type": "lease"},
                "priority": 70,
            },
            "Lease rental obligations",
        )

        self._create_test_fragment(
            "user_experience/novice_guide.md",
            {
                "category": "guidance",
                "context": {"user_experience": "novice"},
                "priority": 60,
            },
            "Novice user guidance",
        )

        # Fragment with no context (should match all)
        self._create_test_fragment(
            "user_experience/general_tips.md",
            {"category": "guidance", "priority": 50},
            "General tips for all users",
        )

        self.manager = FragmentManager(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_test_fragment(self, path: str, metadata: dict, content: str):
        """Helper to create test fragment files"""
        fragment_path = self.temp_dir / path
        fragment_path.parent.mkdir(parents=True, exist_ok=True)

        # Create frontmatter
        import yaml

        frontmatter = yaml.dump(metadata, default_flow_style=False)

        # Write file with frontmatter
        full_content = f"---\n{frontmatter}---\n\n{content}"
        fragment_path.write_text(full_content, encoding="utf-8")

    def test_get_available_groups(self):
        """Test getting available groups from folder structure"""
        groups = self.manager.get_available_groups()

        assert "state_requirements" in groups
        assert "contract_types" in groups
        assert "user_experience" in groups
        assert len(groups) == 3

    def test_load_fragments_for_group(self):
        """Test loading fragments for a specific group"""
        # Test state_requirements group
        fragments = self.manager.load_fragments_for_group("state_requirements")
        assert len(fragments) == 2

        # Check fragments are sorted by priority (highest first)
        assert fragments[0].priority == 85  # VIC vendor statement
        assert fragments[1].priority == 80  # NSW planning

        # Check group is correctly derived
        for fragment in fragments:
            assert fragment.group == "state_requirements"

    def test_compose_fragments_with_context(self):
        """Test composing fragments based on runtime context"""
        runtime_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
        }

        result = self.manager.compose_fragments(runtime_context)

        # Should have content for all groups
        assert "state_requirements" in result
        assert "contract_types" in result
        assert "user_experience" in result

        # Check specific matches
        assert "NSW planning requirements" in result["state_requirements"]
        assert "VIC vendor statement requirements" not in result["state_requirements"]

        assert "Purchase settlement requirements" in result["contract_types"]
        assert "Lease rental obligations" not in result["contract_types"]

        assert "Novice user guidance" in result["user_experience"]
        assert (
            "General tips for all users" in result["user_experience"]
        )  # No context matches all

    def test_compose_fragments_with_specific_groups(self):
        """Test composing only specific requested groups"""
        runtime_context = {"state": "NSW", "contract_type": "purchase"}

        result = self.manager.compose_fragments(
            runtime_context, requested_groups=["state_requirements"]
        )

        # Should only have requested group
        assert "state_requirements" in result
        assert "contract_types" not in result
        assert "user_experience" not in result

    def test_empty_group_returns_empty_string(self):
        """Test that groups with no matching fragments return empty string"""
        runtime_context = {
            "state": "QLD",  # No QLD fragments exist
            "contract_type": "purchase",
        }

        result = self.manager.compose_fragments(runtime_context)

        # state_requirements should be empty (no QLD fragments)
        assert result["state_requirements"] == ""

        # contract_types should have content (wildcard state matches)
        assert result["contract_types"] != ""
        assert "Purchase settlement requirements" in result["contract_types"]

    def test_validate_group_structure(self):
        """Test validation of folder structure and metadata"""
        validation = self.manager.validate_group_structure()

        assert validation["valid"] is True
        assert validation["total_groups"] == 3
        assert validation["total_fragments"] == 6
        assert len(validation["issues"]) == 0

    def test_validate_invalid_group_names(self):
        """Test validation catches invalid group names"""
        # Create invalid group name
        (self.temp_dir / "123invalid").mkdir()
        (self.temp_dir / "123invalid" / "test.md").write_text("content")

        manager = FragmentManager(self.temp_dir)
        validation = manager.validate_group_structure()

        assert validation["valid"] is False
        assert any("123invalid" in issue for issue in validation["issues"])

    def test_validate_deprecated_fields(self):
        """Test validation warns about deprecated metadata fields"""
        # Create fragment with deprecated fields
        self._create_test_fragment(
            "user_experience/deprecated.md",
            {
                "group": "old_group",  # Deprecated
                "domain": "legal",  # Deprecated
                "context": {"state": "*"},
            },
            "Fragment with deprecated fields",
        )

        validation = self.manager.validate_group_structure()

        assert len(validation["deprecated_warnings"]) >= 2
        assert any(
            "'group' field deprecated" in warning
            for warning in validation["deprecated_warnings"]
        )
        assert any(
            "'domain' field deprecated" in warning
            for warning in validation["deprecated_warnings"]
        )

    def test_cache_functionality(self):
        """Test fragment caching works correctly"""
        # Load fragments multiple times
        fragments1 = self.manager.load_fragments_for_group("state_requirements")
        fragments2 = self.manager.load_fragments_for_group("state_requirements")

        # Should return same objects (cached)
        assert fragments1 is fragments2

        # Clear cache and reload
        self.manager.clear_cache()
        fragments3 = self.manager.load_fragments_for_group("state_requirements")

        # Should be different objects but same content
        assert fragments1 is not fragments3
        assert len(fragments1) == len(fragments3)

    def test_multiple_fragments_in_group(self):
        """Test multiple fragments in same group are joined correctly"""
        # Add another NSW fragment
        self._create_test_fragment(
            "state_requirements/NSW/additional.md",
            {"context": {"state": "NSW"}, "priority": 75},
            "Additional NSW requirements",
        )

        runtime_context = {"state": "NSW", "contract_type": "purchase"}
        result = self.manager.compose_fragments(runtime_context)

        # Should contain both NSW fragments joined
        state_content = result["state_requirements"]
        assert "NSW planning requirements" in state_content
        assert "Additional NSW requirements" in state_content
        assert state_content.count("\n\n") >= 1  # Should be joined with double newlines

    def test_get_metrics(self):
        """Test metrics reporting"""
        # Load some fragments to populate cache
        self.manager.load_fragments_for_group("state_requirements")

        metrics = self.manager.get_metrics()

        assert metrics["total_groups"] == 3
        assert metrics["total_fragments"] == 6
        assert metrics["cached_groups"] == 1
        assert "state_requirements" in metrics["available_groups"]
