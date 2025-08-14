"""
Storage utilities for document processing artifacts
"""

import hashlib
import io
from typing import Tuple
from uuid import uuid4

from app.clients.factory import get_service_supabase_client


class ArtifactStorageService:
    """Service for storing and retrieving text artifacts from object storage"""
    
    def __init__(self, bucket_name: str = "documents"):
        """Initialize storage service with configurable bucket name.
        
        Args:
            bucket_name: Name of the storage bucket to use (default: 'documents')
        """
        self.bucket_name = bucket_name
    
    async def upload_text_blob(self, content: str, content_hmac: str) -> Tuple[str, str]:
        """
        Upload text content to object storage and return URI and SHA256.
        
        Args:
            content: Text content to upload
            content_hmac: Content HMAC for path organization
            
        Returns:
            Tuple of (uri, sha256_hash)
        """
        # Convert to bytes
        content_bytes = content.encode('utf-8')
        
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # Generate storage path: artifacts/text/{hmac_prefix}/{uuid}.txt
        hmac_prefix = content_hmac[:8]  # Use first 8 chars for directory structure
        file_uuid = str(uuid4())
        storage_path = f"artifacts/text/{hmac_prefix}/{file_uuid}.txt"
        
        # Upload to Supabase Storage
        client = await get_service_supabase_client()
        
        try:
            # Verify bucket exists before upload
            try:
                storage_client = client.storage().from_(self.bucket_name)
                # Try to list bucket contents to verify access
                storage_client.list()
            except Exception as bucket_error:
                raise RuntimeError(
                    f"Storage bucket '{self.bucket_name}' not found or not accessible: {bucket_error}. "
                    f"Please ensure the bucket exists in Supabase storage."
                )
            
            # Upload file content
            result = storage_client.upload(
                path=storage_path,
                file=content_bytes,
                file_options={
                    "content-type": "text/plain; charset=utf-8",
                    "cache-control": "3600"  # Cache for 1 hour
                }
            )
            
            if not result:
                raise RuntimeError(f"Failed to upload to storage: {storage_path}")
                
            # Return public URL and hash
            uri = f"supabase://{self.bucket_name}/{storage_path}"
            return uri, sha256_hash
            
        except Exception as e:
            # Provide more helpful error context
            error_msg = f"Storage upload failed for {storage_path}: {e}"
            if "bucket not found" in str(e).lower():
                error_msg += f" (Verify '{self.bucket_name}' bucket exists in Supabase)"
            raise RuntimeError(error_msg)
    
    async def download_text_blob(self, uri: str) -> str:
        """
        Download text content from object storage.
        
        Args:
            uri: Storage URI (e.g., supabase://bucket/path)
            
        Returns:
            Text content as string
            
        Raises:
            ValueError: If URI format is invalid
            RuntimeError: If download fails
        """
        if not uri.startswith("supabase://"):
            raise ValueError(f"Invalid URI format: {uri}")
        
        # Extract bucket and path from URI
        parts = uri[11:].split("/", 1)  # Remove "supabase://"
        if len(parts) != 2:
            raise ValueError(f"Invalid URI structure: {uri}")
        
        bucket, path = parts
        
        client = await get_service_supabase_client()
        
        try:
            # Download file content
            file_data = await client.download_file(bucket=bucket, path=path)
            
            if not file_data:
                raise RuntimeError(f"No data returned from storage: {uri}")
            
            # Convert bytes to string
            if isinstance(file_data, bytes):
                return file_data.decode('utf-8')
            else:
                return str(file_data)
                
        except Exception as e:
            raise RuntimeError(f"Storage download failed for {uri}: {e}")
    
    async def verify_blob_integrity(self, uri: str, expected_sha256: str) -> bool:
        """
        Verify the integrity of a stored blob by comparing SHA256.
        
        Args:
            uri: Storage URI
            expected_sha256: Expected SHA256 hash
            
        Returns:
            True if integrity check passes
        """
        try:
            content = await self.download_text_blob(uri)
            actual_sha256 = hashlib.sha256(content.encode('utf-8')).hexdigest()
            return actual_sha256 == expected_sha256
        except Exception:
            return False
    
    async def upload_page_text(self, page_text: str, content_hmac: str, page_number: int) -> Tuple[str, str]:
        """
        Upload page-specific text content.
        
        Args:
            page_text: Page text content
            content_hmac: Document content HMAC
            page_number: Page number (1-based)
            
        Returns:
            Tuple of (uri, sha256_hash)
        """
        # Convert to bytes
        content_bytes = page_text.encode('utf-8')
        
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # Generate storage path: artifacts/pages/{hmac_prefix}/page_{num}_{uuid}.txt
        hmac_prefix = content_hmac[:8]
        file_uuid = str(uuid4())
        storage_path = f"artifacts/pages/{hmac_prefix}/page_{page_number}_{file_uuid}.txt"
        
        client = await get_service_supabase_client()
        
        try:
            result = client.storage().from_(self.bucket_name).upload(
                path=storage_path,
                file=content_bytes,
                file_options={
                    "content-type": "text/plain; charset=utf-8",
                    "cache-control": "3600"
                }
            )
            
            if not result:
                raise RuntimeError(f"Failed to upload page text: {storage_path}")
            
            uri = f"supabase://{self.bucket_name}/{storage_path}"
            return uri, sha256_hash
            
        except Exception as e:
            raise RuntimeError(f"Page text upload failed for {storage_path}: {e}")
    
    async def upload_page_markdown(
        self, 
        markdown_bytes: bytes, 
        content_hmac: str, 
        page_number: int
    ) -> Tuple[str, str]:
        """
        Upload markdown content for external OCR processing.
        
        Args:
            markdown_bytes: Markdown content as bytes
            content_hmac: Document content HMAC
            page_number: Page number (0-based from OCR)
            
        Returns:
            Tuple of (uri, sha256_hash)
        """
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256(markdown_bytes).hexdigest()
        
        # Generate storage path: artifacts/{hmac}/pages/p{page}/content.md
        hmac_prefix = content_hmac[:8]
        storage_path = f"artifacts/{hmac_prefix}/pages/p{page_number}/content.md"
        
        client = await get_service_supabase_client()
        
        try:
            # Verify bucket exists before upload
            try:
                storage_client = client.storage().from_(self.bucket_name)
                storage_client.list()
            except Exception as bucket_error:
                raise RuntimeError(
                    f"Storage bucket '{self.bucket_name}' not found or not accessible: {bucket_error}. "
                    f"Please ensure the bucket exists in Supabase storage."
                )
            
            result = storage_client.upload(
                path=storage_path,
                file=markdown_bytes,
                file_options={
                    "content-type": "text/markdown; charset=utf-8",
                    "cache-control": "3600"
                }
            )
            
            if not result:
                raise RuntimeError(f"Failed to upload markdown: {storage_path}")
            
            uri = f"supabase://{self.bucket_name}/{storage_path}"
            return uri, sha256_hash
            
        except Exception as e:
            raise RuntimeError(f"Markdown upload failed for {storage_path}: {e}")
    
    async def upload_page_image_jpg(
        self,
        image_bytes: bytes,
        content_hmac: str,
        page_number: int
    ) -> Tuple[str, str]:
        """
        Upload JPG image for external OCR processing.
        
        Args:
            image_bytes: JPG image as bytes
            content_hmac: Document content HMAC
            page_number: Page number (0-based from OCR)
            
        Returns:
            Tuple of (uri, sha256_hash)
        """
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()
        
        # Generate storage path: artifacts/{hmac}/pages/p{page}/image.jpg
        hmac_prefix = content_hmac[:8]
        storage_path = f"artifacts/{hmac_prefix}/pages/p{page_number}/image.jpg"
        
        client = await get_service_supabase_client()
        
        try:
            # Verify bucket exists before upload
            try:
                storage_client = client.storage().from_(self.bucket_name)
                storage_client.list()
            except Exception as bucket_error:
                raise RuntimeError(
                    f"Storage bucket '{self.bucket_name}' not found or not accessible: {bucket_error}. "
                    f"Please ensure the bucket exists in Supabase storage."
                )
            
            result = storage_client.upload(
                path=storage_path,
                file=image_bytes,
                file_options={
                    "content-type": "image/jpeg",
                    "cache-control": "86400"  # Cache for 24 hours
                }
            )
            
            if not result:
                raise RuntimeError(f"Failed to upload JPG image: {storage_path}")
            
            uri = f"supabase://{self.bucket_name}/{storage_path}"
            return uri, sha256_hash
            
        except Exception as e:
            raise RuntimeError(f"JPG upload failed for {storage_path}: {e}")
    
    async def upload_page_json(
        self,
        json_bytes: bytes,
        content_hmac: str,
        page_number: int
    ) -> Tuple[str, str]:
        """
        Upload JSON metadata for external OCR processing.
        
        Args:
            json_bytes: JSON content as bytes
            content_hmac: Document content HMAC
            page_number: Page number (0-based from OCR)
            
        Returns:
            Tuple of (uri, sha256_hash)
        """
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256(json_bytes).hexdigest()
        
        # Generate storage path: artifacts/{hmac}/pages/p{page}/metadata.json
        hmac_prefix = content_hmac[:8]
        storage_path = f"artifacts/{hmac_prefix}/pages/p{page_number}/metadata.json"
        
        client = await get_service_supabase_client()
        
        try:
            # Verify bucket exists before upload
            try:
                storage_client = client.storage().from_(self.bucket_name)
                storage_client.list()
            except Exception as bucket_error:
                raise RuntimeError(
                    f"Storage bucket '{self.bucket_name}' not found or not accessible: {bucket_error}. "
                    f"Please ensure the bucket exists in Supabase storage."
                )
            
            result = storage_client.upload(
                path=storage_path,
                file=json_bytes,
                file_options={
                    "content-type": "application/json; charset=utf-8",
                    "cache-control": "3600"
                }
            )
            
            if not result:
                raise RuntimeError(f"Failed to upload JSON metadata: {storage_path}")
            
            uri = f"supabase://{self.bucket_name}/{storage_path}"
            return uri, sha256_hash
            
        except Exception as e:
            raise RuntimeError(f"JSON upload failed for {storage_path}: {e}")
    
    async def upload_diagram_image(
        self,
        image_bytes: bytes,
        content_hmac: str,
        page_number: int,
        sha256: str,
        ext: str
    ) -> Tuple[str, str]:
        """
        Upload extracted diagram image.
        
        Args:
            image_bytes: Image bytes
            content_hmac: Document content HMAC
            page_number: Page number the diagram was found on
            sha256: SHA256 hash of the image
            ext: File extension (png, jpg, etc.)
            
        Returns:
            Tuple of (uri, sha256_hash)
        """
        # Generate storage path: diagrams/{hmac}/p{page}/{sha256}.{ext}
        hmac_prefix = content_hmac[:8]
        storage_path = f"diagrams/{hmac_prefix}/p{page_number}/{sha256}.{ext}"
        
        # Determine content type
        content_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(ext.lower(), 'application/octet-stream')
        
        client = await get_service_supabase_client()
        
        try:
            # Verify bucket exists before upload
            try:
                storage_client = client.storage().from_(self.bucket_name)
                storage_client.list()
            except Exception as bucket_error:
                raise RuntimeError(
                    f"Storage bucket '{self.bucket_name}' not found or not accessible: {bucket_error}. "
                    f"Please ensure the bucket exists in Supabase storage."
                )
            
            result = storage_client.upload(
                path=storage_path,
                file=image_bytes,
                file_options={
                    "content-type": content_type,
                    "cache-control": "86400"  # Cache for 24 hours
                }
            )
            
            if not result:
                raise RuntimeError(f"Failed to upload diagram image: {storage_path}")
            
            uri = f"supabase://{self.bucket_name}/{storage_path}"
            return uri, sha256
            
        except Exception as e:
            raise RuntimeError(f"Diagram upload failed for {storage_path}: {e}")
    
    async def cleanup_orphaned_blobs(self, active_uris: list[str]) -> int:
        """
        Clean up storage blobs that are no longer referenced.
        
        Args:
            active_uris: List of URIs that are still in use
            
        Returns:
            Number of blobs cleaned up
        """
        # This would implement cleanup logic to remove unused blobs
        # For now, return 0 as a placeholder
        return 0