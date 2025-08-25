"""
Unit tests for FontLayoutMapper utility

Tests font size extraction, analysis, and layout mapping generation.
"""

import pytest
from unittest.mock import patch
from app.utils.font_layout_mapper import FontLayoutMapper, FontLayoutConstants


class TestFontLayoutConstants:
    """Test constants used in font layout mapping."""

    def test_constants_are_defined(self):
        """Test that all required constants are defined."""
        assert hasattr(FontLayoutConstants, "MIN_FONT_FREQUENCY")
        assert hasattr(FontLayoutConstants, "MAX_FONT_SIZES")
        assert hasattr(FontLayoutConstants, "HEADING_INDICATORS")
        assert hasattr(FontLayoutConstants, "BODY_INDICATORS")

        assert FontLayoutConstants.MIN_FONT_FREQUENCY == 2
        assert FontLayoutConstants.MAX_FONT_SIZES == 8
        assert len(FontLayoutConstants.HEADING_INDICATORS) > 0
        assert len(FontLayoutConstants.BODY_INDICATORS) > 0


class TestFontLayoutMapper:
    """Test FontLayoutMapper class functionality."""

    @pytest.fixture
    def mapper(self):
        """Create a FontLayoutMapper instance for testing."""
        return FontLayoutMapper()

    @pytest.fixture
    def sample_ocr_text(self):
        """Sample OCR text with font size markers for testing."""
        return """--- Page 1 ---
PURCHASE AGREEMENT[[[24.0]]]
1. GENERAL CONDITIONS[[[18.0]]]
1.1 Definitions[[[16.0]]]
This agreement is made between the parties...[[[12.0]]]
The property address is...[[[12.0]]]

--- Page 2 ---
2. PROPERTY DETAILS[[[18.0]]]
2.1 Location[[[16.0]]]
The property is located at...[[[12.0]]]
2.2 Description[[[16.0]]]
The property consists of...[[[12.0]]]

--- Page 3 ---
Schedule A[[[16.0]]]
Additional terms and conditions...[[[12.0]]]"""

    @pytest.fixture
    def sample_ocr_text_no_fonts(self):
        """Sample OCR text without font size markers."""
        return """--- Page 1 ---
PURCHASE AGREEMENT
1. GENERAL CONDITIONS
1.1 Definitions
This agreement is made between the parties...
The property address is..."""

    @pytest.fixture
    def sample_ocr_text_mixed(self):
        """Sample OCR text with mixed font markers and plain text."""
        return """--- Page 1 ---
PURCHASE AGREEMENT[[[24.0]]]
1. GENERAL CONDITIONS[[[18.0]]]
1.1 Definitions
This agreement is made between the parties...[[[12.0]]]
The property address is...[[[12.0]]]"""

    def test_init(self, mapper):
        """Test FontLayoutMapper initialization."""
        assert mapper.font_size_pattern is not None
        assert mapper.page_delimiter_pattern is not None

        # Test regex patterns compile correctly
        assert mapper.font_size_pattern.search("text[[[12.0]]]") is not None
        assert mapper.page_delimiter_pattern.search("--- Page 1 ---\n") is not None

    def test_extract_font_sizes_from_text(self, mapper, sample_ocr_text):
        """Test font size extraction from OCR text."""
        font_spans = mapper.extract_font_sizes_from_text(sample_ocr_text)

        assert len(font_spans) == 12  # Total font-marked spans

        # Check specific font sizes are extracted
        font_sizes = [size for _, size in font_spans]
        assert 24.0 in font_sizes  # Main title
        assert 18.0 in font_sizes  # Section headings
        assert 16.0 in font_sizes  # Subsection headings
        assert 12.0 in font_sizes  # Body text

        # Check text content is cleaned
        texts = [text for text, _ in font_spans]
        assert "PURCHASE AGREEMENT" in texts
        assert "1. GENERAL CONDITIONS" in texts
        assert "1.1 Definitions" in texts

        # Check no font markers remain in extracted text
        for text, _ in font_spans:
            assert "[[" not in text
            assert "]]" not in text

    def test_extract_font_sizes_no_markers(self, mapper, sample_ocr_text_no_fonts):
        """Test font size extraction when no markers are present."""
        font_spans = mapper.extract_font_sizes_from_text(sample_ocr_text_no_fonts)
        assert len(font_spans) == 0

    def test_extract_font_sizes_mixed_content(self, mapper, sample_ocr_text_mixed):
        """Test font size extraction with mixed marked and unmarked text."""
        font_spans = mapper.extract_font_sizes_from_text(sample_ocr_text_mixed)

        # Should extract only marked text
        assert len(font_spans) == 5

        # Check that unmarked text is not included
        texts = [text for text, _ in font_spans]
        assert "1.1 Definitions" not in texts  # No font marker

        # Check that marked text is included
        assert "PURCHASE AGREEMENT" in texts  # Has font marker

    def test_analyze_font_distribution(self, mapper, sample_ocr_text):
        """Test font distribution analysis."""
        font_spans = mapper.extract_font_sizes_from_text(sample_ocr_text)
        distribution = mapper.analyze_font_distribution(font_spans)

        # Check that all font sizes are present
        assert 24.0 in distribution
        assert 18.0 in distribution
        assert 16.0 in distribution
        assert 12.0 in distribution

        # Check frequencies
        assert distribution[12.0] >= 6  # Body text should be most common
        assert distribution[24.0] == 1  # Main title should be unique
        assert distribution[18.0] >= 2  # Section headings

    def test_analyze_font_distribution_insufficient_frequency(self, mapper):
        """Test font distribution with insufficient frequency."""
        # Create text with low-frequency font sizes
        low_freq_text = """--- Page 1 ---
Title[[[24.0]]]
Content[[[12.0]]]"""

        font_spans = mapper.extract_font_sizes_from_text(low_freq_text)
        distribution = mapper.analyze_font_distribution(font_spans)

        # Should filter out font sizes with frequency < MIN_FONT_FREQUENCY
        assert len(distribution) == 0

    def test_classify_text_by_patterns(self, mapper):
        """Test text classification by patterns."""
        # Test heading indicators
        assert mapper.classify_text_by_patterns("1. GENERAL CONDITIONS") == "heading"
        assert mapper.classify_text_by_patterns("SCHEDULE A") == "heading"
        assert mapper.classify_text_by_patterns("PURCHASE AGREEMENT") == "heading"
        assert mapper.classify_text_by_patterns("PART I") == "heading"

        # Test body text indicators
        assert mapper.classify_text_by_patterns("This is body text") == "body"
        assert mapper.classify_text_by_patterns("1. First item") == "body"
        assert mapper.classify_text_by_patterns("• Bullet point") == "body"
        assert mapper.classify_text_by_patterns("- Another point") == "body"

        # Test edge cases
        assert (
            mapper.classify_text_by_patterns("SHORT") == "heading"
        )  # ALL CAPS but short
        assert mapper.classify_text_by_patterns("") == "other"  # Empty string
        assert mapper.classify_text_by_patterns("   ") == "other"  # Whitespace only

    def test_classify_text_by_patterns_long_text(self, mapper):
        """Test text classification for long text."""
        long_text = "This is a very long piece of text that should be classified as body text because it exceeds the typical length threshold for headings and contains normal sentence structure with proper capitalization and punctuation."
        assert mapper.classify_text_by_patterns(long_text) == "body"

    def test_generate_font_layout_mapping(self, mapper, sample_ocr_text):
        """Test font layout mapping generation."""
        mapping = mapper.generate_font_layout_mapping(sample_ocr_text)

        assert isinstance(mapping, dict)
        assert len(mapping) > 0

        # Check that font sizes are mapped to layout elements
        assert "24.0" in mapping
        assert "18.0" in mapping
        assert "16.0" in mapping
        assert "12.0" in mapping

        # Check layout element types
        layout_elements = set(mapping.values())
        assert "main_title" in layout_elements
        assert "section_heading" in layout_elements
        assert "subsection_heading" in layout_elements
        assert "body_text" in layout_elements

    def test_generate_font_layout_mapping_no_fonts(
        self, mapper, sample_ocr_text_no_fonts
    ):
        """Test mapping generation when no font markers are present."""
        mapping = mapper.generate_font_layout_mapping(sample_ocr_text_no_fonts)
        assert mapping == {}

    def test_generate_font_layout_mapping_insufficient_data(self, mapper):
        """Test mapping generation with insufficient data."""
        # Text with only one font size (below MIN_FONT_FREQUENCY)
        insufficient_text = """--- Page 1 ---
Title[[[24.0]]]
Content[[[24.0]]]"""

        mapping = mapper.generate_font_layout_mapping(insufficient_text)
        assert mapping == {}

    def test_generate_font_layout_mapping_max_fonts_limit(self, mapper):
        """Test that mapping respects MAX_FONT_SIZES limit."""
        # Create text with many different font sizes
        many_fonts_text = ""
        for i in range(15):  # More than MAX_FONT_SIZES (8)
            many_fonts_text += f"Text{i}[[[{10.0 + i}]]]\n"

        mapping = mapper.generate_font_layout_mapping(many_fonts_text)
        assert len(mapping) <= FontLayoutConstants.MAX_FONT_SIZES

    def test_validate_mapping_consistency(self, mapper, sample_ocr_text):
        """Test mapping consistency validation."""
        mapping = mapper.generate_font_layout_mapping(sample_ocr_text)
        confidence_scores = mapper.validate_mapping_consistency(
            mapping, sample_ocr_text
        )

        assert isinstance(confidence_scores, dict)
        assert len(confidence_scores) == len(mapping)

        # Check confidence scores are between 0.0 and 1.0
        for font_size, confidence in confidence_scores.items():
            assert 0.0 <= confidence <= 1.0
            assert font_size in mapping

    def test_validate_mapping_consistency_empty_mapping(self, mapper, sample_ocr_text):
        """Test consistency validation with empty mapping."""
        confidence_scores = mapper.validate_mapping_consistency({}, sample_ocr_text)
        assert confidence_scores == {}

    def test_validate_mapping_consistency_no_fonts_in_text(self, mapper):
        """Test consistency validation when text has no font markers."""
        mapping = {"12.0": "body_text", "18.0": "heading"}
        text_without_fonts = "Plain text without font markers"

        confidence_scores = mapper.validate_mapping_consistency(
            mapping, text_without_fonts
        )

        # All font sizes should have 0.0 confidence
        for font_size in mapping:
            assert confidence_scores[font_size] == 0.0

    @patch("app.utils.font_layout_mapper.logger")
    def test_error_handling_in_generate_mapping(self, mock_logger, mapper):
        """Test error handling in mapping generation."""
        # Mock the extract_font_sizes_from_text to raise an exception
        with patch.object(
            mapper, "extract_font_sizes_from_text", side_effect=Exception("Test error")
        ):
            mapping = mapper.generate_font_layout_mapping("test text")

            assert mapping == {}
            mock_logger.error.assert_called_once()

    @patch("app.utils.font_layout_mapper.logger")
    def test_error_handling_in_consistency_validation(self, mock_logger, mapper):
        """Test error handling in consistency validation."""
        # Mock the extract_font_sizes_from_text to raise an exception
        with patch.object(
            mapper, "extract_font_sizes_from_text", side_effect=Exception("Test error")
        ):
            confidence_scores = mapper.validate_mapping_consistency(
                {"12.0": "body_text"}, "test text"
            )

            assert confidence_scores == {"12.0": 0.0}
            mock_logger.error.assert_called_once()

    def test_floating_point_font_size_handling(self, mapper):
        """Test handling of floating point font sizes."""
        float_font_text = """--- Page 1 ---
Title[[[24.5]]]
Subtitle[[[18.75]]]
Content[[[12.25]]]"""

        font_spans = mapper.extract_font_sizes_from_text(float_font_text)

        # Check that floating point font sizes are extracted correctly
        font_sizes = [size for _, size in font_spans]
        assert 24.5 in font_sizes
        assert 18.75 in font_sizes
        assert 12.25 in font_sizes

    def test_font_size_tolerance_in_mapping(self, mapper):
        """Test that font size mapping handles small floating point differences."""
        # Create text with slightly different font sizes that should be grouped together
        tolerance_text = """--- Page 1 ---
Title1[[[24.0]]]
Title2[[[24.1]]]
Title3[[[23.9]]]"""

        mapping = mapper.generate_font_layout_mapping(tolerance_text)

        # Should group similar font sizes together
        assert len(mapping) < 3  # Should not create separate mappings for each

    def test_page_delimiter_handling(self, mapper):
        """Test handling of page delimiters."""
        multi_page_text = """--- Page 1 ---
Content on page 1[[[12.0]]]

--- Page 2 ---
Content on page 2[[[12.0]]]

--- Page 3 ---
Content on page 3[[[12.0]]]"""

        font_spans = mapper.extract_font_sizes_from_text(multi_page_text)

        # Should extract font spans from all pages
        assert len(font_spans) == 3

        # Check that page delimiter text is not included
        texts = [text for text, _ in font_spans]
        for text in texts:
            assert "--- Page" not in text
            assert "---" not in text
