"""
Test health check endpoint
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_check(client: TestClient):
    """Test health check endpoint returns expected response"""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"
    assert data["environment"] == "testing"


@pytest.mark.unit
def test_health_check_response_format(client: TestClient):
    """Test health check response contains all required fields"""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    required_fields = ["status", "timestamp", "version", "environment"]
    
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Validate timestamp format (ISO format)
    from datetime import datetime
    try:
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail("Invalid timestamp format")