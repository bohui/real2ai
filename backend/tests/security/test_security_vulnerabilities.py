"""
Security vulnerability tests for Real2.AI backend.
"""
from datetime import timedelta
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.main import app
# Token functions removed - need to implement or mock these for tests


class TestAuthenticationSecurity:
    """Test authentication and authorization security."""

    @pytest.mark.asyncio
    async def test_unauthorized_access_blocked(self):
        """Test that unauthorized requests are blocked."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try accessing protected endpoint without token
            response = await client.get("/users/me")
            assert response.status_code == 401
            
            # Try accessing with invalid token
            response = await client.get(
                "/users/me",
                headers={"Authorization": "Bearer invalid_token"}
            )
            assert response.status_code == 401
            
            # Try accessing with malformed token
            response = await client.get(
                "/users/me", 
                headers={"Authorization": "InvalidFormat"}
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_expiration_enforced(self):
        """Test that expired tokens are rejected."""
        # Create expired token
        expired_token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/users/me",
                headers={"Authorization": f"Bearer {expired_token}"}
            )
            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self):
        """Test protection against SQL injection attacks."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users --",
            "admin'/**/OR/**/1=1#",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for malicious_input in malicious_inputs:
                # Try SQL injection in login
                response = await client.post(
                    "/auth/login",
                    json={
                        "email": malicious_input,
                        "password": "password"
                    }
                )
                # Should return validation error, not execute SQL
                assert response.status_code in [422, 401]
                
                # Try SQL injection in document search
                response = await client.get(
                    f"/documents/search?query={malicious_input}",
                    headers={"Authorization": "Bearer valid_token"}
                )
                assert response.status_code in [422, 401, 404]

    @pytest.mark.asyncio
    async def test_xss_protection(self):
        """Test protection against Cross-Site Scripting (XSS) attacks."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>"
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for payload in xss_payloads:
                # Try XSS in user profile update
                response = await client.put(
                    "/users/profile",
                    json={
                        "name": payload,
                        "email": "test@example.com"
                    },
                    headers={"Authorization": "Bearer valid_token"}
                )
                # Should sanitize or reject malicious input
                assert response.status_code in [422, 401, 400]

    @pytest.mark.asyncio
    async def test_file_upload_security(self):
        """Test file upload security restrictions."""
        malicious_files = [
            # Executable file
            ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
            # Script file
            ("script.js", b"alert('malicious')", "application/javascript"),
            # PHP file  
            ("shell.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
            # Oversized file (simulate)
            ("huge.pdf", b"A" * (50 * 1024 * 1024), "application/pdf")  # 50MB
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for filename, content, content_type in malicious_files:
                files = {"file": (filename, content, content_type)}
                response = await client.post(
                    "/documents/upload",
                    files=files,
                    headers={"Authorization": "Bearer valid_token"}
                )
                
                # Should reject malicious files
                assert response.status_code in [422, 413, 400]

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting on sensitive endpoints."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Attempt multiple rapid login requests
            responses = []
            for i in range(10):
                response = await client.post(
                    "/auth/login",
                    json={
                        "email": f"test{i}@example.com",
                        "password": "wrong_password"
                    }
                )
                responses.append(response)
            
            # Should implement rate limiting
            rate_limited_responses = [r for r in responses if r.status_code == 429]
            assert len(rate_limited_responses) > 0, "Rate limiting not implemented"

    @pytest.mark.asyncio
    async def test_session_fixation_protection(self):
        """Test protection against session fixation attacks."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login with valid credentials
            login_response = await client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "valid_password"
                }
            )
            
            if login_response.status_code == 200:
                token1 = login_response.json()["access_token"]
                
                # Login again with same credentials
                login_response2 = await client.post(
                    "/auth/login",
                    json={
                        "email": "test@example.com", 
                        "password": "valid_password"
                    }
                )
                
                if login_response2.status_code == 200:
                    token2 = login_response2.json()["access_token"]
                    
                    # Tokens should be different (new session)
                    assert token1 != token2, "Session fixation vulnerability detected"

    @pytest.mark.asyncio  
    async def test_csrf_protection(self):
        """Test CSRF protection on state-changing operations."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try state-changing operation without proper headers
            response = await client.delete(
                "/documents/doc-123",
                headers={
                    "Authorization": "Bearer valid_token",
                    # Missing CSRF token or referrer validation
                    "Origin": "https://malicious-site.com"
                }
            )
            
            # Should reject cross-origin requests without proper CSRF protection
            assert response.status_code in [403, 401, 400]

    @pytest.mark.asyncio
    async def test_information_disclosure_prevention(self):
        """Test prevention of sensitive information disclosure."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try to access other user's documents
            response = await client.get(
                "/documents/other-user-doc",
                headers={"Authorization": "Bearer valid_token"}
            )
            
            # Should not disclose whether document exists for other users
            assert response.status_code in [404, 403]
            if response.status_code == 404:
                # Error message should not reveal internal details
                error_message = response.json().get("detail", "")
                assert "user" not in error_message.lower()
                assert "unauthorized" not in error_message.lower()

    @pytest.mark.asyncio
    async def test_input_validation_bypass_attempts(self):
        """Test attempts to bypass input validation."""
        bypass_attempts = [
            # Unicode bypass
            {"email": "test\u0000@example.com"},
            # Encoding bypass  
            {"email": "test%00@example.com"},
            # Length bypass
            {"email": "a" * 1000 + "@example.com"},
            # Null bytes
            {"email": "test@example.com\x00.evil.com"},
            # Control characters
            {"email": "test\r\n@example.com"}
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for invalid_data in bypass_attempts:
                response = await client.post(
                    "/auth/register",
                    json=invalid_data
                )
                
                # Should reject invalid input
                assert response.status_code == 422


class TestDataSecurity:
    """Test data security and privacy protections."""

    @pytest.mark.asyncio
    async def test_sensitive_data_not_logged(self):
        """Test that sensitive data is not included in logs."""
        with patch('app.core.config.logger') as mock_logger:
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Make request with sensitive data
                await client.post(
                    "/auth/login",
                    json={
                        "email": "test@example.com",
                        "password": "secret_password"
                    }
                )
                
                # Check that password is not in any log calls
                for call in mock_logger.info.call_args_list:
                    log_message = str(call)
                    assert "secret_password" not in log_message
                    assert "password" not in log_message.lower() or "****" in log_message

    @pytest.mark.asyncio
    async def test_data_encryption_in_transit(self):
        """Test that sensitive data is encrypted in transit."""
        # This would typically be handled by HTTPS in production
        # Here we test that sensitive endpoints require secure connections
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # In production, these should redirect to HTTPS or reject HTTP
            response = await client.post(
                "/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password"
                }
            )
            
            # Check security headers are present
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers

    @pytest.mark.asyncio
    async def test_user_data_isolation(self):
        """Test that users can only access their own data."""
        # Create two different user tokens
        user1_token = create_access_token(data={"sub": "user1@example.com"})
        user2_token = create_access_token(data={"sub": "user2@example.com"})
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # User1 creates a document
            with patch('app.services.document_service.DocumentService') as mock_service:
                mock_service.return_value.store_document.return_value = {
                    'document_id': 'user1-doc-123'
                }
                
                upload_response = await client.post(
                    "/documents/upload",
                    files={"file": ("test.pdf", b"content", "application/pdf")},
                    headers={"Authorization": f"Bearer {user1_token}"}
                )
                
                if upload_response.status_code == 200:
                    doc_id = upload_response.json()['document_id']
                    
                    # User2 tries to access User1's document
                    access_response = await client.get(
                        f"/documents/{doc_id}",
                        headers={"Authorization": f"Bearer {user2_token}"}
                    )
                    
                    # Should be denied
                    assert access_response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_password_security(self):
        """Test password security requirements."""
        weak_passwords = [
            "123",
            "password", 
            "abc",
            "12345678",
            "qwerty",
            ""
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for weak_password in weak_passwords:
                response = await client.post(
                    "/auth/register",
                    json={
                        "email": "test@example.com",
                        "password": weak_password,
                        "name": "Test User"
                    }
                )
                
                # Should reject weak passwords
                assert response.status_code == 422
                error_detail = response.json()["detail"]
                assert any("password" in str(detail).lower() for detail in error_detail)


class TestAPISecurityHeaders:
    """Test security headers and API protection."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test that all necessary security headers are present."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            required_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Referrer-Policy"
            ]
            
            for header in required_headers:
                assert header in response.headers, f"Missing security header: {header}"

    @pytest.mark.asyncio
    async def test_cors_configuration(self):
        """Test CORS configuration is secure."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test CORS preflight
            response = await client.options(
                "/api/contracts",
                headers={
                    "Origin": "https://malicious-site.com",
                    "Access-Control-Request-Method": "POST"
                }
            )
            
            # Should not allow arbitrary origins in production
            cors_origin = response.headers.get("Access-Control-Allow-Origin")
            if cors_origin:
                assert cors_origin != "*", "CORS allows all origins - security risk"

    @pytest.mark.asyncio
    async def test_api_versioning_security(self):
        """Test that API versioning doesn't expose vulnerabilities."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Try accessing deprecated/beta endpoints
            deprecated_endpoints = [
                "/v1/deprecated-endpoint",
                "/beta/experimental", 
                "/internal/admin",
                "/debug/info"
            ]
            
            for endpoint in deprecated_endpoints:
                response = await client.get(endpoint)
                # Should not expose internal/deprecated endpoints
                assert response.status_code in [404, 405], f"Exposed endpoint: {endpoint}"

    @pytest.mark.asyncio
    async def test_error_message_security(self):
        """Test that error messages don't leak sensitive information."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Trigger various error conditions
            error_responses = []
            
            # Database connection error simulation
            with patch('app.clients.supabase.database_client.DatabaseClient') as mock_db:
                mock_db.return_value.query.side_effect = Exception("Connection failed to database server at 192.168.1.100:5432")
                
                response = await client.get(
                    "/documents/nonexistent",
                    headers={"Authorization": "Bearer valid_token"}
                )
                error_responses.append(response)
            
            # Check that error messages don't contain sensitive info
            for response in error_responses:
                error_message = response.json().get("detail", "")
                
                # Should not contain internal IP addresses
                assert "192.168." not in error_message
                assert "127.0.0.1" not in error_message
                
                # Should not contain database connection strings
                assert "postgresql://" not in error_message
                assert "Connection failed to database" not in error_message
                
                # Should not contain file paths
                assert "/etc/" not in error_message
                assert "/var/" not in error_message
                assert "C:\\" not in error_message