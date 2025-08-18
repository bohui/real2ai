# State-Aware Output Parsing System

## Overview

The State-Aware Output Parsing System eliminates the need for conditional logic in prompt templates by handling state-specific parsing requirements in the execution stage. This provides a cleaner architecture where:

- **Prompt templates** focus on content and instructions
- **Output parsers** handle state-specific field requirements
- **Node execution** applies the appropriate parser based on context

## Architecture

### Before (Mixed Logic in Prompts)
```markdown
{% if australian_state == "NSW" %}
## NSW Specific Requirements
- Section 149 Certificate details
- Home Building Act compliance
{% elif australian_state == "VIC" %}
## VIC Specific Requirements  
- Section 32 Statement details
- Owners Corporation information
{% endif %}
```

### After (Clean Separation)
```markdown
## State-Specific Context
This analysis is being performed for {{ australian_state }}. The output parser will automatically include state-specific fields and requirements based on the Australian state context.
```

## Components

### 1. StateAwareParser
The core class that selects appropriate output parsers based on Australian state context.

```python
from app.core.prompts.state_aware_parser import StateAwareParser

# Create a state-aware parser
parser = StateAwareParser(
    base_model=ContractTermsOutput,
    state_specific_models={
        "NSW": NSWContractTermsOutput,
        "VIC": VICContractTermsOutput,
        "QLD": QLDContractTermsOutput
    }
)

# Parse with state context
result = parser.parse_with_retry(response, state="NSW")
```

### 2. StateAwareParserFactory
Factory class providing pre-configured parsers for common use cases.

```python
from app.core.prompts.state_aware_parser import StateAwareParserFactory

# Create parsers for different analysis types
contract_parser = StateAwareParserFactory.create_contract_terms_parser()
compliance_parser = StateAwareParserFactory.create_compliance_parser()
risk_parser = StateAwareParserFactory.create_risk_parser()
```

### 3. Base Node Integration
All workflow nodes now have access to state-aware parsing:

```python
class MyNode(BaseNode):
    async def execute(self, state):
        australian_state = state.get("australian_state", "NSW")
        
        # Get state-aware parser
        parser = self.get_state_aware_parser("contract_terms", australian_state)
        
        # Get format instructions for specific state
        format_instructions = self.get_format_instructions_for_state("contract_terms", australian_state)
        
        # Parse with state context
        result = parser.parse_with_retry(response, australian_state)
```

## Supported States

### NSW (New South Wales)
- **Section 149 Certificate**: Planning certificate details and expiry
- **Home Building Act**: Warranty insurance details and coverage
- **Conveyancing Act**: Compliance with NSW conveyancing requirements
- **Vendor Disclosure**: Required property disclosures under NSW law
- **Consumer Guarantees**: Australian Consumer Law protections

### VIC (Victoria)
- **Section 32 Statement**: Vendor statement details and compliance
- **Owners Corporation**: Owners corporation details for strata properties
- **Planning Permits**: Building and planning permit information
- **Sale of Land Act**: Compliance requirements and consumer rights
- **Building Permits**: Current building permit status and compliance

### QLD (Queensland)
- **Form 1**: Property disclosure statement details
- **Body Corporate**: Body corporate information and levies
- **QBCC Licensing**: Building work licensing requirements
- **Community Titles**: Community titles scheme information
- **Disclosure Requirements**: Required property disclosures

## Usage Examples

### Basic Usage
```python
# Create parser
parser = StateAwareParserFactory.create_contract_terms_parser()

# Parse NSW response
nsw_result = parser.parse_with_retry(nsw_response, "NSW")

# Parse VIC response  
vic_result = parser.parse_with_retry(vic_response, "VIC")

# Get format instructions for specific state
nsw_instructions = parser.get_format_instructions("NSW")
```

### In Workflow Nodes
```python
async def execute(self, state):
    australian_state = state.get("australian_state", "NSW")
    
    # Get state-aware parser
    parser = self.get_state_aware_parser("contract_terms", australian_state)
    
    # Render prompt with state-specific parser
    rendered_prompt = await self.prompt_manager.render(
        template_name="analysis/contract_structure",
        context=context,
        output_parser=parser
    )
    
    # Parse response with state context
    result = parser.parse_with_retry(llm_response, australian_state)
```

## Benefits

### 1. Cleaner Prompt Templates
- No conditional logic in markdown templates
- Easier to maintain and update
- Better separation of concerns

### 2. Centralized State Logic
- State-specific parsing logic in one place
- Easy to add new states and fields
- Consistent behavior across all nodes

### 3. Better Testing
- Can test state-specific parsing independently
- Easier to mock and validate
- Clear test boundaries

### 4. Extensibility
- Simple to add new Australian states
- Easy to add new field types
- Backward compatibility maintained

### 5. Performance
- No template rendering overhead for state logic
- Efficient parser selection
- Cached format instructions

## Migration Guide

### 1. Update Prompt Templates
Remove state-specific conditional logic and replace with generic instructions:

```markdown
# Before
{% if australian_state == "NSW" %}
NSW specific content...
{% elif australian_state == "VIC" %}
VIC specific content...
{% endif %}

# After  
## State-Specific Context
The output parser will automatically include state-specific fields for {{ australian_state }}.
```

### 2. Update Node Execution
Use state-aware parsing in node execution methods:

```python
# Before
output_parser=self.structured_parsers.get("contract_terms")

# After
state_aware_parser = self.get_state_aware_parser("contract_terms", australian_state)
output_parser=state_aware_parser
```

### 3. Update Parsing Logic
Use state context in parsing calls:

```python
# Before
parsing_result = parser.parse(response)

# After
parsing_result = parser.parse_with_retry(response, australian_state)
```

## Adding New States

### 1. Define State-Specific Model
```python
state_models = {
    "WA": type("WAContractTermsOutput", (ContractTermsOutput,), {
        "__annotations__": {
            "wa_specific_field": Dict[str, Any],
            "wa_legal_requirement": str,
        }
    })
}
```

### 2. Update Factory Method
```python
@staticmethod
def create_contract_terms_parser() -> StateAwareParser:
    state_models = {
        # ... existing states ...
        "WA": type("WAContractTermsOutput", (ContractTermsOutput,), {
            "__annotations__": {
                "wa_specific_field": Dict[str, Any],
            }
        })
    }
    
    return StateAwareParser(
        ContractTermsOutput,
        state_specific_models=state_models,
        default_state="NSW"
    )
```

### 3. Add State-Specific Documentation
Update this document with the new state's requirements and fields.

## Testing

### Unit Tests
```python
def test_nsw_parser():
    parser = StateAwareParserFactory.create_contract_terms_parser()
    result = parser.parse_with_retry(nsw_response, "NSW")
    
    assert result.success
    assert "section_149_certificate" in result.parsed_data.dict()
```

### Integration Tests
```python
async def test_workflow_with_state_aware_parsing():
    workflow = ContractAnalysisWorkflow()
    state = {"australian_state": "NSW", "document_content": "..."}
    
    result = await workflow.extract_contract_terms(state)
    assert "section_149_certificate" in result["contract_terms"]
```

## Troubleshooting

### Common Issues

1. **Parser Not Found**
   - Ensure state-aware parsers are initialized in workflow
   - Check that parser type exists in `state_aware_parsers` dict

2. **State-Specific Fields Missing**
   - Verify state-specific model is defined in factory
   - Check that state code matches expected format (e.g., "NSW" not "nsw")

3. **Format Instructions Not State-Specific**
   - Ensure `get_format_instructions(state)` is called with state parameter
   - Verify state-aware parser is passed to prompt manager

### Debug Mode
Enable debug logging to see parser selection:

```python
import logging
logging.getLogger("app.core.prompts.state_aware_parser").setLevel(logging.DEBUG)
```

## Future Enhancements

### 1. Dynamic State Detection
- Automatic state detection from contract content
- Fallback state selection based on context

### 2. Custom Field Mapping
- User-defined state-specific fields
- Dynamic schema generation

### 3. Multi-State Support
- Contracts spanning multiple states
- State transition handling

### 4. Internationalization
- Support for other countries
- Multi-jurisdiction contracts
