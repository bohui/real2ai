#!/usr/bin/env python3
"""
Targeted fixes for contract processing "insufficient content" errors

Based on troubleshooting analysis, this implements specific fixes for the
"Document content is insufficient for analysis" error.
"""

import logging

logger = logging.getLogger(__name__)


def apply_contract_processing_fixes():
    """Apply targeted fixes to resolve document processing issues"""
    
    print("🔧 Applying Contract Processing Fixes")
    print("=" * 50)
    
    fixes_applied = []
    
    # Fix 1: Enhanced logging and diagnostic information
    fix1_code = '''
    # ENHANCED ERROR LOGGING FIX
    # Add to contract_workflow.py validate_document_quality_step method (around line 862)
    
    if not document_text or len(document_text.strip()) < 50:
        # Enhanced diagnostic logging
        extraction_method = document_data.get("extraction_method", "unknown")
        extraction_confidence = document_data.get("extraction_confidence", 0.0)
        document_id = state.get("document_id", "unknown")
        
        diagnostic_info = {
            "raw_length": len(document_text) if document_text else 0,
            "stripped_length": len(document_text.strip()) if document_text else 0,
            "document_id": document_id,
            "extraction_method": extraction_method,
            "extraction_confidence": extraction_confidence,
            "session_id": state.get("content_hash", "unknown")
        }
        
        logger.error(f"Document content insufficient - diagnostic info: {diagnostic_info}")
        
        # Enhanced error message with diagnostic data
        error_message = (
            f"Document content is insufficient for analysis. "
            f"Extracted {diagnostic_info['stripped_length']} characters "
            f"(minimum required: 50). "
            f"Extraction method: {extraction_method}, "
            f"confidence: {extraction_confidence:.2f}"
        )
        
        return update_state_step(
            state,
            "document_analysis_failed",
            error=error_message,
        )
    '''
    
    fixes_applied.append("Enhanced error logging with diagnostic information")
    
    # Fix 2: Retry logic for transient failures
    fix2_code = '''
    # RETRY LOGIC FIX
    # Add to contract_workflow.py as new method
    
    async def process_document_with_retry(self, state: RealEstateAgentState, max_retries: int = 2) -> RealEstateAgentState:
        """Process document with retry logic for transient failures"""
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Document processing attempt {attempt + 1}/{max_retries + 1}")
                
                result = await self.process_document(state)
                
                # Check if processing was successful
                document_data = result.get("document_data", {})
                document_text = document_data.get("content", "")
                
                if document_text and len(document_text.strip()) >= 50:
                    logger.info(f"Document processing successful on attempt {attempt + 1}")
                    return result
                
                if attempt < max_retries:
                    logger.warning(f"Document processing produced insufficient content, retrying...")
                    await asyncio.sleep(2)  # Brief delay before retry
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Document processing exception, retrying: {str(e)}")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Document processing failed after {max_retries} retries: {str(e)}")
                    raise
        
        return result
    '''
    
    fixes_applied.append("Retry logic for transient processing failures")
    
    # Fix 3: Alternative content validation thresholds
    fix3_code = '''
    # FLEXIBLE VALIDATION THRESHOLDS FIX
    # Modify contract_workflow.py validate_document_quality_step method
    
    # Dynamic threshold based on document type and extraction method
    def get_minimum_content_threshold(self, document_data: Dict[str, Any]) -> int:
        """Get minimum content threshold based on extraction context"""
        
        extraction_method = document_data.get("extraction_method", "unknown")
        extraction_confidence = document_data.get("extraction_confidence", 0.0)
        file_type = document_data.get("file_type", "unknown")
        
        # OCR-based extractions may produce fragmented but valid content
        if "ocr" in extraction_method.lower():
            return 30  # Lower threshold for OCR
        
        # Image-based documents
        if file_type in ["png", "jpg", "jpeg"]:
            return 25  # Even lower for pure images
        
        # High-confidence extractions can have lower thresholds
        if extraction_confidence > 0.8:
            return 35
        
        # Default threshold
        return 50
    
    # Then in validation:
    min_threshold = self.get_minimum_content_threshold(document_data)
    
    if not document_text or len(document_text.strip()) < min_threshold:
        # Include threshold information in error
        error_message = (
            f"Document content is insufficient for analysis. "
            f"Extracted {len(document_text.strip()) if document_text else 0} characters "
            f"(minimum required: {min_threshold} for {document_data.get('extraction_method', 'unknown')})"
        )
    '''
    
    fixes_applied.append("Dynamic content validation thresholds based on extraction method")
    
    # Fix 4: Content quality assessment
    fix4_code = '''
    # ENHANCED CONTENT QUALITY ASSESSMENT
    # Add to contract_workflow.py
    
    def assess_content_quality_detailed(self, text: str, extraction_method: str) -> Dict[str, Any]:
        """Detailed content quality assessment with actionable feedback"""
        
        if not text:
            return {
                "score": 0.0,
                "issues": ["No text content extracted"],
                "recommendations": ["Check document format and integrity", "Verify document is not encrypted"]
            }
        
        issues = []
        recommendations = []
        score = 1.0
        
        # Length analysis
        text_length = len(text.strip())
        word_count = len(text.split())
        
        if text_length < 50:
            issues.append(f"Text too short: {text_length} characters")
            recommendations.append("Document may be image-based or corrupted")
            score -= 0.5
        
        if word_count < 10:
            issues.append(f"Very few words: {word_count}")
            recommendations.append("OCR may have failed, try manual review")
            score -= 0.3
        
        # Character analysis for OCR artifacts
        single_char_words = sum(1 for word in text.split() if len(word) == 1)
        if word_count > 0 and (single_char_words / word_count) > 0.3:
            issues.append("High ratio of single characters (possible OCR artifacts)")
            recommendations.append("Document scan quality may be poor")
            score -= 0.3
        
        # Contract relevance
        contract_keywords = ["contract", "agreement", "party", "purchase", "sale", "property", "vendor", "purchaser"]
        keyword_matches = sum(1 for keyword in contract_keywords if keyword.lower() in text.lower())
        
        if keyword_matches < 2:
            issues.append("Missing essential contract keywords")
            recommendations.append("Document may not be a contract or extraction failed")
            score -= 0.2
        
        return {
            "score": max(0.0, score),
            "issues": issues,
            "recommendations": recommendations,
            "metrics": {
                "text_length": text_length,
                "word_count": word_count,
                "keyword_matches": keyword_matches,
                "single_char_ratio": single_char_words / word_count if word_count > 0 else 0
            }
        }
    '''
    
    fixes_applied.append("Enhanced content quality assessment with specific recommendations")
    
    # Print summary
    print("✅ Fixes prepared:")
    for i, fix in enumerate(fixes_applied, 1):
        print(f"{i}. {fix}")
    
    print("\n💡 Integration Instructions:")
    print("1. Apply enhanced error logging to validate_document_quality_step method")
    print("2. Add retry logic method to ContractAnalysisWorkflow class")
    print("3. Implement dynamic validation thresholds")
    print("4. Add detailed content quality assessment")
    print("5. Test with problematic documents to verify fixes")
    
    print("\n🎯 Expected Impact:")
    print("- Better diagnostic information for debugging failures")
    print("- Automatic recovery from transient processing issues")
    print("- More appropriate validation for different document types")
    print("- Actionable feedback for content quality issues")
    
    return fixes_applied


def create_monitoring_improvements():
    """Create monitoring improvements to prevent future issues"""
    
    monitoring_code = '''
    # ENHANCED MONITORING FOR DOCUMENT PROCESSING
    
    import time
    from datetime import datetime
    
    class DocumentProcessingMonitor:
        """Enhanced monitoring for document processing pipeline"""
        
        def __init__(self):
            self.processing_metrics = {
                "total_documents": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "insufficient_content": 0,
                "extraction_methods": {},
                "average_processing_time": 0.0
            }
        
        def log_processing_attempt(self, document_id: str, extraction_method: str):
            """Log start of document processing"""
            self.processing_metrics["total_documents"] += 1
            
            if extraction_method not in self.processing_metrics["extraction_methods"]:
                self.processing_metrics["extraction_methods"][extraction_method] = {"count": 0, "success": 0}
            
            self.processing_metrics["extraction_methods"][extraction_method]["count"] += 1
            
            logger.info(f"Document processing started: {document_id} using {extraction_method}")
        
        def log_processing_result(self, document_id: str, success: bool, text_length: int, 
                                 extraction_method: str, processing_time: float):
            """Log result of document processing"""
            
            if success and text_length >= 50:
                self.processing_metrics["successful_extractions"] += 1
                self.processing_metrics["extraction_methods"][extraction_method]["success"] += 1
                logger.info(f"Document processing successful: {document_id} ({text_length} chars)")
            elif text_length < 50:
                self.processing_metrics["insufficient_content"] += 1
                logger.warning(f"Document processing insufficient content: {document_id} ({text_length} chars)")
            else:
                self.processing_metrics["failed_extractions"] += 1
                logger.error(f"Document processing failed: {document_id}")
            
            # Update average processing time
            total_docs = self.processing_metrics["total_documents"]
            current_avg = self.processing_metrics["average_processing_time"]
            self.processing_metrics["average_processing_time"] = (
                (current_avg * (total_docs - 1) + processing_time) / total_docs
            )
        
        def get_health_report(self) -> Dict[str, Any]:
            """Get health report for document processing"""
            
            total = self.processing_metrics["total_documents"]
            if total == 0:
                return {"status": "no_data", "message": "No documents processed"}
            
            success_rate = (self.processing_metrics["successful_extractions"] / total) * 100
            insufficient_rate = (self.processing_metrics["insufficient_content"] / total) * 100
            
            status = "healthy" if success_rate >= 80 else "degraded" if success_rate >= 60 else "unhealthy"
            
            return {
                "status": status,
                "success_rate": success_rate,
                "insufficient_content_rate": insufficient_rate,
                "total_processed": total,
                "extraction_methods": self.processing_metrics["extraction_methods"],
                "average_processing_time": self.processing_metrics["average_processing_time"]
            }
    '''
    
    return monitoring_code


if __name__ == "__main__":
    # Apply the fixes
    fixes = apply_contract_processing_fixes()
    
    print(f"\n🔍 Root Cause Summary:")
    print("The 'Document content is insufficient for analysis' error occurs when:")
    print("1. Text extraction produces < 50 characters of readable content")
    print("2. OCR processing fails on image-based PDFs")
    print("3. Document processing service returns success but empty content")
    print("4. Transient failures in text extraction methods")
    
    print(f"\n🎯 Immediate Actions:")
    print("1. Implement enhanced error logging for better diagnostics")
    print("2. Add retry logic for transient processing failures") 
    print("3. Use dynamic thresholds based on extraction method")
    print("4. Monitor document processing health metrics")
    
    print(f"\n✅ Implementation Priority:")
    print("HIGH: Enhanced error logging (immediate debugging benefit)")
    print("HIGH: Dynamic validation thresholds (reduces false negatives)")
    print("MEDIUM: Retry logic (handles transient issues)")
    print("MEDIUM: Quality assessment improvements (better user feedback)")
    
    monitoring_code = create_monitoring_improvements()
    print(f"\n📊 Monitoring code generated for health tracking")