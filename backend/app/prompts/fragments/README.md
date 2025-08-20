---
category: README.md
context:
  state: '*'
  contract_type: '*'
  purchase_method: '*'
  use_category: '*'
  user_experience: '*'
  analysis_depth: '*'
priority: 70
version: 1.0.0
description: Fragment System Documentation
tags:
- readme
---

# Fragment System Documentation

This directory implements the new folder-structure-driven fragment system for prompt composition.

## Overview

The fragment system allows dynamic composition of prompts by combining base templates with contextually relevant fragments. The system uses folder structure as the single source of truth for grouping and template variable names.

## Folder Structure

The first-level folder under `fragments/` defines the group name and must match the template variable name used by consumers:

```
fragments/
  state_requirements/            -> {{ state_requirements }}
    NSW/
      planning_certificates.md
      cooling_off_period.md
    VIC/
      vendor_statements.md
      cooling_off_period.md
    QLD/
      disclosure_statements.md
      body_corporate.md
  contract_types/               -> {{ contract_types }}
    purchase/
      settlement_requirements.md
      finance_conditions.md
      inspection_rights.md
    lease/
      rental_obligations.md
      maintenance_responsibilities.md
      termination_rights.md
    option/
      exercise_conditions.md
      time_limitations.md
  user_experience/              -> {{ user_experience }}
    novice/
      first_time_buyer_guide.md
      key_terminology.md
    intermediate/
      advanced_considerations.md
      market_variations.md
    expert/
      technical_analysis.md
      precedent_references.md
  analysis_depth/               -> {{ analysis_depth }}
    comprehensive/
      detailed_risk_matrix.md
      financial_modeling.md
      compliance_checklist.md
    quick/
      key_points_summary.md
      critical_flags_only.md
    focused/
      targeted_assessment.md
  consumer_protection/          -> {{ consumer_protection }}
    cooling_off/
      framework.md
    statutory_warranties/
      protection.md
    unfair_terms/
      protections.md
  risk_factors/                 -> {{ risk_factors }}
    financial_indicators.md
  shared/                       -> {{ shared }}
    legal_terms.md
```

## Fragment Metadata Schema

Each fragment uses YAML frontmatter with the following schema:

```yaml
---
category: "legal_requirement"          # Optional taxonomy classification
context:
  state: "NSW"                        # or "*" or ["NSW", "VIC"]
  contract_type: "purchase"            # or "*" or ["purchase", "option"]
  user_experience: "*"                 # or "novice" | "intermediate" | "expert"
  analysis_depth: "*"                  # or "comprehensive" | "quick" | "focused"
priority: 80                          # Integer 0-100, higher = included first
version: "1.0.0"                      # Semantic version string
description: "NSW Section 149 planning certificate requirements"
tags: ["nsw", "planning", "certificates", "section-149"]
---

### Fragment Content

Your fragment content goes here...
```

### Metadata Fields

- **category** (optional): Free-form classification for taxonomy purposes
- **context** (optional): Defines when this fragment should be included
  - Each key supports: exact value, list of values (any-match), or wildcard `"*"`
  - Case-insensitive string matching for all values
  - Missing context means fragment applies to all scenarios
- **priority** (optional): Integer 0-100, defaults to 50. Higher priority fragments are included first
- **version** (optional): Semantic version string for tracking changes
- **description** (optional): Human-readable description of fragment purpose
- **tags** (optional): List of strings for searching and organization

### Deprecated Fields

These fields are no longer used and should be removed:
- **group**: Replaced by folder structure
- **domain**: No longer needed

## Context Matching Logic

Fragments are included based on generic context matching:

```python
def matches_context(fragment_context: dict, runtime_context: dict) -> bool:
    for key, required in fragment_context.items():
        # Wildcard matches anything
        if required == "*":
            continue
            
        actual = runtime_context.get(key)
        if actual is None:
            return False
            
        # Case-insensitive comparison
        if isinstance(required, list):
            if actual.lower() not in [x.lower() for x in required]:
                return False
        else:
            if actual.lower() != required.lower():
                return False
                
    return True
```

### Example Context Matching

Runtime context:
```json
{
  "state": "NSW",
  "contract_type": "purchase", 
  "user_experience": "novice",
  "analysis_depth": "comprehensive"
}
```

Fragment contexts that would match:
- `{"state": "NSW"}` ✓
- `{"state": "NSW", "contract_type": "*"}` ✓  
- `{"state": ["NSW", "VIC"], "contract_type": "purchase"}` ✓
- `{}` ✓ (empty context matches all)

Fragment contexts that would NOT match:
- `{"state": "VIC"}` ✗
- `{"state": "NSW", "contract_type": "lease"}` ✗
- `{"state": "NSW", "missing_key": "value"}` ✗ (runtime context lacks missing_key)

## Template Usage

Base templates reference groups using exact folder names:

```markdown
## State-Specific Legal Requirements  
{{ state_requirements }}

## Contract Type Specific Analysis
{{ contract_types }}

## Experience Level Guidance
{{ user_experience }}

## Analysis Depth and Focus
{{ analysis_depth }}

## Consumer Protection Framework
{{ consumer_protection }}
```

If a group has no matching fragments, the variable renders as an empty string.

## Naming Rules

### Group Names (Folder Names)
- Must start with a letter
- Can contain letters, digits, and underscores
- Should be descriptive and match template variable names
- Use snake_case convention

### Fragment Files
- Must use `.md` extension
- Can be organized in subfolders within groups
- Subfolder names are for organization only and don't affect logic

## Runtime Context Model

The system expects runtime context with these common keys:

- **state**: Jurisdiction (NSW, VIC, QLD, SA, WA, etc.)
- **contract_type**: Contract type (purchase, lease, option, etc.)
- **user_experience**: User experience level (novice, intermediate, expert)
- **analysis_depth**: Analysis depth (comprehensive, quick, focused)

Additional keys can be added without code changes.

## Validation

The system includes comprehensive validation:

### Folder Structure Validation
- Checks group names follow naming rules
- Warns about empty groups
- Identifies missing referenced groups

### Metadata Validation  
- Validates YAML syntax
- Checks context structure (string, list, or "*")
- Warns about deprecated fields
- Validates priority ranges (0-100)

### Template Reference Validation
- Checks template variables match available groups
- Identifies unused groups
- Reports missing group folders

## Migration from Old System

When migrating from the orchestrator-based system:

1. Move fragments to appropriate group folders
2. Update metadata to new schema:
   - Remove `group` and `domain` fields
   - Add `context` block with appropriate matching rules
   - Use wildcards (`"*"`) for broad applicability
3. Update templates to use group names directly
4. Remove orchestrator fragment mapping configurations

## Performance Considerations

- Fragments are cached after first load
- Group composition is optimized for repeated use
- Large fragment libraries should use priority to limit inclusion
- Complex context matching is O(n) where n = number of fragments

## Examples

### State-Specific Fragment
```yaml
---
category: "legal_requirement"
context:
  state: "NSW"
  contract_type: "*"  # Applies to all contract types
priority: 80
version: "1.0.0"
description: "NSW planning certificate requirements"
---

### NSW Planning Certificate Requirements
Critical NSW requirement for all property transactions...
```

### Contract Type Specific Fragment
```yaml
---
category: "contract_specific"
context:
  state: "*"  # Applies to all states
  contract_type: ["purchase", "option"]  # Applies to purchase OR option
priority: 70
version: "1.0.0"
description: "Settlement and finance conditions"
---

### Settlement Requirements
For purchase and option agreements...
```

### Universal Fragment
```yaml
---
category: "consumer_protection"
context: {}  # Applies to all scenarios (empty context)
priority: 90
version: "1.0.0"
description: "Universal consumer protection framework"
---

### Consumer Protection Rights
These protections apply to all property transactions...
```

## Troubleshooting

### Fragment Not Included
1. Check context matching - ensure runtime context provides required keys
2. Verify case sensitivity - all string matching is case-insensitive
3. Check for typos in context keys or values
4. Ensure fragment has proper YAML frontmatter

### Template Variable Empty
1. Verify group folder exists and contains fragments
2. Check if any fragments match the runtime context
3. Validate fragment metadata is properly formatted
4. Check validation output for errors

### Performance Issues
1. Review fragment priorities to limit inclusion
2. Use more specific context matching to reduce overhead
3. Consider caching strategies for frequently used contexts
4. Monitor fragment loading and composition times