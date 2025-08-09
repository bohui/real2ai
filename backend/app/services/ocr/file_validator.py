"""
File validation for OCR processing.
"""

from typing import Set
from app.clients.base.exceptions import ClientValidationError

# Constants
BYTES_PER_MB = 1024 * 1024


class FileValidator:
    """Validates files for OCR processing."""
    
    def __init__(self, max_file_size: int, supported_formats: Set[str]):
        self.max_file_size = max_file_size
        self.supported_formats = supported_formats
    
    def validate_file(self, content: bytes, content_type: str) -> None:
        """Validate file for OCR processing."""
        # Check file size
        if len(content) > self.max_file_size:
            raise ClientValidationError(
                f"File too large for OCR. Maximum size: {self.max_file_size / BYTES_PER_MB}MB",
                client_name="OCRService",
            )

        # Check file format
        file_extension = (
            content_type.lower().replace("image/", "").replace("application/", "")
        )
        if file_extension not in self.supported_formats:
            raise ClientValidationError(
                f"Unsupported file format for OCR: {content_type}. Supported: {self.supported_formats}",
                client_name="OCRService",
            )