---
category: quality_requirements
context:
  state: '*'
  contract_type: '*'
  purchase_method: '*'
  use_category: '*'
  user_experience: '*'
  analysis_depth: '*'
priority: 70
version: 1.0.0
description: Fast OCR processing instructions for time-sensitive analysis
tags:
- ocr
- fast-processing
- speed
quality_level: fast
type: processing_instructions
---

### Fast Processing Requirements:

**Speed-Optimized Settings:**
- Use rapid OCR processing with acceptable accuracy trade-offs
- Minimal image preprocessing for faster throughput
- Single-pass extraction with basic validation
- Focus on essential information extraction only
- Prioritize speed over perfect accuracy

**Essential Information Focus:**
- Extract key amounts and dates quickly
- Capture party names and basic details
- Identify document type and main sections
- Skip detailed formatting preservation
- Flag only critical extraction failures

**Efficiency Measures:**
- Use fast document recognition patterns
- Apply streamlined validation rules
- Report basic extraction metrics only
- Optimize for time-sensitive decisions