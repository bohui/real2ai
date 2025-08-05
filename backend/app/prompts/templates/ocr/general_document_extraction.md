---
type: "user"
name: "general_document_extraction"
version: "1.0.0"
description: "General OCR extraction for any document type"
required_variables: []
optional_variables:
  - "document_type"
  - "page_number"
  - "is_multi_page"
  - "quality_requirements"
model_compatibility: ["gemini-2.5-pro", "gpt-4"]
max_tokens: 2000
temperature_range: [0.0, 0.1]
tags: ["ocr", "extraction", "general"]
---

# General Document OCR Extraction

You are an expert OCR system. Extract ALL text from this document image with the highest accuracy possible.

## Instructions

- Extract every word, number, and symbol visible in the image
- Maintain the original document structure and formatting where possible
- If text is unclear, provide your best interpretation using [unclear: best_guess] notation
- Include all headers, subheadings, and section numbers
- Preserve tables and lists with appropriate formatting
- Don't add any explanations or comments - just the extracted text

{% if document_type %}
**Document Type**: {{ document_type }}
{% endif %}

{% if is_multi_page and page_number %}
**Page**: {{ page_number }} of a multi-page document
{% endif %}

{% if quality_requirements == "high" %}
## High-Quality Standards
- Zero tolerance for omissions - extract ALL visible text
- Preserve exact formatting including spacing and indentation
- Include footnotes, watermarks, and any marginal text
- Use precise notation for unclear or damaged text
{% endif %}

## Output Format

Return ONLY the extracted text maintaining the original document structure.

**Guidelines:**
- Do NOT add explanations or interpretations
- Use [unclear: text] for illegible portions
- Maintain exact spacing and line breaks where possible
- Include ALL visible content

**For unclear text:**
- [unclear: word] - when text is partially readable
- [handwritten: content] - for handwritten additions
- [watermark: text] - for watermarks or background text

Begin extraction: