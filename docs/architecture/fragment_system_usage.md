# Fragment-Based Prompt System Usage Guide

## Overview

The fragment-based prompt system enables sophisticated composition of prompts from reusable components, providing clean separation between system behavior and user instructions while supporting state-specific legal requirements.

## System Architecture

```
backend/app/prompts/
├── system/                    # AI behavior and personality
│   ├── base/                 # Core assistant behavior
│   ├── domain/               # Specialized expertise
│   └── context/              # Legal and cultural context
├── user/                     # Task-specific instructions
│   ├── instructions/         # How to perform tasks
│   ├── templates/            # Output formatting
│   └── workflows/            # Multi-step processes
├── fragments/                # Reusable content components
│   ├── nsw/                  # NSW-specific legal content
│   ├── vic/                  # Victoria-specific content
│   ├── qld/                  # Queensland-specific content
│   └── common/               # Shared legal frameworks
└── config/                   # Orchestration configuration
    ├── composition_rules.yaml
    ├── prompt_registry.yaml
    └── *_orchestrator.yaml
```

## Usage Examples

### 1. Basic Fragment-Based Composition

```python
from app.core.prompts.manager import PromptManager, PromptManagerConfig
from app.core.prompts.context import PromptContext, ContextType

# Configure with fragment support
config = PromptManagerConfig(
    templates_dir=Path("backend/app/prompts"),
    config_dir=Path("backend/app/prompts/config"),
    enable_composition=True
)

manager = PromptManager(config)

# Create context
context = PromptContext(
    context_type=ContextType.USER,
    variables={
        "contract_text": "Sample NSW purchase agreement...",
        "australian_state": "NSW",
        "analysis_type": "comprehensive",
        "user_experience_level": "novice",
        "transaction_value": 850000
    }
)

# Compose with fragments
result = await manager.render_composed(
    composition_name="contract_analysis_complete",
    context=context,
    return_parts=True
)

print("System Prompt:", result["system"])
print("User Prompt:", result["user"])
```

### 2. State-Specific Fragment Resolution

The system automatically includes appropriate state-specific fragments:

**NSW Context** includes:
- `fragments/nsw/planning_certificates.md` - Section 149 requirements
- `fragments/nsw/cooling_off_period.md` - 5 business day period

**VIC Context** includes:
- `fragments/vic/vendor_statements.md` - Section 32 requirements  
- `fragments/vic/cooling_off_period.md` - 3 business day period

**All States** include:
- `fragments/common/cooling_off_framework.md` - General framework
- `fragments/common/statutory_warranties.md` - Consumer protections

### 3. Custom Fragment Creation

```markdown
---
category: "state_specific"
state: "NSW"
type: "legal_requirement"
priority: 80
description: "NSW Section 149 planning certificate requirements"
tags: ["nsw", "planning", "certificates"]
---

### NSW Section 149 Planning Certificates

**Critical NSW Requirement**: Section 149 planning certificates must be provided.

**Key Information to Verify**:
- Zoning classification and permitted uses
- Development restrictions and height limits
- Heritage listings and conservation areas
- Environmental constraints and flood zones
```

### 4. Orchestration Configuration

```yaml
# contract_analysis_orchestrator.yaml
prompt_id: "contract_analysis"
base_template: "user/instructions/contract_analysis_base.md"

fragments:
  state_specific:
    condition: "australian_state"
    priority: 80
    mappings:
      NSW:
        - "fragments/nsw/planning_certificates.md"
        - "fragments/nsw/cooling_off_period.md"
      VIC:
        - "fragments/vic/vendor_statements.md"
        - "fragments/vic/cooling_off_period.md"
  
  consumer_protection:
    always_include:
      - "fragments/common/cooling_off_framework.md"
      - "fragments/common/statutory_warranties.md"
```

### 5. Base Template with Fragment Placeholders

```markdown
# Contract Analysis Instructions

## Analysis Framework
[Standard analysis instructions...]

## State-Specific Legal Requirements
{{ state_specific_fragments }}

## Consumer Protection Framework  
{{ consumer_protection_fragments }}

## Output Requirements
[Standard output formatting...]
```

## Benefits Achieved

### ✅ **Maintainability**
- **O(n) complexity**: Each fragment maintained independently
- **Isolated changes**: Update NSW requirements without affecting VIC
- **Version control**: Clean diffs, no merge conflicts

### ✅ **Reusability**
- **Cross-prompt sharing**: Use same fragments across different prompts
- **Composition flexibility**: Mix and match fragments for different scenarios
- **DRY principle**: Single source of truth for each legal requirement

### ✅ **Testing & Quality**
- **Unit testing**: Test individual fragments in isolation
- **A/B testing**: Compare different fragment versions
- **Quality metrics**: Track fragment effectiveness and usage

### ✅ **Team Scalability**
- **Parallel development**: Multiple developers work on different fragments
- **Specialization**: Legal experts focus on specific state requirements
- **Clear ownership**: Each fragment has defined responsibility

### ✅ **Performance**
- **Lazy loading**: Load only relevant fragments for each request
- **Intelligent caching**: Cache frequently used fragment combinations
- **Token optimization**: Include only necessary content

## Migration from Logic-in-Prompts

### Before (Logic-in-Prompts)
```jinja2
{% if australian_state == "NSW" %}
### NSW Specific Terms:
- Section 149 planning certificates
- Home Building Act warranties
{% elif australian_state == "VIC" %}  
### Victoria Specific Terms:
- Section 32 vendor statements
- Owners corporation details
{% endif %}
```

### After (Fragment-Based)
```markdown
# Base Template
## State-Specific Requirements
{{ state_specific_fragments }}

# NSW Fragment (nsw/planning_certificates.md)
### NSW Section 149 Planning Certificates
[Detailed NSW requirements...]

# VIC Fragment (vic/vendor_statements.md)  
### Victoria Section 32 Vendor Statements
[Detailed VIC requirements...]
```

## Best Practices

### 1. Fragment Design
- **Single Responsibility**: Each fragment covers one specific topic
- **Self-Contained**: Fragments don't depend on other fragments
- **Rich Metadata**: Include comprehensive metadata for categorization
- **Consistent Structure**: Follow standard format and style guidelines

### 2. Orchestration Strategy
- **Logical Grouping**: Group related fragments in orchestration rules
- **Priority Management**: Use priorities to control fragment ordering
- **Condition Clarity**: Make conditions explicit and well-documented
- **Fallback Handling**: Handle missing fragments gracefully

### 3. Content Management
- **Regular Updates**: Keep fragments current with legal changes
- **Quality Review**: Regular review of fragment content and effectiveness
- **Version Control**: Track changes and maintain version history
- **Expert Review**: Have domain experts validate fragment accuracy

### 4. Performance Optimization
- **Caching Strategy**: Cache resolved fragment combinations
- **Size Management**: Keep fragments focused and appropriately sized
- **Load Testing**: Test with realistic fragment combinations
- **Monitoring**: Track fragment resolution time and cache hit rates

## Advanced Features

### Dynamic Fragment Resolution
- Context-aware fragment selection based on multiple variables
- Conditional logic for complex scenarios (e.g., interstate transactions)
- Runtime fragment composition for specialized requirements

### Fragment Analytics
- Track which fragments are most frequently used
- Measure fragment effectiveness in prompt outcomes
- A/B test different fragment versions for optimization

### Multi-Language Support  
- State-specific fragments in multiple languages
- Cultural adaptation beyond translation
- Legal system context for international users

This fragment-based approach provides enterprise-grade prompt management with the flexibility to handle complex, state-specific legal requirements while maintaining clean, maintainable code architecture.