"""Condition-related enums."""

from enum import Enum


class ConditionType(str, Enum):
    """Condition type classification"""

    STANDARD = "standard"
    SPECIAL = "special"
    PRECEDENT = "precedent"
    SUBSEQUENT = "subsequent"


class ConditionCategory(str, Enum):
    """Condition category classification"""

    FINANCE = "finance"
    INSPECTION = "inspection"
    PLANNING = "planning"
    TITLE = "title"
    STRATA = "strata"
    SALE_OF_PROPERTY = "sale_of_property"
    DEVELOPMENT = "development"
    OTHER = "other"


class ConditionDependencyType(str, Enum):
    """Dependency type between conditions"""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    OTHER = "other"
