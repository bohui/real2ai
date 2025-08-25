"""Entity extraction enums."""

from enum import Enum


class EntityType(str, Enum):
    """Types of entities that can be extracted"""

    ADDRESS = "address"
    PROPERTY_REFERENCE = "property_reference"
    DATE = "date"
    FINANCIAL_AMOUNT = "financial_amount"
    PARTY_NAME = "party_name"
    LEGAL_REFERENCE = "legal_reference"
    CONTACT_INFO = "contact_info"
    PROPERTY_DETAILS = "property_details"


class PartyRole(str, Enum):
    """Roles of parties in contracts"""

    VENDOR = "vendor"
    PURCHASER = "purchaser"
    LANDLORD = "landlord"
    TENANT = "tenant"
    AGENT = "agent"
    SOLICITOR = "solicitor"
    CONVEYANCER = "conveyancer"
    OTHER = "other"


class DateType(str, Enum):
    """Types of dates in contracts"""

    SETTLEMENT_DATE = "settlement_date"
    COMPLETION_DATE = "completion_date"
    EXCHANGE_DATE = "exchange_date"
    LEASE_START = "lease_start"
    LEASE_END = "lease_end"
    COOLING_OFF_EXPIRY = "cooling_off_expiry"
    FINANCE_APPROVAL_DUE = "finance_approval_due"
    INSPECTION_DUE = "inspection_due"
    CONTRACT_DATE = "contract_date"
    OTHER = "other"


class FinancialType(str, Enum):
    """Types of financial amounts in real estate contracts"""

    # Purchase-related
    PURCHASE_PRICE = "purchase_price"
    DEPOSIT = "deposit"
    BALANCE = "balance"  # remaining amount after deposit
    STAMP_DUTY = "stamp_duty"
    LAND_VALUE = "land_value"  # unimproved value for rates/tax
    IMPROVEMENTS_VALUE = "improvements_value"  # building value if split
    GST = "gst"
    TRANSFER_FEES = "transfer_fees"  # title registration, transfer duty admin
    MORTGAGE_REGISTRATION_FEES = "mortgage_registration_fees"
    LENDER_MORTGAGE_INSURANCE = "lender_mortgage_insurance"
    LOAN_AMOUNT = "loan_amount"

    # Ongoing ownership costs
    COUNCIL_RATES = "council_rates"
    WATER_RATES = "water_rates"
    STRATA_FEES = "strata_fees"  # aka body corporate fees
    LAND_TAX = "land_tax"
    INSURANCE_PREMIUMS = "insurance_premiums"
    MAINTENANCE_FEES = "maintenance_fees"

    # Rental / lease-related
    RENT_AMOUNT = "rent_amount"
    BOND = "bond"
    RENT_INCREASE = "rent_increase"
    OUTGOINGS = "outgoings"  # commercial lease pass-through costs
    UTILITY_COSTS = "utility_costs"

    # Transaction / professional fees
    LEGAL_FEES = "legal_fees"
    AGENT_COMMISSION = "agent_commission"
    CONVEYANCING_FEES = "conveyancing_fees"
    VALUATION_FEES = "valuation_fees"
    SURVEY_FEES = "survey_fees"
    BUILDING_INSPECTION_FEES = "building_inspection_fees"
    PEST_INSPECTION_FEES = "pest_inspection_fees"

    # Developer / off-the-plan
    DEVELOPMENT_LEVY = "development_levy"
    INFRASTRUCTURE_CONTRIBUTION = "infrastructure_contribution"
    REGISTRATION_FEES = "registration_fees"  # plan of subdivision, strata registration

    # Miscellaneous
    OTHER_FEES = "other_fees"
