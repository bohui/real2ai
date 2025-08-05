---
type: "user"
category: "instructions"
name: "risk_assessment_base"
version: "2.0.0"
description: "Fragment-based comprehensive risk assessment for Australian property contracts"
fragment_orchestration: "risk_assessment_orchestrator"
required_variables:
  - "contract_data"
  - "contract_type"
  - "australian_state"
  - "user_type"
  - "user_experience"
optional_variables:
  - "focus_areas"
  - "risk_tolerance"
  - "investment_purpose"
model_compatibility:
  - "gemini-2.5-pro"
  - "gpt-4"
max_tokens: 15000
temperature_range: [0.2, 0.5]
tags:
  - "risk"
  - "assessment"
  - "fragment-based"
---

# Comprehensive Risk Assessment Instructions

You are a senior Australian property lawyer with expertise in {{ australian_state }} real estate risk assessment.
Perform comprehensive risk analysis for this {{ contract_type }}.

## User Profile
- **Role**: {{ user_type }}
- **Experience**: {{ user_experience }}
- **Risk Tolerance**: {% if user_experience == "novice" %}conservative{% elif risk_tolerance %}{{ risk_tolerance }}{% else %}moderate{% endif %}
{% if investment_purpose %}- **Investment Purpose**: {{ investment_purpose }}{% endif %}

## Contract Data
```json
{{ contract_data | tojson(indent=2) }}
```

## Risk Assessment Framework

Evaluate risks across these dimensions:

1. **Legal Risks** - Contract terms, compliance, enforceability
2. **Financial Risks** - Price, financing, costs, market factors
3. **Property Risks** - Condition, location, title, planning
4. **Transaction Risks** - Settlement, conditions, timing
5. **{{ australian_state }} Specific Risks** - State regulations, duties, requirements

## State-Specific Risk Indicators

{{ state_specific_fragments }}

## Financial Risk Assessment

{{ financial_risk_fragments }}

## User Experience Guidance

{{ experience_level_fragments }}

## Analysis Output Requirements

Return detailed risk assessment as JSON with the following structure:

### Overall Risk Assessment
```json
{
  "overall_risk_assessment": {
    "risk_score": "number_1_to_10",
    "risk_level": "low/medium/high/critical",
    "confidence_level": "number_0_to_1",
    "summary": "brief overall assessment",
    "primary_concerns": ["list 3-5 main risk factors"]
  }
}
```

### Risk Categories
Provide detailed analysis for each category:

- **Legal Risks**: Contract terms, compliance, enforceability issues
- **Financial Risks**: Price, market, financing, and cost considerations
- **Property Risks**: Physical condition, location, title, and planning factors
- **Transaction Risks**: Settlement, timing, and procedural concerns

### Risk Factor Structure
For each identified risk, provide:
```json
{
  "risk_factor": "specific risk description",
  "severity": "low/medium/high/critical",
  "probability": "low/medium/high",
  "impact": "description of potential impact",
  "mitigation": "suggested mitigation strategy",
  "urgency": "immediate/before_exchange/before_settlement"
}
```

### Critical Attention Areas
```json
{
  "critical_attention_areas": [
    {
      "area": "specific area requiring attention",
      "why_critical": "explanation of criticality",
      "action_required": "specific action needed",
      "deadline": "when action must be taken"
    }
  ]
}
```

### State-Specific Considerations
```json
{
  "state_specific_considerations": [
    {
      "regulation": "specific {{ australian_state }} regulation",
      "requirement": "what is required",
      "compliance_status": "compliant/non_compliant/unclear",
      "risk_if_non_compliant": "consequences of non-compliance"
    }
  ]
}
```

### Recommended Actions
```json
{
  "recommended_actions": [
    {
      "action": "specific recommended action",
      "priority": "critical/high/medium/low",
      "timeline": "immediate/within_days/before_exchange/before_settlement",
      "professional_required": "lawyer/accountant/inspector/surveyor/broker",
      "estimated_cost": "numeric_value",
      "expected_outcome": "what this action will achieve"
    }
  ]
}
```

### Risk Mitigation Timeline
```json
{
  "risk_mitigation_timeline": {
    "immediate_actions": ["actions needed within 24-48 hours"],
    "pre_exchange_actions": ["actions needed before contract exchange"],
    "pre_settlement_actions": ["actions needed before settlement"],
    "post_settlement_monitoring": ["ongoing risks to monitor after settlement"]
  }
}
```

## Assessment Principles

- Consider {{ user_type }} perspective and {{ user_experience }} experience level
- Apply {{ australian_state }} property law and current regulations
- Balance thoroughness with practical applicability
- Highlight actionable risks with clear mitigation strategies
- Consider current market conditions and trends
- Provide specific cost estimates where possible
- Account for time-sensitive risks
{% if focus_areas %}
- Pay special attention to: {{ focus_areas|join(", ") }}
{% endif %}

**Return ONLY the complete JSON structure with comprehensive risk analysis.**