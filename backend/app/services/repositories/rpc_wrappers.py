"""
RPC Wrappers for Essential Database Operations

Centralizes essential RPC calls that must remain in the migration.
These wrappers provide a clean interface while maintaining the RPC functionality.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
import logging
from datetime import datetime

from app.clients.factory import get_supabase_client
from app.core.auth_context import AuthContext

logger = logging.getLogger(__name__)


class StorageRPCWrapper:
    """Wrapper for storage-related RPC operations"""

    @staticmethod
    async def ensure_bucket_exists(
        bucket_name: str, 
        use_service_role: bool = True
    ) -> Dict[str, Any]:
        """
        Ensure storage bucket exists.
        
        Args:
            bucket_name: Name of the bucket
            use_service_role: Whether to use service role (default: True)
            
        Returns:
            Result of bucket creation/validation
        """
        try:
            client = await get_supabase_client(use_service_role=use_service_role)
            result = await client.execute_rpc(
                "ensure_bucket_exists", 
                {"bucket_name": bucket_name}
            )
            
            logger.info(f"Bucket {bucket_name} ensured: {result}")
            return {
                "success": True,
                "bucket_name": bucket_name,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to ensure bucket {bucket_name}: {e}")
            return {
                "success": False,
                "bucket_name": bucket_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    async def check_bucket_access(
        bucket_name: str,
        use_service_role: bool = True
    ) -> Dict[str, Any]:
        """
        Check if bucket is accessible.
        
        Args:
            bucket_name: Name of the bucket
            use_service_role: Whether to use service role
            
        Returns:
            Bucket access status
        """
        try:
            client = await get_supabase_client(use_service_role=use_service_role)
            # Try to list bucket contents (limited) to test access
            result = await client.storage.from_(bucket_name).list(limit=1)
            
            return {
                "success": True,
                "bucket_name": bucket_name,
                "accessible": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Bucket {bucket_name} access check failed: {e}")
            return {
                "success": False,
                "bucket_name": bucket_name,
                "accessible": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class SystemRPCWrapper:
    """Wrapper for system-level RPC operations"""

    @staticmethod
    async def cleanup_expired_documents(
        days_old: int = 30,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up expired documents.
        
        Args:
            days_old: Age threshold in days
            dry_run: If True, only count without deleting
            
        Returns:
            Cleanup results
        """
        try:
            # Always use service role for system operations
            client = await get_supabase_client(use_service_role=True)
            result = await client.execute_rpc(
                "cleanup_expired_documents", 
                {
                    "days_old": days_old,
                    "dry_run": dry_run
                }
            )
            
            logger.info(f"Document cleanup ({'dry run' if dry_run else 'executed'}): {result}")
            return {
                "success": True,
                "days_old": days_old,
                "dry_run": dry_run,
                "deleted_count": result.get("deleted_count", 0),
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document cleanup failed: {e}")
            return {
                "success": False,
                "days_old": days_old,
                "dry_run": dry_run,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    async def generate_system_analytics() -> Dict[str, Any]:
        """
        Generate system-wide analytics.
        
        Returns:
            System analytics data
        """
        try:
            # System analytics require service role
            client = await get_supabase_client(use_service_role=True)
            result = await client.execute_rpc("generate_system_analytics", {})
            
            logger.info("System analytics generated successfully")
            return {
                "success": True,
                "analytics": result.get("data", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System analytics generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    async def health_check() -> Dict[str, Any]:
        """
        Database health check via RPC.
        
        Returns:
            Health check results
        """
        try:
            client = await get_supabase_client(use_service_role=True)
            result = await client.execute_rpc("health_check", {})
            
            return {
                "success": True,
                "database": "healthy",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "success": False,
                "database": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class UserRPCWrapper:
    """Wrapper for user-scoped RPC operations"""

    def __init__(self, user_id: Optional[UUID] = None):
        """
        Initialize user RPC wrapper.
        
        Args:
            user_id: Optional user ID (uses auth context if not provided)
        """
        self.user_id = user_id

    async def get_user_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get user statistics via RPC.
        
        Args:
            user_id: User ID (uses instance user_id if not provided)
            
        Returns:
            User statistics
        """
        target_user_id = user_id or self.user_id or AuthContext.get_user_id()
        
        try:
            # Use user-scoped client for user statistics
            client = await AuthContext.get_authenticated_client()
            result = await client.execute_rpc(
                "get_user_statistics", 
                {"target_user_id": str(target_user_id)}
            )
            
            return {
                "success": True,
                "user_id": str(target_user_id),
                "statistics": result.get("data", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"User statistics retrieval failed for {target_user_id}: {e}")
            return {
                "success": False,
                "user_id": str(target_user_id) if target_user_id else None,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def update_user_metrics(
        self, 
        metrics: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Update user metrics via RPC.
        
        Args:
            metrics: Metrics to update
            user_id: User ID (uses instance user_id if not provided)
            
        Returns:
            Update results
        """
        target_user_id = user_id or self.user_id or AuthContext.get_user_id()
        
        try:
            client = await AuthContext.get_authenticated_client()
            result = await client.execute_rpc(
                "update_user_metrics",
                {
                    "target_user_id": str(target_user_id),
                    "metrics_data": metrics
                }
            )
            
            return {
                "success": True,
                "user_id": str(target_user_id),
                "updated": True,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"User metrics update failed for {target_user_id}: {e}")
            return {
                "success": False,
                "user_id": str(target_user_id) if target_user_id else None,
                "updated": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Convenience functions for common operations
async def ensure_documents_bucket() -> Dict[str, Any]:
    """Ensure documents bucket exists."""
    return await StorageRPCWrapper.ensure_bucket_exists("documents")


async def cleanup_old_documents(days: int = 30, dry_run: bool = False) -> Dict[str, Any]:
    """Clean up documents older than specified days."""
    return await SystemRPCWrapper.cleanup_expired_documents(days, dry_run)


async def check_database_health() -> Dict[str, Any]:
    """Check database health via RPC."""
    return await SystemRPCWrapper.health_check()


async def get_system_analytics() -> Dict[str, Any]:
    """Generate system analytics."""
    return await SystemRPCWrapper.generate_system_analytics()


# Usage examples and documentation
class RPCWrapperUsage:
    """
    Usage examples for RPC wrappers.
    
    These wrappers centralize essential RPC operations that cannot be easily
    migrated to repositories due to their system-level nature or storage requirements.
    
    Example Usage:
    
    # Storage operations
    result = await ensure_documents_bucket()
    access = await StorageRPCWrapper.check_bucket_access("documents")
    
    # System operations  
    cleanup = await cleanup_old_documents(days=30, dry_run=True)
    analytics = await get_system_analytics()
    health = await check_database_health()
    
    # User operations
    user_rpc = UserRPCWrapper(user_id=user_id)
    stats = await user_rpc.get_user_statistics()
    metrics_result = await user_rpc.update_user_metrics({"documents_processed": 10})
    """
    pass