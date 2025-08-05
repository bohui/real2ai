"""Output parser schemas for extracting legal entities from Australian real estate contracts."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from app.model.enums import AustralianState, ContractType, RiskLevel


class PropertyType(str, Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    TOWNHOUSE = "townhouse"
    UNIT = "unit"
    VILLA = "villa"
    LAND = "land"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"


class InspectionType(str, Enum):
    BUILDING_PEST = "building_pest"
    STRATA = "strata"
    FINANCE = "finance"
    LEGAL = "legal"
    SETTLEMENT = "settlement"


class FinanceType(str, Enum):
    BANK_LOAN = "bank_loan"
    CASH = "cash"
    VENDOR_FINANCE = "vendor_finance"
    BRIDGING_LOAN = "bridging_loan"


# Core Entity Models
class PersonEntity(BaseModel):
    """Individual person involved in the contract."""

    full_name: str = Field(description="Complete legal name")
    role: str = Field(description="Role in transaction (buyer, seller, witness, etc.)")
    address: Optional[str] = Field(None, description="Residential address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    email: Optional[str] = Field(None, description="Email address")
    date_of_birth: Optional[date] = Field(
        None, description="Date of birth if specified"
    )
    occupation: Optional[str] = Field(None, description="Occupation if specified")


class CorporateEntity(BaseModel):
    """Corporate entity involved in the contract."""

    company_name: str = Field(description="Full registered company name")
    abn: Optional[str] = Field(None, description="Australian Business Number")
    acn: Optional[str] = Field(None, description="Australian Company Number")
    role: str = Field(description="Role in transaction")
    registered_address: Optional[str] = Field(
        None, description="Registered business address"
    )
    contact_person: Optional[str] = Field(None, description="Authorized contact person")
    phone: Optional[str] = Field(None, description="Business phone number")
    email: Optional[str] = Field(None, description="Business email address")


class PropertyEntity(BaseModel):
    """Property being transacted."""

    street_address: str = Field(description="Full street address")
    suburb: str = Field(description="Suburb name")
    state: AustralianState = Field(description="Australian state")
    postcode: str = Field(description="Postal code")
    property_type: PropertyType = Field(description="Type of property")
    lot_number: Optional[str] = Field(None, description="Lot number if applicable")
    plan_number: Optional[str] = Field(None, description="Plan number if applicable")
    title_reference: Optional[str] = Field(
        None, description="Certificate of title reference"
    )
    land_size: Optional[str] = Field(None, description="Land size (sqm or acres)")
    floor_area: Optional[str] = Field(None, description="Floor area if specified")
    zoning: Optional[str] = Field(None, description="Zoning classification")


class FinancialTerms(BaseModel):
    """Financial terms and conditions."""

    purchase_price: Optional[Decimal] = Field(None, description="Total purchase price")
    deposit_amount: Optional[Decimal] = Field(None, description="Deposit amount")
    deposit_percentage: Optional[float] = Field(
        None, description="Deposit as percentage of price"
    )
    balance_due: Optional[Decimal] = Field(
        None, description="Balance due at settlement"
    )
    rent_amount: Optional[Decimal] = Field(
        None, description="Rental amount (for leases)"
    )
    rent_frequency: Optional[str] = Field(None, description="Rent payment frequency")
    bond_amount: Optional[Decimal] = Field(None, description="Security bond amount")
    additional_costs: Optional[Dict[str, Decimal]] = Field(
        None, description="Additional costs breakdown"
    )
    gst_applicable: Optional[bool] = Field(None, description="Whether GST applies")
    gst_amount: Optional[Decimal] = Field(None, description="GST amount if applicable")


class ImportantDates(BaseModel):
    """Critical dates and deadlines."""

    contract_date: Optional[date] = Field(None, description="Contract execution date")
    cooling_off_expiry: Optional[date] = Field(
        None, description="Cooling off period expiry"
    )
    finance_approval_date: Optional[date] = Field(
        None, description="Finance approval deadline"
    )
    settlement_date: Optional[date] = Field(None, description="Settlement date")
    possession_date: Optional[date] = Field(
        None, description="Possession/handover date"
    )
    lease_commencement: Optional[date] = Field(
        None, description="Lease commencement date"
    )
    lease_expiry: Optional[date] = Field(None, description="Lease expiry date")
    inspection_deadlines: Optional[Dict[str, date]] = Field(
        None, description="Various inspection deadlines"
    )


class Conditions(BaseModel):
    """Contract conditions and contingencies."""

    finance_approval_required: Optional[bool] = Field(
        None, description="Finance approval condition"
    )
    finance_amount: Optional[Decimal] = Field(
        None, description="Required finance amount"
    )
    finance_type: Optional[FinanceType] = Field(None, description="Type of finance")
    building_inspection_required: Optional[bool] = Field(
        None, description="Building inspection condition"
    )
    pest_inspection_required: Optional[bool] = Field(
        None, description="Pest inspection condition"
    )
    strata_inspection_required: Optional[bool] = Field(
        None, description="Strata inspection condition"
    )
    council_approval_required: Optional[bool] = Field(
        None, description="Council approval required"
    )
    development_approval_required: Optional[bool] = Field(
        None, description="Development approval required"
    )
    special_conditions: Optional[List[str]] = Field(
        None, description="Special conditions text"
    )


class LegalRepresentation(BaseModel):
    """Legal representatives and conveyancers."""

    buyer_solicitor: Optional[str] = Field(
        None, description="Buyer's solicitor/conveyancer"
    )
    buyer_solicitor_firm: Optional[str] = Field(None, description="Buyer's law firm")
    seller_solicitor: Optional[str] = Field(
        None, description="Seller's solicitor/conveyancer"
    )
    seller_solicitor_firm: Optional[str] = Field(None, description="Seller's law firm")
    buyer_solicitor_contact: Optional[str] = Field(
        None, description="Buyer's solicitor contact details"
    )
    seller_solicitor_contact: Optional[str] = Field(
        None, description="Seller's solicitor contact details"
    )


class RealEstateAgents(BaseModel):
    """Real estate agents involved."""

    selling_agent: Optional[str] = Field(None, description="Selling agent name")
    selling_agency: Optional[str] = Field(None, description="Selling agency name")
    buying_agent: Optional[str] = Field(None, description="Buyer's agent name")
    buying_agency: Optional[str] = Field(None, description="Buyer's agency name")
    agent_license_number: Optional[str] = Field(
        None, description="Agent license number"
    )
    commission_rate: Optional[float] = Field(None, description="Commission rate")
    commission_amount: Optional[Decimal] = Field(None, description="Commission amount")


class PlanningCertificates(BaseModel):
    """Planning and development certificates."""

    section_10_7_planning_certificate: Optional[bool] = Field(
        None, description="Section 10.7 Planning Certificate provided (NSW)"
    )
    section_32_statement: Optional[bool] = Field(
        None, description="Section 32 Statement provided (VIC)"
    )
    property_information_form: Optional[bool] = Field(
        None, description="Property Information Form provided (QLD)"
    )
    planning_certificate_date: Optional[date] = Field(
        None, description="Date of planning certificate"
    )
    zoning_restrictions: Optional[List[str]] = Field(
        None, description="Zoning restrictions noted"
    )
    development_consents: Optional[List[str]] = Field(
        None, description="Development consents on record"
    )
    building_orders: Optional[List[str]] = Field(
        None, description="Outstanding building orders"
    )
    heritage_restrictions: Optional[List[str]] = Field(
        None, description="Heritage restrictions"
    )
    environmental_planning_act_notices: Optional[List[str]] = Field(
        None, description="EPA Act notices or restrictions"
    )
    contaminated_land_notices: Optional[List[str]] = Field(
        None, description="Contaminated land notices"
    )
    coastal_protection_restrictions: Optional[List[str]] = Field(
        None, description="Coastal protection restrictions"
    )
    flood_planning_restrictions: Optional[List[str]] = Field(
        None, description="Flood planning restrictions"
    )
    acid_sulfate_soil_maps: Optional[List[str]] = Field(
        None, description="Acid sulfate soil mapping"
    )
    bushfire_prone_land: Optional[bool] = Field(
        None, description="Bushfire prone land designation"
    )
    mine_subsidence_district: Optional[bool] = Field(
        None, description="Mine subsidence district"
    )
    aircraft_noise_zones: Optional[List[str]] = Field(
        None, description="Aircraft noise impact zones"
    )


class TechnicalDiagrams(BaseModel):
    """Technical diagrams and surveys."""

    sewer_service_diagram: Optional[bool] = Field(
        None, description="Sewer service diagram provided"
    )
    sewer_diagram_date: Optional[date] = Field(
        None, description="Date of sewer diagram"
    )
    survey_plan: Optional[bool] = Field(None, description="Survey plan provided")
    survey_date: Optional[date] = Field(None, description="Survey date")
    easements_shown: Optional[List[str]] = Field(
        None, description="Easements shown on diagrams"
    )
    encroachments: Optional[List[str]] = Field(
        None, description="Encroachments identified"
    )
    right_of_ways: Optional[List[str]] = Field(None, description="Rights of way")
    covenant_restrictions: Optional[List[str]] = Field(
        None, description="Covenant restrictions"
    )


class AdditionalConditions(BaseModel):
    """Additional conditions and special clauses - CRITICAL for risk assessment."""

    condition_number: str = Field(description="Condition reference number")
    condition_text: str = Field(description="Full text of the condition")
    condition_type: str = Field(
        description="Type of condition (finance, inspection, approval, etc.)"
    )
    risk_level: RiskLevel = Field(description="Assessed risk level of this condition")
    deadline_date: Optional[date] = Field(
        None, description="Deadline associated with condition"
    )
    responsible_party: Optional[str] = Field(
        None, description="Party responsible for fulfilling condition"
    )
    waiver_rights: Optional[str] = Field(
        None, description="Rights to waive the condition"
    )
    failure_consequences: Optional[str] = Field(
        None, description="Consequences if condition not met"
    )
    unusual_terms: Optional[List[str]] = Field(
        None, description="Unusual or non-standard terms"
    )


class SpecialClauses(BaseModel):
    """Special clauses that deviate from standard template."""

    clause_reference: str = Field(description="Clause reference or schedule number")
    clause_title: Optional[str] = Field(None, description="Clause title if provided")
    clause_text: str = Field(description="Full text of the special clause")
    clause_category: str = Field(
        description="Category (price variation, possession, warranties, etc.)"
    )
    risk_assessment: RiskLevel = Field(description="Risk level of this clause")
    legal_implications: Optional[List[str]] = Field(
        None, description="Potential legal implications"
    )
    financial_impact: Optional[str] = Field(
        None, description="Potential financial impact"
    )
    recommendations: Optional[List[str]] = Field(
        None, description="Recommended actions for this clause"
    )


class AttachedDocuments(BaseModel):
    """Documents attached or referenced in contract."""

    document_name: str = Field(description="Name of attached document")
    document_type: str = Field(description="Type of document")
    mandatory: bool = Field(
        description="Whether document is mandatory for contract validity"
    )
    provided: Optional[bool] = Field(
        None, description="Whether document has been provided"
    )
    date_issued: Optional[date] = Field(None, description="Date document was issued")
    validity_period: Optional[date] = Field(
        None, description="Document validity expiry date"
    )
    issuing_authority: Optional[str] = Field(
        None, description="Authority that issued document"
    )
    critical_findings: Optional[List[str]] = Field(
        None, description="Critical findings in the document"
    )


class Disclosures(BaseModel):
    """Required disclosures and declarations."""

    vendor_disclosure_statement: Optional[bool] = Field(
        None, description="VDS provided"
    )
    property_information_form: Optional[bool] = Field(
        None, description="Property info form provided"
    )
    strata_records: Optional[bool] = Field(None, description="Strata records provided")
    council_rates_outstanding: Optional[bool] = Field(
        None, description="Outstanding council rates"
    )
    water_rates_outstanding: Optional[bool] = Field(
        None, description="Outstanding water rates"
    )
    body_corporate_fees: Optional[Decimal] = Field(
        None, description="Body corporate fees"
    )
    environmental_issues: Optional[List[str]] = Field(
        None, description="Environmental concerns"
    )
    heritage_listing: Optional[bool] = Field(
        None, description="Heritage listed property"
    )


class AuctionSpecific(BaseModel):
    """Auction-specific terms (for auction contracts)."""

    auction_date: Optional[date] = Field(None, description="Scheduled auction date")
    auction_time: Optional[str] = Field(None, description="Auction time")
    auction_location: Optional[str] = Field(None, description="Auction venue")
    reserve_price: Optional[Decimal] = Field(
        None, description="Reserve price if disclosed"
    )
    bidder_registration: Optional[bool] = Field(
        None, description="Bidder registration required"
    )
    auctioneer: Optional[str] = Field(None, description="Auctioneer name")
    bidding_conditions: Optional[List[str]] = Field(
        None, description="Special bidding conditions"
    )


class OffPlanSpecific(BaseModel):
    """Off-plan specific terms."""

    development_name: Optional[str] = Field(
        None, description="Development project name"
    )
    developer: Optional[str] = Field(None, description="Developer company")
    expected_completion: Optional[date] = Field(
        None, description="Expected completion date"
    )
    construction_milestones: Optional[Dict[str, date]] = Field(
        None, description="Construction milestone dates"
    )
    sunset_clause_date: Optional[date] = Field(None, description="Sunset clause date")
    plans_and_specifications: Optional[bool] = Field(
        None, description="Plans and specs provided"
    )
    variation_rights: Optional[List[str]] = Field(
        None, description="Developer variation rights"
    )


class StrataSpecific(BaseModel):
    """Strata/body corporate specific terms - CRITICAL for apartments/units."""

    strata_plan_number: Optional[str] = Field(
        None, description="Strata plan registration number"
    )
    lot_number: Optional[str] = Field(None, description="Individual lot number")
    unit_entitlement: Optional[str] = Field(None, description="Unit entitlement ratio")
    body_corporate_name: Optional[str] = Field(
        None, description="Body corporate/owners corporation name"
    )
    management_rights: Optional[bool] = Field(
        None, description="Management rights attached"
    )
    caretaking_agreements: Optional[str] = Field(
        None, description="Caretaking agreement details"
    )

    # Financial obligations
    quarterly_body_corporate_fees: Optional[Decimal] = Field(
        None, description="Quarterly BC fees"
    )
    special_levies_outstanding: Optional[List[Dict[str, Any]]] = Field(
        None, description="Outstanding special levies"
    )
    sinking_fund_balance: Optional[Decimal] = Field(
        None, description="Sinking fund balance"
    )
    administrative_fund_balance: Optional[Decimal] = Field(
        None, description="Administrative fund balance"
    )

    # Critical documents and compliance
    strata_records_provided: Optional[bool] = Field(
        None, description="Strata records bundle provided"
    )
    recent_agm_minutes: Optional[bool] = Field(
        None, description="Recent AGM minutes provided"
    )
    by_laws_current: Optional[bool] = Field(
        None, description="Current by-laws provided"
    )
    building_defects_identified: Optional[List[str]] = Field(
        None, description="Known building defects"
    )
    major_works_planned: Optional[List[Dict[str, Any]]] = Field(
        None, description="Planned major works and costs"
    )
    insurance_currency: Optional[bool] = Field(
        None, description="Building insurance current"
    )

    # Governance issues
    committee_functioning: Optional[str] = Field(
        None, description="Body corporate committee status"
    )
    disputes_current: Optional[List[str]] = Field(
        None, description="Current disputes or legal action"
    )
    by_law_breaches: Optional[List[str]] = Field(
        None, description="Known by-law breaches"
    )


class CommercialIndustrialSpecific(BaseModel):
    """Commercial/Industrial property specific terms."""

    business_use_permitted: Optional[List[str]] = Field(
        None, description="Permitted business uses"
    )
    zoning_compliance: Optional[str] = Field(
        None, description="Current zoning compliance status"
    )
    development_potential: Optional[str] = Field(
        None, description="Development potential notes"
    )

    # Leasing arrangements
    existing_tenancies: Optional[List[Dict[str, Any]]] = Field(
        None, description="Existing tenant details"
    )
    lease_terms_summary: Optional[List[str]] = Field(
        None, description="Summary of lease terms"
    )
    rental_income: Optional[Decimal] = Field(None, description="Current rental income")
    lease_expiry_dates: Optional[List[date]] = Field(
        None, description="Tenant lease expiry dates"
    )

    # Compliance and regulations
    occupational_health_safety: Optional[List[str]] = Field(
        None, description="OH&S compliance issues"
    )
    environmental_compliance: Optional[List[str]] = Field(
        None, description="Environmental compliance status"
    )
    fire_safety_compliance: Optional[bool] = Field(
        None, description="Fire safety compliance current"
    )
    disability_access_compliance: Optional[bool] = Field(
        None, description="DDA compliance status"
    )


class CrownLandMiningRights(BaseModel):
    """Crown land reservations and mining rights - CRITICAL risk factor."""

    crown_land_reservations: Optional[List[str]] = Field(
        None, description="Crown land reservations affecting property"
    )
    mining_lease_applications: Optional[List[str]] = Field(
        None, description="Mining lease applications over property"
    )
    petroleum_exploration_licenses: Optional[List[str]] = Field(
        None, description="Petroleum exploration licenses"
    )
    native_title_claims: Optional[List[str]] = Field(
        None, description="Native title claims affecting property"
    )
    aboriginal_land_rights: Optional[List[str]] = Field(
        None, description="Aboriginal land rights claims"
    )

    # Mineral and resource rights
    mineral_rights_retained: Optional[bool] = Field(
        None, description="Whether mineral rights retained by Crown"
    )
    coal_mining_rights: Optional[List[str]] = Field(
        None, description="Coal mining rights and applications"
    )
    quarrying_rights: Optional[List[str]] = Field(None, description="Quarrying rights")
    water_extraction_rights: Optional[List[str]] = Field(
        None, description="Water extraction licenses"
    )

    # Compensation and access rights
    compensation_provisions: Optional[List[str]] = Field(
        None, description="Compensation provisions for resource extraction"
    )
    access_rights_reserved: Optional[List[str]] = Field(
        None, description="Access rights reserved to Crown/miners"
    )


class EnvironmentalContamination(BaseModel):
    """Environmental contamination and hazardous materials - CRITICAL."""

    contaminated_land_register: Optional[bool] = Field(
        None, description="Property on contaminated land register"
    )
    environmental_site_assessment: Optional[bool] = Field(
        None, description="Environmental site assessment conducted"
    )
    soil_contamination: Optional[List[str]] = Field(
        None, description="Known soil contamination"
    )
    groundwater_contamination: Optional[List[str]] = Field(
        None, description="Groundwater contamination"
    )

    # Hazardous materials
    asbestos_register: Optional[bool] = Field(
        None, description="Asbestos register available"
    )
    asbestos_removal_required: Optional[List[str]] = Field(
        None, description="Asbestos removal requirements"
    )
    lead_paint: Optional[bool] = Field(None, description="Lead paint present")
    underground_storage_tanks: Optional[List[str]] = Field(
        None, description="Underground storage tanks"
    )

    # Industrial legacy
    previous_industrial_use: Optional[List[str]] = Field(
        None, description="Previous industrial uses"
    )
    remediation_orders: Optional[List[str]] = Field(
        None, description="Environmental remediation orders"
    )
    ongoing_monitoring_required: Optional[List[str]] = Field(
        None, description="Ongoing environmental monitoring"
    )


class EasementsCovenants(BaseModel):
    """Easements, covenants and restrictions - Often overlooked high-risk items."""

    registered_easements: Optional[List[Dict[str, str]]] = Field(
        None, description="All registered easements"
    )
    unregistered_easements: Optional[List[str]] = Field(
        None, description="Unregistered or implied easements"
    )
    restrictive_covenants: Optional[List[str]] = Field(
        None, description="Restrictive covenants affecting use"
    )
    positive_covenants: Optional[List[str]] = Field(
        None, description="Positive covenants requiring action"
    )

    # Rights of way and access
    rights_of_way: Optional[List[Dict[str, str]]] = Field(
        None, description="Rights of way details"
    )
    shared_driveways: Optional[List[str]] = Field(
        None, description="Shared driveway arrangements"
    )
    access_disputes: Optional[List[str]] = Field(
        None, description="Known access disputes"
    )

    # Utility easements
    electricity_easements: Optional[List[str]] = Field(
        None, description="Electricity transmission easements"
    )
    gas_pipeline_easements: Optional[List[str]] = Field(
        None, description="Gas pipeline easements"
    )
    telecommunications_easements: Optional[List[str]] = Field(
        None, description="Telecommunications easements"
    )
    water_sewer_easements: Optional[List[str]] = Field(
        None, description="Water and sewer easements"
    )

    # Building restrictions
    building_line_restrictions: Optional[List[str]] = Field(
        None, description="Building line restrictions"
    )
    height_restrictions: Optional[List[str]] = Field(
        None, description="Height restrictions"
    )
    architectural_controls: Optional[List[str]] = Field(
        None, description="Architectural control covenants"
    )


class FinanceSettlementRisks(BaseModel):
    """Finance and settlement specific high-risk terms."""

    unconditional_contract: Optional[bool] = Field(
        None, description="Contract is unconditional - HIGH RISK"
    )
    cash_settlement_required: Optional[bool] = Field(
        None, description="Cash settlement required"
    )
    short_settlement_period: Optional[int] = Field(
        None, description="Settlement period in days"
    )

    # Vendor finance risks
    vendor_finance_terms: Optional[Dict[str, Any]] = Field(
        None, description="Vendor finance arrangement details"
    )
    caveat_arrangements: Optional[List[str]] = Field(
        None, description="Caveat protection arrangements"
    )

    # Deposit risks
    deposit_holder: Optional[str] = Field(None, description="Who holds the deposit")
    deposit_release_conditions: Optional[List[str]] = Field(
        None, description="Conditions for deposit release"
    )
    additional_deposits_required: Optional[List[Dict[str, Any]]] = Field(
        None, description="Additional deposits required"
    )

    # GST and tax implications
    gst_margin_scheme: Optional[bool] = Field(
        None, description="GST margin scheme applicable"
    )
    foreign_investment_approval: Optional[bool] = Field(
        None, description="FIRB approval required"
    )
    land_tax_implications: Optional[List[str]] = Field(
        None, description="Land tax implications"
    )


class RiskAssessment(BaseModel):
    """Enhanced risk assessment focusing on non-standard clauses."""

    overall_risk_level: RiskLevel = Field(description="Overall assessed risk level")
    template_deviation_risk: RiskLevel = Field(
        description="Risk from deviations from standard template"
    )

    # Standard vs non-standard analysis
    standard_template_clauses: List[str] = Field(
        default_factory=list, description="Standard template clauses identified"
    )
    non_standard_modifications: List[str] = Field(
        default_factory=list, description="Modifications to standard clauses"
    )
    additional_clauses_risk: List[str] = Field(
        default_factory=list, description="Risks from additional conditions"
    )

    # Critical risk factors
    high_risk_conditions: List[str] = Field(
        default_factory=list, description="High-risk additional conditions"
    )
    unusual_financial_terms: List[str] = Field(
        default_factory=list, description="Unusual financial arrangements"
    )
    planning_compliance_risks: List[str] = Field(
        default_factory=list, description="Planning and compliance risks"
    )
    environmental_risks: List[str] = Field(
        default_factory=list, description="Environmental risks identified"
    )

    # Missing critical items
    missing_certificates: List[str] = Field(
        default_factory=list, description="Missing required certificates"
    )
    missing_information: List[str] = Field(
        default_factory=list, description="Missing critical information"
    )
    incomplete_conditions: List[str] = Field(
        default_factory=list, description="Incomplete or vague conditions"
    )

    # Urgent actions required
    urgent_deadlines: List[Dict[str, Any]] = Field(
        default_factory=list, description="Urgent upcoming deadlines"
    )
    immediate_actions: List[str] = Field(
        default_factory=list, description="Actions required before settlement"
    )
    recommended_professional_advice: List[str] = Field(
        default_factory=list, description="Recommended specialist advice"
    )

    # Red flags
    contract_red_flags: List[str] = Field(
        default_factory=list,
        description="Serious concerns requiring immediate attention",
    )


# Main Contract Entity Schema
class ContractEntityExtraction(BaseModel):
    """Complete entity extraction schema for Australian real estate contracts."""

    # Contract metadata
    contract_type: ContractType = Field(description="Type of contract being analyzed")
    jurisdiction: AustralianState = Field(description="Australian state jurisdiction")
    document_date: Optional[date] = Field(None, description="Document date")

    # Core entities
    persons: List[PersonEntity] = Field(
        default_factory=list, description="Individual persons involved"
    )
    corporate_entities: List[CorporateEntity] = Field(
        default_factory=list, description="Corporate entities involved"
    )
    property: Optional[PropertyEntity] = Field(None, description="Property details")

    # Financial and legal terms
    financial_terms: Optional[FinancialTerms] = Field(
        None, description="Financial terms and amounts"
    )
    important_dates: Optional[ImportantDates] = Field(
        None, description="Critical dates and deadlines"
    )
    conditions: Optional[Conditions] = Field(None, description="Contract conditions")

    # Professional services
    legal_representation: Optional[LegalRepresentation] = Field(
        None, description="Legal representatives"
    )
    real_estate_agents: Optional[RealEstateAgents] = Field(
        None, description="Real estate agents"
    )

    # Disclosures and compliance
    disclosures: Optional[Disclosures] = Field(None, description="Required disclosures")

    # CRITICAL: Non-standard and additional elements (highest priority for risk)
    planning_certificates: Optional[PlanningCertificates] = Field(
        None, description="Planning certificates and EPA notices"
    )
    technical_diagrams: Optional[TechnicalDiagrams] = Field(
        None, description="Technical diagrams and surveys"
    )
    additional_conditions: List[AdditionalConditions] = Field(
        default_factory=list,
        description="CRITICAL: Additional conditions beyond template",
    )
    special_clauses: List[SpecialClauses] = Field(
        default_factory=list, description="CRITICAL: Special clauses and variations"
    )
    attached_documents: List[AttachedDocuments] = Field(
        default_factory=list, description="All attached/referenced documents"
    )

    # Contract-specific terms
    auction_terms: Optional[AuctionSpecific] = Field(
        None, description="Auction-specific terms"
    )
    off_plan_terms: Optional[OffPlanSpecific] = Field(
        None, description="Off-plan specific terms"
    )

    # Property-type specific high-risk areas
    strata_terms: Optional[StrataSpecific] = Field(
        None, description="CRITICAL: Strata/body corporate terms"
    )
    commercial_terms: Optional[CommercialIndustrialSpecific] = Field(
        None, description="Commercial/industrial specific terms"
    )
    crown_land_mining: Optional[CrownLandMiningRights] = Field(
        None, description="CRITICAL: Crown land and mining rights"
    )
    environmental_contamination: Optional[EnvironmentalContamination] = Field(
        None, description="CRITICAL: Environmental contamination"
    )
    easements_covenants: Optional[EasementsCovenants] = Field(
        None, description="CRITICAL: Easements and covenant restrictions"
    )
    finance_settlement_risks: Optional[FinanceSettlementRisks] = Field(
        None, description="CRITICAL: Finance and settlement risks"
    )

    # Risk analysis
    risk_assessment: Optional[RiskAssessment] = Field(
        None, description="Risk assessment and recommendations"
    )

    # Additional extracted information
    extracted_clauses: Optional[List[str]] = Field(
        None, description="Key contract clauses"
    )
    regulatory_references: Optional[List[str]] = Field(
        None, description="Referenced regulations or acts"
    )
    attachments_referenced: Optional[List[str]] = Field(
        None, description="Referenced attachments or schedules"
    )


# State-specific critical validation schemas
class NSWCriticalValidation(BaseModel):
    """NSW-specific CRITICAL validation requirements."""

    # Mandatory disclosures
    section_10_7_certificate_provided: bool = Field(
        default=False, description="Section 10.7 planning certificate"
    )
    contract_for_sale_land_act_compliance: bool = Field(
        default=False, description="Conveyancing Act 1919 compliance"
    )
    vendor_disclosure_statement: bool = Field(
        default=False, description="VDS under Property Stock and Business Agents Act"
    )

    # NSW specific risks
    mine_subsidence_compensation: Optional[bool] = Field(
        None, description="Mine Subsidence Compensation Act coverage"
    )
    coastal_protection_act_compliance: Optional[bool] = Field(
        None, description="Coastal Protection Act compliance"
    )
    contaminated_land_management_act: Optional[List[str]] = Field(
        None, description="CLM Act notices"
    )

    # Strata specific (NSW)
    strata_schemes_management_act_compliance: Optional[bool] = Field(
        None, description="SSMA 2015 compliance"
    )
    building_bond_and_defects_insurance: Optional[bool] = Field(
        None, description="Building defects insurance"
    )


class VICCriticalValidation(BaseModel):
    """Victoria-specific CRITICAL validation requirements."""

    # Mandatory disclosures
    section_32_statement_provided: bool = Field(
        default=False, description="Vendor's Statement (Section 32)"
    )
    sale_of_land_act_compliance: bool = Field(
        default=False, description="Sale of Land Act 1962 compliance"
    )
    owners_corporation_certificate: Optional[bool] = Field(
        None, description="Owners Corporation certificate"
    )

    # Victoria specific risks
    cladding_rectification_orders: Optional[List[str]] = Field(
        None, description="Cladding rectification orders"
    )
    building_defects_insurance: Optional[bool] = Field(
        None, description="Building defects insurance coverage"
    )
    residential_tenancies_act_compliance: Optional[bool] = Field(
        None, description="RTA compliance for investment properties"
    )


class QLDCriticalValidation(BaseModel):
    """Queensland-specific CRITICAL validation requirements."""

    # Mandatory disclosures
    property_information_form_provided: bool = Field(
        default=False, description="Property Information Form"
    )
    body_corporate_information_certificate: Optional[bool] = Field(
        None, description="Body Corporate Information Certificate"
    )

    # QLD specific risks
    body_corporate_community_management_act: Optional[bool] = Field(
        None, description="BCCM Act compliance"
    )
    sustainable_planning_act_compliance: Optional[bool] = Field(
        None, description="Planning Act compliance"
    )
    building_defects_insurance_required: Optional[bool] = Field(
        None, description="Building defects insurance requirement"
    )

    # Unique QLD issues
    management_rights_disclosure: Optional[bool] = Field(
        None, description="Management rights disclosure"
    )
    caretaking_agreement_disclosure: Optional[bool] = Field(
        None, description="Caretaking agreement disclosure"
    )


class WACriticalValidation(BaseModel):
    """Western Australia-specific CRITICAL validation requirements."""

    transfer_of_land_act_compliance: bool = Field(
        default=False, description="Transfer of Land Act compliance"
    )
    strata_titles_act_compliance: Optional[bool] = Field(
        None, description="Strata Titles Act compliance"
    )

    # WA specific risks
    contaminated_sites_act_compliance: Optional[List[str]] = Field(
        None, description="Contaminated Sites Act notices"
    )
    mining_act_compliance: Optional[List[str]] = Field(
        None, description="Mining Act tenure and applications"
    )


class SACriticalValidation(BaseModel):
    """South Australia-specific CRITICAL validation requirements."""

    land_and_business_sale_act_compliance: bool = Field(
        default=False, description="Land and Business (Sale and Conveyancing) Act"
    )
    community_titles_act_compliance: Optional[bool] = Field(
        None, description="Community Titles Act compliance"
    )

    # SA specific risks
    development_act_compliance: Optional[List[str]] = Field(
        None, description="Development Act compliance issues"
    )
    native_vegetation_act_compliance: Optional[List[str]] = Field(
        None, description="Native Vegetation Act restrictions"
    )


# Usage example and documentation
CONTRACT_EXTRACTION_PROMPT_TEMPLATE = """
You are an expert Australian real estate lawyer specialized in contract analysis.
Extract all legal entities and important information from the provided contract.

Contract Type: {contract_type}
State Jurisdiction: {state}

CRITICAL FOCUS AREAS (highest priority for risk assessment):
1. **Additional Conditions** - Any conditions beyond the standard template
2. **Special Clauses** - Modifications or additions to standard contract terms
3. **Planning Certificates** - Section 10.7 certificates, EPA Act notices, heritage restrictions
4. **Technical Diagrams** - Sewer diagrams, surveys, easements, encroachments
5. **Attached Documents** - All referenced certificates, reports, plans

STANDARD TEMPLATE vs NON-STANDARD ANALYSIS:
- Identify which clauses are standard template language
- Flag any modifications to standard clauses as HIGH PRIORITY
- Assess risk level of each additional condition and special clause
- Focus extraction effort on non-standard elements

Extract information according to the ContractEntityExtraction schema, with special attention to:

HIGHEST PRIORITY (these carry the most risk):
- Additional conditions and special clauses (often handwritten or inserted)
- Planning certificate restrictions and EPA Act notices
- Sewer service diagrams and survey discrepancies
- Environmental planning restrictions
- Heritage and coastal protection limitations
- Contaminated land notices
- Unusual financial arrangements in special clauses
- Non-standard possession or completion terms

MEDIUM PRIORITY:
- All parties and property details
- Standard financial terms and dates
- Professional representatives
- Standard conditions (finance, inspection)

Risk Assessment Guidelines:
- CRITICAL: Missing planning certificates, environmental issues, unusual additional conditions
- HIGH: Tight deadlines, non-standard financial terms, complex special clauses
- MEDIUM: Standard conditions with tight timeframes
- LOW: Standard template clauses with normal terms

Return the extracted information in the specified JSON schema format, prioritizing the identification and risk assessment of non-standard elements.
"""

# Additional extraction patterns for AI models
CRITICAL_EXTRACTION_PATTERNS = {
    "additional_conditions": [
        r"Additional Condition \d+",
        r"Special Condition \d+",
        r"Schedule [A-Z]",
        r"Annexure [A-Z]",
        r"attached hereto",
        r"subject to the following",
    ],
    "planning_restrictions": [
        r"Section 10\.7",
        r"Section 32",
        r"Property Information Form",
        r"Planning Certificate",
        r"Environmental Planning and Assessment Act",
        r"EPA Act",
        r"heritage restriction",
        r"contaminated land",
        r"coastal protection",
        r"flood planning",
        r"acid sulfate",
        r"bushfire prone",
        r"mine subsidence",
    ],
    "strata_risks": [
        r"body corporate",
        r"owners corporation",
        r"strata plan",
        r"unit entitlement",
        r"by-laws",
        r"special levy",
        r"sinking fund",
        r"management rights",
        r"building defects",
    ],
    "crown_land_mining": [
        r"crown land",
        r"mining lease",
        r"petroleum license",
        r"mineral rights",
        r"native title",
        r"aboriginal land rights",
        r"coal mining",
        r"quarrying rights",
    ],
    "environmental_contamination": [
        r"contaminated land",
        r"environmental site assessment",
        r"soil contamination",
        r"asbestos",
        r"lead paint",
        r"underground storage",
        r"remediation",
        r"hazardous materials",
    ],
    "easements_covenants": [
        r"easement",
        r"right of way",
        r"restrictive covenant",
        r"positive covenant",
        r"building line",
        r"height restriction",
        r"architectural control",
        r"electricity easement",
        r"gas pipeline",
    ],
    "finance_settlement_risks": [
        r"unconditional",
        r"vendor finance",
        r"cash settlement",
        r"GST margin scheme",
        r"FIRB approval",
        r"foreign investment",
        r"caveat",
        r"deposit release",
    ],
    "red_flag_terms": [
        r"as is",
        r"where is",
        r"without warranty",
        r"vendor makes no representation",
        r"at purchaser's risk",
        r"unconditional",
        r"no cooling off",
        r"immediate settlement",
        r"cash only",
        r"subject to existing tenancies",
    ],
    "commercial_industrial": [
        r"existing tenancies",
        r"rental income",
        r"lease expiry",
        r"permitted use",
        r"zoning compliance",
        r"OH&S compliance",
        r"fire safety",
        r"DDA compliance",
        r"environmental compliance",
    ],
}

# Property type specific templates
PROPERTY_TYPE_SCHEMAS = {
    "strata_apartment": [
        "StrataSpecific",
        "PlanningCertificates",
        "EasementsCovenants",
        "EnvironmentalContamination",
        "FinanceSettlementRisks",
    ],
    "house_land": [
        "PlanningCertificates",
        "CrownLandMiningRights",
        "EasementsCovenants",
        "EnvironmentalContamination",
        "FinanceSettlementRisks",
    ],
    "commercial_industrial": [
        "CommercialIndustrialSpecific",
        "PlanningCertificates",
        "CrownLandMiningRights",
        "EnvironmentalContamination",
        "EasementsCovenants",
        "FinanceSettlementRisks",
    ],
    "off_plan_development": [
        "OffPlanSpecific",
        "StrataSpecific",
        "PlanningCertificates",
        "EnvironmentalContamination",
        "FinanceSettlementRisks",
    ],
}

# State jurisdiction validation mapping
STATE_VALIDATION_SCHEMAS = {
    "NSW": "NSWCriticalValidation",
    "VIC": "VICCriticalValidation",
    "QLD": "QLDCriticalValidation",
    "WA": "WACriticalValidation",
    "SA": "SACriticalValidation",
    "TAS": "NSWCriticalValidation",  # Similar to NSW
    "NT": "NSWCriticalValidation",  # Similar to NSW
    "ACT": "NSWCriticalValidation",  # Similar to NSW
}
