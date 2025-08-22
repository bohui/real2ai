"""
Domain-specific tools for Australian property contract analysis
"""

from .contract_extraction import extract_australian_contract_terms
from .legal_requirements import derive_legal_requirements
from .template_identification import identify_contract_template_type

__all__ = [
    "extract_australian_contract_terms",
    "derive_legal_requirements",
    "identify_contract_template_type",
]
