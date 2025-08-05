"""
Legal compliance checking tools for Australian property contracts
"""

from .cooling_off import validate_cooling_off_period
from .stamp_duty import calculate_stamp_duty

__all__ = [
    'validate_cooling_off_period',
    'calculate_stamp_duty',
]