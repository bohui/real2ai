#!/usr/bin/env python3
"""
Contract Processing Diagnostic Tool

Diagnoses and fixes document processing failures in the contract analysis workflow.
Specifically addresses "Document content is insufficient for analysis" errors.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import sys

# Configure logging for diagnosis
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContractProcessingDiagnostic:
    """Diagnostic tool for contract processing issues"""
    
    def __init__(self):
        self.session_id = None
        self.document_id = None
        self.content_hash = None
        
    async def diagnose_processing_failure(self, session_id: str) -> Dict[str, Any]:
        """
        Diagnose why a contract processing session failed with insufficient content
        
        Args:
            session_id: The session ID from the error logs
            
        Returns:
            Comprehensive diagnostic report with recommendations
        """
        
        self.session_id = session_id
        
        print(f"🔍 Diagnosing Contract Processing Failure")
        print(f"Session ID: {session_id}")
        print("-" * 60)
        
        diagnostic_report = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "issues_found": [],
            "recommendations": [],
            "severity": "unknown",
            "root_cause": "unknown"
        }
        
        try:
            # Step 1: Check database for session and document info
            document_info = await self._check_document_database(session_id)
            diagnostic_report["document_info"] = document_info
            
            if document_info["found"]:
                self.document_id = document_info["document_id"]
                self.content_hash = document_info["content_hash"]
                
                # Step 2: Validate document storage and accessibility
                storage_check = await self._check_document_storage()
                diagnostic_report["storage_check"] = storage_check
                
                # Step 3: Test text extraction methods
                extraction_test = await self._test_text_extraction()
                diagnostic_report["extraction_test"] = extraction_test
                
                # Step 4: Quality validation analysis
                quality_analysis = await self._analyze_quality_validation()
                diagnostic_report["quality_analysis"] = quality_analysis
                
                # Step 5: Generate root cause assessment
                root_cause = self._determine_root_cause(diagnostic_report)
                diagnostic_report["root_cause"] = root_cause["cause"]
                diagnostic_report["severity"] = root_cause["severity"]
                diagnostic_report["recommendations"] = root_cause["recommendations"]
                
            else:
                diagnostic_report["issues_found"].append("Document not found in database")
                diagnostic_report["severity"] = "high"
                diagnostic_report["root_cause"] = "database_missing"
                
        except Exception as e:
            logger.error(f"Diagnostic failed: {str(e)}")
            diagnostic_report["issues_found"].append(f"Diagnostic error: {str(e)}")
            diagnostic_report["severity"] = "critical"
            
        return diagnostic_report
    
    async def _check_document_database(self, session_id: str) -> Dict[str, Any]:
        """Check database for document associated with session"""
        
        print("🔍 Step 1: Checking document database...")
        
        try:
            # Import here to avoid circular dependencies
            from app.core.database import get_database_client
            
            # Get database client
            db_client = await get_database_client()
            
            # Look for document with the content hash (session ID is content hash based)
            result = await db_client.select(
                "documents",
                columns="id, content_hash, original_filename, file_type, processing_status, storage_path, australian_state",
                filters={"content_hash": session_id}
            )
            
            if result.get("data"):
                doc = result["data"][0]
                print(f"✅ Document found: {doc['original_filename']}")
                print(f"   - Document ID: {doc['id']}")
                print(f"   - File type: {doc['file_type']}")
                print(f"   - Processing status: {doc['processing_status']}")
                print(f"   - Australian state: {doc['australian_state']}")
                
                return {
                    "found": True,
                    "document_id": doc["id"],
                    "content_hash": doc["content_hash"],
                    "original_filename": doc["original_filename"],
                    "file_type": doc["file_type"],
                    "processing_status": doc["processing_status"],
                    "storage_path": doc["storage_path"],
                    "australian_state": doc["australian_state"]
                }
            else:
                print("❌ Document not found in database")
                return {"found": False}
                
        except Exception as e:
            logger.error(f"Database check failed: {str(e)}")
            return {"found": False, "error": str(e)}
    
    async def _check_document_storage(self) -> Dict[str, Any]:
        """Check if document exists in storage and is accessible"""
        
        print("\n🔍 Step 2: Checking document storage...")
        
        try:
            from app.services.document_service import DocumentService
            
            doc_service = DocumentService()
            await doc_service.initialize()
            
            # Try to get processed document summary
            summary = await doc_service.get_processed_document_summary(self.document_id)
            
            if summary:
                print(f"✅ Processed document summary found")
                print(f"   - Success: {summary.get('success', False)}")
                print(f"   - Full text length: {len(summary.get('full_text', ''))}")
                print(f"   - Extraction method: {summary.get('extraction_method', 'unknown')}")
                print(f"   - Confidence: {summary.get('extraction_confidence', 0.0)}")
                
                return {
                    "summary_found": True,
                    "success": summary.get("success", False),
                    "full_text_length": len(summary.get("full_text", "")),
                    "extraction_method": summary.get("extraction_method"),
                    "extraction_confidence": summary.get("extraction_confidence", 0.0),
                    "error": summary.get("error")
                }
            else:
                print("❌ No processed document summary found")
                return {"summary_found": False}
                
        except Exception as e:
            logger.error(f"Storage check failed: {str(e)}")
            return {"summary_found": False, "error": str(e)}
    
    async def _test_text_extraction(self) -> Dict[str, Any]:
        """Test text extraction methods on the document"""
        
        print("\n🔍 Step 3: Testing text extraction...")
        
        try:
            from app.services.document_service import DocumentService
            
            doc_service = DocumentService()
            await doc_service.initialize()
            
            # Try to reprocess the document
            result = await doc_service.process_document_by_id(self.document_id)
            
            if result and hasattr(result, 'success'):
                success = result.success
                full_text_length = len(getattr(result, 'full_text', '') or '')
                extraction_method = getattr(result, 'extraction_method', 'unknown')
                error = getattr(result, 'error', None)
                
                print(f"{'✅' if success else '❌'} Text extraction result:")
                print(f"   - Success: {success}")
                print(f"   - Full text length: {full_text_length}")
                print(f"   - Extraction method: {extraction_method}")
                if error:
                    print(f"   - Error: {error}")
                
                return {
                    "success": success,
                    "full_text_length": full_text_length,
                    "extraction_method": extraction_method,
                    "error": error,
                    "meets_minimum": full_text_length >= 50
                }
            else:
                print("❌ Text extraction failed or returned invalid result")
                return {"success": False, "error": "Invalid extraction result"}
                
        except Exception as e:
            logger.error(f"Text extraction test failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_quality_validation(self) -> Dict[str, Any]:
        """Analyze quality validation thresholds and requirements"""
        
        print("\n🔍 Step 4: Analyzing quality validation...")
        
        validation_analysis = {
            "minimum_length_requirement": 50,
            "recommended_length": 100,
            "quality_checks_enabled": True,
            "validation_rules": [
                "Document text must be > 50 characters (hard limit)",
                "Document text should be > 100 characters (workflow limit)",
                "Text quality score should be > 0.3",
                "Must contain contract-related keywords",
                "OCR artifacts should be < 30% of content"
            ]
        }
        
        print("📋 Quality validation requirements:")
        for rule in validation_analysis["validation_rules"]:
            print(f"   - {rule}")
        
        return validation_analysis
    
    def _determine_root_cause(self, diagnostic_report: Dict[str, Any]) -> Dict[str, Any]:
        """Determine root cause based on diagnostic findings"""
        
        print("\n🎯 Step 5: Root cause analysis...")
        
        issues = []
        recommendations = []
        severity = "low"
        cause = "unknown"
        
        # Analyze document info
        if not diagnostic_report.get("document_info", {}).get("found"):
            cause = "document_not_found"
            severity = "high"
            issues.append("Document not found in database")
            recommendations.extend([
                "Verify the session ID corresponds to a valid document",
                "Check if document was properly uploaded and recorded",
                "Investigate database connectivity and user permissions"
            ])
            
        elif diagnostic_report.get("storage_check", {}).get("summary_found"):
            # Document was processed before
            storage_check = diagnostic_report["storage_check"]
            text_length = storage_check.get("full_text_length", 0)
            
            if text_length < 50:
                cause = "insufficient_extracted_content"
                severity = "high"
                issues.append(f"Extracted text too short: {text_length} characters (minimum: 50)")
                recommendations.extend([
                    "Document may be image-based PDF without text layer",
                    "OCR processing may have failed or produced poor results",
                    "Consider manual document review and re-upload",
                    "Check if document is encrypted or protected",
                    "Try alternative text extraction methods"
                ])
            elif not storage_check.get("success", False):
                cause = "extraction_failure"
                severity = "high"
                issues.append("Text extraction reported failure")
                recommendations.extend([
                    "Check document service logs for extraction errors",
                    "Verify document format is supported",
                    "Test document with different extraction methods",
                    "Check storage service connectivity"
                ])
        
        elif diagnostic_report.get("extraction_test", {}).get("success"):
            # Extraction works now but failed before
            cause = "transient_processing_issue"
            severity = "medium"
            issues.append("Document processing appears to work now - may have been transient")
            recommendations.extend([
                "Monitor for recurring issues with similar documents",
                "Consider adding retry logic for processing failures",
                "Review service resource allocation and timeouts"
            ])
        
        else:
            # Still failing extraction
            extraction_test = diagnostic_report.get("extraction_test", {})
            error = extraction_test.get("error", "unknown")
            
            cause = "persistent_extraction_failure"
            severity = "high"
            issues.append(f"Text extraction continues to fail: {error}")
            recommendations.extend([
                "Document format may be unsupported or corrupted",
                "Storage service may be inaccessible",
                "Review document service configuration and dependencies",
                "Manual document inspection may be required"
            ])
        
        print(f"🎯 Root cause: {cause}")
        print(f"🔥 Severity: {severity}")
        print("💡 Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("🔧 Recommendations:")
        for rec in recommendations:
            print(f"   - {rec}")
        
        return {
            "cause": cause,
            "severity": severity,
            "issues": issues,
            "recommendations": recommendations
        }


async def create_processing_fixes() -> str:
    """Create fixes for common document processing issues"""
    
    fixes = """
# Contract Processing Enhancement Fixes

## 1. Enhanced Error Handling and Logging
```python
# Add to contract_workflow.py validate_document_quality_step method
async def validate_document_quality_step(self, state: RealEstateAgentState) -> RealEstateAgentState:
    document_data = state.get("document_data", {})
    document_text = document_data.get("content", "")
    
    # Enhanced logging for diagnosis
    logger.info(f"Document quality validation - text length: {len(document_text)}")
    logger.debug(f"Document text preview (first 200 chars): {document_text[:200]}")
    
    if not document_text or len(document_text.strip()) < 50:
        # Enhanced error with diagnostic info
        error_details = {
            "raw_length": len(document_text) if document_text else 0,
            "stripped_length": len(document_text.strip()) if document_text else 0,
            "document_id": state.get("document_id"),
            "extraction_method": document_data.get("extraction_method", "unknown"),
            "extraction_confidence": document_data.get("extraction_confidence", 0.0)
        }
        
        logger.error(f"Document content insufficient: {error_details}")
        
        return update_state_step(
            state,
            "document_analysis_failed",
            error=f"Document content is insufficient for analysis. Details: {error_details}",
        )
```

## 2. Retry Logic for Processing Failures
```python
# Add retry mechanism for text extraction
async def process_document_with_retry(self, state: RealEstateAgentState, max_retries: int = 2) -> RealEstateAgentState:
    for attempt in range(max_retries + 1):
        try:
            result = await self.process_document(state)
            
            # Check if processing was successful
            if result.get("parsing_status") != ProcessingStatus.FAILED:
                return result
            
            if attempt < max_retries:
                logger.warning(f"Document processing failed, retrying (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(1)  # Brief delay before retry
            
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Document processing exception, retrying: {str(e)}")
                await asyncio.sleep(1)
            else:
                logger.error(f"Document processing failed after {max_retries} retries: {str(e)}")
                raise
    
    return result
```

## 3. Alternative Extraction Methods
```python
# Add fallback extraction methods to DocumentService
async def _extract_text_with_fallbacks(self, file_content: bytes, file_type: str) -> TextExtractionResult:
    extraction_methods = []
    
    if file_type == "pdf":
        extraction_methods = [
            self._extract_pdf_text_pymupdf,
            self._extract_pdf_text_pdfplumber, 
            self._extract_pdf_text_ocr
        ]
    elif file_type in ["png", "jpg", "jpeg"]:
        extraction_methods = [
            self._extract_image_text_tesseract,
            self._extract_image_text_easyocr,
            self._extract_image_text_basic
        ]
    
    for i, method in enumerate(extraction_methods):
        try:
            result = await method(file_content)
            if result.success and len(result.full_text.strip()) >= 50:
                logger.info(f"Text extraction successful with method {i+1}/{len(extraction_methods)}")
                return result
            else:
                logger.warning(f"Method {i+1} produced insufficient content: {len(result.full_text)} chars")
        except Exception as e:
            logger.warning(f"Extraction method {i+1} failed: {str(e)}")
    
    return TextExtractionResult(
        success=False,
        error="All extraction methods failed to produce sufficient content",
        full_text="",
        extraction_method="failed_all_methods"
    )
```

## 4. Enhanced Quality Validation
```python
# Improved quality assessment with specific feedback
def _assess_document_content_quality(self, text: str) -> Dict[str, Any]:
    issues = []
    score = 1.0
    
    # Length checks
    if len(text) < 50:
        issues.append("Text too short (< 50 characters)")
        score -= 0.5
    elif len(text) < 200:
        issues.append("Text may be incomplete (< 200 characters)")
        score -= 0.2
    
    # Word count
    words = text.split()
    if len(words) < 10:
        issues.append("Very few words detected")
        score -= 0.3
    
    # Contract relevance
    contract_keywords = ["contract", "agreement", "party", "parties", "purchase", "sale", "property", "vendor", "purchaser"]
    keyword_count = sum(1 for keyword in contract_keywords if keyword.lower() in text.lower())
    
    if keyword_count < 2:
        issues.append("Missing essential contract keywords")
        score -= 0.3
    
    return {
        "score": max(0.0, score),
        "issues": issues,
        "text_length": len(text),
        "word_count": len(words),
        "keyword_matches": keyword_count
    }
```

## 5. Diagnostic Integration
```python
# Add diagnostic capabilities to workflow
async def diagnose_processing_failure(self, session_id: str) -> Dict[str, Any]:
    diagnostic = ContractProcessingDiagnostic()
    return await diagnostic.diagnose_processing_failure(session_id)
```
"""
    
    return fixes


async def main():
    """Main diagnostic function"""
    
    if len(sys.argv) < 2:
        print("Usage: python contract_processing_diagnostic.py <session_id>")
        print("Example: python contract_processing_diagnostic.py 01cc2e26d7f7327a86d1dbd98b96cb43a88a0674a571f67d89c385f9dd6b4e2d")
        return
    
    session_id = sys.argv[1]
    
    diagnostic = ContractProcessingDiagnostic()
    
    print("🚀 Contract Processing Diagnostic Tool")
    print("=" * 60)
    
    # Run comprehensive diagnostic
    report = await diagnostic.diagnose_processing_failure(session_id)
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    print(f"Session ID: {report['session_id']}")
    print(f"Root Cause: {report['root_cause']}")
    print(f"Severity: {report['severity']}")
    
    if report['issues_found']:
        print(f"\n❌ Issues Found:")
        for issue in report['issues_found']:
            print(f"   - {issue}")
    
    if report['recommendations']:
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   - {rec}")
    
    # Generate fixes
    fixes = await create_processing_fixes()
    
    print(f"\n🔧 Suggested Code Fixes:")
    print(f"See generated fixes in the diagnostic output above")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())