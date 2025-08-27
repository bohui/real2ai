"""
Tests for the RiskCategory enum.

This test file covers:
- RiskCategory enum values and validation
- Integration with risk models
- Risk categorization logic
"""

import pytest
from app.schema.enums.risk import RiskCategory, RiskSeverity
from backend.app.prompts.schema.diagram_analysis.diagram_risk_schema import (
    BoundaryRisk,
    InfrastructureRisk,
    EnvironmentalRisk,
    DevelopmentRisk,
    DiagramReference,
)
from app.schema.enums import DiagramType, ConfidenceLevel


class TestRiskCategory:
    """Test RiskCategory enum"""

    def test_risk_category_values(self):
        """Test that RiskCategory has the expected values"""
        assert RiskCategory.INFRASTRUCTURE == "infrastructure"
        assert RiskCategory.ENVIRONMENTAL == "environmental"
        assert RiskCategory.BOUNDARY == "boundary"
        assert RiskCategory.DEVELOPMENT == "development"
        assert RiskCategory.EASEMENT == "easement"
        assert RiskCategory.ZONING == "zoning"
        assert RiskCategory.DISCREPANCY == "discrepancy"
        assert RiskCategory.ACCESS == "access"
        assert RiskCategory.COMPLIANCE == "compliance"
        assert RiskCategory.LEGAL == "legal"
        assert RiskCategory.OTHER == "other"

    def test_risk_category_enumeration(self):
        """Test that all expected RiskCategory values are present"""
        expected_values = {
            "infrastructure",
            "environmental",
            "boundary",
            "development",
            "easement",
            "zoning",
            "discrepancy",
            "access",
            "compliance",
            "legal",
            "other",
        }
        actual_values = {risk_category.value for risk_category in RiskCategory}
        assert actual_values == expected_values

    def test_risk_category_string_behavior(self):
        """Test that RiskCategory behaves like strings"""
        risk_category = RiskCategory.INFRASTRUCTURE
        assert risk_category == "infrastructure"
        assert risk_category.value == "infrastructure"
        assert risk_category in ["infrastructure", "environmental", "boundary"]

    def test_risk_category_comparison(self):
        """Test RiskCategory comparison operations"""
        # String enums don't support comparison operators, so test equality and membership
        assert RiskCategory.INFRASTRUCTURE == "infrastructure"
        assert RiskCategory.BOUNDARY == "boundary"
        assert RiskCategory.DEVELOPMENT == "development"
        assert RiskCategory.EASEMENT == "easement"
        assert RiskCategory.ZONING == "zoning"
        assert RiskCategory.COMPLIANCE == "compliance"

    def test_risk_category_in_risk_models(self):
        """Test RiskCategory integration with risk models"""
        # Test infrastructure risk
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk = InfrastructureRisk(
            risk_type="sewer_main",
            description="Test infrastructure risk",
            severity=RiskSeverity.MODERATE,
            linked_diagrams=[diagram_ref],
            pipe_location="Under eastern boundary",
            maintenance_access="3m easement required",
        )

        # Verify the risk was created successfully
        assert risk.risk_type == "sewer_main"
        assert risk.severity == RiskSeverity.MODERATE

        # Test boundary risk
        boundary_risk = BoundaryRisk(
            risk_type="encroachment",
            description="Test boundary risk",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            affected_boundaries=["Eastern boundary"],
            potential_impact="May require legal action",
        )

        assert boundary_risk.risk_type == "encroachment"
        assert boundary_risk.severity == RiskSeverity.MAJOR

    def test_risk_category_validation(self):
        """Test that RiskCategory validation works correctly"""
        # Test valid risk categories
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk = EnvironmentalRisk(
            risk_type="flood_zone",
            description="Test environmental risk",
            severity=RiskSeverity.MINOR,
            linked_diagrams=[diagram_ref],
            environmental_factor="flooding",
            mitigation_required="Elevation assessment needed",
        )

        assert risk.risk_type == "flood_zone"

        # Test that RiskCategory enum validation works
        assert RiskCategory("environmental") == RiskCategory.ENVIRONMENTAL
        assert RiskCategory("infrastructure") == RiskCategory.INFRASTRUCTURE

    def test_risk_category_logical_grouping(self):
        """Test logical grouping of risk categories"""
        # Physical/Infrastructure risks
        physical_risks = {
            RiskCategory.INFRASTRUCTURE,
            RiskCategory.ENVIRONMENTAL,
            RiskCategory.BOUNDARY,
            RiskCategory.ACCESS,
        }

        # Legal/Regulatory risks
        legal_risks = {RiskCategory.LEGAL, RiskCategory.COMPLIANCE, RiskCategory.ZONING}

        # Development/Construction risks
        development_risks = {
            RiskCategory.DEVELOPMENT,
            RiskCategory.EASEMENT,
            RiskCategory.DISCREPANCY,
        }

        # Other risks
        other_risks = {RiskCategory.OTHER}

        # Verify no overlap between logical groups
        all_risks = physical_risks | legal_risks | development_risks | other_risks
        assert len(all_risks) == len(RiskCategory)

        # Verify each risk appears in exactly one logical group
        for risk_category in RiskCategory:
            group_count = sum(
                1
                for group in [
                    physical_risks,
                    legal_risks,
                    development_risks,
                    other_risks,
                ]
                if risk_category in group
            )
            assert (
                group_count == 1
            ), f"Risk {risk_category} appears in {group_count} groups"

    def test_risk_category_cross_cutting_risks(self):
        """Test cross-cutting risks that span multiple categories"""
        # Test a risk that affects multiple categories
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        # Create infrastructure risk that also affects environmental and access
        cross_cutting_risk = InfrastructureRisk(
            risk_type="sewer_easement",
            description="Sewer easement affecting development and access",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            sewer_pipe_location="Under eastern boundary",
            maintenance_access_requirements="3m easement required",
        )

        # Verify cross-cutting risk was created
        assert cross_cutting_risk.risk_type == "sewer_easement"
        assert cross_cutting_risk.severity == RiskSeverity.MAJOR
        assert cross_cutting_risk.sewer_pipe_location == "Under eastern boundary"

        # This demonstrates how one physical situation (sewer easement) can be categorized
        # as infrastructure but also affect environmental, access, and compliance aspects

    def test_risk_category_serialization(self):
        """Test that RiskCategory can be serialized and deserialized"""
        # Test JSON serialization (enum values are strings)
        import json

        data = {
            "primary_category": RiskCategory.INFRASTRUCTURE,
            "secondary_categories": [RiskCategory.ENVIRONMENTAL, RiskCategory.ACCESS],
        }

        json_str = json.dumps(data)
        assert '"infrastructure"' in json_str
        assert '"environmental"' in json_str
        assert '"access"' in json_str

        # Test deserialization
        deserialized = json.loads(json_str)
        assert deserialized["primary_category"] == "infrastructure"
        assert "environmental" in deserialized["secondary_categories"]
        assert "access" in deserialized["secondary_categories"]

    def test_risk_category_iteration(self):
        """Test that RiskCategory can be iterated over"""
        # Test iteration over all values
        risk_categories = list(RiskCategory)
        assert len(risk_categories) == 11  # 11 risk categories

        # Test that all values are unique
        assert len(set(risk_categories)) == len(risk_categories)

        # Test specific categories are present
        assert RiskCategory.INFRASTRUCTURE in risk_categories
        assert RiskCategory.BOUNDARY in risk_categories
        assert RiskCategory.ENVIRONMENTAL in risk_categories

    def test_risk_category_string_operations(self):
        """Test that RiskCategory works with common string operations"""
        # Test string concatenation
        primary = RiskCategory.INFRASTRUCTURE
        secondary = RiskCategory.ENVIRONMENTAL

        combined = f"{primary.value}_and_{secondary.value}"
        assert combined == "infrastructure_and_environmental"

        # Test string methods
        assert primary.upper() == "INFRASTRUCTURE"
        assert secondary.capitalize() == "Environmental"
        assert RiskCategory.BOUNDARY.title() == "Boundary"

    def test_risk_category_in_collections(self):
        """Test that RiskCategory works properly in collections"""
        # Test in sets
        high_risk_categories = {
            RiskCategory.INFRASTRUCTURE,
            RiskCategory.BOUNDARY,
            RiskCategory.LEGAL,
        }
        assert RiskCategory.INFRASTRUCTURE in high_risk_categories
        assert RiskCategory.ENVIRONMENTAL not in high_risk_categories

        # Test in dictionaries
        risk_descriptions = {
            RiskCategory.INFRASTRUCTURE: "Infrastructure and utility risks",
            RiskCategory.BOUNDARY: "Boundary and encroachment risks",
            RiskCategory.ENVIRONMENTAL: "Environmental and natural disaster risks",
        }
        assert (
            risk_descriptions[RiskCategory.INFRASTRUCTURE]
            == "Infrastructure and utility risks"
        )

        # Test in lists
        risk_list = [
            RiskCategory.INFRASTRUCTURE,
            RiskCategory.BOUNDARY,
            RiskCategory.ENVIRONMENTAL,
        ]
        assert RiskCategory.INFRASTRUCTURE in risk_list
        assert RiskCategory.LEGAL not in risk_list

    def test_risk_category_validation_edge_cases(self):
        """Test RiskCategory validation edge cases"""
        # Test valid values
        assert RiskCategory("infrastructure") == RiskCategory.INFRASTRUCTURE
        assert RiskCategory("boundary") == RiskCategory.BOUNDARY
        assert RiskCategory("environmental") == RiskCategory.ENVIRONMENTAL

        # Test invalid values raise ValueError
        with pytest.raises(ValueError):
            RiskCategory("invalid_risk_category")

        with pytest.raises(ValueError):
            RiskCategory("")

        with pytest.raises(ValueError):
            RiskCategory(None)

    def test_risk_category_comprehensive_usage(self):
        """Test comprehensive usage of RiskCategory in risk assessment scenarios"""
        # Create a comprehensive risk assessment with different risk types
        comprehensive_risks = []

        # Create diagram reference for all risks
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        # Infrastructure risks
        comprehensive_risks.append(
            InfrastructureRisk(
                risk_type="sewer_main",
                description="Sewer main under property",
                severity=RiskSeverity.MAJOR,
                linked_diagrams=[diagram_ref],
                sewer_pipe_location="Under building envelope",
                maintenance_access_requirements="3m easement required",
            )
        )

        # Environmental risks
        comprehensive_risks.append(
            EnvironmentalRisk(
                risk_type="flood_zone",
                description="Property in flood zone",
                severity=RiskSeverity.MODERATE,
                linked_diagrams=[diagram_ref],
                environmental_factor="flooding",
                mitigation_required="Elevation assessment needed",
            )
        )

        # Boundary risks
        comprehensive_risks.append(
            BoundaryRisk(
                risk_type="encroachment",
                description="Boundary dispute with neighbor",
                severity=RiskSeverity.MAJOR,
                linked_diagrams=[diagram_ref],
                affected_boundaries=["Eastern boundary"],
                encroachment_details="Shed extends 0.5m over boundary",
                potential_impact="May require legal action or negotiation",
            )
        )

        # Development risks
        comprehensive_risks.append(
            DevelopmentRisk(
                risk_type="height_restriction",
                description="Building height restrictions",
                severity=RiskSeverity.MINOR,
                linked_diagrams=[diagram_ref],
                development_constraint="Maximum height 8.5m",
                current_plan_height="7.2m",
            )
        )

        # Verify all risks were created successfully
        assert len(comprehensive_risks) == 4

        # Verify each risk has the correct type and severity
        for risk in comprehensive_risks:
            assert risk.risk_type is not None
            assert risk.severity in RiskSeverity
            assert isinstance(risk.severity, RiskSeverity)

        # Verify risk types are diverse
        risk_types = {risk.risk_type for risk in comprehensive_risks}
        assert len(risk_types) == 4  # All different risk types
        assert "sewer_main" in risk_types
        assert "flood_zone" in risk_types
        assert "encroachment" in risk_types
        assert "height_restriction" in risk_types
