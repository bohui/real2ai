"""Schema validation and parsing utilities for structured output processing."""

from typing import Dict, List, Any, Optional, Union, Type, Tuple
from pydantic import BaseModel, ValidationError
import json
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from enum import Enum

from app.model.enums import AustralianState, ContractType, RiskLevel
from .extract_entities import ContractEntityExtraction
from .ocr_schemas import OCRExtractionResults, ExtractionConfidence, DocumentQuality


class ValidationLevel(str, Enum):
    STRICT = "strict"      # All required fields must be present and valid
    STANDARD = "standard"  # Required fields present, some flexibility on format
    LENIENT = "lenient"    # Accept partial data, focus on extractable information


class ValidationResult(BaseModel):
    """Result of schema validation."""
    
    is_valid: bool = Field(description="Overall validation status")
    validated_data: Optional[Dict[str, Any]] = Field(None, description="Successfully validated data")
    
    # Error details
    validation_errors: List[str] = Field(default_factory=list, description="Schema validation errors")
    data_quality_issues: List[str] = Field(default_factory=list, description="Data quality concerns")
    formatting_errors: List[str] = Field(default_factory=list, description="Format validation errors")
    
    # Completeness assessment
    missing_required_fields: List[str] = Field(default_factory=list, description="Required fields not provided")
    missing_optional_fields: List[str] = Field(default_factory=list, description="Optional fields not provided")
    
    # Data quality metrics
    confidence_score: float = Field(default=0.0, description="Overall confidence in extracted data (0-1)")
    completeness_score: float = Field(default=0.0, description="Completeness score (0-1)")
    consistency_score: float = Field(default=0.0, description="Internal consistency score (0-1)")
    
    # Recommendations
    manual_review_required: bool = Field(default=False, description="Requires manual review")
    priority_issues: List[str] = Field(default_factory=list, description="High priority issues requiring attention")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended next steps")


class SchemaValidator:
    """Advanced validator for output parser schemas."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self._australian_date_pattern = re.compile(r'^\d{1,2}\/\d{1,2}\/\d{4}$')
        self._iso_date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        self._currency_pattern = re.compile(r'^\$?[\d,]+\.?\d{0,2}$')
        self._postcode_pattern = re.compile(r'^\d{4}$')
        self._abn_pattern = re.compile(r'^\d{2}\s?\d{3}\s?\d{3}\s?\d{3}$')
        self._phone_pattern = re.compile(r'^(\+61|0)[2-9]\d{8}$')
        
    def validate_schema_response(
        self, 
        response: Union[str, Dict[str, Any]], 
        schema_class: Type[BaseModel],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate a response against a Pydantic schema with enhanced checks."""
        
        result = ValidationResult()
        
        try:
            # Parse JSON if needed
            if isinstance(response, str):
                response_data = self._parse_json_response(response)
                if response_data is None:
                    result.validation_errors.append("Invalid JSON format")
                    return result
            else:
                response_data = response
            
            # Basic schema validation
            try:
                validated_instance = schema_class.model_validate(response_data)
                result.validated_data = validated_instance.model_dump()
                result.is_valid = True
                
            except ValidationError as e:
                result.validation_errors = [str(error) for error in e.errors()]
                result.is_valid = False
                
                # Try to extract partial data in lenient mode
                if self.validation_level == ValidationLevel.LENIENT:
                    partial_data = self._extract_partial_data(response_data, schema_class)
                    if partial_data:
                        result.validated_data = partial_data
                        result.is_valid = True
                        result.data_quality_issues.append("Partial data extraction - some fields missing or invalid")
            
            # Enhanced validation checks
            if result.is_valid and result.validated_data:
                self._perform_enhanced_validation(result, schema_class, context)
                
        except Exception as e:
            result.validation_errors.append(f"Unexpected validation error: {str(e)}")
            result.is_valid = False
        
        # Calculate scores
        self._calculate_quality_scores(result, schema_class)
        
        # Generate recommendations
        self._generate_recommendations(result)
        
        return result
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON with error recovery."""
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON-like structure
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        return None
    
    def _extract_partial_data(self, data: Dict[str, Any], schema_class: Type[BaseModel]) -> Optional[Dict[str, Any]]:
        """Extract valid partial data from invalid response."""
        
        schema_info = schema_class.model_json_schema()
        properties = schema_info.get("properties", {})
        
        partial_data = {}
        
        for field_name, field_info in properties.items():
            if field_name in data:
                try:
                    # Basic type validation
                    field_value = data[field_name]
                    field_type = field_info.get("type", "string")
                    
                    if self._validate_field_type(field_value, field_type):
                        partial_data[field_name] = field_value
                        
                except Exception:
                    continue
        
        return partial_data if partial_data else None
    
    def _validate_field_type(self, value: Any, expected_type: str) -> bool:
        """Validate field type."""
        
        if expected_type == "string" and isinstance(value, str):
            return True
        elif expected_type == "integer" and isinstance(value, int):
            return True
        elif expected_type == "number" and isinstance(value, (int, float)):
            return True
        elif expected_type == "boolean" and isinstance(value, bool):
            return True
        elif expected_type == "array" and isinstance(value, list):
            return True
        elif expected_type == "object" and isinstance(value, dict):
            return True
        
        return False
    
    def _perform_enhanced_validation(
        self, 
        result: ValidationResult, 
        schema_class: Type[BaseModel],
        context: Optional[Dict[str, Any]]
    ):
        """Perform enhanced validation beyond basic schema compliance."""
        
        data = result.validated_data
        
        # Australian-specific validations
        self._validate_australian_data(result, data)
        
        # Date consistency checks
        self._validate_date_consistency(result, data)
        
        # Financial calculation checks
        self._validate_financial_consistency(result, data)
        
        # Contract-specific validations
        if schema_class.__name__ == "ContractEntityExtraction":
            self._validate_contract_data(result, data, context)
        elif "OCR" in schema_class.__name__:
            self._validate_ocr_data(result, data, context)
    
    def _validate_australian_data(self, result: ValidationResult, data: Dict[str, Any]):
        """Validate Australian-specific data formats."""
        
        # Postcode validation
        postcode_fields = ["postcode"]
        for field in postcode_fields:
            value = self._get_nested_value(data, field)
            if value and not self._postcode_pattern.match(str(value)):
                result.formatting_errors.append(f"Invalid Australian postcode format: {value}")
        
        # Phone number validation
        phone_fields = ["phone", "contact_phone", "business_phone"]
        for field in phone_fields:
            value = self._get_nested_value(data, field)
            if value and not self._phone_pattern.match(str(value)):
                result.formatting_errors.append(f"Invalid Australian phone number format: {value}")
        
        # ABN validation
        abn_fields = ["abn"]
        for field in abn_fields:
            value = self._get_nested_value(data, field)
            if value and not self._abn_pattern.match(str(value)):
                result.formatting_errors.append(f"Invalid ABN format: {value}")
    
    def _validate_date_consistency(self, result: ValidationResult, data: Dict[str, Any]):
        """Validate date consistency and chronological order."""
        
        dates = {}
        
        # Extract dates
        date_fields = [
            "contract_date", "settlement_date", "cooling_off_expiry", "possession_date",
            "finance_approval_date", "building_inspection_deadline", "pest_inspection_deadline"
        ]
        
        for field in date_fields:
            value = self._get_nested_value(data, field)
            if value:
                parsed_date = self._parse_date(value)
                if parsed_date:
                    dates[field] = parsed_date
                else:
                    result.formatting_errors.append(f"Invalid date format in {field}: {value}")
        
        # Check chronological consistency
        if "contract_date" in dates and "settlement_date" in dates:
            if dates["contract_date"] >= dates["settlement_date"]:
                result.data_quality_issues.append("Settlement date should be after contract date")
        
        if "contract_date" in dates and "cooling_off_expiry" in dates:
            if dates["cooling_off_expiry"] <= dates["contract_date"]:
                result.data_quality_issues.append("Cooling off expiry should be after contract date")
        
        # Check for realistic timeframes
        if "contract_date" in dates and "settlement_date" in dates:
            days_diff = (dates["settlement_date"] - dates["contract_date"]).days
            if days_diff < 14:
                result.data_quality_issues.append(f"Short settlement period ({days_diff} days) - verify if correct")
            elif days_diff > 365:
                result.data_quality_issues.append(f"Long settlement period ({days_diff} days) - verify if correct")
    
    def _validate_financial_consistency(self, result: ValidationResult, data: Dict[str, Any]):
        """Validate financial calculations and consistency."""
        
        # Extract financial amounts
        purchase_price = self._get_nested_value(data, "purchase_price")
        deposit_amount = self._get_nested_value(data, "deposit_amount") 
        balance_due = self._get_nested_value(data, "balance_due")
        
        if purchase_price and deposit_amount:
            try:
                purchase_decimal = Decimal(str(purchase_price))
                deposit_decimal = Decimal(str(deposit_amount))
                
                # Check deposit percentage
                deposit_percentage = (deposit_decimal / purchase_decimal) * 100
                
                if deposit_percentage < 5:
                    result.data_quality_issues.append(f"Low deposit percentage ({deposit_percentage:.1f}%) - verify if correct")
                elif deposit_percentage > 20:
                    result.data_quality_issues.append(f"High deposit percentage ({deposit_percentage:.1f}%) - verify if correct")
                
                # Check balance calculation if provided
                if balance_due:
                    balance_decimal = Decimal(str(balance_due))
                    expected_balance = purchase_decimal - deposit_decimal
                    
                    if abs(balance_decimal - expected_balance) > Decimal('1.00'):
                        result.data_quality_issues.append("Balance due calculation doesn't match purchase price minus deposit")
                        
            except (InvalidOperation, TypeError, ValueError):
                result.formatting_errors.append("Invalid financial amount format")
    
    def _validate_contract_data(self, result: ValidationResult, data: Dict[str, Any], context: Optional[Dict[str, Any]]):
        """Validate contract-specific data."""
        
        # Check for critical missing information
        critical_fields = ["property", "persons", "financial_terms", "important_dates"]
        
        for field in critical_fields:
            if not self._get_nested_value(data, field):
                result.missing_required_fields.append(field)
        
        # Risk assessment validation
        risk_assessment = self._get_nested_value(data, "risk_assessment")
        if risk_assessment:
            overall_risk = risk_assessment.get("overall_risk_level")
            high_risk_conditions = risk_assessment.get("high_risk_conditions", [])
            
            if overall_risk == "HIGH" and not high_risk_conditions:
                result.data_quality_issues.append("High overall risk level but no specific high-risk conditions identified")
    
    def _validate_ocr_data(self, result: ValidationResult, data: Dict[str, Any], context: Optional[Dict[str, Any]]):
        """Validate OCR-specific data."""
        
        # Check document quality indicators
        doc_metadata = data.get("document_metadata", {})
        overall_quality = doc_metadata.get("overall_quality")
        
        if overall_quality in ["POOR", "UNREADABLE"]:
            result.manual_review_required = True
            result.priority_issues.append(f"Document quality is {overall_quality} - manual review essential")
        
        # Check confidence levels
        validation_results = data.get("validation_results", {})
        extraction_quality = validation_results.get("overall_extraction_quality")
        
        if extraction_quality in ["LOW", "UNCERTAIN"]:
            result.manual_review_required = True
            result.priority_issues.append(f"Low extraction confidence ({extraction_quality}) - verify accuracy")
        
        # Check for missing critical fields in OCR
        financial_data = data.get("financial_data", {})
        if not any([financial_data.get(field) for field in ["purchase_price", "deposit_amount"]]):
            result.missing_required_fields.append("critical_financial_data")
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        
        parts = field_path.split('.')
        value = data
        
        try:
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                elif isinstance(value, list) and part.isdigit():
                    value = value[int(part)]
                else:
                    return None
        except (KeyError, IndexError, TypeError):
            return None
        
        return value
    
    def _parse_date(self, date_value: Any) -> Optional[date]:
        """Parse date from various formats."""
        
        if isinstance(date_value, date):
            return date_value
        
        if not isinstance(date_value, str):
            return None
        
        # Try Australian format (DD/MM/YYYY)
        if self._australian_date_pattern.match(date_value):
            try:
                day, month, year = date_value.split('/')
                return date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                pass
        
        # Try ISO format (YYYY-MM-DD)
        if self._iso_date_pattern.match(date_value):
            try:
                year, month, day = date_value.split('-')
                return date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _calculate_quality_scores(self, result: ValidationResult, schema_class: Type[BaseModel]):
        """Calculate quality scores for the validation result."""
        
        if not result.validated_data:
            return
        
        schema_info = schema_class.model_json_schema()
        properties = schema_info.get("properties", {})
        required = schema_info.get("required", [])
        
        # Completeness score
        total_fields = len(properties)
        present_fields = len([k for k in properties.keys() if self._get_nested_value(result.validated_data, k) is not None])
        result.completeness_score = present_fields / total_fields if total_fields > 0 else 0.0
        
        # Required field completeness
        required_present = len([k for k in required if self._get_nested_value(result.validated_data, k) is not None])
        required_completeness = required_present / len(required) if required else 1.0
        
        # Confidence score based on errors and completeness
        error_penalty = min(len(result.validation_errors) * 0.1, 0.5)
        quality_penalty = min(len(result.data_quality_issues) * 0.05, 0.3)
        
        result.confidence_score = max(0.0, required_completeness - error_penalty - quality_penalty)
        
        # Consistency score (inverse of formatting errors)
        format_penalty = min(len(result.formatting_errors) * 0.1, 0.8)
        result.consistency_score = max(0.0, 1.0 - format_penalty)
    
    def _generate_recommendations(self, result: ValidationResult):
        """Generate actionable recommendations based on validation results."""
        
        if result.validation_errors:
            result.recommended_actions.append("Fix schema validation errors before proceeding")
        
        if result.missing_required_fields:
            result.recommended_actions.append(f"Obtain missing required information: {', '.join(result.missing_required_fields)}")
        
        if result.formatting_errors:
            result.recommended_actions.append("Correct data formatting issues")
        
        if result.confidence_score < 0.7:
            result.manual_review_required = True
            result.recommended_actions.append("Manual review recommended due to low confidence score")
        
        if result.data_quality_issues:
            result.recommended_actions.append("Verify identified data quality concerns")
        
        # Priority-based recommendations
        if result.confidence_score < 0.5:
            result.priority_issues.append("Low confidence extraction - high priority for review")
        
        if len(result.validation_errors) > 5:
            result.priority_issues.append("Multiple validation errors - comprehensive review needed")


class ResponseParser:
    """Advanced parser for AI responses to extract structured data."""
    
    def __init__(self):
        self.validator = SchemaValidator()
    
    def parse_and_validate(
        self, 
        response: str, 
        schema_class: Type[BaseModel],
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[BaseModel], ValidationResult]:
        """Parse response and validate against schema."""
        
        self.validator.validation_level = validation_level
        
        # Validate the response
        validation_result = self.validator.validate_schema_response(response, schema_class, context)
        
        # Return validated instance if available
        validated_instance = None
        if validation_result.is_valid and validation_result.validated_data:
            try:
                validated_instance = schema_class.model_validate(validation_result.validated_data)
            except Exception:
                pass
        
        return validated_instance, validation_result
    
    def extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from various response formats."""
        
        return self.validator._parse_json_response(response)
    
    def batch_validate_responses(
        self,
        responses: List[str],
        schema_class: Type[BaseModel],
        validation_level: ValidationLevel = ValidationLevel.STANDARD
    ) -> List[Tuple[Optional[BaseModel], ValidationResult]]:
        """Validate multiple responses."""
        
        results = []
        
        for response in responses:
            instance, validation = self.parse_and_validate(response, schema_class, validation_level)
            results.append((instance, validation))
        
        return results


# Utility functions
def quick_validate(response: Union[str, Dict[str, Any]], schema_class: Type[BaseModel]) -> bool:
    """Quick validation check - returns True if valid."""
    
    validator = SchemaValidator()
    result = validator.validate_schema_response(response, schema_class)
    return result.is_valid


def validate_with_details(
    response: Union[str, Dict[str, Any]], 
    schema_class: Type[BaseModel]
) -> ValidationResult:
    """Detailed validation with comprehensive results."""
    
    validator = SchemaValidator()
    return validator.validate_schema_response(response, schema_class)


def parse_ai_response(
    response: str, 
    schema_class: Type[BaseModel]
) -> Tuple[Optional[BaseModel], ValidationResult]:
    """Parse and validate AI response."""
    
    parser = ResponseParser()
    return parser.parse_and_validate(response, schema_class)