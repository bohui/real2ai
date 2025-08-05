"""State-specific schema variations for different Australian jurisdictions."""

from typing import Dict, List, Optional, Any, Type, Union
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal
from enum import Enum

from app.model.enums import AustralianState, ContractType, RiskLevel
from .extract_entities import (
    ContractEntityExtraction, 
    PlanningCertificates,
    AdditionalConditions,
    SpecialClauses,
    AttachedDocuments,
    Disclosures
)
from .ocr_schemas import OCRExtractionResults, OCRExtractedField


# NSW Specific Enhancements
class NSWPlanningSpecifics(BaseModel):
    """NSW-specific planning and regulatory requirements."""
    
    # Section 10.7 Planning Certificate specifics
    section_10_7_certificate_date: Optional[date] = Field(None, description="Date of Section 10.7 certificate")
    section_10_7_certificate_number: Optional[str] = Field(None, description="Certificate reference number")
    
    # EPA Act notices (critical for NSW)
    environmental_planning_act_notices: List[str] = Field(default_factory=list, description="EPA Act notices")
    contaminated_land_notices: List[str] = Field(default_factory=list, description="Contaminated land notices under CLM Act")
    coastal_protection_notices: List[str] = Field(default_factory=list, description="Coastal Protection Act notices")
    heritage_conservation_notices: List[str] = Field(default_factory=list, description="Heritage Act notices")
    
    # Mine subsidence (specific to NSW)
    mine_subsidence_district: Optional[bool] = Field(None, description="Property in Mine Subsidence District")
    mine_subsidence_compensation_applicable: Optional[bool] = Field(None, description="MSB compensation applies")
    
    # Bushfire and flooding (NSW specific mapping)
    bushfire_prone_land_category: Optional[str] = Field(None, description="Bushfire prone land category")
    flood_planning_level: Optional[str] = Field(None, description="Flood planning level")
    
    # NSW specific risks
    acid_sulfate_soil_class: Optional[str] = Field(None, description="Acid sulfate soil classification")
    salinity_management_plan: Optional[bool] = Field(None, description="Salinity management plan required")


class NSWStrataSpecifics(BaseModel):
    """NSW Strata Schemes Management Act specific requirements."""
    
    # SSMA 2015 specific requirements
    strata_renewal_proposal: Optional[bool] = Field(None, description="Strata renewal proposal affecting property")
    building_defects_bond: Optional[Decimal] = Field(None, description="Building defects bond amount")
    defects_insurance_policy: Optional[str] = Field(None, description="Defects insurance policy details")
    
    # NSW specific strata documents
    by_laws_consolidation: Optional[bool] = Field(None, description="By-laws consolidated under SSMA 2015")
    building_management_statement: Optional[bool] = Field(None, description="Building management statement provided")
    strata_development_contract: Optional[bool] = Field(None, description="Strata development contract disclosed")


class NSWLegalRequirements(BaseModel):
    """NSW legal and compliance requirements."""
    
    # Conveyancing Act 1919 compliance
    contract_for_sale_land_compliance: bool = Field(default=False, description="Conveyancing Act compliance")
    cooling_off_period_days: int = Field(default=5, description="Cooling off period (5 business days NSW)")
    
    # Property Stock and Business Agents Act
    vendor_disclosure_statement_compliant: Optional[bool] = Field(None, description="VDS complies with PSBA Act")
    agent_license_check: Optional[str] = Field(None, description="Agent license verification status")
    
    # Home Building Act (for residential properties)
    home_warranty_insurance: Optional[str] = Field(None, description="Home warranty insurance details")
    building_work_compliance: Optional[List[str]] = Field(None, description="Building work compliance certificates")


# VIC Specific Enhancements  
class VICPlanningSpecifics(BaseModel):
    """Victoria-specific planning and regulatory requirements."""
    
    # Section 32 Statement specifics
    section_32_statement_date: Optional[date] = Field(None, description="Date of Section 32 statement")
    section_32_statement_version: Optional[str] = Field(None, description="Statement version number")
    
    # Planning and Environment Act requirements
    planning_permit_required: Optional[bool] = Field(None, description="Planning permit required for proposed use")
    development_contributions_plan: Optional[str] = Field(None, description="Development contributions plan applicable")
    
    # Victoria specific environmental
    native_vegetation_regulations: List[str] = Field(default_factory=list, description="Native vegetation regulations")
    cultural_heritage_management_plan: Optional[bool] = Field(None, description="CHMP required")
    
    # Residential Tenancies Act (for investment properties)
    rta_compliance_status: Optional[str] = Field(None, description="RTA compliance for rental properties")
    
    # Cladding issues (Victoria specific post-2019)
    cladding_rectification_orders: List[str] = Field(default_factory=list, description="Cladding rectification orders")
    building_defects_insurance_status: Optional[str] = Field(None, description="Building defects insurance status")


class VICOwnersCorpSpecifics(BaseModel):
    """Victoria Owners Corporation Act specific requirements."""
    
    # OC Act 2006 specific requirements
    owners_corporation_manager: Optional[str] = Field(None, description="OC manager details")
    oc_rules_current: Optional[bool] = Field(None, description="OC rules current and compliant")
    
    # Victoria specific OC documents
    maintenance_plan_current: Optional[bool] = Field(None, description="10-year maintenance plan current")
    fire_safety_statement: Optional[bool] = Field(None, description="Essential services fire safety statement")
    
    # Financial obligations
    capital_works_fund_levy: Optional[Decimal] = Field(None, description="Capital works fund levy")
    special_resolution_levies: List[Dict[str, Any]] = Field(default_factory=list, description="Special resolution levies")


class VICLegalRequirements(BaseModel):
    """Victoria legal and compliance requirements."""
    
    # Sale of Land Act 1962 compliance
    sale_of_land_act_compliance: bool = Field(default=False, description="Sale of Land Act compliance")
    cooling_off_period_days: int = Field(default=3, description="Cooling off period (3 business days VIC)")
    
    # Estate Agents Act compliance
    estate_agent_authority: Optional[str] = Field(None, description="Estate agent authority details")
    agency_agreement_disclosure: Optional[bool] = Field(None, description="Agency agreement disclosed")
    
    # Residential Tenancies Act
    rta_bond_requirements: Optional[str] = Field(None, description="RTA bond requirements for investment")


# QLD Specific Enhancements
class QLDPlanningSpecifics(BaseModel):
    """Queensland-specific planning and regulatory requirements."""
    
    # Planning Act requirements
    property_information_form_date: Optional[date] = Field(None, description="Date of Property Information Form")
    sustainable_planning_act_notices: List[str] = Field(default_factory=list, description="Planning Act notices")
    
    # Development approvals
    development_approval_current: Optional[bool] = Field(None, description="Development approval current")
    compliance_certificate_status: Optional[str] = Field(None, description="Compliance certificate status")
    
    # Environmental requirements
    koala_habitat_area: Optional[bool] = Field(None, description="Property in koala habitat area")
    great_barrier_reef_protection: Optional[List[str]] = Field(None, description="GBR protection requirements")
    
    # Queensland specific environmental
    vegetation_management_act: Optional[List[str]] = Field(None, description="Vegetation Management Act requirements")
    water_allocation_notices: Optional[List[str]] = Field(None, description="Water allocation notices")


class QLDBodyCorpSpecifics(BaseModel):
    """Queensland Body Corporate and Community Management Act specifics."""
    
    # BCCM Act specific requirements
    community_management_statement: Optional[bool] = Field(None, description="CMS current and compliant")
    by_laws_registration_status: Optional[str] = Field(None, description="By-laws registration status")
    
    # Management rights (unique to QLD)
    management_rights_module: Optional[str] = Field(None, description="Management rights module type")
    caretaking_agreement_term: Optional[str] = Field(None, description="Caretaking agreement term")
    letting_rights_income: Optional[Decimal] = Field(None, description="Letting rights income disclosure")
    
    # QLD specific body corporate documents  
    body_corporate_information_certificate: Optional[bool] = Field(None, description="BCIC provided")
    form_1_disclosure: Optional[bool] = Field(None, description="Form 1 management rights disclosure")


class QLDLegalRequirements(BaseModel):
    """Queensland legal and compliance requirements."""
    
    # Property Law Act compliance
    property_law_act_compliance: bool = Field(default=False, description="Property Law Act compliance")
    cooling_off_period_days: int = Field(default=5, description="Cooling off period (5 business days QLD)")
    
    # Body Corporate legislation
    bccm_act_compliance: Optional[bool] = Field(None, description="BCCM Act compliance")
    
    # Property Agents and Motor Dealers Act
    property_agent_license: Optional[str] = Field(None, description="Property agent license verification")
    
    # Building defects insurance (post-2020)
    building_defects_insurance_required: Optional[bool] = Field(None, description="Building defects insurance requirement")


# WA Specific Enhancements
class WAPlanningSpecifics(BaseModel):
    """Western Australia-specific planning requirements."""
    
    # Planning and Development Act
    local_planning_scheme: Optional[str] = Field(None, description="Local planning scheme provisions")
    development_approval_conditions: List[str] = Field(default_factory=list, description="Development approval conditions")
    
    # Environmental Protection Act
    environmental_conditions: List[str] = Field(default_factory=list, description="EP Act conditions")
    contaminated_sites_act_notices: List[str] = Field(default_factory=list, description="Contaminated Sites Act notices")
    
    # Mining Act (significant in WA)
    mining_tenements: List[str] = Field(default_factory=list, description="Mining tenements affecting property")
    petroleum_titles: List[str] = Field(default_factory=list, description="Petroleum titles over property")


class WALegalRequirements(BaseModel):
    """WA legal and compliance requirements."""
    
    # Transfer of Land Act
    transfer_of_land_act_compliance: bool = Field(default=False, description="Transfer of Land Act compliance")
    cooling_off_period_days: int = Field(default=5, description="Cooling off period (5 business days WA)")
    
    # Real Estate and Business Agents Act
    agent_license_verification: Optional[str] = Field(None, description="REBA Act license verification")
    
    # Strata Titles Act
    strata_titles_act_compliance: Optional[bool] = Field(None, description="Strata Titles Act compliance")


# SA Specific Enhancements
class SAPlanningSpecifics(BaseModel):
    """South Australia-specific planning requirements."""
    
    # Development Act
    development_act_compliance: List[str] = Field(default_factory=list, description="Development Act compliance")
    planning_consent_required: Optional[bool] = Field(None, description="Planning consent required")
    
    # Native Vegetation Act
    native_vegetation_clearance: List[str] = Field(default_factory=list, description="Native vegetation clearance requirements")
    
    # Environment Protection Act
    environment_protection_notices: List[str] = Field(default_factory=list, description="EPA notices")


class SALegalRequirements(BaseModel):
    """SA legal and compliance requirements."""
    
    # Land and Business (Sale and Conveyancing) Act
    sale_conveyancing_act_compliance: bool = Field(default=False, description="Sale and Conveyancing Act compliance")
    cooling_off_period_days: int = Field(default=2, description="Cooling off period (2 business days SA)")
    
    # Community Titles Act
    community_titles_act_compliance: Optional[bool] = Field(None, description="Community Titles Act compliance")


# Enhanced State-Specific Contract Schemas
class NSWContractExtraction(ContractEntityExtraction):
    """NSW-specific contract extraction with enhanced state requirements."""
    
    nsw_planning_specifics: Optional[NSWPlanningSpecifics] = Field(None, description="NSW planning requirements")
    nsw_strata_specifics: Optional[NSWStrataSpecifics] = Field(None, description="NSW strata requirements")
    nsw_legal_requirements: NSWLegalRequirements = Field(description="NSW legal compliance")


class VICContractExtraction(ContractEntityExtraction):
    """Victoria-specific contract extraction with enhanced state requirements."""
    
    vic_planning_specifics: Optional[VICPlanningSpecifics] = Field(None, description="VIC planning requirements")
    vic_owners_corp_specifics: Optional[VICOwnersCorpSpecifics] = Field(None, description="VIC owners corp requirements")
    vic_legal_requirements: VICLegalRequirements = Field(description="VIC legal compliance")


class QLDContractExtraction(ContractEntityExtraction):
    """Queensland-specific contract extraction with enhanced state requirements."""
    
    qld_planning_specifics: Optional[QLDPlanningSpecifics] = Field(None, description="QLD planning requirements")
    qld_body_corp_specifics: Optional[QLDBodyCorpSpecifics] = Field(None, description="QLD body corp requirements")
    qld_legal_requirements: QLDLegalRequirements = Field(description="QLD legal compliance")


class WAContractExtraction(ContractEntityExtraction):
    """WA-specific contract extraction with enhanced state requirements."""
    
    wa_planning_specifics: Optional[WAPlanningSpecifics] = Field(None, description="WA planning requirements")
    wa_legal_requirements: WALegalRequirements = Field(description="WA legal compliance")


class SAContractExtraction(ContractEntityExtraction):
    """SA-specific contract extraction with enhanced state requirements."""
    
    sa_planning_specifics: Optional[SAPlanningSpecifics] = Field(None, description="SA planning requirements")
    sa_legal_requirements: SALegalRequirements = Field(description="SA legal compliance")


# State-specific schema mapping for dynamic selection
STATE_SPECIFIC_CONTRACT_SCHEMAS: Dict[AustralianState, Type[BaseModel]] = {
    AustralianState.NSW: NSWContractExtraction,
    AustralianState.VIC: VICContractExtraction,
    AustralianState.QLD: QLDContractExtraction,
    AustralianState.WA: WAContractExtraction,
    AustralianState.SA: SAContractExtraction,
    # Other states fall back to base schema
    AustralianState.TAS: ContractEntityExtraction,
    AustralianState.NT: ContractEntityExtraction,
    AustralianState.ACT: NSWContractExtraction,  # ACT follows NSW patterns
}


# State-specific critical validation requirements
class StateSpecificValidation(BaseModel):
    """Base class for state-specific validation requirements."""
    
    mandatory_documents_provided: bool = Field(default=False, description="All mandatory documents provided")
    state_legislation_compliance: bool = Field(default=False, description="State legislation compliance verified")
    cooling_off_period_compliant: bool = Field(default=False, description="Cooling off period compliant")


class NSWValidationEnhanced(StateSpecificValidation):
    """Enhanced NSW validation with comprehensive checks."""
    
    # Document requirements
    section_10_7_certificate_valid: bool = Field(default=False, description="Valid Section 10.7 certificate")
    vendor_disclosure_statement_complete: bool = Field(default=False, description="Complete VDS provided")
    
    # Legal compliance
    conveyancing_act_compliance: bool = Field(default=False, description="Conveyancing Act 1919 compliance")
    cooling_off_period_days: int = Field(default=5, description="5 business day cooling off period")
    
    # Risk factors specific to NSW
    mine_subsidence_assessed: bool = Field(default=False, description="Mine subsidence risk assessed")
    environmental_planning_compliance: bool = Field(default=False, description="EPA Act compliance checked")
    contaminated_land_cleared: bool = Field(default=False, description="Contaminated land status cleared")


class VICValidationEnhanced(StateSpecificValidation):
    """Enhanced Victoria validation with comprehensive checks."""
    
    # Document requirements
    section_32_statement_current: bool = Field(default=False, description="Current Section 32 statement")
    owners_corporation_certificate_valid: bool = Field(default=False, description="Valid OC certificate")
    
    # Legal compliance  
    sale_of_land_act_compliance: bool = Field(default=False, description="Sale of Land Act compliance")
    cooling_off_period_days: int = Field(default=3, description="3 business day cooling off period")
    
    # Victoria specific risks
    cladding_issues_assessed: bool = Field(default=False, description="Cladding issues assessed")
    building_defects_insurance_verified: bool = Field(default=False, description="Building defects insurance verified")


class QLDValidationEnhanced(StateSpecificValidation):
    """Enhanced Queensland validation with comprehensive checks."""
    
    # Document requirements
    property_information_form_current: bool = Field(default=False, description="Current Property Information Form")
    body_corporate_certificate_valid: bool = Field(default=False, description="Valid BCIC")
    
    # Legal compliance
    property_law_act_compliance: bool = Field(default=False, description="Property Law Act compliance")
    cooling_off_period_days: int = Field(default=5, description="5 business day cooling off period")
    
    # QLD specific considerations
    management_rights_disclosed: bool = Field(default=False, description="Management rights properly disclosed")
    bccm_act_compliance_verified: bool = Field(default=False, description="BCCM Act compliance verified")


# Enhanced state-specific validation mapping
ENHANCED_STATE_VALIDATION_SCHEMAS: Dict[AustralianState, Type[BaseModel]] = {
    AustralianState.NSW: NSWValidationEnhanced,
    AustralianState.VIC: VICValidationEnhanced,
    AustralianState.QLD: QLDValidationEnhanced,
    AustralianState.WA: StateSpecificValidation,  # Use base for states without enhanced schemas yet
    AustralianState.SA: StateSpecificValidation,
    AustralianState.TAS: StateSpecificValidation,
    AustralianState.NT: StateSpecificValidation,
    AustralianState.ACT: NSWValidationEnhanced,  # ACT follows NSW
}


# Risk factor mappings by state
STATE_SPECIFIC_RISK_FACTORS = {
    AustralianState.NSW: [
        "mine_subsidence_district",
        "contaminated_land_register", 
        "coastal_protection_restrictions",
        "section_10_7_certificate_issues",
        "environmental_planning_act_notices",
        "heritage_conservation_notices",
        "acid_sulfate_soils",
        "bushfire_prone_land"
    ],
    AustralianState.VIC: [
        "cladding_rectification_orders",
        "owners_corporation_issues",
        "building_defects_insurance",
        "planning_permit_compliance",
        "native_vegetation_regulations",
        "cultural_heritage_requirements",
        "fire_safety_compliance"
    ],
    AustralianState.QLD: [
        "management_rights_complexity", 
        "body_corporate_disputes",
        "building_defects_insurance_gaps",
        "koala_habitat_restrictions",
        "great_barrier_reef_protection",
        "vegetation_management_requirements",
        "development_approval_compliance"
    ],
    AustralianState.WA: [
        "mining_tenements_impact",
        "petroleum_titles_interference", 
        "contaminated_sites_register",
        "aboriginal_heritage_sites",
        "environmental_protection_orders"
    ],
    AustralianState.SA: [
        "development_act_compliance",
        "native_vegetation_clearance",
        "environment_protection_notices",
        "heritage_agreements"
    ]
}


def get_state_specific_schema(
    australian_state: AustralianState, 
    schema_type: str = "contract"
) -> Type[BaseModel]:
    """Get the appropriate state-specific schema."""
    
    if schema_type == "contract":
        return STATE_SPECIFIC_CONTRACT_SCHEMAS.get(australian_state, ContractEntityExtraction)
    elif schema_type == "validation":
        return ENHANCED_STATE_VALIDATION_SCHEMAS.get(australian_state, StateSpecificValidation)
    else:
        return ContractEntityExtraction


def get_state_risk_factors(australian_state: AustralianState) -> List[str]:
    """Get state-specific risk factors to focus on during analysis."""
    
    return STATE_SPECIFIC_RISK_FACTORS.get(australian_state, [])


def get_cooling_off_period(australian_state: AustralianState) -> int:
    """Get the cooling off period for the specified state."""
    
    cooling_off_periods = {
        AustralianState.NSW: 5,
        AustralianState.VIC: 3,
        AustralianState.QLD: 5,
        AustralianState.WA: 5,
        AustralianState.SA: 2,
        AustralianState.TAS: 5,
        AustralianState.NT: 5,
        AustralianState.ACT: 5,
    }
    
    return cooling_off_periods.get(australian_state, 5)  # Default to 5 days