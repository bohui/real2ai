"""
Test configuration and fixtures for Real2.AI backend tests.
Provides environment setup, database fixtures, and common test utilities.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["TESTING"] = "true"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"

from app.main import app
from app.core.config import get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture
def client(test_user, mock_db_client, test_settings) -> Generator[TestClient, None, None]:
    """Create a test client for FastAPI app with auth override."""
    from app.core.auth import get_current_user
    from app.core.database import get_database_client
    from app.core.config import get_settings
    from app.services.document_service import DocumentService
    from unittest.mock import patch
    import app.main
    
    # Override dependencies for testing
    def override_get_current_user():
        return test_user
    
    def override_get_database_client():
        return mock_db_client
    
    def override_get_settings():
        return test_settings
    
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_current_user] = override_get_current_user
    fastapi_app.dependency_overrides[get_database_client] = override_get_database_client
    fastapi_app.dependency_overrides[get_settings] = override_get_settings
    
    # Mock global db_client used in main module and router modules
    import app.main
    from app.core.database import get_database_client as real_get_database_client
    
    with patch.object(app.main, 'db_client', mock_db_client):
        # Also patch the get_database_client function directly in all modules that import it
        with patch('app.core.database.get_database_client', return_value=mock_db_client):
            with patch('app.router.documents.get_database_client', return_value=mock_db_client):
                # Mock document service
                with patch.object(DocumentService, 'upload_file', new_callable=AsyncMock) as mock_upload:
                    mock_upload.return_value = {
                        "document_id": "test-doc-id",
                        "storage_path": "documents/test-user-id/test-doc-id.pdf"
                    }
                    
                    test_client = TestClient(fastapi_app)
                    yield test_client
    
    # Clean up overrides
    fastapi_app.dependency_overrides.clear()
    test_client.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = MagicMock()
    
    # Mock auth
    mock_client.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="test-user-id", email="test@example.com")
    )
    
    # Mock storage
    mock_client.storage.from_.return_value = MagicMock()
    
    # Mock database queries
    mock_select = MagicMock()
    mock_select.execute.return_value = MagicMock(
        data=[{"id": 1, "name": "test"}],
        error=None
    )
    mock_client.table.return_value.select.return_value = mock_select
    
    return mock_client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = AsyncMock()
    
    # Mock chat completions
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Mock AI response",
                        role="assistant"
                    )
                )
            ]
        )
    )
    
    return mock_client


@pytest.fixture
def sample_contract_data():
    """Sample contract data for testing."""
    return {
        "id": "test-contract-id",
        "document_id": "test-doc-id",
        "contract_type": "purchase_agreement",
        "australian_state": "NSW",
        "user_id": "test-user-id",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_risk_assessment():
    """Sample risk assessment data for testing."""
    return {
        "overall_score": 3.5,
        "risk_factors": [
            {
                "category": "financial",
                "severity": "medium",
                "description": "Settlement period shorter than recommended",
                "impact": "Potential difficulty securing finance"
            },
            {
                "category": "legal",
                "severity": "low", 
                "description": "Standard contract terms",
                "impact": "Minimal legal risk"
            }
        ],
        "recommendations": [
            "Seek pre-approval for finance",
            "Consider extending settlement period"
        ]
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables automatically for all tests."""
    test_env_vars = {
        "ENVIRONMENT": "test",
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-key",
        "OPENAI_API_KEY": "test-openai-key",
        "REDIS_URL": "redis://localhost:6379/1",  # Use test DB
    }
    
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for caching tests."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = False
    return mock_client


# Performance test fixtures
@pytest.fixture
def performance_threshold():
    """Performance thresholds for different operations."""
    return {
        "api_response": 0.2,  # 200ms
        "ai_analysis": 5.0,   # 5 seconds
        "file_upload": 1.0,   # 1 second
        "database_query": 0.1  # 100ms
    }


# Database fixtures for integration tests
@pytest.fixture
def clean_database():
    """Clean database state for integration tests."""
    # This would typically clean test database tables
    # Implementation depends on your database setup
    yield
    # Cleanup after test


# Authentication fixtures
@pytest.fixture
def auth_headers():
    """Authentication headers for API tests."""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def mock_db_client():
    """Mock database client for testing."""
    mock_client = MagicMock()
    
    # Mock the _client attribute to simulate initialized state
    mock_client._client = MagicMock()
    
    # Mock the initialize method to prevent real database connection
    async def mock_initialize():
        """Mock initialization that succeeds without connecting"""
        mock_client._client = MagicMock()
        return True
    
    mock_client.initialize = mock_initialize
    
    # Mock table operations
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[], error=None)
    mock_client.table.return_value = mock_table
    
    # Mock auth operations
    mock_client.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="test-user-id", email="test@example.com")
    )
    mock_client.auth.sign_up.return_value = MagicMock(
        user=MagicMock(id="test-user-id", email="test@example.com")
    )
    mock_client.auth.sign_in_with_password.return_value = MagicMock(
        user=MagicMock(id="test-user-id", email="test@example.com"),
        session=MagicMock(access_token="test-token", refresh_token="test-refresh")
    )
    
    return mock_client


@pytest.fixture
def sample_document_data():
    """Sample document data for testing."""
    return {
        "id": "test-doc-id",
        "user_id": "test-user-id",
        "filename": "test-contract.pdf",
        "storage_path": "documents/test-user-id/test-doc-id.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "status": "uploaded",
        "processing_results": {
            "extracted_text": "Sample contract text",
            "extraction_confidence": 0.95,
            "character_count": 1000,
            "word_count": 200
        }
    }


@pytest.fixture
def sample_onboarding_preferences():
    """Sample onboarding preferences for testing."""
    return {
        "practice_area": "property",
        "jurisdiction": "nsw",
        "firm_size": "small",
        "experience_level": "intermediate",
        "notification_preferences": {
            "email_alerts": True,
            "contract_updates": False
        }
    }


@pytest.fixture
def sample_analysis_data():
    """Sample analysis data for testing."""
    return {
        "id": "test-analysis-id",
        "contract_id": "test-contract-id",
        "status": "completed",
        "analysis_result": {
            "contract_terms": {
                "parties": ["John Buyer", "Jane Seller"],
                "property_address": "123 Test Street, Sydney NSW 2000",
                "purchase_price": 850000,
                "settlement_date": "2024-12-01"
            },
            "risk_assessment": {
                "overall_risk_score": 3.5,
                "risk_factors": []
            },
            "compliance_check": {
                "state_compliance": True,
                "compliance_issues": [],
                "cooling_off_compliance": True
            },
            "recommendations": []
        },
        "risk_score": 3,
        "processing_time": 120.5,
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def test_settings():
    """Test-specific settings."""
    settings = get_settings()
    settings.max_file_size = 5 * 1024 * 1024  # 5MB
    settings.allowed_file_types = "pdf,doc,docx"  # Set the actual property
    return settings


@pytest.fixture
def test_user():
    """Test user data."""
    from app.core.auth import User
    return User(
        id="test-user-id",
        email="test@real2ai.com",
        australian_state="NSW",
        user_type="lawyer",
        subscription_status="free",
        credits_remaining=5,
        preferences={"practice_area": "property"}
    )


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@real2ai.com"
    user.australian_state = "NSW"
    user.user_type = "lawyer"
    user.subscription_status = "free"
    user.credits_remaining = 5
    user.preferences = {"practice_area": "property"}
    return user