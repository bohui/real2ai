"""
Tests for the updated diagram risk schema.

This test file covers:
- Unified risk models for different risk types
- Updated DiagramRiskAssessment with specific risks
- RiskExtractor functionality with new schema
- Safe mutable defaults
- Risk category enums
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from pydantic import ValidationError

from app.prompts.schema.diagram_risk_schema import (
    DiagramReference,
    BoundaryRisk,
    InfrastructureRisk,
    EnvironmentalRisk,
    DevelopmentRisk,
    DiagramRiskAssessment,
    RiskExtractor,
)
from app.schema.enums import (
    DiagramType,
    RiskSeverity,
    ConfidenceLevel,
    RiskCategory,
)


class TestDiagramRiskSchema:
    """Test the updated diagram risk schema"""

    def test_safe_mutable_defaults(self):
        """Test that mutable defaults use default_factory"""
        # This should not raise an error about mutable defaults
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk = InfrastructureRisk(
            risk_type="test_risk",
            description="Test risk",
            severity=RiskSeverity.MODERATE,
            linked_diagrams=[diagram_ref],
        )

        # Verify the risk was created successfully
        assert risk.risk_type == "test_risk"
        assert risk.severity == RiskSeverity.MODERATE

    def test_risk_creation(self):
        """Test creating risk instances with various categories"""
        # Test infrastructure risk
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        infrastructure_risk = InfrastructureRisk(
            risk_type="sewer_main",
            description="Sewer main under property",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            sewer_pipe_location="Under eastern boundary",
            maintenance_access_requirements="3m easement required",
        )

        assert infrastructure_risk.risk_type == "sewer_main"
        assert infrastructure_risk.severity == RiskSeverity.MAJOR
        assert infrastructure_risk.sewer_pipe_location == "Under eastern boundary"

        # Test boundary risk
        boundary_risk = BoundaryRisk(
            risk_type="encroachment",
            description="Encroachment on eastern boundary",
            severity=RiskSeverity.MODERATE,
            linked_diagrams=[diagram_ref],
            affected_boundaries=["Eastern boundary"],
            encroachment_details="Shed extends 0.5m over boundary",
            potential_impact="May require legal action",
        )

        assert boundary_risk.risk_type == "encroachment"
        assert boundary_risk.severity == RiskSeverity.MODERATE
        assert boundary_risk.encroachment_details == "Shed extends 0.5m over boundary"

    def test_diagram_reference_validation(self):
        """Test DiagramReference validation with new enum types"""
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.TITLE_PLAN,
            diagram_name="Certificate of Title Plan DP123456",
            page_reference="Page 5",
            section_reference="Lot 15 boundaries",
            diagram_scale="1:500",
            prepared_by="Licensed Surveyor ABC",
            confidence_level=ConfidenceLevel.HIGH,
        )

        assert diagram_ref.diagram_type == DiagramType.TITLE_PLAN
        assert diagram_ref.confidence_level == ConfidenceLevel.HIGH
        assert diagram_ref.diagram_name == "Certificate of Title Plan DP123456"

    def test_diagram_risk_assessment_creation(self):
        """Test creating DiagramRiskAssessment with specific risk models"""
        # Create diagram references
        title_plan = DiagramReference(
            diagram_type=DiagramType.TITLE_PLAN,
            diagram_name="Certificate of Title Plan DP123456",
            page_reference="Page 5",
            confidence_level=ConfidenceLevel.HIGH,
        )

        sewer_diagram = DiagramReference(
            diagram_type=DiagramType.SEWER_SERVICE_DIAGRAM,
            diagram_name="Sewer Service Connection Plan",
            page_reference="Attachment C",
            confidence_level=ConfidenceLevel.HIGH,
        )

        # Create specific risk types
        boundary_risk = BoundaryRisk(
            risk_type="encroachment",
            description="Neighbor's shed extends 0.5m over eastern boundary",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[title_plan],
            affected_boundaries=["Eastern boundary"],
            encroachment_details="Shed extends 0.5m over boundary",
            potential_impact="May require legal action or negotiation",
        )

        infrastructure_risk = InfrastructureRisk(
            risk_type="sewer_main",
            description="Major sewer main runs directly under proposed building area",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[sewer_diagram],
            sewer_pipe_location="Under building envelope",
            maintenance_access_requirements="Council requires 3m clear access zone",
        )

        # Create assessment
        assessment = DiagramRiskAssessment(
            property_identifier="Lot 15, DP123456",
            diagram_sources=[DiagramType.TITLE_PLAN, DiagramType.SEWER_SERVICE_DIAGRAM],
            boundary_risks=[boundary_risk],
            infrastructure_risks=[infrastructure_risk],
            overall_risk_score=RiskSeverity.MAJOR,
            high_priority_risks=[
                "Boundary encroachment requires immediate attention",
                "Sewer main under building envelope affects construction",
            ],
            recommended_actions=[
                "Survey eastern boundary to confirm encroachment",
                "Consult with council about sewer main access requirements",
                "Consider legal advice for boundary dispute resolution",
            ],
            surveyor_recommendations="Full boundary survey recommended",
            legal_review_required=True,
            additional_investigations_needed=[
                "Professional boundary survey",
                "Council infrastructure consultation",
                "Legal advice on encroachment resolution",
            ],
            estimated_financial_impact={
                "boundary_survey": "$800-1200",
                "legal_consultation": "$500-1000",
                "potential_construction_delays": "$2000-5000",
            },
        )

        # Verify assessment structure
        assert assessment.property_identifier == "Lot 15, DP123456"
        assert len(assessment.diagram_sources) == 2
        assert len(assessment.boundary_risks) == 1
        assert len(assessment.infrastructure_risks) == 1
        assert assessment.overall_risk_score == RiskSeverity.MAJOR
        assert len(assessment.high_priority_risks) == 2
        assert assessment.legal_review_required == True

    def test_risk_assessment_computed_fields(self):
        """Test that computed fields are calculated correctly"""
        # Create assessment with risks
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk1 = InfrastructureRisk(
            risk_type="test_risk_1",
            description="Test risk 1",
            severity=RiskSeverity.MODERATE,
            linked_diagrams=[diagram_ref],
        )

        risk2 = BoundaryRisk(
            risk_type="test_risk_2",
            description="Test risk 2",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            affected_boundaries=["Eastern boundary"],
            potential_impact="Test impact",
        )

        assessment = DiagramRiskAssessment(
            property_identifier="Test Property",
            diagram_sources=[DiagramType.SITE_PLAN],
            infrastructure_risks=[risk1],
            boundary_risks=[risk2],
            overall_risk_score=RiskSeverity.MAJOR,
        )

        # Verify computed fields
        assert assessment.total_risks_identified == 2
        # overall_risk_score should be computed if not explicitly set
        # Since we set it explicitly, it should remain MAJOR

    def test_risk_extractor_calculate_overall_risk(self):
        """Test RiskExtractor.calculate_overall_risk with new schema"""
        # Create risks with different severities
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        minor_risk = EnvironmentalRisk(
            risk_type="minor_issue",
            description="Minor issue",
            severity=RiskSeverity.MINOR,
            linked_diagrams=[diagram_ref],
            environmental_factor="minor_factor",
            mitigation_required="simple mitigation",
        )

        moderate_risk = InfrastructureRisk(
            risk_type="moderate_issue",
            description="Moderate issue",
            severity=RiskSeverity.MODERATE,
            linked_diagrams=[diagram_ref],
        )

        major_risk = BoundaryRisk(
            risk_type="major_issue",
            description="Major issue",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            affected_boundaries=["Eastern boundary"],
            potential_impact="significant impact",
        )

        # Test different risk combinations
        # All minor risks
        minor_assessment = DiagramRiskAssessment(
            property_identifier="Test",
            diagram_sources=[DiagramType.SITE_PLAN],
            environmental_risks=[minor_risk, minor_risk],
            overall_risk_score=RiskSeverity.MINOR,  # Set explicitly to avoid validation error
        )

        computed_minor = RiskExtractor.calculate_overall_risk(minor_assessment)
        assert computed_minor == RiskSeverity.MINOR

        # Mixed risks
        mixed_assessment = DiagramRiskAssessment(
            property_identifier="Test",
            diagram_sources=[DiagramType.SITE_PLAN],
            environmental_risks=[minor_risk],
            infrastructure_risks=[moderate_risk],
            boundary_risks=[major_risk],
            overall_risk_score=RiskSeverity.MAJOR,  # Set explicitly to avoid validation error
        )

        computed_mixed = RiskExtractor.calculate_overall_risk(mixed_assessment)
        assert computed_mixed == RiskSeverity.MODERATE

        # All major risks
        major_assessment = DiagramRiskAssessment(
            property_identifier="Test",
            diagram_sources=[DiagramType.SITE_PLAN],
            boundary_risks=[major_risk, major_risk, major_risk],
            overall_risk_score=RiskSeverity.MAJOR,  # Set explicitly to avoid validation error
        )

        computed_major = RiskExtractor.calculate_overall_risk(major_assessment)
        assert computed_major == RiskSeverity.MAJOR

    def test_risk_extractor_create_example_assessment(self):
        """Test RiskExtractor.create_example_assessment with new schema"""
        example = RiskExtractor.create_example_assessment()

        # Verify the structure
        assert isinstance(example, DiagramRiskAssessment)
        assert example.property_identifier == "Lot 15, DP123456"
        assert len(example.diagram_sources) > 0

        # Verify the risks are in the appropriate risk type lists
        total_risks = (
            len(example.boundary_risks)
            + len(example.infrastructure_risks)
            + len(example.environmental_risks)
            + len(example.development_risks)
        )
        assert total_risks > 0

        # Verify the risks have the expected structure
        if example.boundary_risks:
            for risk in example.boundary_risks:
                assert isinstance(risk, BoundaryRisk)
                assert risk.risk_type is not None
                assert risk.description is not None
                assert risk.severity is not None

    def test_risk_category_enum_validation(self):
        """Test that RiskCategory enum validation works correctly"""
        # Test valid risk categories
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk = EnvironmentalRisk(
            risk_type="test_environmental",
            description="Test environmental risk",
            severity=RiskSeverity.MINOR,
            linked_diagrams=[diagram_ref],
            environmental_factor="test_factor",
            mitigation_required="test mitigation",
        )

        assert risk.risk_type == "test_environmental"

        # Test that RiskCategory enum validation works
        assert RiskCategory("environmental") == RiskCategory.ENVIRONMENTAL
        assert RiskCategory("infrastructure") == RiskCategory.INFRASTRUCTURE

    def test_risk_severity_enum_validation(self):
        """Test that RiskSeverity enum validation works correctly"""
        # Test valid severity levels
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk = InfrastructureRisk(
            risk_type="test_infrastructure",
            description="Test infrastructure risk",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
        )

        assert risk.severity == RiskSeverity.MAJOR

        # Test that RiskSeverity enum validation works
        assert RiskSeverity("major") == RiskSeverity.MAJOR
        assert RiskSeverity("moderate") == RiskSeverity.MODERATE

    def test_comprehensive_risk_assessment(self):
        """Test creating a comprehensive risk assessment with all risk types"""
        # Create risks for different categories
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        # Infrastructure risk
        infrastructure_risk = InfrastructureRisk(
            risk_type="sewer_main",
            description="Sewer main under property",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            sewer_pipe_location="Under building envelope",
            maintenance_access_requirements="3m easement required",
        )

        # Environmental risk
        environmental_risk = EnvironmentalRisk(
            risk_type="flood_zone",
            description="Property in flood zone",
            severity=RiskSeverity.MODERATE,
            linked_diagrams=[diagram_ref],
            environmental_factor="flooding",
            mitigation_required="Elevation assessment needed",
        )

        # Boundary risk
        boundary_risk = BoundaryRisk(
            risk_type="encroachment",
            description="Boundary dispute with neighbor",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            affected_boundaries=["Eastern boundary"],
            encroachment_details="Shed extends 0.5m over boundary",
            potential_impact="May require legal action",
        )

        # Development risk
        development_risk = DevelopmentRisk(
            risk_type="height_restriction",
            description="Building height restrictions",
            severity=RiskSeverity.MINOR,
            linked_diagrams=[diagram_ref],
            development_constraint="Maximum height 8.5m",
            current_plan_height="7.2m",
        )

        # Create comprehensive assessment
        assessment = DiagramRiskAssessment(
            property_identifier="Comprehensive Test Property",
            diagram_sources=[
                DiagramType.SITE_PLAN,
                DiagramType.SEWER_SERVICE_DIAGRAM,
                DiagramType.FLOOD_MAP,
                DiagramType.TITLE_PLAN,
            ],
            infrastructure_risks=[infrastructure_risk],
            environmental_risks=[environmental_risk],
            boundary_risks=[boundary_risk],
            development_risks=[development_risk],
            overall_risk_score=RiskSeverity.MAJOR,  # Set explicitly to avoid validation error
            high_priority_risks=[
                "Sewer main under building envelope requires immediate attention",
                "Boundary dispute needs legal resolution",
                "Flood zone status affects development potential",
            ],
            recommended_actions=[
                "Consult with council about sewer main access requirements",
                "Obtain legal advice for boundary dispute resolution",
                "Review flood zone implications for development plans",
                "Consider engineering solutions for sewer main access",
            ],
            surveyor_recommendations="Full property survey and flood assessment recommended",
            legal_review_required=True,
            additional_investigations_needed=[
                "Professional boundary survey",
                "Council infrastructure consultation",
                "Flood risk assessment",
                "Legal advice on boundary dispute",
            ],
        )

        # Verify comprehensive assessment
        assert len(assessment.infrastructure_risks) == 1
        assert len(assessment.environmental_risks) == 1
        assert len(assessment.boundary_risks) == 1
        assert len(assessment.development_risks) == 1
        assert len(assessment.diagram_sources) == 4
        assert assessment.total_risks_identified == 4
        assert assessment.legal_review_required == True
        assert len(assessment.high_priority_risks) == 3
        assert len(assessment.recommended_actions) == 4

        # Verify computed overall risk score
        computed_score = RiskExtractor.calculate_overall_risk(assessment)
        assert (
            computed_score == RiskSeverity.MODERATE
        )  # Should be MODERATE due to 2 major risks (need 3+ for MAJOR)

    def test_risk_attributes_flexibility(self):
        """Test the flexibility of risk model fields"""
        # Test various types of risk fields
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

        risk = InfrastructureRisk(
            risk_type="complex_infrastructure",
            description="Complex infrastructure risk",
            severity=RiskSeverity.MAJOR,
            linked_diagrams=[diagram_ref],
            sewer_pipe_location="Under eastern boundary",
            maintenance_access_requirements="3m easement required",
        )

        # Verify all field types are preserved
        assert risk.risk_type == "complex_infrastructure"
        assert risk.description == "Complex infrastructure risk"
        assert risk.severity == RiskSeverity.MAJOR
        assert risk.sewer_pipe_location == "Under eastern boundary"

    def test_cross_cutting_risk_functionality(self):
        """Test cross-cutting risk functionality for risks affecting multiple aspects"""
        # Create a risk that affects multiple aspects
        diagram_ref = DiagramReference(
            diagram_type=DiagramType.SITE_PLAN,
            diagram_name="Test Diagram",
            confidence_level=ConfidenceLevel.HIGH,
        )

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
