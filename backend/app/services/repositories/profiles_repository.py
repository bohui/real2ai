"""
Profiles Repository - User profile operations

This repository handles user profile operations with proper RLS enforcement.
"""

from typing import Dict, Optional, Any
import json
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
import logging

from app.database.connection import get_user_connection
from app.models.supabase_models import Profile as UserProfile
from app.utils.json_utils import safe_json_loads

logger = logging.getLogger(__name__)


@dataclass
class ProfileSettings:
    """User settings model - temporary until proper settings table is implemented"""

    user_id: UUID
    notifications_enabled: bool = True
    email_notifications: bool = True
    processing_notifications: bool = True
    marketing_emails: bool = False
    theme: str = "system"  # "light", "dark", "system"
    language: str = "en"
    timezone: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfilesRepository:
    """
    Repository for user profile operations.

    Uses proper context managers for all database operations
    to ensure connections are properly released back to the pool.
    """

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize profiles repository.

        Args:
            user_id: Optional user ID (uses auth context if not provided)
        """
        self.user_id = user_id

    # ================================
    # USER PROFILES
    # ================================

    async def get_profile(
        self, user_id: Optional[UUID] = None
    ) -> Optional[UserProfile]:
        """
        Get user profile by ID.
        """
        target_user_id = user_id or self.user_id

        async with get_user_connection(target_user_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    id,
                    email,
                    full_name,
                    phone_number,
                    australian_state,
                    user_type,
                    user_role,
                    subscription_status,
                    credits_remaining,
                    organization,
                    preferences,
                    onboarding_completed,
                    onboarding_completed_at,
                    onboarding_preferences,
                    created_at,
                    updated_at
                FROM profiles
                WHERE id = $1
                """,
                target_user_id,
            )

            if not row:
                return None

            return UserProfile(
                id=row["id"],
                email=row["email"],
                full_name=row["full_name"],
                phone_number=row["phone_number"],
                australian_state=row["australian_state"],
                user_type=row["user_type"],
                user_role=row["user_role"],
                subscription_status=row["subscription_status"],
                credits_remaining=row["credits_remaining"],
                organization=row["organization"],
                preferences=safe_json_loads(row["preferences"], {}),
                onboarding_completed=row["onboarding_completed"],
                onboarding_completed_at=row["onboarding_completed_at"],
                onboarding_preferences=safe_json_loads(
                    row["onboarding_preferences"], {}
                ),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def create_profile(
        self, user_id: UUID, email: str, full_name: Optional[str] = None, **kwargs
    ) -> UserProfile:
        """
        Create a new user profile.

        Args:
            user_id: User ID
            email: User email
            full_name: User's full name
            **kwargs: Additional profile fields

        Returns:
            Created UserProfile
        """
        async with get_user_connection(user_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO profiles (
                    id, email, full_name, phone_number, australian_state, user_type,
                    user_role, subscription_status, credits_remaining, organization, preferences,
                    onboarding_completed, onboarding_completed_at, onboarding_preferences
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id, email, full_name, phone_number, australian_state, user_type,
                          user_role, subscription_status, credits_remaining, organization, preferences,
                          onboarding_completed, onboarding_completed_at, onboarding_preferences,
                          created_at, updated_at
                """,
                user_id,
                email,
                full_name,
                kwargs.get("phone_number"),
                kwargs.get("australian_state", "NSW"),
                kwargs.get("user_type", "buyer"),
                kwargs.get("user_role", "user"),
                kwargs.get("subscription_status", "free"),
                kwargs.get("credits_remaining", 1),
                kwargs.get("organization"),
                json.dumps(kwargs.get("preferences", {})),
                kwargs.get("onboarding_completed", False),
                kwargs.get("onboarding_completed_at"),
                json.dumps(kwargs.get("onboarding_preferences", {})),
            )

            return UserProfile(
                id=row["id"],
                email=row["email"],
                full_name=row["full_name"],
                phone_number=row["phone_number"],
                australian_state=row["australian_state"],
                user_type=row["user_type"],
                user_role=row["user_role"],
                subscription_status=row["subscription_status"],
                credits_remaining=row["credits_remaining"],
                organization=row["organization"],
                preferences=safe_json_loads(row["preferences"], {}),
                onboarding_completed=row["onboarding_completed"],
                onboarding_completed_at=row["onboarding_completed_at"],
                onboarding_preferences=safe_json_loads(
                    row["onboarding_preferences"], {}
                ),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def update_profile(
        self,
        user_id: Optional[UUID] = None,
        **updates,
    ) -> Optional[UserProfile]:
        """
        Update user profile fields.
        """
        target_user_id = user_id or self.user_id

        if not updates:
            return await self.get_profile(target_user_id)

        async with get_user_connection(target_user_id) as conn:
            # Build dynamic update query
            set_clauses = []
            params = []
            param_count = 0

            # Note: user_role is intentionally excluded from self-updates
            updateable_fields = [
                "full_name",
                "phone_number",
                "australian_state",
                "user_type",
                "subscription_status",
                "credits_remaining",
                "organization",
                "preferences",
                "onboarding_completed",
                "onboarding_completed_at",
                "onboarding_preferences",
            ]

            for field, value in updates.items():
                if field in updateable_fields:
                    param_count += 1
                    set_clauses.append(f"{field} = ${param_count}")

                    # Handle JSON fields - serialize dictionaries to JSON strings
                    if field in [
                        "preferences",
                        "onboarding_preferences",
                    ] and isinstance(value, dict):
                        params.append(json.dumps(value))
                    else:
                        params.append(value)

            if not set_clauses:
                return await self.get_profile(target_user_id)

            # Add updated_at and user_id
            set_clauses.append("updated_at = now()")
            param_count += 1
            params.append(target_user_id)

            query = f"""
                UPDATE profiles 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING 
                    id,
                    email,
                    full_name,
                    phone_number,
                    australian_state,
                    user_type,
                    user_role,
                    subscription_status,
                    credits_remaining,
                    organization,
                    preferences,
                    onboarding_completed,
                    onboarding_completed_at,
                    onboarding_preferences,
                    created_at,
                    updated_at
            """

            row = await conn.fetchrow(query, *params)

            if not row:
                return None

            return UserProfile(
                id=row["id"],
                email=row["email"],
                full_name=row["full_name"],
                phone_number=row["phone_number"],
                australian_state=row["australian_state"],
                user_type=row["user_type"],
                user_role=row["user_role"],
                subscription_status=row["subscription_status"],
                credits_remaining=row["credits_remaining"],
                organization=row["organization"],
                preferences=safe_json_loads(row["preferences"], {}),
                onboarding_completed=row["onboarding_completed"],
                onboarding_completed_at=row["onboarding_completed_at"],
                onboarding_preferences=safe_json_loads(
                    row["onboarding_preferences"], {}
                ),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def delete_profile(self, user_id: Optional[UUID] = None) -> bool:
        """
        Delete user profile.

        Args:
            user_id: User ID (uses instance user_id if not provided)

        Returns:
            True if deleted, False if not found
        """
        target_user_id = user_id or self.user_id

        async with get_user_connection(target_user_id) as conn:
            result = await conn.execute(
                "DELETE FROM profiles WHERE id = $1", target_user_id
            )
            return result.split()[-1] == "1"

    # ================================
    # ONBOARDING OPERATIONS
    # ================================

    async def update_onboarding_step(
        self, step: str, user_id: Optional[UUID] = None
    ) -> Optional[UserProfile]:
        """
        Update user's onboarding step.

        Args:
            step: Onboarding step name
            user_id: User ID (uses instance user_id if not provided)

        Returns:
            Updated UserProfile if successful
        """
        return await self.update_profile(
            user_id=user_id, onboarding_preferences={"current_step": step}
        )

    async def complete_onboarding(
        self, user_id: Optional[UUID] = None
    ) -> Optional[UserProfile]:
        """
        Mark user's onboarding as completed.

        Args:
            user_id: User ID (uses instance user_id if not provided)

        Returns:
            Updated UserProfile if successful
        """
        return await self.update_profile(
            user_id=user_id,
            onboarding_completed=True,
            onboarding_completed_at=datetime.now(),
            onboarding_preferences={"current_step": "completed"},
        )

    # ================================
    # USER SETTINGS
    # ================================

    async def get_settings(
        self, user_id: Optional[UUID] = None
    ) -> Optional[ProfileSettings]:
        """
        Get user settings.

        Args:
            user_id: User ID (uses instance user_id if not provided)

        Returns:
            ProfileSettings if found, None otherwise
        """
        target_user_id = user_id or self.user_id

        async with get_user_connection(target_user_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, notifications_enabled, email_notifications,
                       processing_notifications, marketing_emails, theme, language,
                       timezone, settings, created_at, updated_at
                FROM user_settings
                WHERE user_id = $1
                """,
                target_user_id,
            )

            if not row:
                return None

            return ProfileSettings(
                user_id=row["user_id"],
                notifications_enabled=row["notifications_enabled"],
                email_notifications=row["email_notifications"],
                processing_notifications=row["processing_notifications"],
                marketing_emails=row["marketing_emails"],
                theme=row["theme"],
                language=row["language"],
                timezone=row["timezone"],
                settings=row["settings"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def create_or_update_settings(
        self, user_id: Optional[UUID] = None, **settings_updates
    ) -> ProfileSettings:
        """
        Create or update user settings.

        Args:
            user_id: User ID (uses instance user_id if not provided)
            **settings_updates: Settings fields to update

        Returns:
            ProfileSettings (created or updated)
        """
        target_user_id = user_id or self.user_id

        async with get_user_connection(target_user_id) as conn:
            # Upsert settings
            row = await conn.fetchrow(
                """
                INSERT INTO user_settings (
                    user_id, notifications_enabled, email_notifications,
                    processing_notifications, marketing_emails, theme, language,
                    timezone, settings
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id) DO UPDATE SET
                    notifications_enabled = COALESCE(EXCLUDED.notifications_enabled, user_settings.notifications_enabled),
                    email_notifications = COALESCE(EXCLUDED.email_notifications, user_settings.email_notifications),
                    processing_notifications = COALESCE(EXCLUDED.processing_notifications, user_settings.processing_notifications),
                    marketing_emails = COALESCE(EXCLUDED.marketing_emails, user_settings.marketing_emails),
                    theme = COALESCE(EXCLUDED.theme, user_settings.theme),
                    language = COALESCE(EXCLUDED.language, user_settings.language),
                    timezone = COALESCE(EXCLUDED.timezone, user_settings.timezone),
                    settings = COALESCE(EXCLUDED.settings, user_settings.settings),
                    updated_at = now()
                RETURNING user_id, notifications_enabled, email_notifications,
                          processing_notifications, marketing_emails, theme, language,
                          timezone, settings, created_at, updated_at
                """,
                target_user_id,
                settings_updates.get("notifications_enabled", True),
                settings_updates.get("email_notifications", True),
                settings_updates.get("processing_notifications", True),
                settings_updates.get("marketing_emails", False),
                settings_updates.get("theme", "system"),
                settings_updates.get("language", "en"),
                settings_updates.get("timezone"),
                settings_updates.get("settings"),
            )

            return ProfileSettings(
                user_id=row["user_id"],
                notifications_enabled=row["notifications_enabled"],
                email_notifications=row["email_notifications"],
                processing_notifications=row["processing_notifications"],
                marketing_emails=row["marketing_emails"],
                theme=row["theme"],
                language=row["language"],
                timezone=row["timezone"],
                settings=row["settings"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    # ================================
    # UTILITY METHODS
    # ================================

    async def profile_exists(self, user_id: Optional[UUID] = None) -> bool:
        """
        Check if user profile exists.

        Args:
            user_id: User ID (uses instance user_id if not provided)

        Returns:
            True if profile exists
        """
        target_user_id = user_id or self.user_id

        async with get_user_connection(target_user_id) as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM profiles WHERE id = $1)", target_user_id
            )
            return bool(result)

    async def get_profile_summary(
        self, user_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get profile summary for display.

        Args:
            user_id: User ID (uses instance user_id if not provided)

        Returns:
            Profile summary dict or None
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return None

        return {
            "user_id": str(profile.id),
            "email": profile.email,
            "full_name": profile.full_name,
            "organization": profile.organization,
            "onboarding_completed": profile.onboarding_completed,
            "created_at": (
                profile.created_at.isoformat() if profile.created_at else None
            ),
        }
