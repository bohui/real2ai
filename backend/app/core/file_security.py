"""File security validation module for Real2.AI platform.

This module provides comprehensive security validation for file uploads including:
- MIME type validation
- File magic bytes verification
- Content scanning for malicious patterns
- Filename sanitization
- Size limit enforcement
- Logging of security events
"""

import logging
import re
import hashlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from fastapi import UploadFile
import structlog

# Optional magic import with fallback
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

# Optional security config import with fallback
try:
    from app.core.security_config import (
        security_config,
        file_security_policy,
        security_event_logger,
    )

    SECURITY_CONFIG_AVAILABLE = True
except ImportError:
    SECURITY_CONFIG_AVAILABLE = False
    security_config = None
    file_security_policy = None
    security_event_logger = None

# Configure logger
logger = structlog.get_logger(__name__)
security_logger = logging.getLogger("security")


class FileSecurityConfig:
    """Configuration for file security validation."""

    # MIME types allowed for upload (actual content validation)
    ALLOWED_MIME_TYPES = {
        # PDF documents
        "application/pdf",
        # Microsoft Word
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        # Images
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/tiff",
        "image/tif",
    }

    # File extensions mapped to expected MIME types
    EXTENSION_MIME_MAP = {
        "pdf": {"application/pdf"},
        "doc": {"application/msword"},
        "docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        "jpg": {"image/jpeg", "image/jpg"},
        "jpeg": {"image/jpeg", "image/jpg"},
        "png": {"image/png"},
        "webp": {"image/webp"},
        "gif": {"image/gif"},
        "bmp": {"image/bmp"},
        "tiff": {"image/tiff"},
        "tif": {"image/tiff"},
    }

    # Magic bytes for file type verification
    MAGIC_BYTES = {
        "pdf": [b"%PDF-"],
        "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE compound document
        "docx": [b"PK\x03\x04"],  # ZIP archive (DOCX is ZIP-based)
        "jpg": [b"\xff\xd8\xff"],
        "jpeg": [b"\xff\xd8\xff"],
        "png": [b"\x89PNG\r\n\x1a\n"],
        "webp": [b"RIFF", b"WEBP"],
        "gif": [b"GIF87a", b"GIF89a"],
        "bmp": [b"BM"],
        "tiff": [b"II*\x00", b"MM\x00*"],
        "tif": [b"II*\x00", b"MM\x00*"],
    }

    # Suspicious patterns that could indicate malicious content
    MALICIOUS_PATTERNS = [
        # JavaScript patterns
        b"<script",
        b"javascript:",
        b"vbscript:",
        # Executable patterns
        b"MZ\x90\x00",  # PE executable header
        b"\x7fELF",  # ELF executable header
        # Macro patterns in Office docs
        b"VBA",
        b"VBAPROJECT",
        # PHP patterns
        b"<?php",
        # Shell patterns
        b"#!/bin/sh",
        b"#!/bin/bash",
        # HTML injection patterns
        b"<iframe",
        b"<embed",
        b"<object",
        # Base64 encoded suspicious content (common in malware)
        b"TVqQAAMAAAAE",  # MZ header in base64
        b"f0VMRgIBAQAAAAA",  # ELF header in base64
    ]

    # Maximum file sizes by type (in bytes)
    MAX_FILE_SIZES = {
        "pdf": 50 * 1024 * 1024,  # 50MB
        "doc": 25 * 1024 * 1024,  # 25MB
        "docx": 25 * 1024 * 1024,  # 25MB
        "jpg": 10 * 1024 * 1024,  # 10MB
        "jpeg": 10 * 1024 * 1024,  # 10MB
        "png": 10 * 1024 * 1024,  # 10MB
        "webp": 10 * 1024 * 1024,  # 10MB
        "gif": 5 * 1024 * 1024,  # 5MB
        "bmp": 15 * 1024 * 1024,  # 15MB
        "tiff": 20 * 1024 * 1024,  # 20MB
        "tif": 20 * 1024 * 1024,  # 20MB
    }


class SecurityValidationResult:
    """Result of security validation."""

    def __init__(
        self,
        is_valid: bool,
        error_message: Optional[str] = None,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.warnings = warnings or []
        self.metadata = metadata or {}


class FileSecurityValidator:
    """Comprehensive file security validator."""

    def __init__(self):
        self.config = FileSecurityConfig()
        self.security_policy = file_security_policy
        self.event_logger = security_event_logger

    async def validate_file_security(
        self,
        file: UploadFile,
        max_size_override: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> SecurityValidationResult:
        """
        Perform comprehensive security validation on uploaded file.

        Args:
            file: The uploaded file
            max_size_override: Override default max size for file type
            user_id: User ID for logging purposes

        Returns:
            SecurityValidationResult with validation results
        """

        try:
            # Read file content once for all validations
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer for further processing

            # Extract basic file information
            filename = file.filename or "unknown"
            content_type = file.content_type or ""
            file_size = len(file_content)

            # Log security validation attempt
            self.event_logger.log_upload_attempt(
                user_id=user_id or "anonymous", filename=filename, file_size=file_size
            )

            # 1. Filename sanitization and validation
            sanitized_filename, filename_warnings = self._validate_filename(filename)

            # 2. File extension validation
            extension_result = self._validate_file_extension(filename)
            if not extension_result.is_valid:
                return extension_result

            file_extension = self._get_file_extension(filename)

            # 3. File size validation
            size_result = self._validate_file_size(
                file_size, file_extension, max_size_override, user_id
            )
            if not size_result.is_valid:
                return size_result

            # 4. MIME type validation using python-magic
            mime_result = self._validate_mime_type(file_content, file_extension)
            if not mime_result.is_valid:
                return mime_result

            # 5. File magic bytes validation
            magic_bytes_result = self._validate_magic_bytes(
                file_content, file_extension
            )
            if not magic_bytes_result.is_valid:
                return magic_bytes_result

            # 6. Content scanning for malicious patterns
            content_result = self._scan_content_for_threats(
                file_content, filename, user_id
            )
            if not content_result.is_valid:
                return content_result

            # 7. Generate file hash for tracking
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Compile all warnings
            all_warnings = filename_warnings
            all_warnings.extend(mime_result.warnings)
            all_warnings.extend(magic_bytes_result.warnings)
            all_warnings.extend(content_result.warnings)

            # Log successful validation
            security_logger.info(
                "File security validation passed",
                extra={
                    "user_id": user_id,
                    "sanitized_filename": sanitized_filename,
                    "file_hash": file_hash,
                    "file_size": file_size,
                    "warnings_count": len(all_warnings),
                },
            )

            return SecurityValidationResult(
                is_valid=True,
                warnings=all_warnings,
                metadata={
                    "sanitized_filename": sanitized_filename,
                    "file_hash": file_hash,
                    "file_size": file_size,
                    "detected_mime_type": mime_result.metadata.get(
                        "detected_mime_type"
                    ),
                    "validation_checks_passed": [
                        "filename",
                        "extension",
                        "size",
                        "mime_type",
                        "magic_bytes",
                        "content_scan",
                    ],
                },
            )

        except Exception as e:
            # Log security validation error
            security_logger.error(
                "File security validation failed with exception",
                extra={
                    "user_id": user_id,
                    "failed_filename": (
                        filename if "filename" in locals() else "unknown"
                    ),
                    "error": str(e),
                    "exception_type": type(e).__name__,
                },
            )

            return SecurityValidationResult(
                is_valid=False, error_message=f"Security validation failed: {str(e)}"
            )

    def _validate_filename(self, filename: str) -> Tuple[str, List[str]]:
        """Validate and sanitize filename."""

        warnings = []

        if not filename:
            raise ValueError("Filename cannot be empty")

        # Check for directory traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            warnings.append("Filename contains potentially unsafe path characters")

        # Check for suspicious characters
        suspicious_chars = ["<", ">", ":", '"', "|", "?", "*", ";", "&", "$"]
        if any(char in filename for char in suspicious_chars):
            warnings.append("Filename contains suspicious characters")

        # Sanitize filename
        sanitized = re.sub(r'[<>:"/\\|?*;&$]', "_", filename)
        sanitized = re.sub(r"\.\.+", ".", sanitized)  # Replace multiple dots
        sanitized = sanitized.strip(". ")  # Remove leading/trailing dots and spaces

        if sanitized != filename:
            warnings.append(f"Filename was sanitized: '{filename}' -> '{sanitized}'")

        return sanitized, warnings

    def _validate_file_extension(self, filename: str) -> SecurityValidationResult:
        """Validate file extension against allowed types."""

        extension = self._get_file_extension(filename)

        if not extension:
            return SecurityValidationResult(
                is_valid=False, error_message="File must have a valid extension"
            )

        if extension not in self.config.EXTENSION_MIME_MAP:
            allowed_extensions = list(self.config.EXTENSION_MIME_MAP.keys())
            return SecurityValidationResult(
                is_valid=False,
                error_message=f"File type '{extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}",
            )

        return SecurityValidationResult(is_valid=True)

    def _validate_file_size(
        self,
        file_size: int,
        file_extension: str,
        max_size_override: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> SecurityValidationResult:
        """Validate file size against limits."""

        if file_size == 0:
            return SecurityValidationResult(
                is_valid=False, error_message="File is empty"
            )

        # Use override or policy-based limit
        if max_size_override:
            max_size = max_size_override
        else:
            max_size = self.security_policy.get_max_file_size(file_extension)

        if file_size > max_size:
            max_mb = max_size / (1024 * 1024)

            # Log security violation
            if user_id:
                self.event_logger.log_security_violation(
                    user_id=user_id,
                    filename="unknown",  # filename not available in this context
                    violation_type="file_size_exceeded",
                    details=f"File size {file_size} bytes exceeds limit {max_size} bytes",
                )

            return SecurityValidationResult(
                is_valid=False,
                error_message=f"File too large. Maximum size for {file_extension} files: {max_mb:.1f}MB",
            )

        return SecurityValidationResult(is_valid=True)

    def _validate_mime_type(
        self, content: bytes, file_extension: str
    ) -> SecurityValidationResult:
        """Validate MIME type using python-magic if available."""

        warnings = []

        # Check if python-magic is available
        if not MAGIC_AVAILABLE:
            warnings.append("python-magic not available, skipping MIME type validation")
            return SecurityValidationResult(
                is_valid=True,
                warnings=warnings,
                metadata={
                    "mime_validation": "skipped",
                    "reason": "python-magic not installed",
                },
            )

        try:
            # Detect MIME type from content
            detected_mime = magic.from_buffer(content, mime=True)

            # Get expected MIME types for this extension
            expected_mimes = self.config.EXTENSION_MIME_MAP.get(file_extension, set())

            # Check if detected MIME type is allowed
            if detected_mime not in self.config.ALLOWED_MIME_TYPES:
                return SecurityValidationResult(
                    is_valid=False,
                    error_message=f"File content type '{detected_mime}' not allowed",
                )

            # Check if detected MIME matches file extension
            if detected_mime not in expected_mimes:
                # Some flexibility for common mismatches
                if not self._is_acceptable_mime_mismatch(detected_mime, file_extension):
                    warnings.append(
                        f"MIME type '{detected_mime}' doesn't match file extension '{file_extension}'"
                    )

            return SecurityValidationResult(
                is_valid=True,
                warnings=warnings,
                metadata={"detected_mime_type": detected_mime},
            )

        except Exception as e:
            return SecurityValidationResult(
                is_valid=False, error_message=f"Failed to validate file type: {str(e)}"
            )

    def _validate_magic_bytes(
        self, content: bytes, file_extension: str
    ) -> SecurityValidationResult:
        """Validate file magic bytes (file signature)."""

        warnings = []

        if len(content) < 16:  # Need at least 16 bytes for most signatures
            warnings.append("File too small to validate magic bytes")
            return SecurityValidationResult(is_valid=True, warnings=warnings)

        # Get expected magic bytes for this file type
        expected_magic = self.config.MAGIC_BYTES.get(file_extension, [])

        if not expected_magic:
            warnings.append(f"No magic bytes validation available for {file_extension}")
            return SecurityValidationResult(is_valid=True, warnings=warnings)

        # Check if any expected magic bytes match
        file_header = content[:32]  # Check first 32 bytes

        magic_match = False
        for magic_bytes in expected_magic:
            if file_header.startswith(magic_bytes):
                magic_match = True
                break
            # For some formats, magic bytes might not be at the very beginning
            if magic_bytes in file_header:
                magic_match = True
                warnings.append("Magic bytes found but not at file start")
                break

        if not magic_match:
            return SecurityValidationResult(
                is_valid=False,
                error_message=f"File header doesn't match expected {file_extension} format",
            )

        return SecurityValidationResult(is_valid=True, warnings=warnings)

    def _scan_content_for_threats(
        self, content: bytes, filename: str, user_id: Optional[str] = None
    ) -> SecurityValidationResult:
        """Scan file content for malicious patterns."""

        warnings = []
        content_lower = content.lower()

        # Check for suspicious patterns
        for pattern in self.config.MALICIOUS_PATTERNS:
            if pattern in content_lower:
                pattern_str = pattern.decode("utf-8", errors="ignore")

                # Log malware detection
                if user_id:
                    file_hash = hashlib.sha256(content).hexdigest()
                    self.event_logger.log_malware_detection(
                        user_id=user_id,
                        filename=filename,
                        threat_type=f"suspicious_pattern_{pattern_str}",
                        file_hash=file_hash,
                    )

                return SecurityValidationResult(
                    is_valid=False,
                    error_message="File contains potentially malicious content",
                )

        # Additional checks for Office documents
        if filename.lower().endswith((".doc", ".docx")):
            # Check for macro indicators
            macro_indicators = [b"vba", b"macro", b"autoopen", b"autoexec"]
            for indicator in macro_indicators:
                if indicator in content_lower:
                    warnings.append("Document may contain macros - exercise caution")
                    break

        return SecurityValidationResult(is_valid=True, warnings=warnings)

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return Path(filename).suffix.lower().lstrip(".")

    def _is_acceptable_mime_mismatch(
        self, detected_mime: str, file_extension: str
    ) -> bool:
        """Check if a MIME type mismatch is acceptable."""

        # Some common acceptable mismatches
        acceptable_mismatches = {
            "jpg": ["image/jpeg"],
            "jpeg": ["image/jpg"],
            "tiff": ["image/tif"],
            "tif": ["image/tiff"],
        }

        return detected_mime in acceptable_mismatches.get(file_extension, [])


# Global instance for use across the application
file_security_validator = FileSecurityValidator()
