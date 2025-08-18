# Prompt Management System Architecture

## Overview

The Prompt Management System is a composition-based architecture for managing AI prompts with support for fragments, orchestration, and structured output parsing. It follows a **composition-first** approach where all prompts are rendered through compositions that combine system and user prompts with dynamic fragment injection.

## Core Principles

1. **Composition-Only**: All prompt rendering MUST go through `render_composed()` - direct template rendering is deprecated
2. **Pydantic Output Parsing**: Structured outputs use Pydantic models with automatic format instructions
3. **Fragment Orchestration**: Dynamic content assembly based on context (state, user level, contract type)
4. **Single Entry Point**: `PromptManager.render_composed()` returns standardized schema

## Architecture Components

### 1. PromptManager (`manager.py`)
Central orchestrator for all prompt operations.

**Key Methods:**
- `render_composed()`: Primary method returning `{system_prompt, user_prompt, metadata}`
- `render()`: DEPRECATED - legacy method for backward compatibility only

**Return Schema:**
```python
{
    "system_prompt": str,      # Combined system prompts (may be empty)
    "user_prompt": str,         # User prompt with fragments and parser instructions
    "metadata": {
        "composition": str,     # Composition name used
        "steps": List[str],     # Workflow steps executed
        "fragments": List[str], # Fragments applied
        ...
    }
}
```

### 2. Compositions (`composition_rules.yaml`)

Defines how system and user prompts combine for workflows.

**Structure:**
```yaml
compositions:
  composition_name:
    system_prompts:     # List of system prompt configurations
    workflow_steps:     # Sequential/parallel execution steps
    error_handling:     # Retry and failure handling
```

**Available Compositions:**
- `complete_contract_analysis`: Full contract analysis workflow
- `ocr_to_structured_data`: Document OCR with structure extraction
- `single_diagram_analysis`: Semantic analysis of property diagrams
- `multi_diagram_analysis`: Multiple diagram risk consolidation
- `quick_contract_review`: Time-sensitive abbreviated analysis

### 3. Fragment System

Dynamic content injection based on runtime context.

**Fragment Categories:**
- **State-specific**: NSW, VIC, QLD legal requirements
- **Contract-type**: Purchase, lease, option specific terms
- **User-level**: Novice, intermediate, expert considerations
- **Quality-level**: High, standard, fast processing requirements
- **Risk-specific**: Financial, compliance, structural indicators

**Orchestration Files:**
- `contract_analysis_orchestrator.yaml`: Contract analysis fragments
- `risk_assessment_orchestrator.yaml`: Risk assessment fragments
- `ocr_extraction_orchestrator.yaml`: OCR processing fragments

### 4. Service Integration (`service_mixin.py`)

Base class for services using the prompt system.

**Key Features:**
- Automatic service metadata injection
- Standardized `render_composed()` method
- Performance tracking and caching
- Structured output parser integration

**Usage Pattern:**
```python
class MyService(PromptEnabledService):
    async def process(self):
        result = await self.render_composed(
            composition_name="complete_contract_analysis",
            context={...},
            output_parser=MyPydanticModel
        )
        prompt = result["user_prompt"]
        # Use prompt with AI service
```

### 5. Output Parsing System

Pydantic-based structured output with automatic format instructions.

**Key Components:**
- `BaseOutputParser`: Abstract parser interface
- `PydanticOutputParser`: Pydantic model parsing
- `StateAwareParser`: Australian state-specific parsing
- Format instructions automatically appended to user prompts

## Directory Structure

```
backend/app/
├── prompts/
│   ├── ARCHITECTURE.md          # This document
│   ├── config/
│   │   ├── composition_rules.yaml
│   │   ├── prompt_registry.yaml
│   │   └── *_orchestrator.yaml
│   ├── fragments/
│   │   ├── common/              # Shared fragments
│   │   ├── nsw/vic/qld/         # State-specific
│   │   ├── purchase/lease/      # Contract type
│   │   ├── analysis/            # User level
│   │   └── ocr/                 # Processing quality
│   ├── system/
│   │   ├── base/                # Core AI behavior
│   │   ├── domain/              # Domain expertise
│   │   └── context/             # Contextual knowledge
│   └── user/
│       ├── instructions/        # Base templates
│       ├── analysis/            # Analysis templates
│       ├── validation/          # Validation templates
│       └── workflow/            # Workflow templates
└── core/prompts/
    ├── manager.py               # PromptManager
    ├── composer.py              # Composition engine
    ├── fragment_manager.py      # Fragment orchestration
    ├── service_mixin.py         # Service integration
    ├── output_parser.py         # Structured output parsing
    ├── config_validator.py      # Configuration validation
    └── workflow_engine.py       # Workflow execution

```

## Workflow Execution

### 1. Service Request
Service inherits from `PromptEnabledService` and calls `render_composed()`

### 2. Composition Resolution
PromptManager loads composition from `composition_rules.yaml`

### 3. Fragment Orchestration
FragmentManager injects context-specific fragments based on:
- Australian state
- Contract type
- User experience level
- Quality requirements

### 4. Template Rendering
- System prompts combined in priority order
- User prompt rendered with fragments
- Output parser format instructions appended

### 5. Response Structure
Returns standardized dict with system_prompt, user_prompt, and metadata

## Migration Guide

### From Direct Rendering
```python
# OLD - DEPRECATED
prompt = await self.render(
    template_name="analysis/risk_assessment",
    context=context,
    output_parser=parser
)

# NEW - COMPOSITION-BASED
result = await self.render_composed(
    composition_name="complete_contract_analysis",
    context=context,
    output_parser=parser
)
prompt = result["user_prompt"]
```

### Service Implementation
```python
class ContractAnalysisService(PromptEnabledService):
    async def analyze_contract(self, document):
        # Prepare context
        context = {
            "document_text": document.text,
            "australian_state": document.state,
            "contract_type": document.type,
            "user_experience": "intermediate"
        }
        
        # Render through composition
        composition_result = await self.render_composed(
            composition_name="complete_contract_analysis",
            context=context,
            output_parser=ContractAnalysisOutput
        )
        
        # Use with AI service
        ai_response = await self.ai_client.generate(
            system_prompt=composition_result["system_prompt"],
            user_prompt=composition_result["user_prompt"]
        )
        
        # Parse structured output
        parsed = self.parse_output(ai_response, ContractAnalysisOutput)
        return parsed
```

## Configuration Validation

The system includes `config_validator.py` for ensuring:
- All compositions reference existing templates
- Fragment paths resolve correctly
- Orchestrator mappings are valid
- No orphaned templates or fragments

Run validation:
```python
from app.core.prompts.config_validator import validate_prompt_configurations

results = validate_prompt_configurations(templates_dir, config_dir)
if not results["valid"]:
    print(f"Errors: {results['summary']['total_errors']}")
```

## Performance Considerations

1. **Caching**: Templates and compositions cached on first load
2. **Fragment Resolution**: Cached per context combination
3. **Parallel Rendering**: Batch operations supported
4. **Token Optimization**: Fragment system minimizes redundancy

## Best Practices

1. **Always use compositions** - Never call render() directly
2. **Define clear contexts** - Provide all required context variables
3. **Use appropriate compositions** - Match composition to use case
4. **Leverage fragments** - Let orchestrators handle variations
5. **Implement parsers** - Use Pydantic models for structured output
6. **Validate configurations** - Run validator in CI/CD pipeline

## Testing

Tests should verify:
1. Composition returns correct schema
2. Fragments inject properly based on context
3. Output parsers generate correct format instructions
4. Service integration works with new return format
5. Legacy render() shows deprecation warnings

## Future Enhancements

- [ ] Dynamic composition generation
- [ ] ML-based fragment selection
- [ ] Prompt versioning and rollback
- [ ] A/B testing framework
- [ ] Performance analytics dashboard
- [ ] Multi-language support
- [ ] Prompt compression optimization

## References

- Composition Rules: `/backend/app/prompts/config/composition_rules.yaml`
- Fragment Orchestrators: `/backend/app/prompts/config/*_orchestrator.yaml`
- Service Examples: `/backend/app/services/ai/gemini_ocr_service.py`
- Agent Nodes: `/backend/app/agents/nodes/*_node.py`