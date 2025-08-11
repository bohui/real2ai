"""User management router."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.services.repositories.profiles_repository import ProfilesRepository
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/profile")
async def get_user_profile(user: User = Depends(get_current_user)):
    """Get user profile"""
    return user.model_dump()


@router.patch("/profile")
async def update_user_profile(
    user_data: Dict[str, Any],
    user: User = Depends(get_current_user),
):
    """Update user profile"""
    try:
        # Update user profile in database via repository
        allowed_fields = [
            "full_name",
            "phone_number",
            "organization",
            "australian_state",
            "user_type",
            "preferences",
        ]

        # Filter update data to only allowed fields
        update_data = {k: v for k, v in user_data.items() if k in allowed_fields}

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        repo = ProfilesRepository()
        updated = await repo.update_profile(user_id=user.id, **update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="User profile not found")

        return {
            "id": str(updated.user_id),
            "email": updated.email,
            "full_name": updated.full_name,
            "phone_number": updated.phone_number,
            "organization": updated.organization,
            "australian_state": updated.australian_state,
            "user_type": updated.user_type,
            "subscription_status": updated.subscription_status,
            "credits_remaining": updated.credits_remaining,
            "preferences": updated.preferences,
        }

    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any], user: User = Depends(get_current_user)
):
    """Update user preferences"""
    try:
        repo = ProfilesRepository()
        await repo.update_profile(user_id=user.id, preferences=preferences)
        return {"message": "Preferences updated successfully"}

    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage-stats")
async def get_usage_stats(user: User = Depends(get_current_user)):
    """Get user usage statistics"""

    try:
        # Get authenticated client
        db_client = await AuthContext.get_authenticated_client(require_auth=True)

        # Get usage logs
        usage_result = (
            db_client.table("usage_logs")
            .select("*")
            .eq("user_id", user.id)
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )

        # Get contract count
        contracts_result = (
            db_client.from_("documents")
            .select("count", count="exact")
            .eq("user_id", user.id)
            .execute()
        )

        return {
            "credits_remaining": user.credits_remaining,
            "subscription_status": user.subscription_status,
            "total_contracts_analyzed": contracts_result.count,
            "recent_usage": usage_result.data,
        }

    except Exception as e:
        logger.error(f"Usage stats error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
