"""Integration layer connecting output parser schemas with fragment-based prompt system."""

from typing import Dict, Type, Optional, List, Any, Union
from pydantic import BaseModel
import json
from datetime import datetime
from pathlib import Path

from app.model.enums import AustralianState, ContractType, RiskLevel
from app.core.prompts.composer import PromptComposer
from app.core.prompts.fragment_manager import FragmentManager

# Import schemas
from .extract_entities import (
    ContractEntityExtraction, 
    NSWCriticalValidation, 
    VICCriticalValidation, 
    QLDCriticalValidation,
    WACriticalValidation,
    SACriticalValidation,
    CONTRACT_EXTRACTION_PROMPT_TEMPLATE,
    PROPERTY_TYPE_SCHEMAS,
    STATE_VALIDATION_SCHEMAS
)
from .ocr_schemas import (
    OCRExtractionResults,
    PurchaseAgreementOCR,
    AuctionContractOCR, 
    OffPlanContractOCR,
    NSWOCRSpecifics,
    VICOCRSpecifics,
    QLDOCRSpecifics,
    OCR_EXTRACTION_PROMPT_TEMPLATE,
    CONTRACT_OCR_SCHEMA_MAPPING,
    STATE_OCR_SPECIFICS_MAPPING,
    OCR_QUALITY_SETTINGS
)


class SchemaType(str):
    CONTRACT_ANALYSIS = "contract_analysis"
    OCR_EXTRACTION = "ocr_extraction"
    VALIDATION = "validation"
    RISK_ASSESSMENT = "risk_assessment"


class SchemaIntegrationManager:
    """Manages integration between schemas and fragment-based prompts."""
    
    def __init__(self, composer: PromptComposer, fragment_manager: FragmentManager):
        self.composer = composer
        self.fragment_manager = fragment_manager
        self._schema_cache: Dict[str, Type[BaseModel]] = {}
        
    def get_schema_for_operation(
        self,
        operation_type: SchemaType,
        contract_type: ContractType,
        australian_state: AustralianState,
        quality_level: str = "standard",
        **kwargs
    ) -> Type[BaseModel]:
        """Get the appropriate schema for the given operation and context."""
        
        cache_key = f"{operation_type}_{contract_type.value}_{australian_state.value}_{quality_level}"
        
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]
            
        schema_class = self._determine_schema_class(
            operation_type, contract_type, australian_state, quality_level, **kwargs
        )
        
        self._schema_cache[cache_key] = schema_class
        return schema_class
    
    def _determine_schema_class(
        self,
        operation_type: SchemaType,
        contract_type: ContractType,
        australian_state: AustralianState,
        quality_level: str,
        **kwargs
    ) -> Type[BaseModel]:
        """Determine the specific schema class to use."""
        
        if operation_type == SchemaType.CONTRACT_ANALYSIS:
            return ContractEntityExtraction
            
        elif operation_type == SchemaType.OCR_EXTRACTION:
            # Get contract-specific OCR schema
            base_schema = CONTRACT_OCR_SCHEMA_MAPPING.get(contract_type, OCRExtractionResults)
            
            # For states with specific requirements, we might need to modify the schema
            if australian_state in STATE_OCR_SPECIFICS_MAPPING:
                # For now, return the base schema - in future we could dynamically create
                # schemas with state-specific fields mixed in
                return base_schema
            
            return base_schema
            
        elif operation_type == SchemaType.VALIDATION:
            return STATE_VALIDATION_SCHEMAS.get(australian_state.value, NSWCriticalValidation)
            
        else:
            return ContractEntityExtraction  # Default fallback
    
    def compose_prompt_with_schema(
        self,
        composition_name: str,
        schema_type: SchemaType,
        contract_type: ContractType,
        australian_state: AustralianState,
        context_variables: Optional[Dict[str, Any]] = None,
        quality_level: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """Compose a prompt with the appropriate schema and return both."""
        
        # Get the appropriate schema
        schema_class = self.get_schema_for_operation(
            schema_type, contract_type, australian_state, quality_level, **kwargs
        )
        
        # Prepare context variables with schema information
        context_vars = context_variables or {}
        context_vars.update({
            "contract_type": contract_type.value,
            "australian_state": australian_state.value,
            "state": australian_state.value,  # Alias for templates
            "quality_level": quality_level,
            "schema_name": schema_class.__name__,
            **kwargs
        })
        
        # Compose the prompt using fragment system
        prompt_result = self.composer.compose(composition_name, context_vars)
        
        # Add schema-specific instructions if needed
        enhanced_prompt = self._enhance_prompt_with_schema_instructions(
            prompt_result, schema_class, schema_type, quality_level
        )
        
        return {
            "prompt": enhanced_prompt,
            "schema": schema_class,
            "schema_json": schema_class.model_json_schema(),
            "context": context_vars,
            "composition_name": composition_name
        }
    
    def _enhance_prompt_with_schema_instructions(
        self,
        prompt_result: Dict[str, Any],
        schema_class: Type[BaseModel],
        schema_type: SchemaType,
        quality_level: str
    ) -> Dict[str, Any]:
        """Enhance the composed prompt with schema-specific instructions."""
        
        # Add schema instructions based on type
        schema_instructions = self._get_schema_instructions(schema_class, schema_type, quality_level)
        
        if schema_instructions:
            # Append to system prompt if present, otherwise to user prompt
            if "system_prompt" in prompt_result:
                prompt_result["system_prompt"] += f"\n\n{schema_instructions}"
            elif "user_prompt" in prompt_result:
                prompt_result["user_prompt"] += f"\n\n{schema_instructions}"
                
        # Add JSON schema information
        prompt_result["output_schema"] = {
            "description": f"Return response in the following JSON schema format",
            "schema": schema_class.model_json_schema(),
            "example_usage": self._get_schema_example(schema_class)
        }
        
        return prompt_result
    
    def _get_schema_instructions(
        self, 
        schema_class: Type[BaseModel], 
        schema_type: SchemaType, 
        quality_level: str
    ) -> str:
        """Get specific instructions for the schema type."""
        
        base_instruction = f"""
**OUTPUT FORMAT REQUIREMENTS:**

You must return your response as valid JSON that conforms to the {schema_class.__name__} schema.

**CRITICAL REQUIREMENTS:**
- All fields marked as required must be populated
- Use appropriate data types (strings, numbers, dates, booleans, arrays)
- For dates, use YYYY-MM-DD format unless otherwise specified
- For monetary amounts, use decimal numbers (not strings)
- For enums, use exact enum values as defined in schema
- Include confidence scores and quality indicators where specified
"""
        
        if schema_type == SchemaType.OCR_EXTRACTION:
            ocr_instructions = f"""
**OCR-SPECIFIC REQUIREMENTS:**
- Quality Level: {quality_level}
- Flag uncertain extractions with appropriate confidence levels
- Include bounding box information where available
- Note any manual review requirements
- Provide raw OCR text alongside processed values
- Validate extracted financial calculations
- Cross-check date consistency and chronological order
"""
            return base_instruction + ocr_instructions
            
        elif schema_type == SchemaType.CONTRACT_ANALYSIS:
            analysis_instructions = """
**CONTRACT ANALYSIS REQUIREMENTS:**
- Focus on non-standard clauses and modifications to template
- Assess risk levels for each identified condition
- Prioritize additional conditions and special clauses
- Identify missing mandatory documents or information
- Flag any red-flag terms or unusual arrangements
- Provide specific recommendations for each risk identified
"""
            return base_instruction + analysis_instructions
            
        elif schema_type == SchemaType.VALIDATION:
            validation_instructions = """
**VALIDATION REQUIREMENTS:**
- Verify all mandatory state-specific requirements
- Check compliance with relevant legislation
- Identify any missing critical documents
- Flag non-compliance issues with specific remediation steps
- Assess overall contract completeness and validity
"""
            return base_instruction + validation_instructions
            
        return base_instruction
    
    def _get_schema_example(self, schema_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate a basic example of the schema structure."""
        
        try:
            # Create an example instance with minimal required fields
            if hasattr(schema_class, 'model_validate'):
                # For Pydantic v2
                example_data = self._generate_example_data(schema_class)
                example = schema_class.model_validate(example_data)
                return example.model_dump(exclude_none=True)
            else:
                # Fallback for older versions
                return {"example": "See schema definition for structure"}
        except Exception:
            return {"note": "Refer to schema definition for exact structure requirements"}
    
    def _generate_example_data(self, schema_class: Type[BaseModel]) -> Dict[str, Any]:
        """Generate minimal example data for a schema."""
        
        schema_info = schema_class.model_json_schema()
        properties = schema_info.get("properties", {})
        required = schema_info.get("required", [])
        
        example_data = {}
        
        for field_name in required:
            field_info = properties.get(field_name, {})
            field_type = field_info.get("type", "string")
            
            if field_type == "string":
                if "enum" in field_info:
                    example_data[field_name] = field_info["enum"][0]
                else:
                    example_data[field_name] = f"example_{field_name}"
            elif field_type == "integer":
                example_data[field_name] = 1
            elif field_type == "number":
                example_data[field_name] = 1.0
            elif field_type == "boolean":
                example_data[field_name] = True
            elif field_type == "array":
                example_data[field_name] = []
            elif field_type == "object":
                example_data[field_name] = {}
                
        return example_data
    
    def validate_response(
        self, 
        response: Union[str, Dict[str, Any]], 
        schema_class: Type[BaseModel]
    ) -> Dict[str, Any]:
        """Validate a response against the expected schema."""
        
        try:
            # Parse JSON if needed
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            # Validate against schema
            validated_instance = schema_class.model_validate(response_data)
            
            return {
                "valid": True,
                "validated_data": validated_instance.model_dump(),
                "errors": []
            }
            
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "validated_data": None,
                "errors": [f"Invalid JSON: {str(e)}"]
            }
        except Exception as e:
            return {
                "valid": False,
                "validated_data": None,
                "errors": [f"Validation error: {str(e)}"]
            }
    
    def get_contract_analysis_workflow(
        self,
        contract_type: ContractType,
        australian_state: AustralianState,
        analysis_depth: str = "comprehensive"
    ) -> List[Dict[str, Any]]:
        """Get a complete workflow for contract analysis with appropriate schemas."""
        
        workflow_steps = []
        
        # Step 1: OCR Extraction (if needed)
        ocr_step = self.compose_prompt_with_schema(
            composition_name="ocr_extraction_specialized",
            schema_type=SchemaType.OCR_EXTRACTION,
            contract_type=contract_type,
            australian_state=australian_state,
            quality_level="high",
            analysis_depth=analysis_depth
        )
        workflow_steps.append({
            "step": "ocr_extraction",
            "description": "Extract structured data from document",
            **ocr_step
        })
        
        # Step 2: Contract Analysis
        analysis_step = self.compose_prompt_with_schema(
            composition_name="contract_analysis_complete",
            schema_type=SchemaType.CONTRACT_ANALYSIS,
            contract_type=contract_type,
            australian_state=australian_state,
            analysis_depth=analysis_depth
        )
        workflow_steps.append({
            "step": "contract_analysis",
            "description": "Analyze contract terms and identify risks",
            **analysis_step
        })
        
        # Step 3: State-specific Validation
        validation_step = self.compose_prompt_with_schema(
            composition_name="state_specific_analysis",
            schema_type=SchemaType.VALIDATION,
            contract_type=contract_type,
            australian_state=australian_state
        )
        workflow_steps.append({
            "step": "validation",
            "description": "Validate state-specific compliance requirements",
            **validation_step
        })
        
        # Step 4: Risk Assessment
        risk_step = self.compose_prompt_with_schema(
            composition_name="risk_assessment_comprehensive",
            schema_type=SchemaType.CONTRACT_ANALYSIS,
            contract_type=contract_type,
            australian_state=australian_state,
            focus="risk_assessment"
        )
        workflow_steps.append({
            "step": "risk_assessment",
            "description": "Comprehensive risk assessment and recommendations",
            **risk_step
        })
        
        return workflow_steps


# Utility functions for common operations
def create_schema_manager(prompts_base_path: str = None) -> SchemaIntegrationManager:
    """Create a configured schema integration manager."""
    
    if prompts_base_path is None:
        prompts_base_path = Path(__file__).parent.parent
    
    composer = PromptComposer(base_path=prompts_base_path)
    fragment_manager = FragmentManager(base_path=prompts_base_path)
    
    return SchemaIntegrationManager(composer, fragment_manager)


def get_contract_analysis_prompt_with_schema(
    contract_type: ContractType,
    australian_state: AustralianState,
    quality_level: str = "standard"
) -> Dict[str, Any]:
    """Quick helper to get contract analysis prompt with appropriate schema."""
    
    manager = create_schema_manager()
    
    return manager.compose_prompt_with_schema(
        composition_name="contract_analysis_complete",
        schema_type=SchemaType.CONTRACT_ANALYSIS,
        contract_type=contract_type,
        australian_state=australian_state,
        quality_level=quality_level
    )


def get_ocr_extraction_prompt_with_schema(
    contract_type: ContractType,
    australian_state: AustralianState,
    quality_level: str = "high"
) -> Dict[str, Any]:
    """Quick helper to get OCR extraction prompt with appropriate schema."""
    
    manager = create_schema_manager()
    
    return manager.compose_prompt_with_schema(
        composition_name="ocr_extraction_specialized",
        schema_type=SchemaType.OCR_EXTRACTION,
        contract_type=contract_type,
        australian_state=australian_state,
        quality_level=quality_level
    )


# Configuration for different analysis scenarios
ANALYSIS_SCENARIOS = {
    "quick_scan": {
        "ocr_quality": "standard",
        "analysis_depth": "basic",
        "validation_level": "mandatory_only",
        "focus_areas": ["financial_terms", "critical_dates", "standard_conditions"]
    },
    "comprehensive": {
        "ocr_quality": "high",
        "analysis_depth": "comprehensive",
        "validation_level": "full_compliance",
        "focus_areas": ["all"]
    },
    "risk_focused": {
        "ocr_quality": "high", 
        "analysis_depth": "risk_assessment",
        "validation_level": "risk_factors",
        "focus_areas": ["special_clauses", "additional_conditions", "planning_certificates", "environmental_risks"]
    },
    "settlement_prep": {
        "ocr_quality": "high",
        "analysis_depth": "settlement_focus",
        "validation_level": "settlement_requirements",
        "focus_areas": ["financial_terms", "critical_dates", "conditions", "required_documents"]
    }
}


def get_scenario_workflow(
    scenario: str,
    contract_type: ContractType,
    australian_state: AustralianState
) -> List[Dict[str, Any]]:
    """Get a workflow tailored to a specific analysis scenario."""
    
    if scenario not in ANALYSIS_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    
    config = ANALYSIS_SCENARIOS[scenario]
    manager = create_schema_manager()
    
    return manager.get_contract_analysis_workflow(
        contract_type=contract_type,
        australian_state=australian_state,
        analysis_depth=config["analysis_depth"]
    )