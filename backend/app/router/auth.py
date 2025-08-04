"""Authentication router."""

from fastapi import APIRouter, HTTPException, Depends
import logging

from app.core.auth import User
from app.core.database import get_database_client
from app.schema.auth import UserRegistrationRequest, UserLoginRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register")
async def register_user(user_data: UserRegistrationRequest, db_client=Depends(get_database_client)):
    """Register a new user"""
    try:
        # Create user in Supabase
        user_result = db_client.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "australian_state": user_data.australian_state,
                        "user_type": user_data.user_type,
                    }
                },
            }
        )

        if user_result.user:
            # Create user profile
            profile_data = {
                "id": user_result.user.id,
                "email": user_data.email,
                "australian_state": user_data.australian_state,
                "user_type": user_data.user_type,
                "subscription_status": "free",
                "credits_remaining": 1,  # First contract free
                "onboarding_completed": False,
                "onboarding_preferences": {}
            }

            db_client.table("profiles").insert(profile_data).execute()

            return {
                "user_id": user_result.user.id,
                "email": user_data.email,
                "message": "User registered successfully",
            }
        else:
            raise HTTPException(status_code=400, detail="Registration failed")

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail="Registration failed")


@router.post("/login")
async def login_user(login_data: UserLoginRequest, db_client=Depends(get_database_client)):
    """Authenticate user"""
    try:
        auth_result = db_client.auth.sign_in_with_password(
            {"email": login_data.email, "password": login_data.password}
        )

        if auth_result.user and auth_result.session:
            # Get user profile
            profile_result = (
                db_client.table("profiles")
                .select("*")
                .eq("id", auth_result.user.id)
                .execute()
            )

            return {
                "access_token": auth_result.session.access_token,
                "refresh_token": auth_result.session.refresh_token,
                "user_profile": profile_result.data[0] if profile_result.data else None,
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")