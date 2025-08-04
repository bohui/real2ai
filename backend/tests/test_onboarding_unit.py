"""
Unit tests for onboarding functionality
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime, timezone


@pytest.mark.unit
class TestOnboardingStatus:
    """Test onboarding status endpoint"""
    
    def test_get_onboarding_status_not_completed(self, client: TestClient, mock_db_client):
        """Test getting onboarding status when not completed"""
        # Mock profile data
        profile_data = {
            "onboarding_completed": False,
            "onboarding_completed_at": None,
            "onboarding_preferences": {}
        }
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[profile_data]
        )
        
        response = client.get("/api/users/onboarding/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["onboarding_completed"] is False
        assert data["onboarding_completed_at"] is None
        assert data["onboarding_preferences"] == {}
    
    def test_get_onboarding_status_completed(self, client: TestClient, mock_db_client):
        """Test getting onboarding status when completed"""
        completed_at = datetime.now(timezone.utc).isoformat()
        preferences = {
            "practice_area": "property",
            "jurisdiction": "nsw",
            "firm_size": "small"
        }
        
        profile_data = {
            "onboarding_completed": True,
            "onboarding_completed_at": completed_at,
            "onboarding_preferences": preferences
        }
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[profile_data]
        )
        
        response = client.get("/api/users/onboarding/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["onboarding_completed"] is True
        assert data["onboarding_completed_at"] == completed_at
        assert data["onboarding_preferences"] == preferences
    
    def test_get_onboarding_status_no_profile(self, client: TestClient, mock_db_client):
        """Test getting onboarding status when profile doesn't exist"""
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        response = client.get("/api/users/onboarding/status")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "User profile not found"


@pytest.mark.unit
class TestCompleteOnboarding:
    """Test complete onboarding endpoint"""
    
    def test_complete_onboarding_success(self, client: TestClient, mock_db_client, sample_onboarding_preferences):
        """Test successful onboarding completion"""
        # Mock profile check - not completed
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"onboarding_completed": False}]
        )
        
        # Mock successful update and log insertion
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        mock_db_client.table.return_value.insert.return_value.execute.return_value = None
        
        request_data = {
            "onboarding_preferences": sample_onboarding_preferences
        }
        
        response = client.post("/api/users/onboarding/complete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Onboarding completed successfully"
        assert data["skip_onboarding"] is False
        assert data["preferences_saved"] is True
    
    def test_complete_onboarding_already_completed(self, client: TestClient, mock_db_client):
        """Test completing onboarding when already completed"""
        # Mock profile check - already completed
        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"onboarding_completed": True}]
        )
        
        request_data = {
            "onboarding_preferences": {
                "practice_area": "property",
                "jurisdiction": "nsw"
            }
        }
        
        response = client.post("/api/users/onboarding/complete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Onboarding already completed"
        assert data["skip_onboarding"] is True
    
    def test_complete_onboarding_invalid_practice_area(self, client: TestClient):
        """Test completing onboarding with invalid practice area"""
        request_data = {
            "onboarding_preferences": {
                "practice_area": "invalid_area",
                "jurisdiction": "nsw"
            }
        }
        
        response = client.post("/api/users/onboarding/complete", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_complete_onboarding_invalid_jurisdiction(self, client: TestClient):
        """Test completing onboarding with invalid jurisdiction"""
        request_data = {
            "onboarding_preferences": {
                "practice_area": "property",
                "jurisdiction": "invalid"
            }
        }
        
        response = client.post("/api/users/onboarding/complete", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_complete_onboarding_invalid_firm_size(self, client: TestClient):
        """Test completing onboarding with invalid firm size"""
        request_data = {
            "onboarding_preferences": {
                "practice_area": "property",
                "firm_size": "invalid_size"
            }
        }
        
        response = client.post("/api/users/onboarding/complete", json=request_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.unit
class TestUpdateOnboardingPreferences:
    """Test update onboarding preferences endpoint"""
    
    def test_update_preferences_success(self, client: TestClient, mock_db_client):
        """Test successful preferences update"""
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        
        preferences_data = {
            "practice_area": "commercial",
            "jurisdiction": "vic",
            "firm_size": "medium"
        }
        
        response = client.put("/api/users/onboarding/preferences", json=preferences_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Onboarding preferences updated successfully"
    
    def test_update_preferences_partial_update(self, client: TestClient, mock_db_client):
        """Test partial preferences update"""
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        
        preferences_data = {
            "practice_area": "litigation"
        }
        
        response = client.put("/api/users/onboarding/preferences", json=preferences_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Onboarding preferences updated successfully"
    
    def test_update_preferences_empty_data(self, client: TestClient, mock_db_client):
        """Test preferences update with empty data"""
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = None
        
        preferences_data = {}
        
        response = client.put("/api/users/onboarding/preferences", json=preferences_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Onboarding preferences updated successfully"