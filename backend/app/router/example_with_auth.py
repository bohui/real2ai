"""
Example API endpoint demonstrating the new authentication context pattern.

This file shows how to properly use the context-based authentication
system with Supabase RLS in FastAPI endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
import logging

from app.core.auth import get_current_user, User
from app.core.auth_context import AuthContext
from app.services.document_service import DocumentService
from app.clients import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/example", tags=["example"])


@router.get("/protected-data")
async def get_protected_data(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Example endpoint showing automatic RLS enforcement.
    
    The auth token is automatically extracted by middleware and
    used by the Supabase client for RLS enforcement.
    """
    try:
        # Log the auth action
        AuthContext.log_auth_action("read", "user_data", user.id)
        
        # Get authenticated Supabase client from context
        supabase_client = await AuthContext.get_authenticated_client()
        
        # Query will automatically be scoped to the authenticated user
        # thanks to RLS policies
        result = await supabase_client.database.select(
            "user_documents",
            columns=["id", "title", "created_at"],
            filters={"user_id": user.id}  # This is redundant with RLS but shown for clarity
        )
        
        return {
            "user_id": user.id,
            "documents": result.get("data", []),
            "count": result.get("count", 0),
            "auth_context": {
                "is_authenticated": AuthContext.is_authenticated(),
                "user_email": AuthContext.get_user_email(),
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch protected data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch data"
        )


@router.post("/create-document")
async def create_document(
    document_data: Dict[str, Any],
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Example of creating a resource with automatic user association.
    
    The document service will use the auth context to ensure
    proper RLS enforcement during file upload and database operations.
    """
    try:
        # Initialize document service (auth handled by context)
        document_service = DocumentService()
        await document_service.initialize()
        
        # Process document - user association happens automatically via RLS
        result = await document_service.create_document(
            title=document_data.get("title"),
            content=document_data.get("content"),
            user_id=user.id,  # Still passed for application logic
        )
        
        return {
            "success": True,
            "document_id": result.get("id"),
            "message": "Document created successfully with RLS protection"
        }
        
    except Exception as e:
        logger.error(f"Failed to create document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document"
        )


@router.get("/mixed-access")
async def mixed_access_endpoint(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Example showing mixed access patterns - some operations with user context,
    others with service role for administrative tasks.
    """
    try:
        # User-scoped operation
        user_data = await _get_user_specific_data(user.id)
        
        # Administrative operation (requires service role)
        system_stats = await _get_system_statistics()
        
        return {
            "user_data": user_data,
            "system_stats": system_stats,
            "auth_info": {
                "user_id": AuthContext.get_user_id(),
                "has_admin_access": False,  # Regular users don't have admin access
            }
        }
        
    except Exception as e:
        logger.error(f"Mixed access operation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Operation failed"
        )


async def _get_user_specific_data(user_id: str) -> Dict[str, Any]:
    """Helper function for user-scoped data access."""
    # Uses auth context for RLS
    supabase_client = await AuthContext.get_authenticated_client()
    
    result = await supabase_client.database.select(
        "user_preferences",
        columns=["*"],
        filters={"user_id": user_id}
    )
    
    return result.get("data", {})


async def _get_system_statistics() -> Dict[str, Any]:
    """Helper function for system-wide statistics (requires service role)."""
    # Get service role client (bypasses RLS)
    supabase_client = await get_supabase_client(use_service_role=True)
    
    # This query accesses all users' data (admin operation)
    result = await supabase_client.database.execute_rpc(
        "get_system_statistics",
        {}
    )
    
    return result.get("data", {})


@router.get("/verify-auth-context")
async def verify_auth_context(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Diagnostic endpoint to verify auth context is properly set.
    
    Useful for debugging authentication issues.
    """
    return {
        "auth_context": {
            "is_authenticated": AuthContext.is_authenticated(),
            "user_token_present": AuthContext.get_user_token() is not None,
            "user_id_from_context": AuthContext.get_user_id(),
            "user_id_from_dependency": user.id,
            "user_email": AuthContext.get_user_email(),
            "metadata": AuthContext.get_auth_metadata(),
        },
        "user_info": {
            "id": user.id,
            "email": user.email,
            "roles": getattr(user, "roles", []),
        }
    }


# Example of a decorator for endpoints requiring specific permissions
def require_admin(func):
    """Decorator to require admin role for an endpoint."""
    async def wrapper(*args, user: User = None, **kwargs):
        if not user or "admin" not in getattr(user, "roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return await func(*args, user=user, **kwargs)
    return wrapper


@router.delete("/admin/clear-cache")
@require_admin
async def clear_cache(
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Example admin endpoint with role-based access control.
    
    This demonstrates how to combine RLS with application-level
    permission checks.
    """
    # Log admin action
    AuthContext.log_auth_action("admin_action", "cache_clear", None)
    
    # Perform admin operation with service role
    supabase_client = await get_supabase_client(use_service_role=True)
    
    # Clear cache or perform other admin tasks
    result = await supabase_client.database.execute_rpc(
        "clear_application_cache",
        {"cleared_by": user.id}
    )
    
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "cleared_by": user.id,
        "timestamp": result.get("timestamp"),
    }