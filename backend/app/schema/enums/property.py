"""Property and contract enums."""

from enum import Enum


class PropertyType(str, Enum):
    """Property types"""

    HOUSE = "house"
    UNIT = "unit"
    TOWNHOUSE = "townhouse"
    APARTMENT = "apartment"
    VILLA = "villa"
    LAND = "land"
    ACREAGE = "acreage"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RETAIL = "retail"
    RESIDENTIAL_HOUSE = "residential_house"
    UNIT_APARTMENT = "unit_apartment"
    MIXED_USE = "mixed_use"
    OTHER = "other"


class ContractType(str, Enum):
    """Authoritative user-provided contract classification"""

    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    OPTION_TO_PURCHASE = "option_to_purchase"
    UNKNOWN = "unknown"


class PurchaseMethod(str, Enum):
    """Purchase method, only when contract_type = purchase_agreement"""

    OFF_PLAN = "off_plan"
    AUCTION = "auction"
    PRIVATE_TREATY = "private_treaty"
    TENDER = "tender"
    EXPRESSION_OF_INTEREST = "expression_of_interest"
    OTHER = "other"


class UseCategory(str, Enum):
    """Property use category, applied to purchase_agreement and lease_agreement"""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RETAIL = "retail"


class PropertyCondition(str, Enum):
    """Property condition/building work status affecting legal requirements"""

    NEW_CONSTRUCTION = "new_construction"  # Under construction/just completed
    OFF_THE_PLAN = "off_the_plan"  # Not yet built
    RECENT_BUILDING_WORK = "recent_building_work"  # Major work within 6-7 years
    EXISTING_STANDARD = "existing_standard"  # Standard existing property
    RENOVATED_HISTORIC = "renovated_historic"  # Historic property with recent work
    AS_IS_CONDITION = "as_is_condition"  # Sold in current condition
    UNKNOWN_CONDITION = "unknown_condition"  # Cannot determine from contract


class TransactionComplexity(str, Enum):
    """Transaction complexity affecting compliance requirements"""

    STANDARD_RESIDENTIAL = "standard_residential"  # Standard home sale
    NEW_DEVELOPMENT = "new_development"  # New construction/off-plan
    COMMERCIAL_COMPLEX = "commercial_complex"  # Commercial/industrial
    STRATA_COMPLEX = "strata_complex"  # Strata/body corporate involved
    RURAL_SPECIALIZED = "rural_specialized"  # Rural/agricultural property
    HERITAGE_RESTRICTED = "heritage_restricted"  # Heritage/conservation area
    UNKNOWN_COMPLEXITY = "unknown_complexity"  # Cannot determine


class DocumentType(str, Enum):
    """Document types"""

    CONTRACT = "contract"
    TITLE_DEED = "title_deed"
    SURVEY = "survey"
    PLANNING_DOCUMENT = "planning_document"
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    LEGAL_CONTRACT = "legal_contract"
    FINANCIAL_DOCUMENT = "financial_document"
    GENERAL_DOCUMENT = "general_document"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing status"""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    BASIC_COMPLETE = "basic_complete"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYSIS_COMPLETE = "analysis_complete"
    FAILED = "failed"


class ProcessingStatus(str, Enum):
    """General processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
