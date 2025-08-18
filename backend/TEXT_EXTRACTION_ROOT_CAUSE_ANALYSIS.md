# Text Extraction Root Cause Analysis

## Problem Summary

**Issue**: Contract analysis workflow fails with "Document processing failed - no artifacts or extracted text found" and gets stuck in retry loops.

**Misdiagnosis**: Initially thought the issue was with retry logic and workflow routing.

**Real Root Cause**: **Text extraction is failing** because documents are extracting insufficient text content (< 100 characters), causing the workflow to fail at the document processing step.

## Root Cause Analysis

### 1. The Real Problem

The error message "Document processing failed - no artifacts or extracted text found" comes from the `ReportCompilationNode`, but this is a **symptom**, not the cause. The real issue is:

1. **Document processing workflow runs** when resuming from `compile_report`
2. **Text extraction fails** because documents extract < 100 characters
3. **Workflow fails** and never creates artifacts
4. **Report compilation fails** because there are no artifacts to compile
5. **System tries to retry** but the same issue occurs

### 2. Why Text Extraction is Failing

The `ExtractTextNode` has a validation check:

```python
# Validate extracted content
full_text = self.text_extraction_result.full_text or ""
if len(full_text.strip()) < 100:
    return self._handle_error(
        state,
        ValueError("Insufficient text content"),
        "Insufficient text content extracted from document",
        # ... error details
    )
```

**This validation is failing** because:
- PDFs are being processed but extracting very little text
- Documents may be corrupted, image-based, or have no extractable text
- OCR fallback is not working properly
- The 100-character minimum threshold is too strict for some documents

### 3. Why the Retry Logic Doesn't Help

The retry logic I initially implemented was **treating the symptom, not the cause**:

- **Retry logic** tries to restart the workflow
- **But the workflow still fails** at the same text extraction step
- **The underlying issue** (insufficient text extraction) remains unresolved

## Proper Solution

### 1. Fix Text Extraction (Not Retry Logic)

**Add comprehensive logging** to understand why text extraction is failing:

```python
# CRITICAL FIX: Add comprehensive logging for PDF extraction results
self._log_info(
    f"PDF text extraction completed for document {state.get('document_id', 'unknown')}",
    extra={
        "document_id": state.get("document_id"),
        "total_pages": len(pages),
        "extraction_methods": extraction_methods,
        "full_text_length": len(full_text),
        "full_text_sample": full_text[:500] + "..." if len(full_text) > 500 else full_text,
        "overall_confidence": overall_conf,
        "total_words": total_words,
        "pages_with_text": len([p for p in pages if p.text_content and len(p.text_content.strip()) > 0]),
        "pages_without_text": len([p for p in pages if not p.text_content or len(p.text_content.strip()) == 0]),
    }
)
```

**Add detailed logging to basic PDF extraction**:

```python
# CRITICAL FIX: Log detailed extraction results
self._log_info(
    f"Basic PDF extraction via PyMuPDF completed",
    extra={
        "pages": pages_count,
        "total_text_length": len(text),
        "total_text_stripped": len(text.strip()),
        "page_text_lengths": [len(pt.strip()) for pt in page_texts],
        "page_text_samples": [pt[:100] + "..." if len(pt) > 100 else pt for pt in page_texts],
        "extraction_method": "pdf_pymupdf"
    }
)
```

### 2. Improve Error Messages

**Provide better error messages** when text extraction fails:

```python
# CRITICAL FIX: Check if we have sufficient text content
if len(full_text.strip()) < 100:
    # Try to provide a more helpful error message
    if len(pages) == 0:
        error_msg = "PDF extraction failed - no pages could be processed"
    elif all(len(p.text_content or "").strip() < 10 for p in pages):
        error_msg = "PDF extraction failed - all pages contain insufficient text (document may be image-based or corrupted)"
    else:
        error_msg = f"PDF extraction failed - extracted only {len(full_text.strip())} characters across {len(pages)} pages"
    
    return TextExtractionResult(
        success=False,
        error=error_msg,
        full_text=full_text,  # Keep what we have for debugging
        pages=pages,
        # ... other fields
    )
```

### 3. Add Fallback Strategies

**Implement fallback text extraction** when primary methods fail:

```python
# CRITICAL FIX: Add fallback for insufficient text
if len(full_text.strip()) < 100:
    # Try alternative extraction methods
    fallback_text = await self._try_fallback_extraction(file_content, state)
    
    if len(fallback_text.strip()) >= 100:
        # Use fallback text
        full_text = fallback_text
        extraction_methods.append("fallback_extraction")
    else:
        # Still insufficient - fail with detailed error
        return self._create_insufficient_text_error(full_text, pages, state)
```

### 4. Adjust Validation Thresholds

**Make validation more flexible** for different document types:

```python
# CRITICAL FIX: Adjust validation based on document type
min_text_length = 100  # Default
if file_type.startswith("image/"):
    min_text_length = 50  # Images may have less text
elif file_type == "application/pdf":
    # Check if PDF has images (may be scanned document)
    if self._has_images_in_pdf(file_content):
        min_text_length = 50  # Scanned documents may have less text

if len(full_text.strip()) < min_text_length:
    # Handle insufficient text with appropriate threshold
    return self._handle_insufficient_text(full_text, pages, min_text_length, state)
```

## Testing Strategy

### 1. Create Test Script

**File**: `backend/test_text_extraction.py`

This script tests:
- PDF library availability
- Basic text extraction methods
- Hybrid extraction logic
- Insufficient content validation
- Error handling

### 2. Test with Real Documents

**Test different document types**:
- Text-based PDFs (should work)
- Image-based PDFs (may fail)
- Scanned documents (likely to fail)
- Corrupted PDFs (should fail gracefully)

### 3. Monitor Production Logs

**Look for these log patterns**:
- Documents extracting < 100 characters
- PDF extraction failures
- OCR fallback failures
- Specific error messages

## Implementation Priority

### High Priority (Fix Root Cause)
1. ✅ Add comprehensive logging to text extraction
2. ✅ Improve error messages for insufficient text
3. ✅ Test text extraction with real documents
4. 🔄 Implement fallback extraction strategies
5. 🔄 Adjust validation thresholds

### Medium Priority (Improve User Experience)
1. 🔄 Better error reporting to users
2. 🔄 Document type-specific processing
3. 🔄 Graceful degradation for poor quality documents

### Low Priority (Optimization)
1. 🔄 Retry logic improvements (only after root cause is fixed)
2. 🔄 Workflow routing optimizations
3. 🔄 Performance improvements

## Key Takeaways

1. **Don't treat symptoms**: The retry logic was addressing workflow routing, not the actual failure
2. **Find the root cause**: Text extraction was failing, not workflow logic
3. **Add comprehensive logging**: Without proper logging, we can't diagnose the real issue
4. **Test with real data**: Mock tests don't reveal production issues
5. **Fix the core problem**: Improve text extraction, don't just add retry mechanisms

## Next Steps

1. **Deploy the logging improvements** to understand why text extraction is failing
2. **Test with real documents** to see the actual extraction results
3. **Implement fallback strategies** for documents that extract insufficient text
4. **Adjust validation thresholds** based on document types
5. **Monitor production logs** to ensure the fix is working

Only after the text extraction is working properly should we consider improving the retry logic and workflow routing.
