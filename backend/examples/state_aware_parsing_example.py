#!/usr/bin/env python3
"""
State-Aware Parsing Example

This example demonstrates how the new state-aware parsing system works,
eliminating the need for conditional logic in prompt templates.
"""

import asyncio
import json
from typing import Dict, Any

from app.core.prompts.state_aware_parser import StateAwareParserFactory


async def demonstrate_state_aware_parsing():
    """Demonstrate state-aware parsing for different Australian states."""
    
    print("=== State-Aware Parsing Example ===\n")
    
    # Create state-aware parsers
    contract_terms_parser = StateAwareParserFactory.create_contract_terms_parser()
    compliance_parser = StateAwareParserFactory.create_compliance_parser()
    risk_parser = StateAwareParserFactory.create_risk_parser()
    
    # Example LLM responses for different states
    nsw_response = """
    {
        "purchase_price": 850000,
        "settlement_date": "2024-06-15",
        "deposit_amount": 85000,
        "property_address": "123 Main St, Sydney NSW 2000",
        "section_149_certificate": {
            "expiry_date": "2025-12-31",
            "planning_zone": "R2"
        },
        "home_building_act": {
            "warranty_insurance": "required",
            "coverage_period": "6 years"
        },
        "australian_state": "NSW"
    }
    """
    
    vic_response = """
    {
        "purchase_price": 750000,
        "settlement_date": "2024-07-20",
        "deposit_amount": 75000,
        "property_address": "456 Collins St, Melbourne VIC 3000",
        "section_32_statement": {
            "provided": true,
            "compliance": "compliant"
        },
        "owners_corporation": {
            "levies": 2000,
            "period": "quarterly"
        },
        "australian_state": "VIC"
    }
    """
    
    qld_response = """
    {
        "purchase_price": 650000,
        "settlement_date": "2024-08-10",
        "deposit_amount": 65000,
        "property_address": "789 Queen St, Brisbane QLD 4000",
        "form_1": {
            "disclosure_complete": true,
            "body_corporate": "ABC Corp"
        },
        "qbcc_licensing": {
            "license_required": true,
            "license_type": "Building"
        },
        "australian_state": "QLD"
    }
    """
    
    # Test parsing for each state
    states = [
        ("NSW", nsw_response),
        ("VIC", vic_response),
        ("QLD", qld_response)
    ]
    
    for state, response in states:
        print(f"--- Testing {state} Parsing ---")
        
        # Parse with state-aware parser
        result = contract_terms_parser.parse_with_retry(response, state)
        
        if result.success:
            print(f"✅ Successfully parsed {state} response")
            print(f"   Confidence: {result.confidence_score:.2f}")
            
            # Show state-specific fields
            parsed_data = result.parsed_data.dict() if hasattr(result.parsed_data, 'dict') else result.parsed_data
            print(f"   State-specific fields:")
            
            if state == "NSW":
                if "section_149_certificate" in parsed_data:
                    print(f"     - Section 149 Certificate: {parsed_data['section_149_certificate']}")
                if "home_building_act" in parsed_data:
                    print(f"     - Home Building Act: {parsed_data['home_building_act']}")
            
            elif state == "VIC":
                if "section_32_statement" in parsed_data:
                    print(f"     - Section 32 Statement: {parsed_data['section_32_statement']}")
                if "owners_corporation" in parsed_data:
                    print(f"     - Owners Corporation: {parsed_data['owners_corporation']}")
            
            elif state == "QLD":
                if "form_1" in parsed_data:
                    print(f"     - Form 1: {parsed_data['form_1']}")
                if "qbcc_licensing" in parsed_data:
                    print(f"     - QBCC Licensing: {parsed_data['qbcc_licensing']}")
            
        else:
            print(f"❌ Failed to parse {state} response")
            print(f"   Errors: {result.parsing_errors}")
            print(f"   Validation errors: {result.validation_errors}")
        
        print()
    
    # Demonstrate format instructions for different states
    print("--- Format Instructions by State ---")
    for state in ["NSW", "VIC", "QLD"]:
        format_instructions = contract_terms_parser.get_format_instructions(state)
        print(f"\n{state} Format Instructions (first 200 chars):")
        print(f"   {format_instructions[:200]}...")


def demonstrate_parser_factory():
    """Demonstrate the parser factory methods."""
    
    print("\n=== Parser Factory Example ===\n")
    
    # Create different types of parsers
    contract_parser = StateAwareParserFactory.create_contract_terms_parser()
    compliance_parser = StateAwareParserFactory.create_compliance_parser()
    risk_parser = StateAwareParserFactory.create_risk_parser()
    
    print("Created parsers:")
    print(f"  - Contract Terms Parser: {type(contract_parser).__name__}")
    print(f"  - Compliance Parser: {type(compliance_parser).__name__}")
    print(f"  - Risk Parser: {type(risk_parser).__name__}")
    
    # Show supported states
    print(f"\nSupported states for contract terms:")
    for state in ["NSW", "VIC", "QLD"]:
        parser = contract_parser.get_parser_for_state(state)
        print(f"  - {state}: {type(parser).__name__}")


if __name__ == "__main__":
    print("State-Aware Parsing System Demo")
    print("=" * 50)
    
    # Run examples
    asyncio.run(demonstrate_state_aware_parsing())
    demonstrate_parser_factory()
    
    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nKey Benefits:")
    print("1. ✅ No conditional logic in prompt templates")
    print("2. ✅ State-specific parsing handled in execution stage")
    print("3. ✅ Clean separation of concerns")
    print("4. ✅ Easy to add new states and fields")
    print("5. ✅ Backward compatibility maintained")
