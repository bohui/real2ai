#!/usr/bin/env python3
"""
Font Layout Mapping Demo

This script demonstrates the font layout mapping functionality by processing
sample OCR text and showing how font sizes are mapped to layout elements.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.utils.font_layout_mapper import FontLayoutMapper


def demo_basic_mapping():
    """Demonstrate basic font layout mapping."""
    print("=" * 60)
    print("BASIC FONT LAYOUT MAPPING DEMO")
    print("=" * 60)

    # Sample OCR text with font size markers
    sample_text = """--- Page 1 ---
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

    print("Sample OCR Text:")
    print(sample_text)
    print("\n" + "-" * 40)

    # Create mapper and generate mapping
    mapper = FontLayoutMapper()
    font_mapping = mapper.generate_font_layout_mapping(sample_text)

    print("Generated Font Layout Mapping:")
    for font_size, layout_element in font_mapping.items():
        print(f"  Font Size {font_size}: {layout_element}")

    # Validate consistency
    confidence_scores = mapper.validate_mapping_consistency(font_mapping, sample_text)

    print("\nMapping Consistency Scores:")
    for font_size, confidence in confidence_scores.items():
        print(f"  Font Size {font_size}: {confidence:.2f}")


def demo_floating_point_sizes():
    """Demonstrate handling of floating point font sizes."""
    print("\n" + "=" * 60)
    print("FLOATING POINT FONT SIZES DEMO")
    print("=" * 60)

    # Sample text with floating point font sizes
    float_text = """--- Page 1 ---
Title[[[24.5]]]
Subtitle[[[18.75]]]
Content[[[12.25]]]
More content[[[12.25]]]"""

    print("Sample Text with Floating Point Font Sizes:")
    print(float_text)
    print("\n" + "-" * 40)

    # Create mapper and generate mapping
    mapper = FontLayoutMapper()
    font_mapping = mapper.generate_font_layout_mapping(float_text)

    print("Generated Font Layout Mapping:")
    for font_size, layout_element in font_mapping.items():
        print(f"  Font Size {font_size}: {layout_element}")


def demo_mixed_content():
    """Demonstrate handling of mixed content (with and without font markers)."""
    print("\n" + "=" * 60)
    print("MIXED CONTENT DEMO")
    print("=" * 60)

    # Sample text with mixed font markers
    mixed_text = """--- Page 1 ---
PURCHASE AGREEMENT[[[24.0]]]
1. GENERAL CONDITIONS[[[18.0]]]
1.1 Definitions
This agreement is made between the parties...[[[12.0]]]
The property address is...[[[12.0]]]

--- Page 2 ---
2. PROPERTY DETAILS[[[18.0]]]
2.1 Location
The property is located at...[[[12.0]]]
2.2 Description[[[16.0]]]
The property consists of...[[[12.0]]]"""

    print("Sample Text with Mixed Font Markers:")
    print(mixed_text)
    print("\n" + "-" * 40)

    # Create mapper and generate mapping
    mapper = FontLayoutMapper()
    font_mapping = mapper.generate_font_layout_mapping(mixed_text)

    print("Generated Font Layout Mapping:")
    for font_size, layout_element in font_mapping.items():
        print(f"  Font Size {font_size}: {layout_element}")

    # Show what text was extracted
    font_spans = mapper.extract_font_sizes_from_text(mixed_text)
    print(f"\nExtracted {len(font_spans)} font-marked text spans:")
    for text, font_size in font_spans:
        print(f"  '{text[:50]}{'...' if len(text) > 50 else ''}' (Font: {font_size})")


def demo_no_font_markers():
    """Demonstrate behavior when no font markers are present."""
    print("\n" + "=" * 60)
    print("NO FONT MARKERS DEMO")
    print("=" * 60)

    # Sample text without font markers
    no_font_text = """--- Page 1 ---
PURCHASE AGREEMENT
1. GENERAL CONDITIONS
1.1 Definitions
This agreement is made between the parties...
The property address is..."""

    print("Sample Text without Font Markers:")
    print(no_font_text)
    print("\n" + "-" * 40)

    # Create mapper and generate mapping
    mapper = FontLayoutMapper()
    font_mapping = mapper.generate_font_layout_mapping(no_font_text)

    print("Generated Font Layout Mapping:")
    if font_mapping:
        for font_size, layout_element in font_mapping.items():
            print(f"  Font Size {font_size}: {layout_element}")
    else:
        print("  No font mapping generated (no font markers found)")

    # Show what text was extracted
    font_spans = mapper.extract_font_sizes_from_text(no_font_text)
    print(f"\nExtracted {len(font_spans)} font-marked text spans:")
    if font_spans:
        for text, font_size in font_spans:
            print(
                f"  '{text[:50]}{'...' if len(text) > 50 else ''}' (Font: {font_size})"
            )
    else:
        print("  No font-marked text spans found")


def demo_text_classification():
    """Demonstrate text classification patterns."""
    print("\n" + "=" * 60)
    print("TEXT CLASSIFICATION PATTERNS DEMO")
    print("=" * 60)

    mapper = FontLayoutMapper()

    # Test various text patterns
    test_texts = [
        "1. GENERAL CONDITIONS",
        "SCHEDULE A",
        "PURCHASE AGREEMENT",
        "PART I",
        "This is body text",
        "1. First item",
        "• Bullet point",
        "- Another point",
        "SHORT",
        "This is a very long piece of text that should be classified as body text because it exceeds the typical length threshold for headings and contains normal sentence structure with proper capitalization and punctuation.",
    ]

    print("Text Classification Examples:")
    for text in test_texts:
        classification = mapper.classify_text_by_patterns(text)
        print(f"  '{text[:50]}{'...' if len(text) > 50 else ''}' → {classification}")


def main():
    """Run all demos."""
    print("Font Layout Mapping System Demo")
    print("=" * 40)

    try:
        # Run all demos
        demo_basic_mapping()
        demo_floating_point_sizes()
        demo_mixed_content()
        demo_no_font_markers()
        demo_text_classification()

        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
