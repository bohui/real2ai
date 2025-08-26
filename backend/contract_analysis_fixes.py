#!/usr/bin/env python3
"""
Contract Analysis System Fixes - Orchestrated Implementation

This script implements the solutions identified in the troubleshooting analysis:
1. Replace manual JSON parsing with LangChain OutputParser + format_instructions
2. Fix Pydantic validation issues with australian_state field defaults
3. Add OCR fallback mechanisms for Tesseract failures
4. Update prompt templates with missing variables
"""

import re
import logging
from typing import Dict, Any
from pathlib import Path

# LangChain OutputParser integration
from app.core.prompts.parsers import create_parser, ParsingResult
from app.prompts.schema.workflow_outputs import (
    RiskAnalysisOutput,
    RecommendationsOutput,
    ContractTermsOutput,
    ContractTermsValidationOutput,
)

logger = logging.getLogger(__name__)


class StructuredResponseGenerator:
    """
    Enhanced response generation with LangChain OutputParser integration
    Replaces manual JSON parsing with structured output parsing
    """

    def __init__(self, pydantic_model_class):
        """Initialize with Pydantic model for structured parsing"""
        self.parser = create_parser(
            pydantic_model_class,
            strict_mode=False,  # Allow partial parsing for error recovery
            retry_on_failure=True,
            max_retries=3,
        )

    def get_format_instructions(self) -> str:
        """Get format instructions to append to prompts"""
        return self.parser.get_format_instructions()

    def build_structured_prompt(self, base_prompt: str) -> str:
        """Build complete prompt with format instructions"""
        format_instructions = self.get_format_instructions()

        return f"""
{base_prompt}

{format_instructions}
"""

    def parse_response(self, llm_response: str) -> ParsingResult:
        """Parse LLM response using structured parser"""
        return self.parser.parse_with_retry(llm_response)


class ContractAnalysisEnhancedWorkflow:
    """
    Enhanced workflow methods that replace manual JSON parsing
    with structured LangChain OutputParser integration
    """

    def __init__(self):
        # Initialize parsers for different response types
        self.risk_generator = StructuredResponseGenerator(RiskAnalysisOutput)
        self.recommendations_generator = StructuredResponseGenerator(
            RecommendationsOutput
        )
        self.contract_terms_generator = StructuredResponseGenerator(ContractTermsOutput)
        self.validation_generator = StructuredResponseGenerator(
            ContractTermsValidationOutput
        )

    async def enhanced_risk_assessment(
        self, base_prompt: str, llm_client, **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced risk assessment with structured output parsing
        Replaces manual JSON parsing in assess_contract_risks
        """
        # Build structured prompt with format instructions
        structured_prompt = self.risk_generator.build_structured_prompt(base_prompt)

        try:
            # Generate response using LLM
            llm_response = await self._generate_llm_response(
                llm_client, structured_prompt, **kwargs
            )

            # Parse response with structured parser
            result = self.risk_generator.parse_response(llm_response)

            if result.success:
                logger.info(
                    f"Risk assessment parsed successfully (confidence: {result.confidence_score:.2f})"
                )
                return self._convert_to_legacy_format(result.parsed_data)
            else:
                logger.warning(
                    f"Risk assessment parsing failed: {result.parsing_errors + result.validation_errors}"
                )
                return self._create_fallback_risk_assessment()

        except Exception as e:
            logger.error(f"Risk assessment failed: {str(e)}")
            return self._create_fallback_risk_assessment()

    async def enhanced_recommendations_generation(
        self, base_prompt: str, llm_client, **kwargs
    ) -> list:
        """
        Enhanced recommendations generation with structured output parsing
        Replaces manual JSON parsing in generate_recommendations
        """
        # Build structured prompt
        structured_prompt = self.recommendations_generator.build_structured_prompt(
            base_prompt
        )

        try:
            llm_response = await self._generate_llm_response(
                llm_client, structured_prompt, **kwargs
            )

            result = self.recommendations_generator.parse_response(llm_response)

            if result.success:
                recommendations = (
                    result.parsed_data.recommendations
                    if hasattr(result.parsed_data, "recommendations")
                    else []
                )
                logger.info(
                    f"Generated {len(recommendations)} recommendations successfully"
                )
                return [
                    rec.dict() if hasattr(rec, "dict") else rec
                    for rec in recommendations
                ]
            else:
                logger.warning(
                    f"Recommendations parsing failed: {result.parsing_errors + result.validation_errors}"
                )
                return self._create_fallback_recommendations()

        except Exception as e:
            logger.error(f"Recommendations generation failed: {str(e)}")
            return self._create_fallback_recommendations()

    async def enhanced_contract_terms_extraction(
        self,
        base_prompt: str,
        llm_client,
        australian_state: str,  # Ensure australian_state is always provided
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Enhanced contract terms extraction with australian_state default handling
        Fixes Pydantic validation issues
        """
        # Add australian_state to prompt context if not already present
        enhanced_prompt = f"""
{base_prompt}

Important: Ensure the response includes the australian_state field with value: "{australian_state}"
"""

        structured_prompt = self.contract_terms_generator.build_structured_prompt(
            enhanced_prompt
        )

        try:
            llm_response = await self._generate_llm_response(
                llm_client, structured_prompt, **kwargs
            )

            result = self.contract_terms_generator.parse_response(llm_response)

            if result.success:
                # Ensure australian_state is set in the response
                terms_data = (
                    result.parsed_data.dict()
                    if hasattr(result.parsed_data, "dict")
                    else result.parsed_data
                )
                terms_data["australian_state"] = australian_state  # Force set the state

                logger.info(
                    "Contract terms extraction successful with australian_state validation"
                )
                return terms_data
            else:
                logger.warning(
                    f"Contract terms parsing failed: {result.parsing_errors + result.validation_errors}"
                )
                return self._create_fallback_contract_terms(australian_state)

        except Exception as e:
            logger.error(f"Contract terms extraction failed: {str(e)}")
            return self._create_fallback_contract_terms(australian_state)

    async def enhanced_compliance_analysis(
        self, base_prompt: str, llm_client, australian_state: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced compliance analysis with state validation
        """
        structured_prompt = self.validation_generator.build_structured_prompt(
            base_prompt
        )

        try:
            llm_response = await self._generate_llm_response(
                llm_client, structured_prompt, **kwargs
            )

            result = self.validation_generator.parse_response(llm_response)

            if result.success:
                compliance_data = (
                    result.parsed_data.dict()
                    if hasattr(result.parsed_data, "dict")
                    else result.parsed_data
                )
                compliance_data["australian_state"] = australian_state

                logger.info("Compliance analysis successful")
                return compliance_data
            else:
                logger.warning(
                    f"Compliance analysis parsing failed: {result.parsing_errors + result.validation_errors}"
                )
                return self._create_fallback_compliance(australian_state)

        except Exception as e:
            logger.error(f"Compliance analysis failed: {str(e)}")
            return self._create_fallback_compliance(australian_state)

    # Helper methods for fallback scenarios
    def _create_fallback_risk_assessment(self) -> Dict[str, Any]:
        """Create fallback risk assessment when parsing fails"""
        return {
            "overall_risk_score": 5,  # Medium risk as default
            "risk_factors": [
                {
                    "factor": "Parsing Error",
                    "severity": "medium",
                    "description": "Unable to perform complete risk analysis due to parsing issues",
                    "mitigation_suggestions": [
                        "Manual review required",
                        "Re-analyze with updated system",
                    ],
                }
            ],
            "critical_issues": [],
            "recommendations": ["Manual review of contract recommended"],
            "confidence_score": 0.3,
        }

    def _create_fallback_recommendations(self) -> list:
        """Create fallback recommendations when parsing fails"""
        return [
            {
                "category": "system",
                "priority": "high",
                "title": "Manual Review Required",
                "description": "Automated analysis was incomplete. Manual legal review recommended.",
                "action_items": [
                    "Contact legal professional",
                    "Review contract manually",
                ],
                "timeline": "immediate",
                "cost_impact": "medium",
            }
        ]

    def _create_fallback_contract_terms(self, australian_state: str) -> Dict[str, Any]:
        """Create fallback contract terms with required australian_state"""
        return {
            "australian_state": australian_state,
            "property_information": {
                "address": "Unable to extract",
                "legal_description": "Manual extraction required",
            },
            "financial_terms": {
                "purchase_price": 0,
                "deposit": 0,
                "settlement_date": None,
            },
            "parties_information": {
                "vendor": "Unable to extract",
                "purchaser": "Unable to extract",
            },
            "conditions": [],
            "special_conditions": [],
            "parsing_notes": "Automated extraction failed - manual review required",
        }

    def _create_fallback_compliance(self, australian_state: str) -> Dict[str, Any]:
        """Create fallback compliance analysis"""
        return {
            "australian_state": australian_state,
            "overall_compliance_score": 5,
            "state_compliance": False,
            "compliance_issues": [
                {
                    "area": "analysis",
                    "issue": "Unable to complete automated compliance analysis",
                    "severity": "medium",
                    "recommendation": "Manual legal review required",
                }
            ],
            "mandatory_disclosures": [],
            "cooling_off_period": {"applicable": None, "period_days": None},
        }

    def _convert_to_legacy_format(self, structured_data) -> Dict[str, Any]:
        """Convert structured Pydantic model to legacy dict format"""
        if hasattr(structured_data, "dict"):
            return structured_data.dict()
        elif hasattr(structured_data, "__dict__"):
            return structured_data.__dict__
        else:
            return structured_data

    async def _generate_llm_response(self, client, prompt: str, **kwargs) -> str:
        """Generate LLM response - implementation depends on client type"""
        # This would be implemented based on the actual client interface
        # For now, return a placeholder that shows the structure
        return await client.generate_content(prompt, **kwargs)


class OCRFallbackHandler:
    """
    Enhanced OCR processing with fallback mechanisms
    Addresses Tesseract OCR failures from the logs
    """

    @staticmethod
    def process_pdf_with_fallbacks(pdf_path: Path) -> tuple[str, list]:
        """
        Process PDF with multiple OCR fallback strategies
        Returns: (extracted_text, processing_notes)
        """
        extraction_notes = []

        # Strategy 1: Try Tesseract OCR
        try:
            text = OCRFallbackHandler._tesseract_ocr(pdf_path)
            if text and len(text.strip()) > 100:  # Reasonable content threshold
                extraction_notes.append("Successfully extracted using Tesseract OCR")
                return text, extraction_notes
        except Exception as e:
            extraction_notes.append(f"Tesseract OCR failed: {str(e)}")

        # Strategy 2: Try alternative OCR engine (e.g., EasyOCR)
        try:
            text = OCRFallbackHandler._alternative_ocr(pdf_path)
            if text and len(text.strip()) > 100:
                extraction_notes.append(
                    "Successfully extracted using alternative OCR engine"
                )
                return text, extraction_notes
        except Exception as e:
            extraction_notes.append(f"Alternative OCR failed: {str(e)}")

        # Strategy 3: PDF text extraction without OCR
        try:
            text = OCRFallbackHandler._direct_pdf_text_extraction(pdf_path)
            if text and len(text.strip()) > 50:
                extraction_notes.append(
                    "Successfully extracted direct PDF text (no OCR)"
                )
                return text, extraction_notes
        except Exception as e:
            extraction_notes.append(f"Direct PDF extraction failed: {str(e)}")

        # Strategy 4: Page-by-page processing with error recovery
        try:
            text = OCRFallbackHandler._page_by_page_extraction(pdf_path)
            extraction_notes.append("Partial extraction using page-by-page fallback")
            return text, extraction_notes
        except Exception as e:
            extraction_notes.append(f"Page-by-page extraction failed: {str(e)}")

        # Final fallback
        extraction_notes.append(
            "All OCR strategies failed - manual processing required"
        )
        return "OCR_EXTRACTION_FAILED", extraction_notes

    @staticmethod
    def _tesseract_ocr(pdf_path: Path) -> str:
        """Original Tesseract OCR with error handling for quotation issues"""
        import pytesseract
        from pdf2image import convert_from_path

        pages = convert_from_path(pdf_path)
        full_text = []

        for page_num, page in enumerate(pages, 1):
            try:
                # Configure Tesseract to handle quotation issues
                custom_config = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"
                text = pytesseract.image_to_string(page, config=custom_config)

                # Clean up malformed quotations that cause parsing errors
                text = re.sub(
                    r"[\u201c\u201d\u2018\u2019]", '"', text
                )  # Normalize quotes
                text = re.sub(r"[^\x00-\x7F]+", " ", text)  # Remove non-ASCII chars

                full_text.append(text)

            except Exception as e:
                logger.warning(f"Tesseract failed on page {page_num}: {str(e)}")
                full_text.append(f"[PAGE {page_num} EXTRACTION FAILED]")

        return "\n\n".join(full_text)

    @staticmethod
    def _alternative_ocr(pdf_path: Path) -> str:
        """Alternative OCR using EasyOCR or similar"""
        try:
            import easyocr
            from pdf2image import convert_from_path

            reader = easyocr.Reader(["en"])  # English language
            pages = convert_from_path(pdf_path)
            full_text = []

            for page in pages:
                result = reader.readtext(page, paragraph=True)
                page_text = " ".join([detection[1] for detection in result])
                full_text.append(page_text)

            return "\n\n".join(full_text)

        except ImportError:
            logger.warning("EasyOCR not available, trying other methods...")
            raise Exception("Alternative OCR engine not available")

    @staticmethod
    def _direct_pdf_text_extraction(pdf_path: Path) -> str:
        """Direct text extraction from PDF without OCR"""
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        full_text = []

        for page in doc:
            text = page.get_text()
            if text.strip():
                full_text.append(text)

        doc.close()
        return "\n\n".join(full_text)

    @staticmethod
    def _page_by_page_extraction(pdf_path: Path) -> str:
        """Page-by-page extraction with individual error handling"""
        import fitz
        from pdf2image import convert_from_path
        import pytesseract

        # Try direct text extraction first
        doc = fitz.open(pdf_path)
        extracted_pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Try direct text extraction
            direct_text = page.get_text()
            if direct_text and len(direct_text.strip()) > 50:
                extracted_pages.append(direct_text)
                continue

            # Fall back to OCR for this page
            try:
                page_images = convert_from_path(
                    pdf_path, first_page=page_num + 1, last_page=page_num + 1
                )
                if page_images:
                    ocr_text = pytesseract.image_to_string(page_images[0])
                    # Clean OCR text
                    ocr_text = re.sub(r"[\u201c\u201d\u2018\u2019]", '"', ocr_text)
                    extracted_pages.append(
                        ocr_text if ocr_text.strip() else f"[PAGE {page_num+1} NO TEXT]"
                    )
                else:
                    extracted_pages.append(f"[PAGE {page_num+1} PROCESSING FAILED]")
            except Exception:
                extracted_pages.append(f"[PAGE {page_num+1} OCR FAILED]")

        doc.close()
        return "\n\n".join(extracted_pages)


# Integration helper functions
def integrate_structured_parsing_into_workflow():
    """
    Integration guide for updating the existing ContractAnalysisWorkflow
    """

    integration_notes = """
    # Integration Steps for ContractAnalysisWorkflow
    
    1. Replace all manual json.loads() calls with structured parsing:
    
    OLD CODE:
    ```python
    try:
        extraction_result = json.loads(llm_response)
        # ... manual validation
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {e}")
        # ... fallback
    ```
    
    NEW CODE:
    ```python
    generator = StructuredResponseGenerator(ContractTermsOutput)
    structured_prompt = generator.build_structured_prompt(base_prompt)
    llm_response = await self._generate_content_with_fallback(structured_prompt)
    result = generator.parse_response(llm_response)
    
    if result.success:
        return result.parsed_data.dict()
    else:
        logger.warning(f"Structured parsing failed: {result.parsing_errors}")
        return self._create_fallback_response()
    ```
    
    2. Update all LLM service calls to include format_instructions:
    
    OLD PROMPT:
    "Analyze the contract and return JSON with the following structure..."
    
    NEW PROMPT:
    ```python
    base_prompt = "Analyze the contract based on the requirements..."
    generator = StructuredResponseGenerator(YourPydanticModel)
    full_prompt = generator.build_structured_prompt(base_prompt)
    # full_prompt now includes detailed format instructions
    ```
    
    3. Add australian_state defaults in all Pydantic models:
    ```python
    class ContractTerms(BaseModel):
        australian_state: str = "NSW"  # Default value
        # ... other fields
        
        @field_validator('australian_state', mode='before')
        def set_default_state(cls, v):
            return v or "NSW"  # Ensure never None/empty
    ```
    
    4. Update OCR processing with fallbacks:
    ```python
    # Replace direct Tesseract calls
    text, notes = OCRFallbackHandler.process_pdf_with_fallbacks(pdf_path)
    state["processing_notes"] = notes
    if text == "OCR_EXTRACTION_FAILED":
        # Handle extraction failure appropriately
    ```
    """

    return integration_notes


if __name__ == "__main__":
    print("Contract Analysis System Fixes")
    print("=" * 50)
    print(integrate_structured_parsing_into_workflow())

    # Example usage
    print("\nExample: Risk Assessment with Structured Parsing")
    workflow = ContractAnalysisEnhancedWorkflow()

    sample_prompt = "Analyze the risk factors in this contract..."
    structured_prompt = workflow.risk_generator.build_structured_prompt(sample_prompt)

    print(f"Generated structured prompt preview:")
    print(structured_prompt[:500] + "...")
