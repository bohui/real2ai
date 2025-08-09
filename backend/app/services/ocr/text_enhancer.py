"""
Text enhancement and post-processing for OCR results.
"""

import re
from typing import Dict, Any

# Constants
PATTERN_NAME_MAX_LENGTH = 20
ENHANCEMENT_FACTOR_INCREMENT = 0.02


class TextEnhancer:
    """Enhances extracted text with post-processing."""
    
    async def enhance_extracted_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """Enhance extracted text with post-processing."""
        try:
            enhanced_text = text
            enhancements_applied = []

            # Fix common OCR errors
            ocr_corrections = {
                r"\$\s*(\d)": r"$\1",  # Fix spacing in currency
                r"(\d),(\d{3})": r"\1,\2",  # Fix comma in numbers
                r"(\d{1,2})/(\d{1,2})/(\d{4})": r"\1/\2/\3",  # Standardize dates
            }

            for pattern, replacement in ocr_corrections.items():
                if re.search(pattern, enhanced_text):
                    enhanced_text = re.sub(pattern, replacement, enhanced_text)
                    enhancements_applied.append(
                        f"corrected_pattern_{pattern[:PATTERN_NAME_MAX_LENGTH]}"
                    )

            return {
                "text": enhanced_text,
                "enhancements_applied": enhancements_applied,
                "enhancement_factor": 1.0
                + len(enhancements_applied) * ENHANCEMENT_FACTOR_INCREMENT,
            }

        except Exception as e:
            return {"text": text, "enhancements_applied": [], "enhancement_factor": 1.0}