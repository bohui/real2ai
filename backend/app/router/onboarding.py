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
async def get_onboarding_status(
    user: User = Depends(get_current_user)
):
    """Get user onboarding status"""
    try:
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)
        
        profile_result = (
            db_client.table("profiles")
            .select(
                "onboarding_completed",
                "onboarding_completed_at",
                "onboarding_preferences",
            )
            .eq("id", user.id)
            .execute()
        )

        if not profile_result.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        profile = profile_result.data[0]
        return OnboardingStatusResponse(
            onboarding_completed=profile.get("onboarding_completed", False),
            onboarding_completed_at=profile.get("onboarding_completed_at"),
            onboarding_preferences=profile.get("onboarding_preferences", {}),
        )

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
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)
        
        # Check if already completed
        profile_result = (
            db_client.table("profiles")
            .select("onboarding_completed")
            .eq("id", user.id)
            .execute()
        )

        if profile_result.data and profile_result.data[0].get(
            "onboarding_completed", False
        ):
            return {"message": "Onboarding already completed", "skip_onboarding": True}

        # Update profile with onboarding completion
        update_data = {
            "onboarding_completed": True,
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
            "onboarding_preferences": request.onboarding_preferences.model_dump(
                exclude_unset=True
            ),
        }

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
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)
        
        update_data = {
            "onboarding_preferences": preferences.model_dump(exclude_unset=True),
        }

        db_client.table("profiles").update(update_data).eq("id", user.id).execute()

        return {"message": "Onboarding preferences updated successfully"}

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Update onboarding preferences error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
