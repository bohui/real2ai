#!/usr/bin/env python3
"""
Layout Format Cleanup Demo

This script demonstrates the LayoutFormatCleanupNode functionality by processing
sample OCR text and showing how font sizes are mapped to layout elements to
create clean, formatted markdown output.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.utils.font_layout_mapper import FontLayoutMapper


def demo_layout_format_cleanup():
    """Demonstrate layout format cleanup functionality."""
    print("=" * 60)
    print("LAYOUT FORMAT CLEANUP DEMO")
    print("=" * 60)

    # Show how the node would be initialized with progress range
    print("Node initialization with progress range:")
    print("  LayoutFormatCleanupNode(progress_range=(43, 48))")
    print("  - Start: 43%")
    print("  - End: 48%")
    print()

    # Sample font mapping from user's example
    font_mapping = {
        "10.0": "body_text",
        "11.0": "body_text",
        "12.0": "section_heading",
        "8.0": "emphasis_text",
        "9.0": "subsection_heading",
        "14.0": "emphasis_text",
        "37.0": "emphasis_text",
        "9.5": "emphasis_text",
    }

    print("Font to Layout Mapping:")
    for font_size, layout_element in font_mapping.items():
        print(f"  Font Size {font_size}: {layout_element}")

    print("\n" + "-" * 40)

    # Sample input text from user's example
    input_text = """--- Page 7 ---
55 Roseville Avenue, Roseville NSW 2069[[[37.0]]]
1.[[[12.0]]]"""

    print("Input Text:")
    print(input_text)
    print("\n" + "-" * 40)

    # Simulate the formatting logic from LayoutFormatCleanupNode
    formatted_text = format_text_with_layout_mapping(input_text, font_mapping)

    print("Formatted Output:")
    print(formatted_text)
    print("\n" + "-" * 40)

    # Show the expected output from user's example
    expected_output = """**55 Roseville Avenue, Roseville NSW 2069**

## 1."""

    print("Expected Output:")
    print(expected_output)
    print("\n" + "-" * 40)

    # Verify the output matches
    if formatted_text.strip() == expected_output.strip():
        print("✅ SUCCESS: Output matches expected format!")
    else:
        print("❌ MISMATCH: Output differs from expected format")
        print("\nDifferences:")
        print(f"Generated: '{formatted_text}'")
        print(f"Expected: '{expected_output}'")


def format_text_with_layout_mapping(text: str, font_mapping: dict) -> str:
    """
    Simulate the formatting logic from LayoutFormatCleanupNode.

    Args:
        text: Raw OCR text with font markers
        font_mapping: Dictionary mapping font sizes to layout elements

    Returns:
        Formatted markdown text
    """
    import re

    if not font_mapping:
        # If no font mapping, return cleaned text without font markers
        font_pattern = re.compile(r"\[\[\[\d+(?:\.\d+)?\]\]\]")
        return font_pattern.sub("", text)

    # Split by page delimiters
    page_delimiter_pattern = re.compile(r"^--- Page \d+ ---\n", re.MULTILINE)
    pages = page_delimiter_pattern.split(text)

    formatted_pages = []

    for page in pages:
        if not page.strip():
            continue

        formatted_page = format_page_with_mapping(page, font_mapping)
        if formatted_page:
            formatted_pages.append(formatted_page)

    return "\n\n".join(formatted_pages)


def format_page_with_mapping(page_text: str, font_mapping: dict) -> str:
    """
    Format a single page using font mapping.

    Args:
        page_text: Text content of a single page
        font_mapping: Dictionary mapping font sizes to layout elements

    Returns:
        Formatted page text
    """
    import re

    lines = page_text.strip().split("\n")
    formatted_lines = []

    for line in lines:
        if not line.strip():
            continue

        # Look for font size markers
        font_pattern = re.compile(r"\[\[\[(\d+(?:\.\d+)?)\]\]\]")
        match = font_pattern.search(line)

        if match:
            font_size = match.group(1)
            # Remove the font marker for clean text
            clean_text = font_pattern.sub("", line).strip()

            if clean_text:
                # Apply formatting based on font mapping
                layout_element = font_mapping.get(font_size, "body_text")
                formatted_line = apply_layout_formatting(clean_text, layout_element)
                formatted_lines.append(formatted_line)
        else:
            # No font marker, treat as regular text
            if line.strip():
                formatted_lines.append(line.strip())

    # Join with double newlines to match expected format
    return "\n\n".join(formatted_lines)


def apply_layout_formatting(text: str, layout_element: str) -> str:
    """
    Apply markdown formatting based on layout element type.

    Args:
        text: Clean text without font markers
        layout_element: Type of layout element (main_title, section_heading, etc.)

    Returns:
        Formatted markdown text
    """
    if not text:
        return ""

    if layout_element == "main_title":
        return f"# {text}"
    elif layout_element == "section_heading":
        return f"## {text}"
    elif layout_element == "subsection_heading":
        return f"### {text}"
    elif layout_element == "emphasis_text":
        return f"**{text}**"
    elif layout_element == "body_text":
        return text
    elif layout_element == "other":
        return text
    else:
        # Default to body text for unknown layout elements
        return text


def demo_more_complex_example():
    """Demonstrate with a more complex example."""
    print("\n" + "=" * 60)
    print("MORE COMPLEX EXAMPLE")
    print("=" * 60)

    # More complex font mapping
    complex_font_mapping = {
        "24.0": "main_title",
        "18.0": "section_heading",
        "16.0": "subsection_heading",
        "12.0": "body_text",
        "14.0": "emphasis_text",
        "10.0": "body_text",
    }

    # More complex input text
    complex_input = """--- Page 1 ---
PURCHASE AGREEMENT[[[24.0]]]
1. GENERAL CONDITIONS[[[18.0]]]
1.1 Definitions[[[16.0]]]
This agreement is made between the parties...[[[12.0]]]
The property address is...[[[12.0]]]

--- Page 2 ---
2. PROPERTY DETAILS[[[18.0]]]
2.1 Location[[[16.0]]]
The property is located at...[[[12.0]]]
Important Note: This is a critical section[[[14.0]]]"""

    print("Complex Input Text:")
    print(complex_input)
    print("\n" + "-" * 40)

    # Format the complex text
    complex_formatted = format_text_with_layout_mapping(
        complex_input, complex_font_mapping
    )

    print("Complex Formatted Output:")
    print(complex_formatted)


if __name__ == "__main__":
    demo_layout_format_cleanup()
    demo_more_complex_example()
