---
name: "risk_analysis_structured"
version: "2.0"
description: "Structured risk analysis with automatic format instructions"
required_variables: ["document_content", "analysis_focus"]
optional_variables: ["contract_type", "australian_state", "user_experience"]
model_compatibility: ["gemini-2.5-flash", "gpt-4", "claude-3-5-sonnet"]
max_tokens: 4000
temperature_range: [0.1, 0.3]
tags: ["analysis", "risk", "structured", "contract", "parser-enabled"]
output_parser_enabled: true
expects_structured_output: true
---

# Structured Risk Analysis - {{ analysis_focus | title }}

{% if contract_type %}
Analyzing {{ contract_type }} in {{ australian_state | default("NSW") }} for {{ user_experience | default("novice") }} user.
{% endif %}

## Analysis Task

Perform comprehensive risk analysis of the provided document content, focusing on {{ analysis_focus }}.

### Document Content
```
{{ document_content }}
```

## Analysis Requirements

1. **Identify all risks** related to {{ analysis_focus }}
2. **Categorize risks** by severity (LOW, MEDIUM, HIGH, CRITICAL)
3. **Provide detailed descriptions** with specific evidence from the document
4. **Suggest mitigation strategies** for each identified risk
5. **Estimate potential impact** (financial, legal, operational)

{% if analysis_focus == "infrastructure" %}
### Infrastructure-Specific Focus Areas:
- Utility connections and service availability
- Access roads and transportation infrastructure
- Telecommunications and digital connectivity
- Drainage and flood management systems
- Waste management and environmental services
{% elif analysis_focus == "environmental" %}
### Environmental-Specific Focus Areas:
- Flood risk and water management
- Bushfire risk and vegetation management
- Soil stability and contamination
- Noise pollution and air quality
- Heritage and conservation overlays
{% elif analysis_focus == "compliance" %}
### Compliance-Specific Focus Areas:
- Building code compliance
- Planning permit requirements
- Environmental regulations
- Fire safety standards
- Accessibility compliance
{% endif %}

## Context Information
- Analysis Date: {{ now.strftime('%Y-%m-%d') }}
- Analysis Focus: {{ analysis_focus }}
- Service: {{ service_name | default("risk_analysis") }}

{% if expects_structured_output %}
{{ format_instructions }}
{% endif %}

---

**Important**: Return your analysis as structured data following the exact format specified above. Include all required fields and ensure proper data types for numerical values.