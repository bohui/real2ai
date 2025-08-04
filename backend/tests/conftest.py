"""
Test configuration and fixtures for Real2.AI backend tests
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
try:
    from httpx import AsyncClient
except ImportError:
    AsyncClient = None
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.core.database import get_database_client
from app.core.auth import get_current_user
from app.core.config import get_settings


# Test configuration
@pytest.fixture
def test_settings():
    """Override settings for testing"""
    from app.core.config import Settings
    return Settings(
        environment="testing",
        database_url="sqlite:///test.db",
        openai_api_key="test-key",
        supabase_url="http://localhost:54321",
        supabase_anon_key="test-anon-key",
        supabase_service_key="test-service-key",
        jwt_secret="test-jwt-secret",
        max_file_size=10 * 1024 * 1024,  # 10MB for testing
        allowed_file_types="pdf,doc,docx,txt"
    )


@pytest.fixture
def mock_db_client():
    """Mock database client for testing"""
    mock_client = MagicMock()
    
    # Mock auth methods
    mock_client.auth.sign_up = MagicMock()
    mock_client.auth.sign_in_with_password = MagicMock()
    
    # Mock table methods
    mock_table = MagicMock()
    mock_table.insert = MagicMock(return_value=mock_table)
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.update = MagicMock(return_value=mock_table)
    mock_table.delete = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.execute = MagicMock()
    
    mock_client.table = MagicMock(return_value=mock_table)
    mock_client.initialize = AsyncMock()
    mock_client.close = AsyncMock()
    
    return mock_client


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing"""
    from app.core.auth import User
    from app.models.contract_state import AustralianState
    
    return User(
        id="test-user-id",
        email="test@example.com",
        australian_state=AustralianState.NSW,
        user_type="buyer",
        subscription_status="free",
        credits_remaining=5,
        preferences={},
        onboarding_completed=True
    )


@pytest.fixture
def override_dependencies(mock_db_client, mock_user, test_settings):
    """Override FastAPI dependencies for testing"""
    
    async def get_test_db():
        return mock_db_client
    
    async def get_test_user():
        return mock_user
    
    def get_test_settings():
        return test_settings
    
    app.dependency_overrides[get_database_client] = get_test_db
    app.dependency_overrides[get_current_user] = get_test_user
    app.dependency_overrides[get_settings] = get_test_settings
    
    yield
    
    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_dependencies) -> Generator[TestClient, None, None]:
    """Create test client with dependency overrides"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(override_dependencies):
    """Create async test client with dependency overrides"""
    if AsyncClient is None:
        pytest.skip("AsyncClient not available")
    async with AsyncClient(app=app, base_url="http://test") as async_test_client:
        yield async_test_client


@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "id": "test-doc-id",
        "user_id": "test-user-id",
        "filename": "test-contract.pdf",
        "file_type": "pdf",
        "file_size": 1024000,
        "status": "uploaded",
        "storage_path": "documents/test-user-id/test-doc-id.pdf",
        "processing_results": {
            "extracted_text": "Sample contract text",
            "extraction_confidence": 0.95,
            "character_count": 1000,
            "word_count": 200
        }
    }


@pytest.fixture
def sample_contract_data():
    """Sample contract data for testing"""
    return {
        "id": "test-contract-id",
        "document_id": "test-doc-id",
        "contract_type": "purchase_agreement",
        "australian_state": "NSW",
        "user_id": "test-user-id"
    }


@pytest.fixture
def sample_analysis_data():
    """Sample analysis data for testing"""
    return {
        "id": "test-analysis-id",
        "contract_id": "test-contract-id",
        "agent_version": "1.0",
        "status": "completed",
        "analysis_result": {
            "contract_terms": {
                "purchase_price": 500000,
                "deposit": 50000,
                "settlement_date": "2024-03-15"
            },
            "risk_assessment": {
                "overall_risk_score": 3,
                "risk_factors": [
                    {
                        "factor": "Short settlement period",
                        "severity": "medium",
                        "description": "Settlement period is shorter than recommended"
                    }
                ]
            },
            "compliance_check": {
                "state_compliance": True,
                "compliance_issues": [],
                "cooling_off_compliance": True
            },
            "recommendations": [
                {
                    "priority": "high",
                    "category": "legal",
                    "recommendation": "Review settlement date with conveyancer",
                    "action_required": True
                }
            ]
        },
        "risk_score": 3,
        "processing_time": 45.2
    }


@pytest.fixture
def sample_onboarding_preferences():
    """Sample onboarding preferences for testing"""
    return {
        "practice_area": "property",
        "jurisdiction": "nsw",
        "firm_size": "small",
        "primary_contract_types": ["Purchase Agreements", "Lease Agreements"]
    }


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Async test marker
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )