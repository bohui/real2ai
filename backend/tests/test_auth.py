"""
Test authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock


@pytest.mark.auth
class TestUserRegistration:
    """Test user registration functionality"""
    
    def test_register_user_success(self, client: TestClient, mock_db_client):
        """Test successful user registration"""
        # Mock successful Supabase auth response
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_session = MagicMock()
        mock_session.access_token = "test-access-token"
        mock_session.refresh_token = "test-refresh-token"
        mock_db_client.auth.sign_up.return_value = MagicMock(user=mock_user, session=mock_session)
        
        # Mock profile creation
        mock_profile_result = MagicMock()
        mock_profile_result.data = [{"id": "test-user-id", "email": "test@example.com"}]
        mock_db_client.table.return_value.insert.return_value.execute.return_value = mock_profile_result
        
        registration_data = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_profile"]["id"] == "test-user-id"
        assert data["user_profile"]["email"] == "test@example.com"
        assert data["message"] == "User registered successfully"
        
        # Verify auth.sign_up was called
        mock_db_client.auth.sign_up.assert_called_once()
    
    def test_register_user_invalid_password(self, client: TestClient):
        """Test registration with invalid password"""
        registration_data = {
            "email": "test@example.com",
            "password": "short",  # Too short
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_user_invalid_email(self, client: TestClient):
        """Test registration with invalid email"""
        registration_data = {
            "email": "invalid-email",
            "password": "TestPass123!",
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_user_invalid_state(self, client: TestClient):
        """Test registration with invalid Australian state"""
        registration_data = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "australian_state": "INVALID",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_user_auth_failure(self, client: TestClient, mock_db_client):
        """Test registration failure from auth service"""
        # Mock failed Supabase auth response
        mock_db_client.auth.sign_up.return_value = MagicMock(user=None)
        
        registration_data = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        
        response = client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Registration failed"


@pytest.mark.auth
class TestUserLogin:
    """Test user login functionality"""
    
    def test_login_user_success(self, client: TestClient, mock_db_client):
        """Test successful user login"""
        # Create proper mock objects that can be JSON serialized
        from types import SimpleNamespace
        
        # Use SimpleNamespace instead of MagicMock for serializable objects
        mock_user = SimpleNamespace()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        
        mock_session = SimpleNamespace()
        mock_session.access_token = "test-access-token"
        mock_session.refresh_token = "test-refresh-token"
        
        # Create auth result mock
        auth_result = SimpleNamespace()
        auth_result.user = mock_user
        auth_result.session = mock_session
        
        mock_db_client.auth.sign_in_with_password.return_value = auth_result
        
        # Mock profile fetch
        profile_data = {
            "id": "test-user-id",
            "email": "test@example.com",
            "australian_state": "NSW",
            "user_type": "buyer"
        }
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[profile_data]
        )
        
        login_data = {
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-access-token"
        assert data["refresh_token"] == "test-refresh-token"
        assert data["user_profile"] == profile_data
    
    def test_login_user_invalid_credentials(self, client: TestClient, mock_db_client):
        """Test login with invalid credentials"""
        # Mock failed auth response
        mock_db_client.auth.sign_in_with_password.return_value = MagicMock(
            user=None,
            session=None
        )
        
        login_data = {
            "email": "test@example.com",
            "password": "WrongPassword"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid credentials"
    
    def test_login_user_invalid_email_format(self, client: TestClient):
        """Test login with invalid email format"""
        login_data = {
            "email": "invalid-email",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_user_exception_handling(self, client: TestClient, mock_db_client):
        """Test login exception handling"""
        # Mock exception from auth service
        mock_db_client.auth.sign_in_with_password.side_effect = Exception("Auth service error")
        
        login_data = {
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication failed"