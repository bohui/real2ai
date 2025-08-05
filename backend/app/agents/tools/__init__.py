"""
Real2.AI Contract Analysis Tools

This module organizes all contract analysis tools into categorized submodules:
- domain: Australian property law domain-specific tools
- validation: Document and data validation tools
- analysis: Risk and content analysis tools
- compliance: Legal compliance checking tools
"""

# Import all tools for easy access
from .domain import *
from .validation import *
from .analysis import *
from .compliance import *

__all__ = [
    # Domain tools
    'extract_australian_contract_terms',
    'identify_contract_template_type',
    
    # Validation tools
    'validate_document_quality',
    'validate_contract_terms_completeness',
    'validate_workflow_step',
    
    # Analysis tools
    'analyze_special_conditions',
    'comprehensive_risk_scoring_system',
    'calculate_overall_confidence_score',
    
    # Compliance tools
    'validate_cooling_off_period',
    'calculate_stamp_duty',
]