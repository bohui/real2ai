"""Onboarding router."""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import logging

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
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
        
        # Use the working user data directly since get_current_user already fetched the profile
        response = OnboardingStatusResponse(
            onboarding_completed=user.onboarding_completed,
            onboarding_completed_at=user.onboarding_completed_at,
            onboarding_preferences=user.onboarding_preferences,
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
        
        # Check if already completed
        if user.onboarding_completed:
            logger.info(
                f"[Onboarding] Already completed for user_id={user.id}; skipping updates"
            )
            return {"message": "Onboarding already completed", "skip_onboarding": True}

        # Get authenticated client for database operations
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Update profile with onboarding completion
        update_data = {
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
            "onboarding_preferences": request.onboarding_preferences.model_dump(
                exclude_unset=True
            ),
        }
        logger.debug(
            f"[Onboarding] Updating profile for user_id={user.id} with keys={list(update_data.keys())}"
        )

        db_client.table("profiles").update(update_data).eq("id", user.id).execute()

        # Log onboarding completion
        db_client.table("usage_logs").insert(
            {
                "user_id": user.id,
                "action_type": "onboarding_completed",
                "credits_used": 0,
                "credits_remaining": user.credits_remaining,
                "resource_used": "onboarding",
                "metadata": {
                    "preferences": request.onboarding_preferences.model_dump(
                        exclude_unset=True
                    )
                },
            }
        ).execute()

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
        
        # Get authenticated client for database operations
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        update_data = {
            "onboarding_preferences": preferences.model_dump(exclude_unset=True),
        }
        logger.debug(
            f"[Onboarding] Preferences update payload for user_id={user.id}: {update_data['onboarding_preferences']}"
        )

        db_client.table("profiles").update(update_data).eq("id", user.id).execute()

        logger.info(f"[Onboarding] Preferences updated for user_id={user.id}")
        return {"message": "Onboarding preferences updated successfully"}

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Update onboarding preferences error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
