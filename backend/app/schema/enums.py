"""Shared enums and constants for the application."""

from enum import Enum


class AustralianState(str, Enum):
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    SA = "SA"
    WA = "WA"
    TAS = "TAS"
    NT = "NT"
    ACT = "ACT"


class ContractType(str, Enum):
    PURCHASE_AGREEMENT = "purchase_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    OFF_PLAN = "off_plan"
    AUCTION = "auction"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"