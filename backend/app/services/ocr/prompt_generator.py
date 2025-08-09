"""
OCR prompt generation.
"""

from typing import Optional, Dict, Any


class PromptGenerator:
    """Generates OCR prompts for different contexts."""
    
    def create_ocr_prompt(
        self, 
        page_number: int, 
        is_single_image: bool = False, 
        **kwargs
    ) -> str:
        """Create optimized OCR prompt."""
        base_prompt = """
        You are an expert OCR system. Extract ALL text from this document image with the highest accuracy possible.
        
        Instructions:
        - Extract every word, number, and symbol visible in the image
        - Maintain the original document structure and formatting where possible
        - If text is unclear, provide your best interpretation
        - Include all headers, subheadings, and section numbers
        - Preserve tables and lists with appropriate formatting
        - Don't add any explanations or comments - just the extracted text
        
        Focus on accuracy and completeness. Extract all visible text content.
        """

        # Add context-specific instructions
        contract_context = kwargs.get("contract_context", {})
        if contract_context:
            if contract_context.get("australian_state"):
                base_prompt += f"\nNote: This appears to be an Australian document from {contract_context['australian_state']}."
            if contract_context.get("contract_type"):
                base_prompt += f"\nDocument type: {contract_context['contract_type']}"

        if not is_single_image:
            base_prompt += f"\nThis is page {page_number} of a multi-page document."

        base_prompt += "\n\nExtracted text:"
        return base_prompt