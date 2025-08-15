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
    """Contract types for analysis"""

    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    RENTAL_AGREEMENT = "rental_agreement"
    COMMERCIAL_LEASE = "commercial_lease"
    OPTION_TO_PURCHASE = "option_to_purchase"
    OFF_PLAN = "off_plan"
    AUCTION = "auction"
    UNKNOWN = "unknown"


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
