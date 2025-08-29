#!/usr/bin/env python3
"""
Test script to debug text extraction issues.

This script tests the actual text extraction logic to understand why
documents are extracting insufficient text content (< 100 characters).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_text_extraction():
    """Test the text extraction logic with sample documents."""

    print("🔍 Testing Text Extraction Logic")
    print("=" * 50)

    try:
        # Import the ExtractTextNode
        from app.agents.nodes.step0_document_processing.extract_text_node import (
            ExtractTextNode,
        )
        from app.agents.subflows.document_processing_workflow import (
            DocumentProcessingState,
        )

        # Create a mock workflow state
        class MockWorkflow:
            def __init__(self):
                self.name = "mock_workflow"

        # Create the extract text node
        extract_node = ExtractTextNode(use_llm=False)  # Disable LLM for testing
        await extract_node.initialize()

        # Test 1: Test with a sample PDF file if available
        test_pdf_path = backend_dir / "test_files" / "sample_contract.pdf"

        if test_pdf_path.exists():
            print(f"\n📄 Testing with sample PDF: {test_pdf_path}")

            # Read the PDF file
            with open(test_pdf_path, "rb") as f:
                pdf_content = f.read()

            print(
                f"File size: {len(pdf_content)} bytes ({len(pdf_content) / 1024:.2f} KB)"
            )

            # Test basic PDF extraction
            text, method = await extract_node._extract_pdf_text_basic(pdf_content)
            print(f"Basic extraction method: {method}")
            print(f"Extracted text length: {len(text)} characters")
            print(f"Extracted text sample: {text[:200]}...")

            # Test hybrid PDF extraction
            mock_state = DocumentProcessingState(
                document_id="test_doc_123",
                content_hmac="test_hash",
                australian_state="NSW",
                contract_type="purchase_agreement",
                document_type="contract",
            )

            result = await extract_node._extract_pdf_text_hybrid(
                pdf_content, mock_state
            )
            print(f"\nHybrid extraction result:")
            print(f"  Success: {result.success}")
            print(f"  Total pages: {result.total_pages}")
            print(f"  Full text length: {len(result.full_text)} characters")
            print(f"  Extraction methods: {result.extraction_methods}")
            print(f"  Overall confidence: {result.overall_confidence}")

            if not result.success:
                print(f"  Error: {result.error}")

            # Show page details
            for i, page in enumerate(result.pages):
                print(
                    f"  Page {i+1}: {len(page.text_content)} chars, method: {page.extraction_method}"
                )

        else:
            print(f"\n⚠️  No test PDF found at {test_pdf_path}")
            print("Create a test PDF file to test extraction logic")

        # Test 2: Test with minimal text to trigger the insufficient content error
        print(f"\n🧪 Testing insufficient content validation")

        # Create a mock state with minimal text
        mock_state = DocumentProcessingState(
            document_id="test_minimal_123",
            content_hmac="test_hash_minimal",
            australian_state="NSW",
            contract_type="purchase_agreement",
            document_type="contract",
        )

        # Create a TextExtractionResult with minimal text
        from app.schema.document import TextExtractionResult, PageExtraction

        minimal_result = TextExtractionResult(
            success=True,
            full_text="Short",  # Only 5 characters
            pages=[
                PageExtraction(
                    page_number=1,
                    text_content="Short",
                    text_length=5,
                    word_count=1,
                    extraction_method="test",
                    confidence=0.8,
                    content_analysis=None,
                )
            ],
            total_pages=1,
            extraction_methods=["test"],
            total_word_count=1,
            overall_confidence=0.8,
        )

        # Test the validation logic
        print(
            f"Minimal text: '{minimal_result.full_text}' ({len(minimal_result.full_text)} chars)"
        )

        if len(minimal_result.full_text.strip()) < 100:
            print("✅ Correctly detected insufficient content")
        else:
            print("❌ Failed to detect insufficient content")

        return True

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_pdf_libraries():
    """Test if PDF libraries are available and working."""

    print("\n🔧 Testing PDF Libraries")
    print("=" * 30)

    # Test PyMuPDF
    try:
        import pymupdf

        print(f"✅ PyMuPDF available: {pymupdf.version}")
    except ImportError:
        print("❌ PyMuPDF not available")

    # Test pypdf
    try:
        import pypdf

        print(f"✅ pypdf available: {pypdf.__version__}")
    except ImportError:
        print("❌ pypdf not available")

    # Test PIL for image processing
    try:
        from PIL import Image

        print(f"✅ PIL available: {Image.__version__}")
    except ImportError:
        print("❌ PIL not available")

    # Test pytesseract
    try:
        import pytesseract

        print(f"✅ pytesseract available")
        # Try to get version
        try:
            version = pytesseract.get_tesseract_version()
            print(f"   Tesseract version: {version}")
        except:
            print("   Tesseract version: unknown")
    except ImportError:
        print("❌ pytesseract not available")


async def main():
    """Main test function."""
    print("🚀 Starting Text Extraction Debug Tests")
    print("=" * 60)

    # Test PDF libraries first
    await test_pdf_libraries()

    # Test text extraction logic
    success = await test_text_extraction()

    if success:
        print("\n🎉 Text extraction tests completed successfully!")
        print("\n📋 Next steps:")
        print("1. Check the logs above for any extraction issues")
        print("2. If using a test PDF, verify the extracted text length")
        print("3. Look for any error messages or warnings")
        print("4. Check if the document has extractable text or is image-based")
    else:
        print("\n💥 Some tests failed. Check the error messages above.")

    return success


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())
