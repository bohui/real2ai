"""Comprehensive usage examples for the output parser schema system."""

import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from app.model.enums import AustralianState, ContractType, RiskLevel
from .schema_integration import (
    SchemaIntegrationManager, 
    SchemaType,
    create_schema_manager,
    get_contract_analysis_prompt_with_schema,
    get_ocr_extraction_prompt_with_schema,
    ANALYSIS_SCENARIOS,
    get_scenario_workflow
)
from .schema_validators import (
    SchemaValidator, 
    ValidationLevel,
    ResponseParser,
    ValidationResult,
    quick_validate,
    validate_with_details,
    parse_ai_response
)
from .state_specific_schemas import (
    get_state_specific_schema,
    get_state_risk_factors,
    get_cooling_off_period,
    NSWContractExtraction,
    VICContractExtraction,
    QLDContractExtraction
)
from .extract_entities import ContractEntityExtraction
from .ocr_schemas import OCRExtractionResults, PurchaseAgreementOCR


def example_1_basic_contract_analysis():
    """Example 1: Basic contract analysis with schema validation."""
    
    print("=== Example 1: Basic Contract Analysis ===")
    print()
    
    # Set up the analysis parameters
    contract_type = ContractType.PURCHASE_AGREEMENT
    australian_state = AustralianState.NSW
    
    # Get the prompt and schema for contract analysis
    result = get_contract_analysis_prompt_with_schema(
        contract_type=contract_type,
        australian_state=australian_state,
        quality_level="comprehensive"
    )
    
    print("Generated Prompt Components:")
    print(f"- Schema: {result['schema'].__name__}")
    print(f"- Composition: {result['composition_name']}")
    print(f"- Context variables: {list(result['context'].keys())}")
    print()
    
    # Show the actual prompt structure
    prompt = result['prompt']
    print("System Prompt (first 200 chars):")
    print(prompt.get('system_prompt', '')[:200] + "...")
    print()
    
    # Show schema information
    schema = result['schema']
    schema_json = result['schema_json']
    print(f"Schema Properties Count: {len(schema_json.get('properties', {}))}")
    print(f"Required Fields: {schema_json.get('required', [])}")
    print()
    
    return result


def example_2_ocr_extraction_workflow():
    """Example 2: OCR extraction with validation."""
    
    print("=== Example 2: OCR Extraction Workflow ===")
    print()
    
    # Set up OCR extraction
    contract_type = ContractType.PURCHASE_AGREEMENT
    australian_state = AustralianState.VIC
    
    # Get OCR extraction prompt with schema
    ocr_result = get_ocr_extraction_prompt_with_schema(
        contract_type=contract_type,
        australian_state=australian_state,
        quality_level="high"
    )
    
    print("OCR Extraction Setup:")
    print(f"- Schema: {ocr_result['schema'].__name__}")
    print(f"- Quality Level: {ocr_result['context']['quality_level']}")
    print(f"- State: {ocr_result['context']['australian_state']}")
    print()
    
    # Simulate an AI response (normally this would come from your AI model)
    mock_ocr_response = {
        "document_metadata": {
            "document_name": "Purchase_Agreement_VIC.pdf",
            "document_type": "PURCHASE_AGREEMENT",
            "total_pages": 12,
            "overall_quality": "GOOD",
            "processing_timestamp": datetime.now().isoformat(),
            "average_confidence": 0.85,
            "manual_review_required": False,
            "detected_languages": ["en"],
            "handwritten_text_detected": True,
            "table_count": 3,
            "signature_count": 4
        },
        "financial_data": {
            "purchase_price": {
                "field_name": "purchase_price",
                "field_type": "CURRENCY",
                "raw_value": "$750,000.00",
                "processed_value": "750000.00", 
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.95,
                "requires_manual_review": False
            },
            "deposit_amount": {
                "field_name": "deposit_amount",
                "field_type": "CURRENCY", 
                "raw_value": "$75,000.00",
                "processed_value": "75000.00",
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.93,
                "requires_manual_review": False
            }
        },
        "date_information": {
            "contract_date": {
                "field_name": "contract_date",
                "field_type": "DATE",
                "raw_value": "15/03/2024",
                "processed_value": "2024-03-15",
                "confidence": "HIGH",
                "document_section": "HEADER",
                "page_number": 1,
                "ocr_confidence_score": 0.89,
                "requires_manual_review": False
            },
            "settlement_date": {
                "field_name": "settlement_date",
                "field_type": "DATE",
                "raw_value": "15/05/2024",
                "processed_value": "2024-05-15", 
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 2,
                "ocr_confidence_score": 0.91,
                "requires_manual_review": False
            }
        },
        "party_information": {
            "vendor_names": [{
                "field_name": "vendor_name",
                "field_type": "TEXT",
                "raw_value": "John Smith & Mary Smith",
                "processed_value": "John Smith & Mary Smith",
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.88,
                "requires_manual_review": False
            }],
            "purchaser_names": [{
                "field_name": "purchaser_name", 
                "field_type": "TEXT",
                "raw_value": "James Brown",
                "processed_value": "James Brown",
                "confidence": "MEDIUM",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.76,
                "requires_manual_review": True
            }]
        },
        "property_details": {
            "street_address": {
                "field_name": "street_address",
                "field_type": "ADDRESS",
                "raw_value": "123 Collins Street",
                "processed_value": "123 Collins Street",
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.92,
                "requires_manual_review": False
            },
            "suburb": {
                "field_name": "suburb",
                "field_type": "TEXT",
                "raw_value": "Melbourne",
                "processed_value": "Melbourne",
                "confidence": "HIGH",
                "document_section": "BODY", 
                "page_number": 1,
                "ocr_confidence_score": 0.95,
                "requires_manual_review": False
            },
            "state": {
                "field_name": "state",
                "field_type": "TEXT",
                "raw_value": "VIC",
                "processed_value": "VIC",
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.98,
                "requires_manual_review": False
            },
            "postcode": {
                "field_name": "postcode",
                "field_type": "TEXT",
                "raw_value": "3000",
                "processed_value": "3000",
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 1,
                "ocr_confidence_score": 0.94,
                "requires_manual_review": False
            }
        },
        "conditions": {
            "finance_condition": {
                "field_name": "finance_condition",
                "field_type": "TEXT",
                "raw_value": "Subject to finance approval within 21 days",
                "processed_value": "Subject to finance approval within 21 days",
                "confidence": "HIGH",
                "document_section": "BODY",
                "page_number": 3,
                "ocr_confidence_score": 0.87,
                "requires_manual_review": False
            }
        },
        "tables": [],
        "signatures": {
            "vendor_signatures": [{
                "field_name": "vendor_signature_1",
                "field_type": "SIGNATURE",
                "raw_value": "[Signature Present]",
                "processed_value": "John Smith - Signed",
                "confidence": "MEDIUM",
                "document_section": "SIGNATURE_BLOCK",
                "page_number": 12,
                "ocr_confidence_score": 0.65,
                "requires_manual_review": True
            }],
            "purchaser_signatures": [{
                "field_name": "purchaser_signature_1",
                "field_type": "SIGNATURE", 
                "raw_value": "[Signature Present]",
                "processed_value": "James Brown - Signed",
                "confidence": "LOW",
                "document_section": "SIGNATURE_BLOCK",
                "page_number": 12,
                "ocr_confidence_score": 0.55,
                "requires_manual_review": True
            }]
        },
        "validation_results": {
            "internal_consistency": True,
            "required_fields_present": True,
            "overall_extraction_quality": "MEDIUM",
            "manual_review_priority": "MEDIUM",
            "missing_critical_fields": [],
            "conflicting_information": [],
            "formatting_issues": ["Some signatures require manual verification"],
            "recommended_actions": ["Verify signature authenticity", "Cross-check purchaser name spelling"],
            "specialist_review_needed": ["Legal review of finance conditions"]
        }
    }
    
    # Validate the OCR response
    parser = ResponseParser()
    validated_instance, validation_result = parser.parse_and_validate(
        response=json.dumps(mock_ocr_response),
        schema_class=ocr_result['schema'],
        validation_level=ValidationLevel.STANDARD
    )
    
    print("Validation Results:")
    print(f"- Valid: {validation_result.is_valid}")
    print(f"- Confidence Score: {validation_result.confidence_score:.2f}")
    print(f"- Completeness Score: {validation_result.completeness_score:.2f}")
    print(f"- Manual Review Required: {validation_result.manual_review_required}")
    
    if validation_result.data_quality_issues:
        print(f"- Data Quality Issues: {len(validation_result.data_quality_issues)}")
        for issue in validation_result.data_quality_issues[:3]:  # Show first 3
            print(f"  • {issue}")
    
    if validation_result.recommended_actions:
        print(f"- Recommended Actions: {len(validation_result.recommended_actions)}")
        for action in validation_result.recommended_actions[:2]:  # Show first 2
            print(f"  • {action}")
    print()
    
    return validated_instance, validation_result


def example_3_state_specific_analysis():
    """Example 3: State-specific analysis with enhanced schemas."""
    
    print("=== Example 3: State-Specific Analysis ===")
    print()
    
    # Compare different states
    states_to_compare = [AustralianState.NSW, AustralianState.VIC, AustralianState.QLD]
    
    for state in states_to_compare:
        print(f"--- {state.value} Analysis ---")
        
        # Get state-specific schema
        state_schema = get_state_specific_schema(state, "contract")
        validation_schema = get_state_specific_schema(state, "validation")
        
        print(f"Contract Schema: {state_schema.__name__}")
        print(f"Validation Schema: {validation_schema.__name__}")
        print(f"Cooling Off Period: {get_cooling_off_period(state)} business days")
        
        # Get state-specific risk factors
        risk_factors = get_state_risk_factors(state)
        print(f"Key Risk Factors ({len(risk_factors)}):")
        for factor in risk_factors[:3]:  # Show first 3
            print(f"  • {factor}")
        
        print()
    
    # Create a detailed NSW analysis
    print("--- Detailed NSW Analysis Setup ---")
    
    manager = create_schema_manager()
    
    nsw_analysis = manager.compose_prompt_with_schema(
        composition_name="contract_analysis_complete",
        schema_type=SchemaType.CONTRACT_ANALYSIS,
        contract_type=ContractType.PURCHASE_AGREEMENT,
        australian_state=AustralianState.NSW,
        context_variables={
            "property_type": "house",
            "analysis_focus": "comprehensive",
            "special_requirements": ["mine_subsidence_check", "section_10_7_validation"]
        }
    )
    
    print(f"NSW Analysis Schema: {nsw_analysis['schema'].__name__}")
    print("Context Variables:")
    for key, value in nsw_analysis['context'].items():
        print(f"  {key}: {value}")
    print()


def example_4_full_workflow_scenario():
    """Example 4: Complete workflow using analysis scenarios."""
    
    print("=== Example 4: Complete Analysis Workflow ===")
    print()
    
    # Set up scenario
    scenario = "comprehensive"
    contract_type = ContractType.PURCHASE_AGREEMENT
    australian_state = AustralianState.QLD
    
    print(f"Scenario: {scenario}")
    print(f"Contract Type: {contract_type.value}")
    print(f"State: {australian_state.value}")
    print()
    
    # Get the complete workflow
    workflow = get_scenario_workflow(scenario, contract_type, australian_state)
    
    print(f"Workflow Steps ({len(workflow)}):")
    for i, step in enumerate(workflow, 1):
        print(f"{i}. {step['step']}: {step['description']}")
        print(f"   Schema: {step['schema'].__name__}")
        print(f"   Composition: {step['composition_name']}")
    print()
    
    # Show scenario configuration
    scenario_config = ANALYSIS_SCENARIOS[scenario]
    print("Scenario Configuration:")
    for key, value in scenario_config.items():
        print(f"  {key}: {value}")
    print()
    
    return workflow


def example_5_validation_levels():
    """Example 5: Different validation levels and error handling."""
    
    print("=== Example 5: Validation Levels ===")
    print()
    
    # Create a problematic response to test validation
    problematic_response = {
        "contract_type": "PURCHASE_AGREEMENT",
        "jurisdiction": "NSW",
        "persons": [
            {
                "full_name": "John Smith",
                "role": "vendor",
                "phone": "invalid_phone_format"  # This will cause validation issues
            }
        ],
        "property": {
            "street_address": "123 Main St",
            "suburb": "Sydney",
            "state": "NSW",
            "postcode": "12345"  # Invalid Australian postcode
        },
        "financial_terms": {
            "purchase_price": "not_a_number"  # Invalid format
        },
        "important_dates": {
            "contract_date": "2024-03-15",
            "settlement_date": "2024-03-10"  # Before contract date - chronological issue
        }
    }
    
    # Test different validation levels
    validation_levels = [
        ValidationLevel.STRICT,
        ValidationLevel.STANDARD,
        ValidationLevel.LENIENT
    ]
    
    validator = SchemaValidator()
    
    for level in validation_levels:
        print(f"--- {level.value.upper()} Validation ---")
        
        validator.validation_level = level
        result = validator.validate_schema_response(
            response=problematic_response,
            schema_class=ContractEntityExtraction
        )
        
        print(f"Valid: {result.is_valid}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Completeness: {result.completeness_score:.2f}")
        print(f"Manual Review Required: {result.manual_review_required}")
        
        if result.validation_errors:
            print(f"Validation Errors ({len(result.validation_errors)}):")
            for error in result.validation_errors[:2]:  # Show first 2
                print(f"  • {error}")
        
        if result.data_quality_issues:
            print(f"Data Quality Issues ({len(result.data_quality_issues)}):")
            for issue in result.data_quality_issues[:2]:  # Show first 2
                print(f"  • {issue}")
        
        if result.formatting_errors:
            print(f"Formatting Errors ({len(result.formatting_errors)}):")
            for error in result.formatting_errors[:2]:  # Show first 2
                print(f"  • {error}")
        
        print()


def example_6_quick_validation_helpers():
    """Example 6: Quick validation helper functions."""
    
    print("=== Example 6: Quick Validation Helpers ===")
    print()
    
    # Test data - good response
    good_response = {
        "contract_type": "PURCHASE_AGREEMENT",
        "jurisdiction": "NSW",
        "persons": [
            {
                "full_name": "John Smith",
                "role": "vendor"
            }
        ]
    }
    
    # Test data - bad response  
    bad_response = "This is not JSON"
    
    print("Quick Validation Tests:")
    
    # Test quick_validate function
    print(f"Good response valid: {quick_validate(good_response, ContractEntityExtraction)}")
    print(f"Bad response valid: {quick_validate(bad_response, ContractEntityExtraction)}")
    print()
    
    # Test detailed validation
    print("Detailed Validation of Good Response:")
    detailed_result = validate_with_details(good_response, ContractEntityExtraction)
    print(f"  Valid: {detailed_result.is_valid}")
    print(f"  Confidence: {detailed_result.confidence_score:.2f}")
    print(f"  Missing Required: {detailed_result.missing_required_fields}")
    print()
    
    # Test AI response parsing
    print("AI Response Parsing:")
    ai_response_text = '''
    Here is the extracted contract information:
    
    ```json
    {
        "contract_type": "PURCHASE_AGREEMENT",
        "jurisdiction": "VIC",
        "persons": [
            {
                "full_name": "Jane Doe",
                "role": "purchaser"
            }
        ]
    }
    ```
    
    The analysis shows...
    '''
    
    parsed_instance, parse_result = parse_ai_response(ai_response_text, ContractEntityExtraction)
    print(f"  Parsed successfully: {parsed_instance is not None}")
    print(f"  Parse validation valid: {parse_result.is_valid}")
    if parsed_instance:
        print(f"  Extracted persons: {len(parsed_instance.persons)}")
    print()


def run_all_examples():
    """Run all usage examples."""
    
    print("🏢 OUTPUT PARSER SCHEMA SYSTEM - USAGE EXAMPLES")
    print("=" * 60)
    print()
    
    try:
        # Run examples
        example_1_basic_contract_analysis()
        print("-" * 60)
        print()
        
        example_2_ocr_extraction_workflow()
        print("-" * 60)
        print()
        
        example_3_state_specific_analysis()
        print("-" * 60)
        print()
        
        example_4_full_workflow_scenario()
        print("-" * 60)
        print()
        
        example_5_validation_levels()
        print("-" * 60)
        print()
        
        example_6_quick_validation_helpers()
        print("-" * 60)
        print()
        
        print("✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Error running examples: {str(e)}")
        import traceback
        traceback.print_exc()


def create_integration_guide():
    """Create a guide for integrating the schema system."""
    
    guide = """
# Output Parser Schema System Integration Guide

## Quick Start

1. **Basic Contract Analysis**:
```python
from app.prompts.template.schema_integration import get_contract_analysis_prompt_with_schema
from app.model.enums import ContractType, AustralianState

result = get_contract_analysis_prompt_with_schema(
    contract_type=ContractType.PURCHASE_AGREEMENT,
    australian_state=AustralianState.NSW,
    quality_level="comprehensive"
)

# Use result['prompt'] with your AI model
# Validate response with result['schema']
```

2. **OCR Extraction**:
```python
from app.prompts.template.schema_integration import get_ocr_extraction_prompt_with_schema

ocr_result = get_ocr_extraction_prompt_with_schema(
    contract_type=ContractType.PURCHASE_AGREEMENT,
    australian_state=AustralianState.VIC,
    quality_level="high"
)
```

3. **Response Validation**:
```python
from app.prompts.template.schema_validators import parse_ai_response

validated_instance, validation_result = parse_ai_response(
    ai_response_text, 
    result['schema']
)

if validation_result.is_valid:
    # Use validated_instance.model_dump() for your data
    data = validated_instance.model_dump()
else:
    # Handle validation errors
    print(validation_result.validation_errors)
```

4. **State-Specific Analysis**:
```python
from app.prompts.template.state_specific_schemas import get_state_specific_schema

# Get enhanced NSW schema
nsw_schema = get_state_specific_schema(AustralianState.NSW, "contract")
# Use NSWContractExtraction instead of base ContractEntityExtraction
```

5. **Complete Workflow**:
```python
from app.prompts.template.schema_integration import get_scenario_workflow

workflow = get_scenario_workflow(
    scenario="comprehensive",
    contract_type=ContractType.PURCHASE_AGREEMENT,
    australian_state=AustralianState.QLD
)

# Execute each step in workflow
for step in workflow:
    # step['prompt'] contains the prompt
    # step['schema'] contains the validation schema
    pass
```

## Key Benefits

- **Structured Output**: Guaranteed consistent data structure
- **State-Specific**: Handles different Australian state requirements
- **Validation**: Comprehensive validation with quality scoring
- **Fragment Integration**: Works with fragment-based prompt system
- **Flexible**: Multiple validation levels and quality settings

## Best Practices

1. Always validate AI responses before using the data
2. Use appropriate quality levels for different use cases
3. Handle validation errors gracefully with fallback strategies
4. Leverage state-specific schemas for regulatory compliance
5. Monitor confidence scores and flag low-quality extractions
"""
    
    return guide


if __name__ == "__main__":
    # Run examples if script is executed directly
    run_all_examples()
    
    # Print integration guide
    print()
    print(create_integration_guide())