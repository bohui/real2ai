---
type: "user"
name: "contract_structure_analysis"
version: "1.0.0"
description: "Analyze and extract structured information from Australian real estate contracts"
fragment_orchestration: "contract_analysis"
required_variables:
  - "extracted_text"
  - "australian_state"
  - "contract_type"
  - "user_type"
  - "user_experience_level"
optional_variables:
  - "complexity"
  - "analysis_depth"
  - "focus_areas"
  - "expects_structured_output"
  - "format_instructions"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 15000
temperature_range: [0.1, 0.3]
tags: ["analysis", "contract", "structure", "australian", "legal"]
---

# Contract Structure Analysis - {{ australian_state }} {{ contract_type }}

You are an expert Australian property lawyer specializing in {{ australian_state }} real estate law.
Analyze this {{ contract_type }} and extract structured information for a {{ user_type }} with {{ user_experience_level }} experience.

## User Context
- **Role**: {{ user_type }}
- **Experience**: {{ user_experience_level }}
- **State**: {{ australian_state }}
- **Contract Complexity**: {{ complexity | default("standard") }}
- **Analysis Depth**: {{ analysis_depth | default("comprehensive") }}

## Contract Text
```
{{ extracted_text}}
```

## Analysis Guidelines

### Data Extraction Principles:
1. **Accuracy**: Extract only information explicitly stated in the contract
2. **Completeness**: Include all relevant financial and legal details
3. **Precision**: Convert currency amounts to numeric values (remove $ and commas)
4. **Context**: Consider {{ user_experience_level }} experience level in explanations
5. **State Law**: Apply {{ australian_state }}-specific legal requirements

### Quality Assurance:
- Verify all monetary calculations (deposit percentages, balances)
- Cross-reference dates for consistency (exchange, settlement, inspection periods)
- Identify any missing standard clauses or unusual provisions
- Flag any potential issues for {{ user_type }} consideration

### Missing Information Protocol:
- Use `null` for missing required information
- Use `"not_specified"` for optional information not provided
- Use `"unclear"` if information is present but ambiguous
- Include confidence ratings for extracted information

{{ user_experience_fragments }}

## Structured Output
{% if expects_structured_output %}
{{ format_instructions }}
{% endif %}
