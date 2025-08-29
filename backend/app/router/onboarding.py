"""Onboarding router."""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from uuid import UUID
import logging

from app.core.auth import get_current_user, User
from app.services.repositories.profiles_repository import ProfilesRepository
import json
from app.schema.onboarding import (
    OnboardingStatusResponse,
    OnboardingPreferencesRequest,
    OnboardingCompleteRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(user: User = Depends(get_current_user)):
    """Get user onboarding status"""
    try:
        logger.info(f"[Onboarding] Fetching status for user_id={user.id}")

        # Use repository to fetch onboarding status
        repo = ProfilesRepository()
        profile = await repo.get_profile(user_id=UUID(user.id))

        if not profile:
            logger.error(f"[Onboarding] User profile not found for user_id={user.id}")
            raise HTTPException(status_code=401, detail="User not authenticated")

        def _to_dict(value):
            if value is None:
                return {}
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
            return {}

        response = OnboardingStatusResponse(
            onboarding_completed=profile.onboarding_completed,
            onboarding_completed_at=profile.onboarding_completed_at,
            onboarding_preferences=_to_dict(profile.onboarding_preferences),
        )
        logger.info(
            f"[Onboarding] Status for user_id={user.id}: completed={response.onboarding_completed}, "
            f"completed_at={response.onboarding_completed_at}"
        )
        return response

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Get onboarding status error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/complete")
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    user: User = Depends(get_current_user),
):
    """Complete user onboarding and save preferences"""
    try:
        logger.info(f"[Onboarding] Completing onboarding for user_id={user.id}")

        repo = ProfilesRepository()
        existing = await repo.get_profile(user_id=UUID(user.id))
        if existing and existing.onboarding_completed:
            logger.info(
                f"[Onboarding] Already completed for user_id={user.id}; skipping updates"
            )
            return {"message": "Onboarding already completed", "skip_onboarding": True}

        # Update profile with onboarding completion via repository
        await repo.update_profile(
            user_id=UUID(user.id),
            onboarding_completed=True,
            onboarding_completed_at=datetime.now(timezone.utc),
            onboarding_preferences=request.onboarding_preferences.model_dump(
                exclude_unset=True
            ),
        )

        # Log onboarding completion
        # TODO: migrate usage_logs insertion to repository as well

        logger.info(f"[Onboarding] Onboarding completed for user_id={user.id}")
        return {
            "message": "Onboarding completed successfully",
            "skip_onboarding": False,
            "preferences_saved": True,
        }

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Complete onboarding error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/preferences")
async def update_onboarding_preferences(
    preferences: OnboardingPreferencesRequest,
    user: User = Depends(get_current_user),
):
    """Update user onboarding preferences"""
    try:
        logger.info(f"[Onboarding] Updating preferences for user_id={user.id}")

        repo = ProfilesRepository()
        await repo.update_profile(
            user_id=UUID(user.id),
            onboarding_preferences=preferences.model_dump(exclude_unset=True),
        )

        logger.info(f"[Onboarding] Preferences updated for user_id={user.id}")
        return {"message": "Onboarding preferences updated successfully"}

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Update onboarding preferences error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
