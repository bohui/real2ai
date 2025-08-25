"""Test file security validation functionality."""

import pytest
from io import BytesIO
from fastapi import UploadFile
from unittest.mock import patch

from app.core.file_security import FileSecurityValidator


class TestFileSecurityValidator:
    """Test suite for FileSecurityValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return FileSecurityValidator()
    
    def create_upload_file(self, filename: str, content: bytes, content_type: str = "application/pdf") -> UploadFile:
        """Create a mock UploadFile for testing."""
        file_obj = BytesIO(content)
        return UploadFile(
            filename=filename,
            file=file_obj,
            content_type=content_type,
            size=len(content)
        )
    
    @pytest.mark.asyncio
    async def test_valid_pdf_file(self, validator):
        """Test validation of a valid PDF file."""
        # Valid PDF magic bytes
        pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' + b'x' * 1000
        file = self.create_upload_file("test.pdf", pdf_content, "application/pdf")
        
        with patch('magic.from_buffer', return_value="application/pdf"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert result.is_valid
        assert result.error_message is None
        assert "file_hash" in result.metadata
        assert result.metadata["sanitized_filename"] == "test.pdf"
    
    @pytest.mark.asyncio
    async def test_malicious_file_with_executable_header(self, validator):
        """Test rejection of file with executable magic bytes."""
        # PE executable header (Windows .exe file)
        malicious_content = b'MZ\x90\x00' + b'x' * 1000
        file = self.create_upload_file("document.pdf", malicious_content)
        
        with patch('magic.from_buffer', return_value="application/x-executable"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "potentially malicious content" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_file_with_script_injection(self, validator):
        """Test rejection of file with script injection attempts."""
        # PDF with embedded JavaScript
        malicious_content = b'%PDF-1.4\n<script>alert("xss")</script>' + b'x' * 1000
        file = self.create_upload_file("document.pdf", malicious_content)
        
        with patch('magic.from_buffer', return_value="application/pdf"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "potentially malicious content" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_oversized_file_rejection(self, validator):
        """Test rejection of oversized files."""
        # Create a file larger than 50MB
        large_content = b'%PDF-1.4\n' + b'x' * (51 * 1024 * 1024)
        file = self.create_upload_file("large.pdf", large_content)
        
        result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "too large" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_empty_file_rejection(self, validator):
        """Test rejection of empty files."""
        file = self.create_upload_file("empty.pdf", b"")
        
        result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "empty" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_file_extension(self, validator):
        """Test rejection of files with invalid extensions."""
        content = b'%PDF-1.4\n' + b'x' * 1000
        file = self.create_upload_file("document.exe", content)
        
        result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "not allowed" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_filename_sanitization(self, validator):
        """Test filename sanitization for unsafe characters."""
        content = b'%PDF-1.4\n' + b'x' * 1000
        unsafe_filename = "../../malicious<script>.pdf"
        file = self.create_upload_file(unsafe_filename, content)
        
        with patch('magic.from_buffer', return_value="application/pdf"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert result.is_valid
        assert len(result.warnings) > 0
        sanitized = result.metadata.get("sanitized_filename")
        assert sanitized != unsafe_filename
        assert ".." not in sanitized
        assert "<" not in sanitized
    
    @pytest.mark.asyncio
    async def test_mime_type_mismatch(self, validator):
        """Test handling of MIME type mismatches."""
        # File with .pdf extension but different content
        image_content = b'\x89PNG\r\n\x1a\n' + b'x' * 1000
        file = self.create_upload_file("document.pdf", image_content)
        
        with patch('magic.from_buffer', return_value="image/png"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "content type" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_valid_word_document(self, validator):
        """Test validation of a valid Word document."""
        # Valid DOCX magic bytes (ZIP archive)
        docx_content = b'PK\x03\x04' + b'x' * 1000
        file = self.create_upload_file("contract.docx", docx_content)
        
        with patch('magic.from_buffer', return_value="application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert result.is_valid
        assert result.metadata["sanitized_filename"] == "contract.docx"
    
    @pytest.mark.asyncio
    async def test_valid_jpeg_image(self, validator):
        """Test validation of a valid JPEG image."""
        # Valid JPEG magic bytes
        jpeg_content = b'\xff\xd8\xff\xe0' + b'x' * 1000
        file = self.create_upload_file("photo.jpg", jpeg_content)
        
        with patch('magic.from_buffer', return_value="image/jpeg"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert result.is_valid
        assert result.metadata["sanitized_filename"] == "photo.jpg"
    
    @pytest.mark.asyncio
    async def test_macro_enabled_document_warning(self, validator):
        """Test warning for documents that may contain macros."""
        # Document with potential macro indicators
        doc_with_macro = b'\xd0\xcf\x11\xe0VBA_PROJECT' + b'x' * 1000
        file = self.create_upload_file("contract.doc", doc_with_macro)
        
        with patch('magic.from_buffer', return_value="application/msword"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert result.is_valid
        # Should have warnings about macros
        assert any("macro" in warning.lower() for warning in result.warnings)
    
    @pytest.mark.asyncio
    async def test_php_injection_attempt(self, validator):
        """Test rejection of files containing PHP code."""
        # PDF with embedded PHP
        malicious_content = b'%PDF-1.4\n<?php system($_GET["cmd"]); ?>' + b'x' * 1000
        file = self.create_upload_file("document.pdf", malicious_content)
        
        with patch('magic.from_buffer', return_value="application/pdf"):
            result = await validator.validate_file_security(file, user_id="test-user")
        
        assert not result.is_valid
        assert "potentially malicious content" in result.error_message.lower()
    
    def test_filename_validation(self, validator):
        """Test filename validation and sanitization."""
        # Test various problematic filenames
        test_cases = [
            ("normal.pdf", "normal.pdf", False),
            ("../../../etc/passwd.pdf", "___etc_passwd.pdf", True),
            ("file<script>alert</script>.pdf", "file_script_alert_script_.pdf", True),
            ("file|with|pipes.pdf", "file_with_pipes.pdf", True),
            ("file...with...dots.pdf", "file.with.dots.pdf", True),
        ]
        
        for original, expected_sanitized, should_warn in test_cases:
            sanitized, warnings = validator._validate_filename(original)
            assert sanitized == expected_sanitized
            if should_warn:
                assert len(warnings) > 0
            else:
                assert len(warnings) == 0


@pytest.mark.asyncio 
async def test_security_integration_with_documents_router():
    """Test that the security validation integrates properly with the documents router."""
    # This would be an integration test that tests the actual endpoint
    # For now, we'll test that the import works correctly
    
    from app.core.file_security import file_security_validator
    
    # Verify the validator is properly initialized
    assert file_security_validator is not None
    assert hasattr(file_security_validator, 'validate_file_security')
    
    # Test with a simple valid file
    pdf_content = b'%PDF-1.4\n' + b'x' * 1000
    file_obj = BytesIO(pdf_content)
    file = UploadFile(filename="test.pdf", file=file_obj, content_type="application/pdf")
    
    with patch('magic.from_buffer', return_value="application/pdf"):
        result = await file_security_validator.validate_file_security(file, user_id="test-user")
    
    assert result.is_valid


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])