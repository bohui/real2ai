"""
Document analysis for extracted OCR text.
"""

from typing import Dict, Any

# Constants
CONTENT_QUALITY_THRESHOLD = 100


class DocumentAnalyzer:
    """Analyzes extracted text for document structure and content."""
    
    async def analyze_text_content(self, text: str, **kwargs) -> Dict[str, Any]:
        """Analyze extracted text for document structure and content."""
        try:
            # Basic content analysis
            word_count = len(text.split())
            char_count = len(text)

            # Detect potential document type based on keywords
            document_indicators = {
                "contract": ["agreement", "contract", "party", "vendor", "purchaser"],
                "legal": ["whereas", "therefore", "clause", "section", "subsection"],
                "financial": ["amount", "payment", "price", "$", "total", "balance"],
                "real_estate": ["property", "premises", "settlement", "title", "lease"],
            }

            detected_types = []
            for doc_type, keywords in document_indicators.items():
                matches = sum(
                    1 for keyword in keywords if keyword.lower() in text.lower()
                )
                if matches >= 2:  # Require at least 2 keyword matches
                    detected_types.append(doc_type)

            return {
                "word_count": word_count,
                "character_count": char_count,
                "detected_document_types": detected_types,
                "content_quality": (
                    "good" if word_count > CONTENT_QUALITY_THRESHOLD else "limited"
                ),
                "analysis_method": "keyword_detection",
            }

        except Exception as e:
            return {"error": str(e), "analysis_method": "failed"}