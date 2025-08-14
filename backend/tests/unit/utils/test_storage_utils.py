"""
Tests for storage utilities
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.utils.storage_utils import ArtifactStorageService


@pytest.mark.asyncio
class TestArtifactStorageService:
    """Test the ArtifactStorageService class."""

    @pytest.fixture
    def storage_service(self):
        """Create a storage service instance."""
        return ArtifactStorageService(bucket_name="artifacts")

    async def test_upload_page_image_jpg_uses_image_jpeg(self, storage_service):
        """Test that JPG uploads use image/jpeg content type."""
        # Mock data
        image_bytes = b"fake_jpg_data"
        content_hmac = "abc123def456"
        page_number = 1

        # Mock the Supabase client
        with patch(
            "app.utils.storage_utils.get_service_supabase_client"
        ) as mock_get_client:
            # Create mock client
            mock_client = Mock()
            mock_storage = Mock()
            mock_bucket = Mock()

            # Setup mock chain
            mock_client.storage.return_value = mock_storage
            mock_storage.from_.return_value = mock_bucket
            mock_bucket.list.return_value = []
            mock_bucket.upload.return_value = {"path": "test/path"}

            mock_get_client.return_value = mock_client

            # Call the method
            uri, sha256 = await storage_service.upload_page_image_jpg(
                image_bytes, content_hmac, page_number
            )

            # Verify the upload was called with correct content type
            mock_bucket.upload.assert_called_once()
            call_args = mock_bucket.upload.call_args

            # Check that content-type is image/jpeg
            assert call_args[1]["file_options"]["content-type"] == "image/jpeg"
            assert call_args[1]["file_options"]["cache-control"] == "86400"

            # Verify the returned values
            assert uri.startswith("supabase://artifacts/")
            assert len(sha256) == 64  # SHA256 hash is 64 characters

    async def test_upload_page_image_jpg_error_handling(self, storage_service):
        """Test error handling in JPG upload."""
        image_bytes = b"fake_jpg_data"
        content_hmac = "abc123def456"
        page_number = 1

        with patch(
            "app.utils.storage_utils.get_service_supabase_client"
        ) as mock_get_client:
            # Setup mock to raise an error
            mock_client = Mock()
            mock_storage = Mock()
            mock_bucket = Mock()

            mock_client.storage.return_value = mock_storage
            mock_storage.from_.return_value = mock_bucket
            mock_bucket.list.side_effect = Exception("Bucket not found")

            mock_get_client.return_value = mock_client

            # Verify that the error is properly raised
            with pytest.raises(RuntimeError) as exc_info:
                await storage_service.upload_page_image_jpg(
                    image_bytes, content_hmac, page_number
                )

            assert "Storage bucket 'artifacts' not found" in str(exc_info.value)

    async def test_upload_diagram_image_content_types(self, storage_service):
        """Test that diagram images use correct content types."""
        image_bytes = b"fake_image_data"
        content_hmac = "abc123def456"
        page_number = 1
        sha256 = "a" * 64

        test_cases = [
            ("png", "image/png"),
            ("jpg", "image/jpeg"),
            ("jpeg", "image/jpeg"),
            ("gif", "image/gif"),
            ("svg", "image/svg+xml"),
            ("webp", "image/webp"),
            ("unknown", "application/octet-stream"),
        ]

        for ext, expected_content_type in test_cases:
            with patch(
                "app.utils.storage_utils.get_service_supabase_client"
            ) as mock_get_client:
                # Create mock client
                mock_client = Mock()
                mock_storage = Mock()
                mock_bucket = Mock()

                # Setup mock chain
                mock_client.storage.return_value = mock_storage
                mock_storage.from_.return_value = mock_bucket
                mock_bucket.list.return_value = []
                mock_bucket.upload.return_value = {"path": "test/path"}

                mock_get_client.return_value = mock_client

                # Call the method
                uri, returned_sha256 = await storage_service.upload_diagram_image(
                    image_bytes, content_hmac, page_number, sha256, ext
                )

                # Verify the upload was called with correct content type
                mock_bucket.upload.assert_called_once()
                call_args = mock_bucket.upload.call_args

                assert (
                    call_args[1]["file_options"]["content-type"]
                    == expected_content_type
                )
                assert uri.endswith(f".{ext}")
                assert returned_sha256 == sha256
