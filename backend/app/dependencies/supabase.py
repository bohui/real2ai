"""
Supabase Client Dependencies for FastAPI

Provides dependency injection for user-authenticated and system-role Supabase clients
with clear separation of concerns and security boundaries.
"""

from typing import Annotated
import logging

from fastapi import Depends, HTTPException, status
from app.clients import get_supabase_client
from app.clients.supabase.client import SupabaseClient
from app.core.auth_context import AuthContext
from app.core.auth import get_current_user, User

logger = logging.getLogger(__name__)


async def get_user_supabase_client() -> SupabaseClient:
    """
    Get Supabase client with user authentication context.
    
    This client will have RLS (Row Level Security) enforced and all operations
    will be scoped to the authenticated user.
    
    Returns:
        SupabaseClient configured with user authentication
        
    Raises:
        HTTPException: If no user authentication context is available
    """
    try:
        # Get user-authenticated client from auth context
        return await AuthContext.get_authenticated_client(require_auth=True)
    except HTTPException:
        # Re-raise auth exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get user Supabase client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize database connection"
        )


async def get_system_supabase_client() -> SupabaseClient:
    """
    Get Supabase client with service role (system) privileges.
    
    WARNING: This client bypasses RLS and has elevated permissions.
    Only use for legitimate system operations like:
    - System maintenance tasks
    - Cross-user aggregations
    - Administrative operations
    - Bucket management
    
    Returns:
        SupabaseClient configured with service role
    """
    try:
        return await get_supabase_client(use_service_role=True)
    except Exception as e:
        logger.error(f"Failed to get system Supabase client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize system database connection"
        )


async def get_optional_user_supabase_client() -> SupabaseClient:
    """
    Get Supabase client with user authentication if available, otherwise service role.
    
    Use this for operations that can work with both user context and system context,
    such as health checks or operations that need to gracefully handle anonymous access.
    
    Returns:
        SupabaseClient with user auth if available, otherwise service role
    """
    try:
        if AuthContext.is_authenticated():
            return await AuthContext.get_authenticated_client(require_auth=True)
        else:
            logger.info("No user authentication available, using service role")
            return await get_supabase_client(use_service_role=True)
    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize database connection"
        )


# Type annotations for dependency injection
UserSupabaseClient = Annotated[SupabaseClient, Depends(get_user_supabase_client)]
SystemSupabaseClient = Annotated[SupabaseClient, Depends(get_system_supabase_client)]
OptionalUserSupabaseClient = Annotated[SupabaseClient, Depends(get_optional_user_supabase_client)]


# Legacy compatibility - gradually migrate away from this
async def get_supabase_client_legacy() -> SupabaseClient:
    """
    Legacy Supabase client dependency.
    
    DEPRECATED: Use UserSupabaseClient or SystemSupabaseClient instead.
    This maintains backward compatibility but should be migrated.
    """
    logger.warning(
        "Using legacy get_supabase_client dependency. "
        "Consider migrating to UserSupabaseClient or SystemSupabaseClient."
    )
    return await get_optional_user_supabase_client()


# Additional dependencies for specific use cases

async def get_authenticated_user_client(
    user: User = Depends(get_current_user),
) -> SupabaseClient:
    """
    Get user Supabase client with explicit user dependency.
    
    This ensures both user authentication and client initialization
    in a single dependency, useful for endpoints that need both.
    
    Args:
        user: Authenticated user from get_current_user dependency
        
    Returns:
        SupabaseClient configured for the authenticated user
    """
    # User dependency ensures authentication
    # Now get the user client
    client = await get_user_supabase_client()
    
    # Log the operation for audit trail
    AuthContext.log_auth_action("database_access", "supabase_client", user.id)
    
    return client


async def get_admin_supabase_client(
    user: User = Depends(get_current_user),
) -> SupabaseClient:
    """
    Get system Supabase client for admin operations.
    
    Ensures user is authenticated (for audit trail) but returns
    system client for operations that need elevated privileges.
    
    Args:
        user: Authenticated user (for audit purposes)
        
    Returns:
        SupabaseClient with system role privileges
    """
    # TODO: Add admin role verification
    # For now, any authenticated user can get admin client
    # In production, add role-based access control
    
    if not hasattr(user, 'roles') or 'admin' not in getattr(user, 'roles', []):
        logger.warning(f"Non-admin user {user.id} requested admin client")
        # For now, allow it but log the access
        
    # Log admin access
    AuthContext.log_auth_action("admin_database_access", "supabase_admin_client", user.id)
    
    return await get_system_supabase_client()


# Convenience type aliases
AuthenticatedUserClient = Annotated[SupabaseClient, Depends(get_authenticated_user_client)]
AdminSupabaseClient = Annotated[SupabaseClient, Depends(get_admin_supabase_client)]