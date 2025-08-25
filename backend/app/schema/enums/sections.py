"""Section key enum for Step 2 analysis sections.

Defines canonical keys used across seeds and analysis nodes.
"""

from enum import Enum


class SectionKey(str, Enum):
    PARTIES_PROPERTY = "parties_property"
    FINANCIAL_TERMS = "financial_terms"
    CONDITIONS = "conditions"
    WARRANTIES = "warranties"
    DEFAULT_TERMINATION = "default_termination"
    SETTLEMENT_LOGISTICS = "settlement_logistics"
    TITLE_ENCUMBRANCES = "title_encumbrances"
    ADJUSTMENTS_OUTGOINGS = "adjustments_outgoings"
    DISCLOSURE_COMPLIANCE = "disclosure_compliance"
    SPECIAL_RISKS = "special_risks"
    CROSS_SECTION_VALIDATION = "cross_section_validation"
