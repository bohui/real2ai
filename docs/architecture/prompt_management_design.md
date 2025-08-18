# Prompt Management System Design

## Overview

This document outlines the refactored prompt management architecture that properly separates system prompts from user prompts using Markdown files, following best practices for maintainability, scalability, and version control.

## Current State Analysis

**Existing Strengths:**
- ✅ Sophisticated prompt management system in `backend/app/core/prompts/`
- ✅ Jinja2 templating with custom filters
- ✅ YAML frontmatter metadata support
- ✅ Template validation and caching
- ✅ Australian legal terminology specialization

**Areas for Improvement:**
- ❌ No clear separation between system and user prompts
- ❌ Inconsistent template organization structure
- ❌ Limited prompt versioning strategy
- ❌ Missing prompt composition and inheritance
- ❌ No dedicated user interaction prompt management

## Refactored Architecture

### Directory Structure

```
backend/app/prompts/
├── system/                           # System prompts (AI behavior)
│   ├── base/
│   │   ├── assistant_core.md         # Core AI assistant behavior
│   │   ├── safety_guidelines.md      # Safety and ethical guidelines
│   │   └── reasoning_framework.md    # Logical reasoning approach
│   ├── domain/
│   │   ├── legal_specialist.md       # Legal domain expertise
│   │   ├── contract_analyst.md       # Contract analysis specialization
│   │   └── ocr_processor.md          # OCR processing behavior
│   └── context/
│       ├── australian_legal.md       # Australian legal context
│       └── state_specific/
│           ├── nsw_context.md
│           ├── vic_context.md
│           └── qld_context.md
├── user/                             # User-facing prompts
│   ├── instructions/
│   │   ├── contract_analysis.md      # How to analyze contracts
│   │   ├── ocr_extraction.md         # OCR processing instructions
│   │   └── risk_assessment.md        # Risk evaluation instructions
│   ├── templates/
│   │   ├── outputs/
│   │   │   ├── analysis_report.md    # Output formatting templates
│   │   │   └── risk_summary.md
│   │   └── interactions/
│   │       ├── clarification.md      # User clarification prompts
│   │       └── error_recovery.md     # Error handling prompts
│   └── workflows/
│       ├── contract_workflow.md      # Multi-step processes
│       └── validation_workflow.md
├── shared/                           # Reusable components
│   ├── fragments/
│   │   ├── legal_terms.md           # Common legal terminology
│   │   ├── formatting_rules.md      # Output formatting standards
│   │   └── validation_rules.md      # Input validation patterns
│   └── macros/
│       ├── currency_formatting.md   # Jinja2 macros
│       └── date_formatting.md
└── config/
    ├── prompt_registry.yaml         # Central prompt catalog
    ├── composition_rules.yaml       # How prompts combine
    └── version_manifest.yaml        # Version tracking
```

### System Prompt Design

#### Template Structure

```markdown
---
type: "system"
category: "base|domain|context"
name: "assistant_core"
version: "2.1.0"
description: "Core AI assistant behavior and personality"
dependencies: []
inheritance: null
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 2000
temperature_range: [0.0, 0.2]
priority: 100  # Loading priority (higher = first)
tags: ["core", "system", "behavior"]
---

# System Identity

You are a specialized AI assistant for Australian real estate contract analysis.

## Core Principles

1. **Accuracy First**: Provide precise, fact-based analysis
2. **Australian Context**: Apply Australian legal frameworks
3. **User Safety**: Prioritize user protection and informed decisions
4. **Clarity**: Communicate complex legal concepts clearly

## Behavioral Guidelines

### Response Style
- Professional yet approachable
- Structured and organized
- Evidence-based reasoning
- Clear disclaimers when appropriate

### Error Handling
- Acknowledge limitations honestly
- Request clarification when needed
- Provide partial answers when complete information unavailable
- Escalate to human experts when appropriate
```

### User Prompt Design

#### Template Structure

```markdown
---
type: "user"
category: "instructions|templates|workflows"
name: "contract_analysis"
version: "1.4.0"
description: "Instructions for analyzing Australian real estate contracts"
system_requirements: ["legal_specialist", "australian_legal"]
required_variables:
  - "contract_text"
  - "australian_state"
  - "analysis_type"
optional_variables:
  - "user_experience_level"
  - "specific_concerns"
model_compatibility: ["gemini-2.5-flash"]
max_tokens: 12000
temperature_range: [0.1, 0.4]
tags: ["contract", "analysis", "user-facing"]
---

# Contract Analysis Instructions

Analyze the provided Australian real estate contract focusing on the following areas:

## Analysis Framework

{% include "shared/fragments/legal_terms.md" %}

### 1. Document Identification
- Contract type and jurisdiction
- Parties involved (vendor/purchaser)
- Property details and description

### 2. Financial Analysis
{% macro format_currency(amount) %}
{{ amount | currency }}
{% endmacro %}

- Purchase price: {{ contract_details.purchase_price | currency }}
- Deposit amount and terms
- Settlement arrangements

### 3. Risk Assessment
{% if analysis_type == "comprehensive" %}
{% include "shared/fragments/validation_rules.md" %}
{% endif %}

## State-Specific Considerations

{% if australian_state == "NSW" %}
{% include "system/context/state_specific/nsw_context.md" %}
{% elif australian_state == "VIC" %}
{% include "system/context/state_specific/vic_context.md" %}
{% elif australian_state == "QLD" %}
{% include "system/context/state_specific/qld_context.md" %}
{% endif %}

## Output Requirements

Format your analysis using the template:
{% include "user/templates/outputs/analysis_report.md" %}
```

## Advanced Features

### 1. Prompt Composition System

```yaml
# config/composition_rules.yaml
compositions:
  contract_analysis_complete:
    description: "Complete contract analysis with all components"
    system_prompts:
      - "system/base/assistant_core"
      - "system/domain/legal_specialist"
      - "system/context/australian_legal"
    user_prompts:
      - "user/instructions/contract_analysis"
```

### 2. Version Management

```yaml
# config/version_manifest.yaml
versions:
  "2.1.0":
    release_date: "2024-01-15"
    changes:
      - "Enhanced NSW-specific legal context"
      - "Improved currency formatting macros"
      - "Added comprehensive risk assessment framework"
    compatibility:
      breaking_changes: false
      deprecated_features: []
    
  "2.0.0":
    release_date: "2024-01-01"
    changes:
      - "Complete restructure with system/user separation"
      - "Introduced prompt composition system"
    compatibility:
      breaking_changes: true
      migration_guide: "docs/migration/v2.0.0.md"
```

### 3. Prompt Registry

```yaml
# config/prompt_registry.yaml
registry:
  system_prompts:
    assistant_core:
      path: "system/base/assistant_core.md"
      category: "base"
      priority: 100
      dependencies: []
    
    legal_specialist:
      path: "system/domain/legal_specialist.md"
      category: "domain"
      priority: 80
      dependencies: ["assistant_core"]
  
  user_prompts:
    contract_analysis:
      path: "user/instructions/contract_analysis.md"
      category: "instructions"
      system_requirements: ["legal_specialist", "australian_legal"]

  shared_components:
    legal_terms:
      path: "shared/fragments/legal_terms.md"
      type: "fragment"
      reusable: true
```

## Implementation Strategy

### Phase 1: Core Refactoring
1. **Migrate existing templates** to new structure
2. **Separate system/user concerns** in current prompts
3. **Create base system prompts** for AI behavior
4. **Implement composition system** in PromptManager

### Phase 2: Enhanced Features
1. **Add prompt inheritance** and template composition
2. **Implement version management** with rollback capabilities
3. **Create validation workflows** for prompt quality
4. **Add performance monitoring** and optimization

### Phase 3: Advanced Capabilities
1. **Dynamic prompt generation** based on context
2. **A/B testing framework** for prompt effectiveness
3. **Multi-language support** for prompts
4. **Integration with CI/CD** for automated testing

## Best Practices Implementation

### 1. Separation of Concerns
- **System prompts**: Define AI behavior and personality
- **User prompts**: Contain task-specific instructions
- **Shared fragments**: Reusable components across prompts

### 2. Version Control Integration
- Each prompt file has semantic versioning
- Version manifest tracks changes and compatibility
- Migration guides for breaking changes
- Automated testing of prompt combinations

### 3. Template Composition
- Inheritance hierarchy prevents duplication
- Jinja2 includes and macros for modularity
- Dynamic prompt assembly based on requirements
- Validation of composed prompts

### 4. Quality Assurance
- Automated validation of prompt syntax
- Token usage optimization and monitoring
- A/B testing framework for prompt effectiveness
- Performance metrics and continuous improvement

### 5. Developer Experience
- Clear documentation and examples
- IDE support with schema validation
- Hot-reloading for development
- Comprehensive error messages and debugging

## Migration Path

### Current State → Target State

1. **Audit existing prompts** in `backend/app/prompts/user/`
2. **Extract system behavior** from current templates
3. **Create base system prompts** for AI personality
4. **Refactor user-facing prompts** to remove system concerns
5. **Implement composition layer** in PromptManager
6. **Add validation and testing** for new structure
7. **Deploy with backward compatibility** during transition
8. **Remove deprecated patterns** after validation

This design ensures clean separation between system and user prompts while maintaining the sophisticated features of your existing system.