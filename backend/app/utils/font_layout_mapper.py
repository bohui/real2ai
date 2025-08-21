"""
Font Layout Mapper Utility

Provides utilities for analyzing font sizes in OCR text and generating consistent
mappings between font sizes and layout elements (headings, body text, etc.).
"""

import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


# Constants for font size analysis
class FontLayoutConstants:
    """Constants for font layout mapping analysis."""

    # Minimum frequency threshold for a font size to be considered significant
    MIN_FONT_FREQUENCY = 2

    # Maximum number of distinct font sizes to map (to avoid over-mapping)
    MAX_FONT_SIZES = 8

    # Font size patterns that indicate specific layout elements
    HEADING_INDICATORS = [
        r"^[0-9]+\.",  # Numbered sections (1., 1.1, etc.)
        r"^[A-Z][A-Z\s]+$",  # ALL CAPS text
        r"^(Schedule|Annexure|Appendix|Part|Section)",  # Document structure keywords
        r"^(PURCHASE AGREEMENT|LEASE AGREEMENT|CONTRACT)",  # Document type keywords
    ]

    # Body text indicators
    BODY_INDICATORS = [
        r"^[a-z]",  # Lowercase start
        r"^[0-9]+\s+[a-z]",  # Numbered lists
        r"^[•\-\*]\s",  # Bullet points
    ]


class FontLayoutMapper:
    """Maps font sizes to layout elements based on text analysis."""

    def __init__(self):
        self.font_size_pattern = re.compile(r"\[\[\[(\d+(?:\.\d+)?)\]\]\]")
        self.page_delimiter_pattern = re.compile(r"^--- Page \d+ ---\n", re.MULTILINE)

    def extract_font_sizes_from_text(self, text: str) -> List[Tuple[str, float]]:
        """
        Extract all font sizes and their associated text from OCR text.

        Args:
            text: OCR text with font size markers

        Returns:
            List of (text_span, font_size) tuples
        """
        font_spans = []

        # Split by page delimiters to process each page separately
        pages = self.page_delimiter_pattern.split(text)

        for page in pages:
            if not page.strip():
                continue

            lines = page.strip().split("\n")
            for line in lines:
                if not line.strip():
                    continue

                # Look for font size markers
                match = self.font_size_pattern.search(line)
                if match:
                    font_size = float(match.group(1))
                    # Remove the font marker for clean text
                    clean_text = self.font_size_pattern.sub("", line).strip()
                    if clean_text:
                        font_spans.append((clean_text, font_size))

        return font_spans

    def analyze_font_distribution(
        self, font_spans: List[Tuple[str, float]]
    ) -> Dict[float, int]:
        """
        Analyze the frequency distribution of font sizes.

        Args:
            font_spans: List of (text, font_size) tuples

        Returns:
            Dictionary mapping font sizes to their frequencies
        """
        font_counts = Counter(font_size for _, font_size in font_spans)

        # Filter out very rare font sizes
        significant_fonts = {
            font_size: count
            for font_size, count in font_counts.items()
            if count >= FontLayoutConstants.MIN_FONT_FREQUENCY
        }

        return significant_fonts

    def classify_text_by_patterns(self, text: str) -> str:
        """
        Classify text as heading, body, or other based on patterns.

        Args:
            text: Text to classify

        Returns:
            Classification: 'heading', 'body', or 'other'
        """
        text = text.strip()

        # Check for heading indicators
        for pattern in FontLayoutConstants.HEADING_INDICATORS:
            if re.match(pattern, text, re.IGNORECASE):
                return "heading"

        # Check for body text indicators
        for pattern in FontLayoutConstants.BODY_INDICATORS:
            if re.match(pattern, text, re.IGNORECASE):
                return "body"

        # Default classification based on length and case
        if len(text) > 50:
            return "body"
        elif text.isupper() and len(text) > 3:
            return "heading"
        else:
            return "other"

    def generate_font_layout_mapping(self, text: str) -> Dict[str, str]:
        """
        Generate a mapping from font sizes to layout elements.

        Args:
            text: OCR text with font size markers

        Returns:
            Dictionary mapping font sizes (as strings) to layout element types
        """
        try:
            # Extract font sizes and associated text
            font_spans = self.extract_font_sizes_from_text(text)

            if not font_spans:
                logger.warning("No font size markers found in text")
                return {}

            # Analyze font distribution
            font_distribution = self.analyze_font_distribution(font_spans)

            if not font_distribution:
                logger.warning("No significant font sizes found")
                return {}

            # Sort font sizes by frequency (most common first)
            sorted_fonts = sorted(
                font_distribution.items(), key=lambda x: x[1], reverse=True
            )

            # Limit to maximum number of font sizes
            significant_fonts = sorted_fonts[: FontLayoutConstants.MAX_FONT_SIZES]

            # Generate mapping based on frequency and text patterns
            font_mapping = {}

            for font_size, frequency in significant_fonts:
                # Analyze text associated with this font size
                texts_with_font = [
                    text
                    for text, size in font_spans
                    if abs(size - font_size)
                    < 0.1  # Allow small floating point differences
                ]

                if not texts_with_font:
                    continue

                # Classify the text patterns for this font size
                classifications = [
                    self.classify_text_by_patterns(text) for text in texts_with_font
                ]
                classification_counts = Counter(classifications)

                # Determine primary classification
                primary_class = max(classification_counts.items(), key=lambda x: x[1])[
                    0
                ]

                # Map font size to layout element
                if primary_class == "heading":
                    if frequency > max(font_distribution.values()) * 0.3:  # Very common
                        layout_element = "main_title"
                    elif frequency > max(font_distribution.values()) * 0.15:  # Common
                        layout_element = "section_heading"
                    else:
                        layout_element = "subsection_heading"
                elif primary_class == "body":
                    if frequency > max(font_distribution.values()) * 0.5:  # Most common
                        layout_element = "body_text"
                    else:
                        layout_element = "emphasis_text"
                else:
                    layout_element = "other"

                font_mapping[str(font_size)] = layout_element

            logger.info(f"Generated font layout mapping: {font_mapping}")
            return font_mapping

        except Exception as e:
            logger.error(f"Error generating font layout mapping: {e}")
            return {}

    def validate_mapping_consistency(
        self, mapping: Dict[str, str], text: str
    ) -> Dict[str, float]:
        """
        Validate the consistency of font layout mapping across the document.

        Args:
            mapping: Font to layout mapping
            text: OCR text to validate against

        Returns:
            Dictionary with confidence scores for each mapping
        """
        confidence_scores = {}

        try:
            font_spans = self.extract_font_sizes_from_text(text)

            for font_size_str, layout_element in mapping.items():
                font_size = float(font_size_str)

                # Find all text spans with this font size
                texts_with_font = [
                    text for text, size in font_spans if abs(size - font_size) < 0.1
                ]

                if not texts_with_font:
                    confidence_scores[font_size_str] = 0.0
                    continue

                # Calculate consistency score based on pattern matching
                classifications = [
                    self.classify_text_by_patterns(text) for text in texts_with_font
                ]
                classification_counts = Counter(classifications)

                # Calculate consistency as percentage of most common classification
                total_texts = len(texts_with_font)
                most_common_count = max(classification_counts.values())
                consistency = most_common_count / total_texts

                # Adjust confidence based on consistency and frequency
                frequency = len(texts_with_font)
                max_frequency = max(
                    len([t for t, s in font_spans if abs(s - fs) < 0.1])
                    for fs in [float(fs) for fs in mapping.keys()]
                )

                frequency_score = min(frequency / max_frequency, 1.0)

                # Combined confidence score
                confidence = (consistency * 0.7) + (frequency_score * 0.3)
                confidence_scores[font_size_str] = round(confidence, 2)

            return confidence_scores

        except Exception as e:
            logger.error(f"Error validating mapping consistency: {e}")
            return {font_size: 0.0 for font_size in mapping.keys()}
