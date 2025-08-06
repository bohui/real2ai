"""User management router."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

from app.core.auth import get_current_user, User
from app.clients.factory import get_supabase_client

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
    db_client=Depends(get_supabase_client)
):
    """Update user profile"""
    try:
        # Update user profile in database
        allowed_fields = [
            "full_name", "phone_number", "organization", 
            "australian_state", "user_type", "preferences"
        ]
        
        # Filter update data to only allowed fields
        update_data = {k: v for k, v in user_data.items() if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        # Update in database
        result = db_client.table("profiles").update(update_data).eq("id", user.id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User profile not found")
            
        # Return updated profile
        updated_profile = result.data[0]
        return updated_profile
        
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any], user: User = Depends(get_current_user), db_client=Depends(get_supabase_client)
):
    """Update user preferences"""
    try:
        db_client.table("profiles").update({"preferences": preferences}).eq(
            "id", user.id
        ).execute()
        return {"message": "Preferences updated successfully"}

    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage-stats")
async def get_usage_stats(user: User = Depends(get_current_user), db_client=Depends(get_supabase_client)):
    """Get user usage statistics"""

    try:
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