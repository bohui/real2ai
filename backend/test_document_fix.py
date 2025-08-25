#!/usr/bin/env python3
"""
Test script to verify that the document creation and retrieval fix works correctly.
"""

import asyncio
import json
from uuid import uuid4
from app.services.repositories.documents_repository import DocumentsRepository


async def test_document_creation_and_retrieval():
    """Test that document creation and retrieval works with the fixed JSON handling."""

    print("Testing document creation and retrieval with fixed JSON handling...")

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
        "upload_metadata": {"test_key": "test_value"},
        "processing_results": {"status": "pending"},
    }

    print(f"Document data: {json.dumps(document_data, indent=2)}")

    try:
        # Create repository instance
        repo = DocumentsRepository()

        # Try to create document
        print("Creating document...")
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

        # Test retrieval
        print("\nTesting document retrieval...")
        retrieved_doc = await repo.get_document(document.id)

        if retrieved_doc:
            print("✅ Document retrieved successfully!")
            print(
                f"Retrieved upload metadata type: {type(retrieved_doc.upload_metadata)}"
            )
            print(
                f"Retrieved processing results type: {type(retrieved_doc.processing_results)}"
            )
            print(f"Retrieved upload metadata: {retrieved_doc.upload_metadata}")
            print(f"Retrieved processing results: {retrieved_doc.processing_results}")

            # Verify retrieved fields are also dictionaries
            assert isinstance(
                retrieved_doc.upload_metadata, dict
            ), f"Retrieved upload_metadata should be dict, got {type(retrieved_doc.upload_metadata)}"
            assert isinstance(
                retrieved_doc.processing_results, dict
            ), f"Retrieved processing_results should be dict, got {type(retrieved_doc.processing_results)}"
        else:
            print("❌ Document retrieval failed!")
            return

        print("✅ All assertions passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("Starting document creation and retrieval test...")
    asyncio.run(test_document_creation_and_retrieval())
    print("Test completed successfully!")
