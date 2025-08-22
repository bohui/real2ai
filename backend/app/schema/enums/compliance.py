"""Compliance and legal requirement enums."""

from enum import Enum


class LegalRequirement(str, Enum):
    """Legal/compliance requirement flags used by prompts and tools"""

    HOME_BUILDING_ACT = "home_building_act"
    BUILDING_CERTIFICATES = "building_certificates"
    OCCUPATION_CERTIFICATES = "occupation_certificates"
    SUNSET_CLAUSES = "sunset_clauses"
    PROGRESS_PAYMENTS = "progress_payments"
    BUILDING_WARRANTIES = "building_warranties"

    COOLING_OFF_PERIOD = "cooling_off_period"
    VENDOR_STATEMENT = "vendor_statement"
    PLANNING_CERTIFICATES = "planning_certificates"

    COMMERCIAL_DUE_DILIGENCE = "commercial_due_diligence"
    ENVIRONMENTAL_ASSESSMENTS = "environmental_assessments"
    ZONING_COMPLIANCE = "zoning_compliance"
