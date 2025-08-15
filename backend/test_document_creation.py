#!/usr/bin/env python3
"""
Test script to verify document creation works correctly after the fix.
"""

import asyncio
import json
from uuid import uuid4
from app.services.repositories.documents_repository import DocumentsRepository
from app.models.supabase_models import Document


async def test_document_creation():
    """Test that document creation works with the fixed upload_metadata and processing_results fields."""

    # Create a test document data
    document_data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),  # Test user ID
        "original_filename": "test_document.pdf",
        "storage_path": "test_user/test_document.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "content_hash": "test_hash_123",
        "processing_status": "uploaded",
        "contract_type": "purchase_agreement",
        "australian_state": "NSW",
        "text_extraction_method": "pending",
        "upload_metadata": {},
        "processing_results": {},
    }

    print("Testing document creation with fixed fields...")
    print(f"Document data: {json.dumps(document_data, indent=2)}")

    try:
        # Create repository instance
        repo = DocumentsRepository()

        # Try to create document
        document = await repo.create_document(document_data)

        print("✅ Document created successfully!")
        print(f"Document ID: {document.id}")
        print(f"Upload metadata type: {type(document.upload_metadata)}")
        print(f"Processing results type: {type(document.processing_results)}")
        print(f"Upload metadata: {document.upload_metadata}")
        print(f"Processing results: {document.processing_results}")

        # Verify the fields are dictionaries, not strings
        assert isinstance(
            document.upload_metadata, dict
        ), f"upload_metadata should be dict, got {type(document.upload_metadata)}"
        assert isinstance(
            document.processing_results, dict
        ), f"processing_results should be dict, got {type(document.processing_results)}"

        print("✅ All assertions passed!")

    except Exception as e:
        print(f"❌ Error creating document: {e}")
        raise


if __name__ == "__main__":
    print("Starting document creation test...")
    asyncio.run(test_document_creation())
    print("Test completed successfully!")
