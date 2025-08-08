"""
Client factory for dependency injection and client management.
"""

import logging
from typing import Dict, Any, Optional, Type, Callable
from functools import lru_cache

from .base.client import BaseClient
from .base.exceptions import ClientError

# Import all client implementations
from .supabase import SupabaseClient, SupabaseClientConfig, SupabaseSettings
from .gemini import GeminiClient, GeminiClientConfig, GeminiSettings
from .openai import OpenAIClient, OpenAIClientConfig, OpenAISettings
from .domain import DomainClient, DomainClientConfig, DomainSettings
from .corelogic import CoreLogicClient, CoreLogicClientConfig, CoreLogicSettings

logger = logging.getLogger(__name__)


class ClientFactory:
    """Factory class for creating and managing external service clients."""

    def __init__(self):
        self._clients: Dict[str, BaseClient] = {}
        self._client_configs: Dict[str, Any] = {}
        self._client_classes: Dict[str, Type[BaseClient]] = {
            "supabase": SupabaseClient,
            "gemini": GeminiClient,
            "openai": OpenAIClient,
            "domain": DomainClient,
            "corelogic": CoreLogicClient,
        }
        self._config_classes: Dict[str, Type] = {
            "supabase": SupabaseSettings,
            "gemini": GeminiSettings,
            "openai": OpenAISettings,
            "domain": DomainSettings,
            "corelogic": CoreLogicSettings,
        }
        self._initialized = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register_client(
        self, name: str, client_class: Type[BaseClient], config_class: Type = None
    ) -> None:
        """Register a new client type with the factory."""
        self._client_classes[name] = client_class
        if config_class:
            self._config_classes[name] = config_class
        self.logger.info(f"Registered client type: {name}")

    def _load_config(self, client_name: str) -> Any:
        """Load configuration for a client."""
        if client_name not in self._config_classes:
            raise ClientError(
                f"No configuration class registered for client: {client_name}"
            )

        config_class = self._config_classes[client_name]

        try:
            # Load configuration from environment
            settings = config_class()

            # Convert to client config if needed
            if hasattr(settings, "to_client_config"):
                return settings.to_client_config()
            else:
                return settings

        except Exception as e:
            self.logger.error(f"Failed to load configuration for {client_name}: {e}")
            raise ClientError(
                f"Failed to load configuration for {client_name}: {str(e)}",
                client_name=client_name,
                original_error=e,
            )

    def get_client(self, name: str) -> BaseClient:
        """Get a client instance, creating it if necessary."""
        if name not in self._clients:
            if name not in self._client_classes:
                raise ClientError(f"No client registered with name: {name}")

            # Load configuration
            config = self._load_config(name)

            # Create client instance
            client_class = self._client_classes[name]
            client = client_class(config)

            self._clients[name] = client
            self._client_configs[name] = config

            self.logger.info(f"Created client instance: {name}")

        return self._clients[name]

    async def initialize_client(self, name: str) -> None:
        """Initialize a specific client."""
        client = self.get_client(name)
        if not client.is_initialized:
            await client.initialize()
            self.logger.info(f"Initialized client: {name}")

    async def initialize_all(self) -> None:
        """Initialize all registered clients."""
        self.logger.info("Initializing all clients...")

        for name in self._client_classes.keys():
            try:
                await self.initialize_client(name)
            except Exception as e:
                self.logger.error(f"Failed to initialize client {name}: {e}")
                # Continue with other clients

        self._initialized = True
        self.logger.info("Client factory initialization complete")

    async def close_client(self, name: str) -> None:
        """Close a specific client."""
        if name in self._clients:
            await self._clients[name].close()
            del self._clients[name]
            self.logger.info(f"Closed client: {name}")

    async def close_all(self) -> None:
        """Close all client connections."""
        self.logger.info("Closing all clients...")

        for name in list(self._clients.keys()):
            try:
                await self.close_client(name)
            except Exception as e:
                self.logger.error(f"Error closing client {name}: {e}")

        self._clients.clear()
        self._client_configs.clear()
        self._initialized = False
        self.logger.info("All clients closed")

    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all clients."""
        health_results = {
            "factory_status": "healthy" if self._initialized else "not_initialized",
            "clients": {},
        }

        for name, client in self._clients.items():
            try:
                if client.is_initialized:
                    health_result = await client.get_health_status()
                else:
                    health_result = {"status": "not_initialized", "client_name": name}

                health_results["clients"][name] = health_result

            except Exception as e:
                self.logger.error(f"Health check failed for client {name}: {e}")
                health_results["clients"][name] = {
                    "status": "error",
                    "client_name": name,
                    "error": str(e),
                }

        # Determine overall health
        overall_healthy = all(
            client_health.get("status") == "healthy"
            for client_health in health_results["clients"].values()
        )
        health_results["overall_status"] = "healthy" if overall_healthy else "degraded"

        return health_results

    def get_client_info(self) -> Dict[str, Any]:
        """Get information about all registered clients."""
        return {
            "factory_initialized": self._initialized,
            "registered_client_types": list(self._client_classes.keys()),
            "active_clients": list(self._clients.keys()),
            "client_details": {
                name: (
                    client.get_client_info()
                    if client.is_initialized
                    else {"status": "not_initialized"}
                )
                for name, client in self._clients.items()
            },
        }

    async def reload_client(self, name: str) -> None:
        """Reload a client with fresh configuration."""
        self.logger.info(f"Reloading client: {name}")

        # Close existing client if it exists
        if name in self._clients:
            await self.close_client(name)

        # Create and initialize new client
        await self.initialize_client(name)

        self.logger.info(f"Successfully reloaded client: {name}")

    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all()


# Global factory instance
_client_factory: Optional[ClientFactory] = None


@lru_cache()
def get_client_factory() -> ClientFactory:
    """Get the global client factory instance."""
    global _client_factory
    if _client_factory is None:
        _client_factory = ClientFactory()
    return _client_factory


# Convenience functions for commonly used clients
async def get_supabase_client(use_service_role: bool = False) -> SupabaseClient:
    """Get initialized Supabase client.

    Args:
        use_service_role: If True, returns a service role client.
                         If False (default), returns a client suitable for RLS.

    Returns:
        SupabaseClient instance configured appropriately.
    """
    if use_service_role:
        return await get_service_supabase_client()

    factory = get_client_factory()
    client = factory.get_client("supabase")
    if not client.is_initialized:
        await factory.initialize_client("supabase")
    return client


async def get_gemini_client() -> GeminiClient:
    """Get initialized Gemini client."""
    factory = get_client_factory()
    client = factory.get_client("gemini")
    if not client.is_initialized:
        await factory.initialize_client("gemini")
    return client


async def get_openai_client() -> OpenAIClient:
    """Get initialized OpenAI client."""
    factory = get_client_factory()
    client = factory.get_client("openai")
    if not client.is_initialized:
        await factory.initialize_client("openai")
    return client


async def get_domain_client() -> DomainClient:
    """Get initialized Domain client."""
    factory = get_client_factory()
    client = factory.get_client("domain")
    if not client.is_initialized:
        await factory.initialize_client("domain")
    return client


async def get_corelogic_client() -> CoreLogicClient:
    """Get initialized CoreLogic client."""
    factory = get_client_factory()
    client = factory.get_client("corelogic")
    if not client.is_initialized:
        await factory.initialize_client("corelogic")
    return client


async def get_service_supabase_client() -> SupabaseClient:
    """Create and return a dedicated Supabase client using the service role key.

    This function returns a separate client instance and does NOT mutate the
    cached anon-key client managed by the factory. It is intended strictly for
    backend internal operations (e.g., recovery/monitoring) where RLS bypass is
    required and access is controlled via SECURITY DEFINER RPCs and least
    privilege on the database side.
    """
    factory = get_client_factory()
    base_client = factory.get_client("supabase")
    if not base_client.is_initialized:
        await factory.initialize_client("supabase")

    # Build a brand new SupabaseClient instance configured with the service key
    from supabase import create_client
    from .supabase.client import SupabaseClient as _SupabaseClient
    from .supabase.auth_client import SupabaseAuthClient
    from .supabase.database_client import SupabaseDatabaseClient

    raw_service = create_client(base_client.config.url, base_client.config.service_key)

    service_client = _SupabaseClient(base_client.config)
    # Attach underlying raw client and sub-clients
    service_client._supabase_client = raw_service
    service_client._auth_client = SupabaseAuthClient(raw_service, base_client.config)
    service_client._db_client = SupabaseDatabaseClient(raw_service, base_client.config)
    await service_client._db_client.initialize()
    service_client._initialized = True

    return service_client
