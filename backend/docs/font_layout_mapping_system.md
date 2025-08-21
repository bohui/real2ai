# Font Layout Mapping System

## Overview

The Font Layout Mapping System provides consistent interpretation of font sizes across document chunks during OCR text processing. It analyzes font size patterns in OCR text and generates mappings that ensure structural consistency throughout the document analysis process.

## Architecture

### Core Components

1. **FontLayoutMapper** (`app/utils/font_layout_mapper.py`)
   - Main utility class for font analysis and mapping generation
   - Handles font size extraction, pattern analysis, and layout element classification

2. **LayoutSummariseNode** (`app/agents/nodes/document_processing_subflow/layout_summarise_node.py`)
   - Document processing node that integrates font mapping
   - Generates mapping once and applies it consistently across all document chunks

3. **Updated Prompt** (`app/prompts/user/ocr/layout_summarise.md`)
   - Enhanced prompt that receives and uses font mapping context
   - Ensures LLM calls maintain consistent layout interpretation

### Data Flow

```
OCR Text with Font Markers
           ↓
   FontLayoutMapper.generate_font_layout_mapping()
           ↓
   Font Size → Layout Element Mapping
           ↓
   Consistent Context for All LLM Calls
           ↓
   Unified Document Structure Analysis
```

## Font Layout Mapping

### Layout Element Types

- **main_title**: Largest font size, typically document title
- **section_heading**: Large font for major sections (e.g., "1. GENERAL CONDITIONS")
- **subsection_heading**: Medium-large font for subsections (e.g., "1.1 Definitions")
- **body_text**: Standard font size for main content
- **emphasis_text**: Slightly larger font for emphasized content
- **other**: Special cases or less common font sizes

### Mapping Generation Logic

1. **Font Size Extraction**: Parses OCR text for `[[[font_size]]]` markers
2. **Frequency Analysis**: Identifies significant font sizes (minimum frequency threshold)
3. **Pattern Classification**: Analyzes text patterns associated with each font size
4. **Layout Assignment**: Maps font sizes to layout elements based on classification and frequency
5. **Consistency Validation**: Provides confidence scores for mapping reliability

### Configuration Constants

```python
class FontLayoutConstants:
    MIN_FONT_FREQUENCY = 2      # Minimum occurrences for significance
    MAX_FONT_SIZES = 8          # Maximum distinct font sizes to map
```

## Usage

### Basic Font Mapping

```python
from app.utils.font_layout_mapper import FontLayoutMapper

mapper = FontLayoutMapper()

# Generate mapping from OCR text
font_mapping = mapper.generate_font_layout_mapping(ocr_text)

# Result: {"24.0": "main_title", "18.0": "section_heading", ...}
```

### Integration in Document Processing

```python
# In LayoutSummariseNode
font_to_layout_mapping = self.font_mapper.generate_font_layout_mapping(full_text)

# Use consistent mapping across all chunks
for chunk_text in chunks:
    context = {
        "full_text": chunk_text,
        "font_to_layout_mapping": font_to_layout_mapping,  # Consistent mapping
        # ... other context
    }
```

### Prompt Context

The font mapping is passed to the LLM prompt to ensure consistent interpretation:

```markdown
Input context:
- font_to_layout_mapping: {{ font_to_layout_mapping }}

**CRITICAL**: Always use this mapping when interpreting font sizes. 
Do not create new mappings or deviate from the provided mapping.
```

## Benefits

### Consistency
- **Unified Structure**: Same font interpretation across all document chunks
- **Reduced Variance**: Eliminates inconsistent heading/body text classification
- **Predictable Output**: LLM responses follow consistent structural patterns

### Quality
- **Better Headings**: Accurate identification of document hierarchy
- **Improved Analysis**: Consistent structure enables better contract analysis
- **Reliable Taxonomy**: More accurate contract type and term extraction

### Performance
- **Single Analysis**: Font mapping generated once per document
- **Efficient Processing**: No repeated font analysis per chunk
- **Scalable**: Handles documents of any size with consistent performance

## Error Handling

### Graceful Degradation
- **No Font Markers**: Returns empty mapping, continues processing
- **Insufficient Data**: Filters out low-frequency font sizes
- **Mapping Errors**: Continues with empty mapping, logs warnings

### Validation
- **Consistency Scoring**: Provides confidence scores for each mapping
- **Pattern Validation**: Ensures mapping aligns with text patterns
- **Frequency Analysis**: Validates mapping against actual font usage

## Testing

### Test Coverage

1. **Unit Tests** (`tests/unit/utils/test_font_layout_mapper.py`)
   - Font size extraction and analysis
   - Text classification patterns
   - Mapping generation logic
   - Error handling scenarios

2. **Integration Tests** (`tests/integration/agents/nodes/test_layout_summarise_node_font_mapping.py`)
   - End-to-end font mapping integration
   - Consistency across document chunks
   - Error handling in document processing

### Running Tests

```bash
# Run all font mapping tests
cd backend
python scripts/test_font_mapping.py

# Run specific test patterns
python scripts/test_font_mapping.py "test_extract_font_sizes"

# Run with pytest directly
pytest tests/unit/utils/test_font_layout_mapper.py -v
pytest tests/integration/agents/nodes/test_layout_summarise_node_font_mapping.py -v
```

### Demo Script

```bash
# Run the demo to see font mapping in action
cd backend
python examples/font_mapping_demo.py
```

## Configuration

### Font Size Patterns

The system recognizes various text patterns for classification:

```python
HEADING_INDICATORS = [
    r'^[0-9]+\.',                    # Numbered sections
    r'^[A-Z][A-Z\s]+$',             # ALL CAPS text
    r'^(Schedule|Annexure|Appendix)', # Document structure keywords
    r'^(PURCHASE AGREEMENT|LEASE)',   # Document type keywords
]

BODY_INDICATORS = [
    r'^[a-z]',                       # Lowercase start
    r'^[0-9]+\s+[a-z]',             # Numbered lists
    r'^[•\-\*]\s',                   # Bullet points
]
```

### Thresholds

- **MIN_FONT_FREQUENCY**: Minimum occurrences for a font size to be considered significant
- **MAX_FONT_SIZES**: Maximum number of distinct font sizes to map (prevents over-mapping)
- **Font Size Tolerance**: Handles small floating-point differences in font sizes

## Monitoring and Logging

### Log Messages

```python
# Font mapping generation
logger.info(f"Generated font layout mapping with {len(mapping)} font sizes")

# Font mapping usage
logger.info("Using consistent font mapping across document chunks")

# Error handling
logger.warning("No font layout mapping generated; proceeding without mapping")
logger.error(f"Error generating font layout mapping: {e}")
```

### Metrics

- **Mapping Generation Time**: Performance monitoring for font analysis
- **Mapping Success Rate**: Percentage of documents with successful font mapping
- **Consistency Scores**: Average confidence scores across mappings

## Future Enhancements

### Planned Features

1. **Machine Learning Integration**: Train models on document structure patterns
2. **Dynamic Thresholds**: Adaptive frequency thresholds based on document size
3. **Multi-language Support**: Extend pattern recognition to other languages
4. **Advanced Classification**: More sophisticated text pattern analysis

### Extensibility

The system is designed for easy extension:

- **Custom Patterns**: Add new text classification patterns
- **Layout Elements**: Define new layout element types
- **Analysis Methods**: Implement alternative font analysis algorithms
- **Validation Rules**: Add custom consistency validation logic

## Troubleshooting

### Common Issues

1. **No Font Mapping Generated**
   - Check if OCR text contains font markers `[[[font_size]]]`
   - Verify font markers follow the expected format
   - Check minimum frequency threshold

2. **Inconsistent Mapping**
   - Ensure the same mapping is passed to all chunks
   - Verify font mapping is included in prompt context
   - Check for font size variations across document

3. **Performance Issues**
   - Monitor document size and chunk count
   - Check font analysis execution time
   - Verify memory usage during processing

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('app.utils.font_layout_mapper').setLevel(logging.DEBUG)
```

## Related Documentation

- [Contract Layout Summary Schema](../prompts/schema/contract_layout_summary_schema.py)
- [Layout Summarise Node](../agents/nodes/document_processing_subflow/layout_summarise_node.py)
- [OCR Text Extraction](../agents/nodes/document_processing_subflow/extract_text_node.py)
- [Prompt System Overview](../prompts/PROMPT_SYSTEM_OVERVIEW.md)
