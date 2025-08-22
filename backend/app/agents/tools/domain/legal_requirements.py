"""
Legal requirements derivation tool.

Converts (ContractType, PurchaseMethod, UseCategory, PropertyCondition)
into a requirements dict for downstream prompt specialization.
"""

from typing import Dict, Tuple
from langchain.tools import tool

from app.schema.enums import (
    ContractType,
    PurchaseMethod,
    UseCategory,
    PropertyCondition,
    LegalRequirement,
)


# Integration mapping for legal requirements
LEGAL_REQUIREMENTS_MATRIX: Dict[
    Tuple[ContractType, PurchaseMethod, UseCategory, PropertyCondition],
    Dict[LegalRequirement, bool],
] = {
    # New Construction/Off-Plan - HIGH COMPLIANCE
    (
        ContractType.PURCHASE_AGREEMENT,
        PurchaseMethod.OFF_PLAN,
        UseCategory.RESIDENTIAL,
        PropertyCondition.NEW_CONSTRUCTION,
    ): {
        LegalRequirement.HOME_BUILDING_ACT: True,
        LegalRequirement.BUILDING_CERTIFICATES: True,
        LegalRequirement.OCCUPATION_CERTIFICATES: True,
        LegalRequirement.SUNSET_CLAUSES: True,
        LegalRequirement.PROGRESS_PAYMENTS: True,
        LegalRequirement.BUILDING_WARRANTIES: True,
    },
    (
        ContractType.PURCHASE_AGREEMENT,
        PurchaseMethod.OFF_PLAN,
        UseCategory.RESIDENTIAL,
        PropertyCondition.OFF_THE_PLAN,
    ): {
        LegalRequirement.HOME_BUILDING_ACT: True,
        LegalRequirement.BUILDING_CERTIFICATES: True,
        LegalRequirement.OCCUPATION_CERTIFICATES: True,
        LegalRequirement.SUNSET_CLAUSES: True,
        LegalRequirement.PROGRESS_PAYMENTS: True,
        LegalRequirement.BUILDING_WARRANTIES: True,
    },
    # Recent Building Work - MODERATE COMPLIANCE
    (
        ContractType.PURCHASE_AGREEMENT,
        PurchaseMethod.STANDARD,
        UseCategory.RESIDENTIAL,
        PropertyCondition.RECENT_BUILDING_WORK,
    ): {
        LegalRequirement.HOME_BUILDING_ACT: True,
        LegalRequirement.BUILDING_CERTIFICATES: True,
        LegalRequirement.OCCUPATION_CERTIFICATES: False,
        LegalRequirement.SUNSET_CLAUSES: False,
        LegalRequirement.PROGRESS_PAYMENTS: False,
        LegalRequirement.BUILDING_WARRANTIES: True,
    },
    # Standard Existing Property - STANDARD COMPLIANCE
    (
        ContractType.PURCHASE_AGREEMENT,
        PurchaseMethod.STANDARD,
        UseCategory.RESIDENTIAL,
        PropertyCondition.EXISTING_STANDARD,
    ): {
        LegalRequirement.HOME_BUILDING_ACT: False,
        LegalRequirement.BUILDING_CERTIFICATES: False,
        LegalRequirement.OCCUPATION_CERTIFICATES: False,
        LegalRequirement.SUNSET_CLAUSES: False,
        LegalRequirement.PROGRESS_PAYMENTS: False,
        LegalRequirement.BUILDING_WARRANTIES: False,
    },
    # Auction Sales - Modified requirements
    (
        ContractType.PURCHASE_AGREEMENT,
        PurchaseMethod.AUCTION,
        UseCategory.RESIDENTIAL,
        PropertyCondition.EXISTING_STANDARD,
    ): {
        LegalRequirement.HOME_BUILDING_ACT: False,
        LegalRequirement.BUILDING_CERTIFICATES: False,
        LegalRequirement.COOLING_OFF_PERIOD: False,
        LegalRequirement.VENDOR_STATEMENT: True,
        LegalRequirement.PLANNING_CERTIFICATES: True,
    },
    # Commercial - Different framework
    (
        ContractType.PURCHASE_AGREEMENT,
        PurchaseMethod.STANDARD,
        UseCategory.COMMERCIAL,
        PropertyCondition.EXISTING_STANDARD,
    ): {
        LegalRequirement.HOME_BUILDING_ACT: False,
        LegalRequirement.BUILDING_CERTIFICATES: False,
        LegalRequirement.COMMERCIAL_DUE_DILIGENCE: True,
        LegalRequirement.ENVIRONMENTAL_ASSESSMENTS: True,
        LegalRequirement.ZONING_COMPLIANCE: True,
    },
}


def _coerce_enum(value, enum_cls):
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value))
    except Exception:
        # Attempt case-insensitive match on value attribute
        try:
            normalized = str(value).lower()
            for member in enum_cls:
                if member.value == normalized:
                    return member
        except Exception:
            pass
    return None


@tool
def derive_legal_requirements(
    contract_type: str,
    purchase_method: str,
    use_category: str,
    property_condition: str,
) -> Dict[str, bool]:
    """Derive legal requirements given contract taxonomy.

    Inputs are string values matching enum values; will be coerced to enums.
    Returns a dict of requirement flags to annotate state and future prompts.
    """
    ct = _coerce_enum(contract_type, ContractType)
    pm = _coerce_enum(purchase_method, PurchaseMethod)
    uc = _coerce_enum(use_category, UseCategory)
    pc = _coerce_enum(property_condition, PropertyCondition)

    if not all([ct, pm, uc, pc]):
        return {}

    # Convert enum-keyed mapping back to string-keyed for state/prompt compatibility
    enum_map = LEGAL_REQUIREMENTS_MATRIX.get((ct, pm, uc, pc), {})
    return {k.value if hasattr(k, "value") else str(k): v for k, v in enum_map.items()}
