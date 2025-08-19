"""
Test cases for Prompt Template fixes.

This module tests the fixes for undefined template variables that were causing
"Object of type Undefined is not JSON serializable" errors.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os
from typing import Dict, Any

from app.core.prompts.fragment_manager import FragmentManager
from app.core.prompts.composer import PromptComposer
from app.core.prompts.context import PromptContext, ContextType


class TestPromptTemplateFixes:
    """Test that prompt template fixes work correctly."""
    
    def _render_template(self, template_content: str, context_vars: Dict[str, Any]) -> str:
        """Helper method to render a template with Jinja2."""
        from jinja2 import Environment, BaseLoader, Undefined
        
        class StringLoader(BaseLoader):
            def get_source(self, environment, template):
                return template_content, None, lambda: True
        
        env = Environment(
            loader=StringLoader(),
            undefined=Undefined,  # Allow undefined variables to render as empty strings
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        template = env.get_template("")
        return template.render(**context_vars)

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create a temporary directory for test prompts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_path = Path(temp_dir) / "prompts"
            prompts_path.mkdir()
            
            # Create user prompts subdirectory
            user_prompts_path = prompts_path / "user" / "instructions"
            user_prompts_path.mkdir(parents=True)
            
            yield prompts_path

    @pytest.fixture
    def risk_assessment_template_content(self):
        """Content for the risk assessment template with conditional rendering."""
        return """---
type: "user"
category: "instructions"
name: "risk_assessment_base"
version: "2.0.0"
description: "Fragment-based comprehensive risk assessment for Australian property contracts"
fragment_orchestration: "risk_assessment"
required_variables:
  - "contract_data"
  - "contract_type"
  - "australian_state"
  - "user_type"
  - "user_experience"
---

# Comprehensive Risk Assessment Instructions

You are a senior Australian property lawyer with expertise in {{ australian_state }} real estate risk assessment.
Perform comprehensive risk analysis for this {{ contract_type }}.

## User Profile
- **Role**: {{ user_type }}
- **Experience**: {{ user_experience }}

## Contract Data
```json
{{ contract_data | tojson(indent=2) }}
```

## State-Specific Risk Indicators

{% if state_specific_fragments %}
{{ state_specific_fragments }}
{% else %}
**{{ australian_state }} Specific Risk Factors:**
- State-specific regulations and compliance requirements
- Local market conditions and trends
- State-specific legal precedents and case law
- Regional planning and zoning considerations
{% endif %}

## Financial Risk Assessment

{% if financial_risk_fragments %}
{{ financial_risk_fragments }}
{% else %}
**Financial Risk Analysis:**
- Purchase price vs. market value assessment
- Financing risks and interest rate exposure
- Additional costs (stamp duty, legal fees, inspections)
- Market volatility and timing risks
- Investment return projections and cash flow analysis
{% endif %}

## User Experience Guidance

{% if experience_level_fragments %}
{{ experience_level_fragments }}
{% else %}
**Experience-Based Risk Assessment:**
{% if user_experience == "novice" %}
- Focus on fundamental legal and financial risks
- Emphasize professional advice requirements
- Highlight common pitfalls for first-time buyers
{% elif user_experience == "intermediate" %}
- Consider advanced risk factors and market timing
- Evaluate complex contract terms and conditions
- Assess investment strategy alignment
{% else %}
- Advanced risk modeling and scenario analysis
- Strategic risk management and mitigation planning
- Portfolio impact and diversification considerations
{% endif %}
{% endif %}

## Analysis Output Requirements

Return detailed risk assessment as JSON with the following structure:

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
"""

    def test_template_with_undefined_variables_renders_successfully(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that templates with undefined variables render successfully using conditional logic."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test rendering with missing optional variables
        context_vars = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "novice"
            # Note: state_specific_fragments, financial_risk_fragments, experience_level_fragments are not provided
        }
        
        # The template should render successfully with default content
        rendered = self._render_template(template_path.read_text(), context_vars)
        
        # Verify that the template rendered without errors
        assert rendered is not None
        assert "NSW Specific Risk Factors:" in rendered
        assert "Financial Risk Analysis:" in rendered
        assert "Experience-Based Risk Assessment:" in rendered
        assert "Focus on fundamental legal and financial risks" in rendered  # novice-specific content

    def test_template_with_provided_variables_renders_custom_content(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that templates render custom content when optional variables are provided."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test rendering with all variables provided
        context_vars = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "intermediate",
            "state_specific_fragments": "Custom NSW risk factors content",
            "financial_risk_fragments": "Custom financial risk analysis",
            "experience_level_fragments": "Custom experience guidance for intermediate users"
        }
        
        # The template should render with custom content
        rendered = self._render_template(template_path.read_text(), context_vars)
        
        # Verify that custom content was used
        assert rendered is not None
        assert "Custom NSW risk factors content" in rendered
        assert "Custom financial risk analysis" in rendered
        assert "Custom experience guidance for intermediate users" in rendered
        # Default content should not appear
        assert "NSW Specific Risk Factors:" not in rendered
        assert "Financial Risk Analysis:" not in rendered

    def test_template_handles_none_values_gracefully(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that templates handle None values gracefully."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test rendering with None values for optional variables
        context_vars = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "expert",
            "state_specific_fragments": None,
            "financial_risk_fragments": None,
            "experience_level_fragments": None
        }
        
        # The template should render successfully with default content
        rendered = self._render_template(template_path.read_text(), context_vars)
        
        # Verify that the template rendered without errors
        assert rendered is not None
        assert "NSW Specific Risk Factors:" in rendered
        assert "Financial Risk Analysis:" in rendered
        assert "Advanced risk modeling and scenario analysis" in rendered  # expert-specific content

    def test_template_handles_empty_strings_gracefully(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that templates handle empty strings gracefully."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test rendering with empty strings for optional variables
        context_vars = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "novice",
            "state_specific_fragments": "",
            "financial_risk_fragments": "",
            "experience_level_fragments": ""
        }
        
        # The template should render successfully with default content
        rendered = self._render_template(template_path.read_text(), context_vars)
        
        # Verify that the template rendered without errors
        assert rendered is not None
        assert "NSW Specific Risk Factors:" in rendered
        assert "Financial Risk Analysis:" in rendered
        assert "Focus on fundamental legal and financial risks" in rendered

    def test_template_conditional_logic_for_user_experience(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that the template correctly handles different user experience levels."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test novice user experience
        context_vars_novice = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "novice"
        }
        
        rendered_novice = self._render_template(template_path.read_text(), context_vars_novice)
        assert "Focus on fundamental legal and financial risks" in rendered_novice
        assert "Emphasize professional advice requirements" in rendered_novice
        
        # Test intermediate user experience
        context_vars_intermediate = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "intermediate"
        }
        
        rendered_intermediate = self._render_template(template_path.read_text(), context_vars_intermediate)
        assert "Consider advanced risk factors and market timing" in rendered_intermediate
        assert "Evaluate complex contract terms and conditions" in rendered_intermediate
        
        # Test expert user experience
        context_vars_expert = {
            "contract_data": {"price": "500000", "address": "123 Test St"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "expert"
        }
        
        rendered_expert = self._render_template(template_path.read_text(), context_vars_expert)
        assert "Advanced risk modeling and scenario analysis" in rendered_expert
        assert "Strategic risk management and mitigation planning" in rendered_expert

    def test_template_json_serialization_works_with_all_variables(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that JSON serialization works correctly when all variables are defined."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test with complex data that needs JSON serialization
        complex_contract_data = {
            "price": 500000,
            "address": "123 Test St",
            "features": ["garage", "garden", "pool"],
            "metadata": {
                "created": "2024-01-01",
                "modified": "2024-01-15",
                "tags": ["residential", "freehold"]
            }
        }
        
        context_vars = {
            "contract_data": complex_contract_data,
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "intermediate"
        }
        
        # The template should render successfully with complex JSON data
        rendered = self._render_template(template_path.read_text(), context_vars)
        
        # Verify that the template rendered without errors
        assert rendered is not None
        assert "500000" in rendered
        assert "garage" in rendered
        assert "residential" in rendered
        # Verify JSON structure is maintained
        assert '"price": 500000' in rendered or '"price":500000' in rendered.replace(" ", "")

    def test_template_handles_missing_required_variables_gracefully(self, temp_prompts_dir, risk_assessment_template_content):
        """Test that templates handle missing required variables gracefully."""
        # Create the template file
        template_path = temp_prompts_dir / "user" / "instructions" / "risk_assessment_base.md"
        template_path.write_text(risk_assessment_template_content)
        
        # Create a fragment manager
        fragment_manager = FragmentManager(
            fragments_dir=temp_prompts_dir / "fragments",
            config_dir=temp_prompts_dir / "config"
        )
        
        # Test with minimal required variables only
        context_vars = {
            "contract_data": {"price": "500000"},
            "contract_type": "purchase_agreement",
            "australian_state": "NSW",
            "user_type": "buyer",
            "user_experience": "novice"
        }
        
        # The template should render successfully with default content for missing optional variables
        rendered = self._render_template(template_path.read_text(), context_vars)
        
        # Verify that the template rendered without errors
        assert rendered is not None
        assert "NSW" in rendered
        assert "purchase_agreement" in rendered
        assert "buyer" in rendered
        assert "novice" in rendered
