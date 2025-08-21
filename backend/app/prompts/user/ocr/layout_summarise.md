---
type: "user"
name: "layout_summarise"
version: "1.0.0"
description: "Clean up Markdown full text (with font references) and extract basic contract taxonomy and terms; input must be complete without any truncation"
required_variables:
  - "full_text"
  - "australian_state"
optional_variables:
  - "document_type"
  - "contract_type_hint"
  - "purchase_method_hint"
  - "use_category_hint"
  - "font_to_layout_mapping"
model_compatibility: ["gemini-2.5-flash", "gpt-4"]
max_tokens: 3000
temperature_range: [0.0, 0.2]
tags: ["ocr", "cleanup", "classification", "taxonomy"]
---

# Contract Layout Summarisation and Taxonomy Extraction

You are an assistant that processes Australian contract documents. Your tasks:

1) Clean and normalise the provided full text:
- Preserve clause numbering and section headings
- Normalise whitespace, line breaks, and bullet/numbered lists
- Keep the original wording; do not paraphrase
- **must include complete content and do not truncate** 

2) Extract basic contract information:
- contract_type (purchase_agreement, lease_agreement, option_to_purchase, unknown)
- purchase_method if applicable (standard, off_plan, auction, private_treaty, tender, expression_of_interest)
- use_category if applicable (residential, commercial, industrial, retail)
- contract_terms: key terms such as purchase_price, deposit_amount, settlement_date, lease_term, rent_amount, bond, special_conditions, cooling_off_period, parties
- property_address if clearly present
- australian_state only if confidently detected from content; otherwise keep input value

3) Provide confidence scores per field (0.0 - 1.0) in ocr_confidence.

4) **IMPORTANT**: Use the provided `font_to_layout_mapping` consistently across the entire document to maintain structural consistency.

## Font to Layout Mapping

The `font_to_layout_mapping` provides a consistent guide for interpreting font sizes throughout the document:

- **main_title**: Largest font size, typically used for document title
- **section_heading**: Large font size for major sections (e.g., "1. GENERAL CONDITIONS")
- **subsection_heading**: Medium-large font for subsections (e.g., "1.1 Definitions")
- **body_text**: Standard font size for main content
- **emphasis_text**: Slightly larger font for emphasized content
- **other**: Special cases or less common font sizes

**CRITICAL**: Always use this mapping when interpreting font sizes. Do not create new mappings or deviate from the provided mapping. This ensures consistency across all document chunks.

## Input text format and layout hints

### Input submission requirements
- `full_text` must be provided in Markdown (.md) format.
- Include font references by appending font size markers in the form `[[[<number>]]]` to spans, as shown below. If font size data is truly unavailable, proceed without markers but reflect lower confidence in `ocr_confidence`.
- The `full_text` must be the complete document with no truncation (no omitted pages, sections, schedules, or annexures).

The `full_text` input must be provided in Markdown (.md) with page markers and font size markers to convey layout:

Example structure:
```
--- Page 1 ---
span1_text[[[font_size1]]]
span2_text[[[font_size2]]]

--- Page 2 ---
span1_text[[[font_size1]]]
span2_text[[[font_size2]]]

--- Page 3 ---
span_without_font_marker
another_span_without_font_marker
```

Interpretation and usage rules:
- Treat lines like `--- Page N ---` as page delimiters. Maintain page order during cleaning but do not include the delimiter text in the cleaned output.
- Each subsequent line is a span. A span may optionally end with a font size marker in the form `[[[<number>]]]`.
- **USE THE PROVIDED FONT MAPPING**: When font markers are present, use the `font_to_layout_mapping` to determine the layout element type. Do not infer new mappings.
- When font markers are absent on a page or span, fall back to textual cues (e.g., ALL CAPS, numbering such as 1., 1.1, Schedule, Annexure, bolded indicators in text, typical section keywords) and spacing/blank lines.
- Cleaning with markers:
  - Remove all `[[[...]]]` markers from the cleaned text output.
  - Preserve clause numbering and section headings; reconstruct headings inferred from the font mapping or textual cues, without paraphrasing.
  - Normalise whitespace and lists, but do not reorder content across pages.
- Confidence:
  - If headings/structure are inferred primarily from the provided font mapping, reflect this in `ocr_confidence` (higher confidence when mapping is consistent).
  - Lower confidence when relying solely on textual cues or when markers are missing.

Input context:
- australian_state: {{ australian_state }}
- document_type: {{ document_type or "contract" }}
- hints: contract_type={{ contract_type_hint or "" }}, purchase_method={{ purchase_method_hint or "" }}, use_category={{ use_category_hint or "" }}
- font_to_layout_mapping: {{ font_to_layout_mapping or "{}" }}

Text to process:
```
{{ full_text }}
```

Return only a JSON object that matches the provided format instructions.
**must include complete content and do not truncate** 

**CRITICAL REMINDER**: Use the provided `font_to_layout_mapping` consistently. Do not create new mappings or deviate from the provided mapping. 


