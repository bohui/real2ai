#!/usr/bin/env python3
"""
Test script to verify that circular import issues are resolved
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def test_imports():
    """Test that both services can be imported without circular import issues"""
    try:
        print("Testing DocumentService import...")
        from app.services.document_service import DocumentService

        print("✓ DocumentService imported successfully")

        print("Testing SemanticAnalysisService import...")
        from app.services.semantic_analysis_service import SemanticAnalysisService

        print("✓ SemanticAnalysisService imported successfully")

        print("Testing service initialization...")
        # Test that DocumentService can be instantiated
        doc_service = DocumentService()
        print("✓ DocumentService instantiated successfully")

        # Test that SemanticAnalysisService can be instantiated
        semantic_service = SemanticAnalysisService()
        print("✓ SemanticAnalysisService instantiated successfully")

        print("\n🎉 All tests passed! Circular import issue is resolved.")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
