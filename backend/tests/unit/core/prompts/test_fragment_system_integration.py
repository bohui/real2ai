"""Integration tests for the complete fragment system redesign"""

import pytest
import tempfile
import shutil
from pathlib import Path
from app.core.prompts.fragment_manager import FragmentManager
from app.core.prompts.validators import FragmentSystemValidator


class TestFragmentSystemIntegration:
    """Test the complete fragment system with realistic scenarios"""

    def setup_method(self):
        """Set up realistic test fragment structure"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create realistic folder structure as per PRD
        self._create_folder_structure()
        self._create_realistic_fragments()

        self.manager = FragmentManager(self.temp_dir)
        self.validator = FragmentSystemValidator(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_folder_structure(self):
        """Create folder structure according to PRD"""
        folders = [
            "state_requirements/NSW",
            "state_requirements/VIC",
            "state_requirements/QLD",
            "contract_types/purchase",
            "contract_types/lease",
            "contract_types/option",
            "user_experience/novice",
            "user_experience/intermediate",
            "user_experience/expert",
            "analysis_depth/comprehensive",
            "analysis_depth/quick",
            "analysis_depth/focused",
            "consumer_protection/cooling_off",
            "consumer_protection/statutory_warranties",
            "consumer_protection/unfair_terms",
            "risk_factors",
            "shared",
        ]

        for folder in folders:
            (self.temp_dir / folder).mkdir(parents=True)

    def _create_realistic_fragments(self):
        """Create realistic fragment examples"""
        # NSW state requirements
        self._create_fragment(
            "state_requirements/NSW/planning_certificates.md",
            {
                "category": "legal_requirement",
                "context": {"state": "NSW", "contract_type": "*"},
                "priority": 80,
                "version": "1.0.0",
                "description": "NSW Section 149 planning certificate requirements",
                "tags": ["nsw", "planning", "certificates"],
            },
            """### NSW Section 149 Planning Certificates

**Critical NSW Requirement**: Section 149 planning certificates must be provided under NSW Conveyancing Act.

**Key Information to Verify**:
- Zoning Classification: Residential, commercial, industrial designation
- Development Restrictions: Height limits, floor space ratios, setbacks
- Heritage Listings: Conservation areas or individual listings""",
        )

        # VIC state requirements
        self._create_fragment(
            "state_requirements/VIC/vendor_statements.md",
            {
                "category": "legal_requirement",
                "context": {"state": "VIC", "contract_type": "*"},
                "priority": 85,
                "version": "1.0.0",
                "description": "Victorian vendor statement requirements",
            },
            """### Victorian Vendor Statement Requirements

**Section 32 Statement**: Must be provided before contract signing.

**Key Components**:
- Property details and title information
- Planning and building permits
- Outgoings and rates information""",
        )

        # Purchase contract specifics
        self._create_fragment(
            "contract_types/purchase/settlement_requirements.md",
            {
                "category": "contract_specific",
                "context": {"state": "*", "contract_type": "purchase"},
                "priority": 70,
                "version": "1.0.0",
            },
            """### Purchase Settlement Requirements

**Settlement Process**:
- Final inspection before settlement
- Balance payment on settlement date
- Title transfer and registration""",
        )

        # User experience - novice
        self._create_fragment(
            "user_experience/novice/first_time_buyer.md",
            {
                "category": "guidance",
                "context": {
                    "user_experience": "novice",
                    "contract_type": ["purchase", "option"],
                },
                "priority": 60,
                "version": "1.0.0",
            },
            """### First Time Buyer Guidance

**Important Steps**:
- Understand cooling off periods
- Arrange building and pest inspections
- Secure finance pre-approval""",
        )

        # Consumer protection (universal)
        self._create_fragment(
            "consumer_protection/cooling_off/framework.md",
            {
                "category": "consumer_protection",
                "context": {},  # Universal - applies to all
                "priority": 90,
                "version": "1.0.0",
            },
            """### Cooling Off Rights

**Universal Protection**: All states provide cooling off periods for residential property purchases.

**Key Rights**:
- Right to withdraw within cooling off period
- Penalty limitations for early withdrawal
- Exceptions for auction purchases""",
        )

        # Analysis depth - comprehensive
        self._create_fragment(
            "analysis_depth/comprehensive/detailed_risk_matrix.md",
            {
                "category": "analysis",
                "context": {"analysis_depth": "comprehensive"},
                "priority": 75,
                "version": "1.0.0",
            },
            """### Comprehensive Risk Analysis

**Detailed Risk Assessment Matrix**:
- Financial risks: Market volatility, interest rate changes
- Legal risks: Title defects, planning restrictions
- Physical risks: Structural issues, environmental hazards""",
        )

    def _create_fragment(self, path: str, metadata: dict, content: str):
        """Helper to create fragment files"""
        fragment_path = self.temp_dir / path

        import yaml

        frontmatter = yaml.dump(metadata, default_flow_style=False)
        full_content = f"---\n{frontmatter}---\n\n{content}"

        fragment_path.write_text(full_content, encoding="utf-8")

    def test_realistic_nsw_purchase_novice_comprehensive(self):
        """Test realistic scenario: NSW purchase for novice user with comprehensive analysis"""
        runtime_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
            "analysis_depth": "comprehensive",
        }

        result = self.manager.compose_fragments(runtime_context)

        # Should include NSW state requirements
        assert "state_requirements" in result
        assert "NSW Section 149 Planning Certificates" in result["state_requirements"]
        assert "Victorian Vendor Statement" not in result["state_requirements"]

        # Should include purchase contract specifics
        assert "contract_types" in result
        assert "Purchase Settlement Requirements" in result["contract_types"]

        # Should include novice user guidance
        assert "user_experience" in result
        assert "First Time Buyer Guidance" in result["user_experience"]

        # Should include comprehensive analysis
        assert "analysis_depth" in result
        assert "Comprehensive Risk Analysis" in result["analysis_depth"]

        # Should include universal consumer protection
        assert "consumer_protection" in result
        assert "Cooling Off Rights" in result["consumer_protection"]

    def test_vic_lease_expert_quick_analysis(self):
        """Test different scenario: VIC lease for expert user with quick analysis"""
        runtime_context = {
            "state": "VIC",
            "contract_type": "lease",
            "user_experience": "expert",
            "analysis_depth": "quick",
        }

        result = self.manager.compose_fragments(runtime_context)

        # Should include VIC state requirements
        assert "Victorian Vendor Statement" in result["state_requirements"]
        assert "NSW Section 149" not in result["state_requirements"]

        # Should NOT include purchase-specific content
        assert "Purchase Settlement Requirements" not in result["contract_types"]

        # Should NOT include novice guidance
        assert "First Time Buyer Guidance" not in result["user_experience"]

        # Should NOT include comprehensive analysis
        assert "Comprehensive Risk Analysis" not in result["analysis_depth"]

        # Should still include universal consumer protection
        assert "Cooling Off Rights" in result["consumer_protection"]

    def test_template_composition_end_to_end(self):
        """Test complete template composition with realistic base template"""
        base_template = """# Contract Analysis Report

## State-Specific Legal Requirements
{{ state_requirements }}

## Contract Type Analysis  
{{ contract_types }}

## User Guidance
{{ user_experience }}

## Analysis Details
{{ analysis_depth }}

## Consumer Protection Information
{{ consumer_protection }}

## Risk Assessment
{{ risk_factors }}
"""

        runtime_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
            "analysis_depth": "comprehensive",
        }

        # Use the composer method directly
        from app.core.prompts.composer import PromptComposer
        from pathlib import Path

        composer = PromptComposer(
            prompts_dir=self.temp_dir.parent, config_dir=self.temp_dir.parent / "config"
        )
        composer.folder_fragment_manager = self.manager

        result = composer.compose_with_folder_fragments(
            base_template=base_template, runtime_context=runtime_context
        )

        # Check that template was properly composed
        assert "# Contract Analysis Report" in result
        assert "NSW Section 149 Planning Certificates" in result
        assert "Purchase Settlement Requirements" in result
        assert "First Time Buyer Guidance" in result
        assert "Comprehensive Risk Analysis" in result
        assert "Cooling Off Rights" in result

        # Check that VIC content is not included
        assert "Victorian Vendor Statement" not in result

    def test_system_validation_passes(self):
        """Test that the realistic system passes validation"""
        validation = self.validator.validate_complete_system()

        assert validation["valid"] is True
        assert len(validation["issues"]) == 0
        assert validation["summary"]["total_groups"] == 7
        assert validation["summary"]["total_fragments"] == 6

    def test_empty_groups_render_as_empty_strings(self):
        """Test that groups with no matching fragments render as empty strings"""
        runtime_context = {
            "state": "SA",  # No SA fragments exist
            "contract_type": "commercial",  # No commercial fragments exist
            "user_experience": "expert",
            "analysis_depth": "quick",
        }

        result = self.manager.compose_fragments(runtime_context)

        # Groups with no matches should be empty
        assert result["state_requirements"] == ""
        assert result["contract_types"] == ""

        # Universal consumer protection should still be included
        assert result["consumer_protection"] != ""
        assert "Cooling Off Rights" in result["consumer_protection"]

    def test_multiple_list_matching(self):
        """Test fragments with list context values"""
        # Create fragment that matches multiple contract types
        self._create_fragment(
            "user_experience/expert/multi_contract_analysis.md",
            {
                "category": "guidance",
                "context": {
                    "user_experience": "expert",
                    "contract_type": ["purchase", "option"],  # List matching
                },
                "priority": 65,
            },
            "Advanced analysis for purchase and option contracts",
        )

        # Test purchase context (should match)
        result_purchase = self.manager.compose_fragments(
            {"state": "NSW", "contract_type": "purchase", "user_experience": "expert"}
        )

        assert (
            "Advanced analysis for purchase and option"
            in result_purchase["user_experience"]
        )

        # Test option context (should match)
        result_option = self.manager.compose_fragments(
            {"state": "NSW", "contract_type": "option", "user_experience": "expert"}
        )

        assert (
            "Advanced analysis for purchase and option"
            in result_option["user_experience"]
        )

        # Test lease context (should NOT match)
        result_lease = self.manager.compose_fragments(
            {"state": "NSW", "contract_type": "lease", "user_experience": "expert"}
        )

        assert (
            "Advanced analysis for purchase and option"
            not in result_lease["user_experience"]
        )

    def test_priority_ordering(self):
        """Test that fragments are included in priority order"""
        # Add another NSW fragment with different priority
        self._create_fragment(
            "state_requirements/NSW/additional_requirements.md",
            {
                "context": {"state": "NSW"},
                "priority": 95,  # Higher than planning certificates (80)
            },
            "Additional NSW requirements (high priority)",
        )

        result = self.manager.compose_fragments(
            {"state": "NSW", "contract_type": "purchase"}
        )

        state_content = result["state_requirements"]

        # Higher priority content should appear first
        high_priority_pos = state_content.find("Additional NSW requirements")
        lower_priority_pos = state_content.find("NSW Section 149 Planning")

        assert high_priority_pos < lower_priority_pos
