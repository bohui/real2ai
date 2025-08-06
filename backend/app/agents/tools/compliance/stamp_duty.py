"""
Stamp duty calculation for Australian property purchases
"""

from typing import Dict, List, Any, Optional
from langchain.tools import tool
from decimal import Decimal

from app.schema.enums import AustralianState
from app.models.contract_state import StampDutyCalculation


@tool
def calculate_stamp_duty(
    purchase_price: float, 
    state: str, 
    is_first_home: bool = False,
    is_foreign_buyer: bool = False,
    is_investment: bool = False
) -> Dict[str, Any]:
    """Calculate Australian stamp duty with state-specific rates and exemptions"""
    
    stamp_duty_rates = {
        "NSW": {
            "thresholds": [
                (14000, 0.0125),
                (32000, 0.015), 
                (85000, 0.0175),
                (319000, 0.035),
                (1064000, 0.045),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 650000,
            "first_home_concession_threshold": 800000,
            "foreign_buyer_surcharge": 0.08,
            "investment_surcharge": 0.02
        },
        "VIC": {
            "thresholds": [
                (25000, 0.014),
                (130000, 0.024),
                (960000, 0.06),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 600000,
            "first_home_concession_threshold": 750000,
            "foreign_buyer_surcharge": 0.07,
            "vacant_land_tax": 0.01
        },
        "QLD": {
            "thresholds": [
                (5000, 0.015),
                (75000, 0.035),
                (540000, 0.045),
                (1000000, 0.055),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 550000,
            "foreign_buyer_surcharge": 0.07
        },
        "SA": {
            "thresholds": [
                (12000, 0.011),
                (30000, 0.033),
                (50000, 0.045),
                (100000, 0.05),
                (200000, 0.055),
                (250000, 0.06),
                (500000, 0.065),
                (float('inf'), 0.065)
            ],
            "first_home_exemption_threshold": 650000,
            "foreign_buyer_surcharge": 0.07
        },
        "WA": {
            "thresholds": [
                (120000, 0.019),
                (150000, 0.029),
                (360000, 0.038),
                (725000, 0.049),
                (float('inf'), 0.051)
            ],
            "first_home_exemption_threshold": 430000,
            "first_home_concession_threshold": 530000,
            "foreign_buyer_surcharge": 0.07
        },
        "TAS": {
            "thresholds": [
                (1300, 0.015),
                (3000, 0.025),
                (50000, 0.04),
                (75000, 0.04),
                (200000, 0.04),
                (375000, 0.04),
                (725000, 0.04),
                (float('inf'), 0.04)
            ],
            "first_home_exemption_threshold": 400000,
            "foreign_buyer_surcharge": 0.03
        },
        "NT": {
            "thresholds": [
                (525000, 0.067),
                (3000000, 0.05),
                (float('inf'), 0.055)
            ],
            "first_home_exemption_threshold": 650000,
            "foreign_buyer_surcharge": 0.10
        },
        "ACT": {
            "thresholds": [
                (200000, 0.012),
                (300000, 0.024),
                (500000, 0.048),
                (750000, 0.06),
                (1455000, 0.067),
                (float('inf'), 0.067)
            ],
            "first_home_exemption_threshold": 600000,
            "foreign_buyer_surcharge": 0.075
        }
    }
    
    if state not in stamp_duty_rates:
        return {
            "error": f"Stamp duty rates not available for state: {state}",
            "total_duty": 0,
            "state": state
        }
    
    rates = stamp_duty_rates[state]
    
    # Calculate base stamp duty
    base_duty = _calculate_tiered_duty(purchase_price, rates["thresholds"])
    
    # Apply first home buyer exemption/concession
    first_home_adjustment = 0
    if is_first_home:
        exemption_threshold = rates.get("first_home_exemption_threshold", 0)
        concession_threshold = rates.get("first_home_concession_threshold", 0)
        
        if purchase_price <= exemption_threshold:
            first_home_adjustment = -base_duty  # Full exemption
        elif concession_threshold and purchase_price <= concession_threshold:
            # Partial concession (simplified calculation)
            concession_rate = (concession_threshold - purchase_price) / (concession_threshold - exemption_threshold)
            first_home_adjustment = -base_duty * concession_rate
    
    # Apply foreign buyer surcharge
    foreign_buyer_surcharge = 0
    if is_foreign_buyer:
        surcharge_rate = rates.get("foreign_buyer_surcharge", 0)
        foreign_buyer_surcharge = purchase_price * surcharge_rate
    
    # Apply investment property surcharge (NSW specific)
    investment_surcharge = 0
    if is_investment and state == "NSW":
        investment_rate = rates.get("investment_surcharge", 0)
        investment_surcharge = purchase_price * investment_rate
    
    # Calculate total
    total_duty = base_duty + first_home_adjustment + foreign_buyer_surcharge + investment_surcharge
    total_duty = max(0, total_duty)  # Ensure non-negative
    
    return {
        "base_duty": round(base_duty, 2),
        "first_home_adjustment": round(first_home_adjustment, 2),
        "foreign_buyer_surcharge": round(foreign_buyer_surcharge, 2),
        "investment_surcharge": round(investment_surcharge, 2),
        "total_duty": round(total_duty, 2),
        "purchase_price": purchase_price,
        "state": state,
        "is_first_home": is_first_home,
        "is_foreign_buyer": is_foreign_buyer,
        "is_investment": is_investment,
        "calculation_breakdown": {
            "base_calculation": f"Calculated using {state} tiered rates",
            "first_home_benefit": f"${abs(first_home_adjustment):.2f} {'exemption' if first_home_adjustment < 0 else 'no benefit'}" if is_first_home else "Not applicable",
            "foreign_buyer_impact": f"${foreign_buyer_surcharge:.2f} additional duty" if is_foreign_buyer else "Not applicable",
            "investment_impact": f"${investment_surcharge:.2f} additional duty" if is_investment else "Not applicable"
        }
    }


def _calculate_tiered_duty(purchase_price: float, thresholds: List[tuple]) -> float:
    """Calculate stamp duty using tiered thresholds"""
    
    total_duty = 0
    remaining_price = purchase_price
    previous_threshold = 0
    
    for threshold, rate in thresholds:
        if remaining_price <= 0:
            break
        
        # Calculate the amount in this tier
        tier_amount = min(remaining_price, threshold - previous_threshold)
        
        # Calculate duty for this tier
        tier_duty = tier_amount * rate
        total_duty += tier_duty
        
        # Update for next iteration
        remaining_price -= tier_amount
        previous_threshold = threshold
        
        if threshold == float('inf'):
            break
    
    return total_duty