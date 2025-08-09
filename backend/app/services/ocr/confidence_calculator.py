"""
Confidence score calculation for OCR results.
"""

# Constants
TEXT_LENGTH_THRESHOLD_SMALL = 100
TEXT_LENGTH_THRESHOLD_MEDIUM = 500
TEXT_LENGTH_THRESHOLD_LARGE = 1000


class ConfidenceCalculator:
    """Calculates confidence scores for OCR results."""
    
    def calculate_confidence(self, extracted_text: str) -> float:
        """Calculate confidence score for extracted text."""
        if not extracted_text:
            return 0.0

        confidence = 0.5  # Base confidence

        # Text length factor
        text_length = len(extracted_text.strip())
        if text_length > TEXT_LENGTH_THRESHOLD_SMALL:
            confidence += 0.1
        if text_length > TEXT_LENGTH_THRESHOLD_MEDIUM:
            confidence += 0.1
        if text_length > TEXT_LENGTH_THRESHOLD_LARGE:
            confidence += 0.1

        # Quality indicators
        words = extracted_text.split()
        if words:
            # Reduce confidence for high ratio of single characters (poor OCR)
            single_char_ratio = sum(1 for word in words if len(word) == 1) / len(words)
            confidence -= single_char_ratio * 0.3

            # Boost confidence for reasonable word lengths
            avg_word_length = sum(len(word) for word in words) / len(words)
            if 3 <= avg_word_length <= 8:
                confidence += 0.1

        return max(0.0, min(1.0, confidence))