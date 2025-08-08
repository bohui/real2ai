"""Authentication router."""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import logging

from app.core.auth import User, get_current_user_token
from app.clients.factory import get_service_supabase_client
from app.schema.auth import UserRegistrationRequest, UserLoginRequest
from app.core.error_handler import handle_api_error, create_error_context, ErrorCategory
from app.core.config import get_settings
from app.services.backend_token_service import BackendTokenService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register")
async def register_user(
    user_data: UserRegistrationRequest, db_client=Depends(get_service_supabase_client)
):
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
                "onboarding_preferences": {},
            }

            profile_result = db_client.table("profiles").insert(profile_data).execute()

            # Return format consistent with frontend expectations
            return {
                "access_token": (
                    user_result.session.access_token if user_result.session else None
                ),
                "refresh_token": (
                    user_result.session.refresh_token if user_result.session else None
                ),
                "user_profile": (
                    profile_result.data[0] if profile_result.data else profile_data
                ),
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
async def login_user(
    login_data: UserLoginRequest, db_client=Depends(get_service_supabase_client)
):
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

            user_profile = profile_result.data[0] if profile_result.data else None

            settings = get_settings()
            if settings.use_backend_tokens:
                backend_token = BackendTokenService.issue_backend_token(
                    user_id=auth_result.user.id,
                    email=auth_result.user.email,
                    supabase_access_token=auth_result.session.access_token,
                    supabase_refresh_token=auth_result.session.refresh_token,
                    ttl_seconds=settings.jwt_expiration_hours * 3600,
                )
                return {
                    "access_token": backend_token,
                    "token_type": "backend",
                    "user_profile": user_profile,
                }
            else:
                return {
                    "access_token": auth_result.session.access_token,
                    "refresh_token": auth_result.session.refresh_token,
                    "user_profile": user_profile,
                }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    except HTTPException:
        # Re-raise HTTPExceptions (validation errors) without modification
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/refresh")
async def refresh_token(
    refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token"),
    db_client=Depends(get_service_supabase_client),
):
    """Refresh access token using refresh token"""

    context = create_error_context(
        user_id="unknown",
        operation="refresh_token",
        metadata={"has_refresh_token": refresh_token is not None},
    )

    try:
        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Refresh token required. Please provide X-Refresh-Token header.",
            )

        logger.info("Attempting token refresh")

        # Use Supabase refresh session
        refresh_result = db_client.auth.refresh_session(refresh_token)

        if refresh_result.session and refresh_result.user:
            logger.info(f"Token refresh successful for user {refresh_result.user.id}")

            # Get updated user profile
            profile_result = (
                db_client.table("profiles")
                .select("*")
                .eq("id", refresh_result.user.id)
                .execute()
            )

            user_profile = profile_result.data[0] if profile_result.data else None

            return {
                "access_token": refresh_result.session.access_token,
                "refresh_token": refresh_result.session.refresh_token,
                "user_profile": user_profile,
                "expires_in": refresh_result.session.expires_in,
                "message": "Token refreshed successfully",
            }
        else:
            logger.warning("Token refresh failed: No session or user returned")
            raise HTTPException(
                status_code=401, detail="Invalid refresh token. Please log in again."
            )

    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")

        # Check if this is a refresh token expiration
        error_str = str(e).lower()
        if any(
            indicator in error_str
            for indicator in ["expired", "invalid", "unauthorized"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Refresh token expired or invalid. Please log in again.",
            )

        # Use enhanced error handling for other errors
        raise handle_api_error(e, context, ErrorCategory.AUTHENTICATION)


@router.post("/logout")
async def logout_user(
    current_token: str = Depends(get_current_user_token),
    db_client=Depends(get_service_supabase_client),
):
    """Logout user and invalidate tokens"""

    context = create_error_context(
        user_id="unknown",
        operation="logout",
        metadata={"has_token": current_token is not None},
    )

    try:
        logger.info("User logout attempt")

        # Sign out from Supabase (this invalidates the refresh token)
        db_client.auth.sign_out()

        logger.info("User logout successful")

        return {"message": "Logged out successfully", "status": "success"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Even if logout fails, we can return success since the client should clear tokens
        return {"message": "Logged out (with warnings)", "status": "success"}
