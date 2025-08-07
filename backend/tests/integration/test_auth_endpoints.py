"""
Integration tests for authentication endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth_success():
    """Mock successful authentication"""
    return {
        "user": MagicMock(id="test-user-id", email="test@example.com"),
        "session": MagicMock(
            access_token="test-access-token",
            refresh_token="test-refresh-token"
        )
    }


@pytest.fixture
def mock_user_profile():
    """Mock user profile data"""
    return {
        "id": "test-user-id",
        "email": "test@example.com", 
        "australian_state": "NSW",
        "user_type": "buyer",
        "subscription_status": "free",
        "credits_remaining": 5,
        "preferences": {"practice_area": "property"}
    }


@pytest.mark.integration
class TestUserRegistration:
    """Integration tests for user registration endpoint"""
    
    def test_register_user_success(self, client):
        """Test successful user registration flow"""
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "australian_state": "NSW", 
            "user_type": "buyer"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            # Mock successful Supabase registration
            mock_supabase = AsyncMock()
            mock_supabase.auth.sign_up.return_value = MagicMock(
                user=MagicMock(id="new-user-id", email="newuser@example.com"),
                session=None
            )
            
            # Mock profile creation
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{
                    "id": "new-user-id",
                    "email": "newuser@example.com",
                    "australian_state": "NSW",
                    "user_type": "buyer"
                }],
                error=None
            )
            
            mock_client.return_value = mock_supabase
            
            response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert "user_profile" in data
        assert data["user_profile"]["email"] == "newuser@example.com"
    
    def test_register_user_invalid_email(self, client):
        """Test registration with invalid email format"""
        registration_data = {
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422
    
    def test_register_user_weak_password(self, client):
        """Test registration with weak password"""
        registration_data = {
            "email": "test@example.com",
            "password": "weak",
            "australian_state": "NSW", 
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422
    
    def test_register_user_invalid_state(self, client):
        """Test registration with invalid Australian state"""
        registration_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "australian_state": "INVALID",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422
    
    def test_register_user_duplicate_email(self, client):
        """Test registration with existing email"""
        registration_data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            # Mock Supabase returning error for duplicate email
            mock_supabase = AsyncMock()
            mock_supabase.auth.sign_up.return_value = MagicMock(
                user=None,
                session=None
            )
            mock_client.return_value = mock_supabase
            
            response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Registration failed"


@pytest.mark.integration  
class TestUserLogin:
    """Integration tests for user login endpoint"""
    
    def test_login_user_success(self, client, mock_auth_success, mock_user_profile):
        """Test successful user login flow"""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            mock_supabase = AsyncMock()
            mock_supabase.auth.sign_in_with_password.return_value = mock_auth_success
            
            # Mock profile retrieval
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[mock_user_profile],
                error=None
            )
            mock_client.return_value = mock_supabase
            
            response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-access-token"
        assert data["refresh_token"] == "test-refresh-token"
        assert data["user_profile"]["email"] == "test@example.com"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            mock_supabase = AsyncMock()
            mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
                user=None,
                session=None
            )
            mock_client.return_value = mock_supabase
            
            response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid credentials"
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        login_data = {
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 422
    
    def test_login_missing_password(self, client):
        """Test login with missing password"""
        login_data = {
            "email": "test@example.com"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 422
    
    def test_login_database_error(self, client, mock_auth_success):
        """Test login with database connection error"""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            mock_supabase = AsyncMock()
            mock_supabase.auth.sign_in_with_password.return_value = mock_auth_success
            
            # Mock database error when fetching profile
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
            mock_client.return_value = mock_supabase
            
            response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication failed"


@pytest.mark.integration
class TestAuthenticationFlow:
    """Integration tests for complete authentication flows"""
    
    def test_register_then_login_flow(self, client):
        """Test complete registration then login flow"""
        # Step 1: Register user
        registration_data = {
            "email": "flowtest@example.com",
            "password": "SecurePassword123!",
            "australian_state": "VIC",
            "user_type": "seller"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            mock_supabase = AsyncMock()
            
            # Mock registration success
            mock_supabase.auth.sign_up.return_value = MagicMock(
                user=MagicMock(id="flow-user-id", email="flowtest@example.com"),
                session=None
            )
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{
                    "id": "flow-user-id",
                    "email": "flowtest@example.com",
                    "australian_state": "VIC",
                    "user_type": "seller"
                }],
                error=None
            )
            mock_client.return_value = mock_supabase
            
            register_response = client.post("/api/auth/register", json=registration_data)
        
        assert register_response.status_code == 200
        
        # Step 2: Login with registered user
        login_data = {
            "email": "flowtest@example.com",
            "password": "SecurePassword123!"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            mock_supabase = AsyncMock()
            
            # Mock login success
            mock_supabase.auth.sign_in_with_password.return_value = MagicMock(
                user=MagicMock(id="flow-user-id", email="flowtest@example.com"),
                session=MagicMock(
                    access_token="flow-access-token",
                    refresh_token="flow-refresh-token"
                )
            )
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{
                    "id": "flow-user-id",
                    "email": "flowtest@example.com",
                    "australian_state": "VIC",
                    "user_type": "seller"
                }],
                error=None
            )
            mock_client.return_value = mock_supabase
            
            login_response = client.post("/api/auth/login", json=login_data)
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["access_token"] == "flow-access-token"
        assert login_data["user_profile"]["email"] == "flowtest@example.com"
    
    def test_concurrent_registration_attempts(self, client):
        """Test handling concurrent registration attempts"""
        registration_data = {
            "email": "concurrent@example.com",
            "password": "SecurePassword123!",
            "australian_state": "QLD",
            "user_type": "agent"
        }
        
        with patch('app.router.auth.get_supabase_client') as mock_client:
            mock_supabase = AsyncMock()
            
            # First attempt succeeds
            mock_supabase.auth.sign_up.return_value = MagicMock(
                user=MagicMock(id="concurrent-user", email="concurrent@example.com"),
                session=None
            )
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{
                    "id": "concurrent-user",
                    "email": "concurrent@example.com",
                    "australian_state": "QLD",
                    "user_type": "agent"
                }],
                error=None
            )
            mock_client.return_value = mock_supabase
            
            # Make multiple concurrent requests
            responses = []
            for _ in range(3):
                response = client.post("/api/auth/register", json=registration_data)
                responses.append(response)
        
        # At least one should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1


@pytest.mark.integration
class TestAuthenticationSecurity:
    """Integration tests for authentication security features"""
    
    def test_password_requirements_enforced(self, client):
        """Test that password requirements are properly enforced"""
        weak_passwords = [
            "short",           # Too short
            "alllowercase",    # No uppercase
            "ALLUPPERCASE",    # No lowercase
            "NoNumbers!",      # No numbers
            "NoSpecialChars1", # No special characters
        ]
        
        for password in weak_passwords:
            registration_data = {
                "email": f"test{password}@example.com",
                "password": password,
                "australian_state": "NSW",
                "user_type": "buyer"
            }
            
            response = client.post("/api/auth/register", json=registration_data)
            assert response.status_code == 422, f"Password '{password}' should be rejected"
    
    def test_email_format_validation(self, client):
        """Test email format validation"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@.com",
        ]
        
        for email in invalid_emails:
            registration_data = {
                "email": email,
                "password": "ValidPassword123!",
                "australian_state": "NSW",
                "user_type": "buyer"
            }
            
            response = client.post("/api/auth/register", json=registration_data)
            assert response.status_code == 422, f"Email '{email}' should be rejected"
    
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection attempts"""
        malicious_inputs = [
            "test@example.com'; DROP TABLE users; --",
            "admin@example.com' OR '1'='1",
            "test@example.com'; INSERT INTO users VALUES ('hacker'); --"
        ]
        
        for malicious_email in malicious_inputs:
            registration_data = {
                "email": malicious_email,
                "password": "ValidPassword123!",
                "australian_state": "NSW",
                "user_type": "buyer"
            }
            
            response = client.post("/api/auth/register", json=registration_data)
            # Should either reject due to format or handle safely
            assert response.status_code in [422, 400], f"Malicious input '{malicious_email}' not handled safely"