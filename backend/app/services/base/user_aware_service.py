"""
Base Service Classes for User-Aware Operations

Provides base classes for services that need to handle both user-scoped
and system-level operations with proper authentication context management.
"""

import logging
from typing import Optional
from abc import ABC, abstractmethod

from app.clients.supabase.client import SupabaseClient
from app.clients import get_supabase_client
from app.core.auth_context import AuthContext

logger = logging.getLogger(__name__)


class UserAwareService(ABC):
    """
    Base class for services that primarily operate in user context.
    
    This class provides methods to get both user-authenticated and system-level
    Supabase clients, with user context being the default.
    
    Services inheriting from this class should prefer user operations
    and only use system operations when absolutely necessary.
    """
    
    def __init__(self, user_client: Optional[SupabaseClient] = None):
        """
        Initialize user-aware service.
        
        Args:
            user_client: Optional pre-initialized user client (for dependency injection)
        """
        self._user_client = user_client
        self._system_client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def get_user_client(self) -> SupabaseClient:
        """
        Get user-authenticated Supabase client.
        
        This client will respect RLS policies and operate within the
        authenticated user's permissions.
        
        Returns:
            SupabaseClient with user authentication
            
        Raises:
            HTTPException: If no user authentication available
        """
        if self._user_client:
            return self._user_client
        
        return await AuthContext.get_authenticated_client(require_auth=True)
    
    async def get_system_client(self) -> SupabaseClient:
        """
        Get system-level Supabase client.
        
        WARNING: This client bypasses RLS and has elevated permissions.
        Use only for legitimate system operations.
        
        Returns:
            SupabaseClient with service role privileges
        """
        if not self._system_client:
            self._system_client = await get_supabase_client(use_service_role=True)
        
        return self._system_client
    
    async def get_client_for_operation(self, requires_system_role: bool = False) -> SupabaseClient:
        """
        Get appropriate client based on operation requirements.
        
        Args:
            requires_system_role: If True, returns system client
            
        Returns:
            Appropriate SupabaseClient for the operation
        """
        if requires_system_role:
            self.logger.debug("Operation requires system role, getting system client")
            return await self.get_system_client()
        else:
            return await self.get_user_client()
    
    def is_user_authenticated(self) -> bool:
        """Check if user is authenticated in current context."""
        return AuthContext.is_authenticated()
    
    def get_current_user_id(self) -> Optional[str]:
        """Get current user ID from auth context."""
        return AuthContext.get_user_id()
    
    def log_operation(self, operation: str, resource_type: str, resource_id: Optional[str] = None):
        """Log service operation for audit trail."""
        AuthContext.log_auth_action(operation, resource_type, resource_id)
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the service.
        
        Services must implement this method to perform any necessary
        initialization steps.
        """
        pass
    
    async def cleanup(self) -> None:
        """
        Clean up service resources.
        
        Override this method if the service needs cleanup.
        """
        if self._system_client:
            await self._system_client.close()
            self._system_client = None


class SystemService(ABC):
    """
    Base class for services that primarily operate at system level.
    
    These services typically handle:
    - System maintenance
    - Cross-user aggregations
    - Administrative operations
    - Infrastructure management
    
    Use this base class when the service legitimately needs system-level
    access for most of its operations.
    """
    
    def __init__(self):
        """Initialize system service."""
        self._system_client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def get_system_client(self) -> SupabaseClient:
        """
        Get system-level Supabase client.
        
        Returns:
            SupabaseClient with service role privileges
        """
        if not self._system_client:
            self._system_client = await get_supabase_client(use_service_role=True)
        
        return self._system_client
    
    def log_system_operation(
        self, 
        operation: str, 
        resource_type: str, 
        resource_id: Optional[str] = None,
        initiated_by: Optional[str] = None
    ):
        """
        Log system operation for audit trail.
        
        Args:
            operation: Operation being performed
            resource_type: Type of resource
            resource_id: Optional resource ID
            initiated_by: Optional user ID who initiated the operation
        """
        self.logger.info(
            f"System operation: {operation} on {resource_type}",
            extra={
                "operation": operation,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "initiated_by": initiated_by,
                "service": self.__class__.__name__,
                "system_operation": True,
            }
        )
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the system service."""
        pass
    
    async def cleanup(self) -> None:
        """Clean up system service resources."""
        if self._system_client:
            await self._system_client.close()
            self._system_client = None


class HybridService(UserAwareService):
    """
    Base class for services that need both user and system operations.
    
    This extends UserAwareService to provide clear patterns for services
    that need to perform both user-scoped and system-level operations.
    
    Use this when a service needs to:
    - Perform user operations (default)
    - Occasionally perform system operations (explicit)
    - Clearly separate the two types of operations
    """
    
    async def perform_user_operation(self, operation_func, *args, **kwargs):
        """
        Perform operation in user context.
        
        Args:
            operation_func: Async function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Result of the operation
        """
        client = await self.get_user_client()
        return await operation_func(client, *args, **kwargs)
    
    async def perform_system_operation(
        self, 
        operation_func, 
        *args, 
        reason: str = None,
        **kwargs
    ):
        """
        Perform operation in system context.
        
        Args:
            operation_func: Async function to execute
            reason: Reason for using system privileges (for audit)
            *args, **kwargs: Arguments for the function
            
        Returns:
            Result of the operation
        """
        if reason:
            self.logger.info(f"System operation: {reason}")
        
        client = await self.get_system_client()
        return await operation_func(client, *args, **kwargs)


class ServiceInitializationMixin:
    """
    Mixin for common service initialization patterns.
    """
    
    async def ensure_dependencies(self, *dependencies):
        """
        Ensure all dependencies are initialized.
        
        Args:
            *dependencies: Services or clients to initialize
        """
        for dependency in dependencies:
            if hasattr(dependency, 'initialize') and not getattr(dependency, '_initialized', False):
                await dependency.initialize()
    
    async def health_check(self) -> dict:
        """
        Basic health check for services.
        
        Override this method to add service-specific health checks.
        """
        return {
            "service": self.__class__.__name__,
            "status": "healthy",
            "authenticated": getattr(self, 'is_user_authenticated', lambda: False)(),
        }