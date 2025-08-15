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
    """Types of financial amounts"""

    PURCHASE_PRICE = "purchase_price"
    DEPOSIT = "deposit"
    RENT_AMOUNT = "rent_amount"
    BOND = "bond"
    STAMP_DUTY = "stamp_duty"
    LEGAL_FEES = "legal_fees"
    AGENT_COMMISSION = "agent_commission"
    BODY_CORPORATE_FEES = "body_corporate_fees"
    COUNCIL_RATES = "council_rates"
    OTHER_FEES = "other_fees"
