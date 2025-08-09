#!/usr/bin/env python3
"""
Security Enhancement Demo Script for Real2.AI Platform

This script demonstrates the comprehensive security improvements made to prevent
malicious file uploads and enhance overall platform security.
"""

import asyncio
from io import BytesIO
from fastapi import UploadFile
import sys
import os

# Add the app directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def create_test_file(filename: str, content: bytes, content_type: str = "application/pdf") -> UploadFile:
    """Create a test UploadFile for demonstration."""
    file_obj = BytesIO(content)
    return UploadFile(
        filename=filename,
        file=file_obj,
        content_type=content_type
    )

async def demo_security_features():
    """Demonstrate the security features."""
    
    print("🔒 Real2.AI File Security Enhancement Demo")
    print("=" * 50)
    
    try:
        from app.core.file_security import file_security_validator
        from app.core.security_config import security_config, file_security_policy
        from app.core.rate_limiter import upload_rate_limiter
        
        print("✅ Security modules loaded successfully")
        print()
        
        # Test 1: Valid PDF file
        print("Test 1: Valid PDF File")
        print("-" * 30)
        
        valid_pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' + b'Valid PDF content here' * 100
        valid_file = create_test_file("contract.pdf", valid_pdf_content)
        
        # Mock magic library for demo
        import unittest.mock
        with unittest.mock.patch('magic.from_buffer', return_value="application/pdf"):
            result = await file_security_validator.validate_file_security(
                file=valid_file, 
                user_id="demo-user"
            )
        
        print(f"  Result: {'✅ PASSED' if result.is_valid else '❌ FAILED'}")
        if result.warnings:
            print(f"  Warnings: {len(result.warnings)}")
        if result.metadata:
            print(f"  File hash: {result.metadata.get('file_hash', 'N/A')[:16]}...")
        print()
        
        # Test 2: Malicious file with executable header
        print("Test 2: Malicious File (PE Executable Header)")
        print("-" * 45)
        
        malicious_content = b'MZ\x90\x00' + b'This is actually an executable' * 50
        malicious_file = create_test_file("document.pdf", malicious_content)
        
        with unittest.mock.patch('magic.from_buffer', return_value="application/x-executable"):
            result = await file_security_validator.validate_file_security(
                file=malicious_file, 
                user_id="demo-user"
            )
        
        print(f"  Result: {'✅ BLOCKED' if not result.is_valid else '❌ ALLOWED (BAD!)'}")
        print(f"  Reason: {result.error_message}")
        print()
        
        # Test 3: File with script injection
        print("Test 3: File with Script Injection")
        print("-" * 35)
        
        script_content = b'%PDF-1.4\n<script>alert("xss")</script>' + b'x' * 1000
        script_file = create_test_file("document.pdf", script_content)
        
        with unittest.mock.patch('magic.from_buffer', return_value="application/pdf"):
            result = await file_security_validator.validate_file_security(
                file=script_file,
                user_id="demo-user"
            )
        
        print(f"  Result: {'✅ BLOCKED' if not result.is_valid else '❌ ALLOWED (BAD!)'}")
        print(f"  Reason: {result.error_message}")
        print()
        
        # Test 4: Filename sanitization
        print("Test 4: Filename Sanitization")
        print("-" * 30)
        
        unsafe_filename = "../../malicious<script>.pdf"
        safe_content = b'%PDF-1.4\n' + b'x' * 1000
        unsafe_file = create_test_file(unsafe_filename, safe_content)
        
        with unittest.mock.patch('magic.from_buffer', return_value="application/pdf"):
            result = await file_security_validator.validate_file_security(
                file=unsafe_file,
                user_id="demo-user"
            )
        
        print(f"  Original filename: {unsafe_filename}")
        print(f"  Sanitized filename: {result.metadata.get('sanitized_filename', 'N/A')}")
        print(f"  Warnings: {len(result.warnings)} security warnings")
        print()
        
        # Test 5: Rate limiting
        print("Test 5: Rate Limiting")
        print("-" * 20)
        
        # Simulate multiple requests
        user_id = "demo-user"
        client_ip = "127.0.0.1"
        
        for i in range(12):  # Try 12 requests (limit is 10/minute)
            is_limited, reason = upload_rate_limiter.is_rate_limited(user_id, client_ip)
            if is_limited:
                print(f"  Request {i+1}: ❌ RATE LIMITED - {reason}")
                break
            else:
                print(f"  Request {i+1}: ✅ Allowed")
        
        print()
        
        # Test 6: Security policy info
        print("Test 6: Security Configuration")
        print("-" * 32)
        
        settings = file_security_policy.get_security_settings()
        print(f"  Content validation: {'✅' if settings['content_validation'] else '❌'}")
        print(f"  MIME validation: {'✅' if settings['mime_validation'] else '❌'}")
        print(f"  Magic bytes validation: {'✅' if settings['magic_bytes_validation'] else '❌'}")
        print(f"  Malware scanning: {'✅' if settings['malware_scanning'] else '❌'}")
        print(f"  Rate limiting: {'✅' if settings['rate_limiting']['enabled'] else '❌'}")
        print(f"  Max PDF size: {settings['max_file_sizes']['pdf'] // (1024*1024)}MB")
        print(f"  Allowed extensions: {', '.join(settings['allowed_extensions'])}")
        print()
        
        print("🎉 Security Enhancement Demo Complete!")
        print()
        print("Security Features Implemented:")
        print("  ✅ MIME type validation using python-magic")
        print("  ✅ File magic bytes verification")
        print("  ✅ Malicious content pattern detection")
        print("  ✅ Filename sanitization against directory traversal")
        print("  ✅ File size validation by type")
        print("  ✅ Rate limiting per user and IP")
        print("  ✅ Comprehensive security logging")
        print("  ✅ SHA256 file hashing for tracking")
        print("  ✅ Configurable security policies")
        print()
        print("The Real2.AI platform is now protected against:")
        print("  🛡️  Malicious executable uploads")
        print("  🛡️  Script injection attacks")
        print("  🛡️  Directory traversal attempts")
        print("  🛡️  MIME type spoofing")
        print("  🛡️  Oversized file DoS attacks")
        print("  🛡️  Brute force upload attempts")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed:")
        print("  pip install python-magic")
    except Exception as e:
        print(f"❌ Demo error: {e}")

if __name__ == "__main__":
    asyncio.run(demo_security_features())