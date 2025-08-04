"""
Configuration for Supabase client.
"""

from dataclasses import dataclass
from typing import Optional
from pydantic import BaseSettings

from ..base.client import ClientConfig


@dataclass
class SupabaseClientConfig(ClientConfig):
    """Configuration for Supabase client."""
    
    # Supabase connection settings
    url: str
    anon_key: str
    service_key: str
    
    # Database-specific settings
    db_timeout: int = 30
    max_connections: int = 10
    connection_retry_delay: float = 1.0
    
    # Auth-specific settings
    auth_timeout: int = 10
    jwt_secret: Optional[str] = None
    
    # Performance settings
    auto_refresh_token: bool = True
    persist_session: bool = True


class SupabaseSettings(BaseSettings):
    """Pydantic settings for Supabase configuration from environment."""
    
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    supabase_jwt_secret: Optional[str] = None
    
    # Database settings
    supabase_db_timeout: int = 30
    supabase_max_connections: int = 10
    supabase_connection_retry_delay: float = 1.0
    
    # Auth settings
    supabase_auth_timeout: int = 10
    supabase_auto_refresh_token: bool = True
    supabase_persist_session: bool = True
    
    # Base client settings
    supabase_max_retries: int = 3
    supabase_backoff_factor: float = 1.0
    supabase_circuit_breaker_enabled: bool = True
    supabase_failure_threshold: int = 5
    supabase_circuit_timeout: int = 60
    
    class Config:
        env_file = [".env", ".env.local"]
        case_sensitive = False
    
    def to_client_config(self) -> SupabaseClientConfig:
        """Convert to SupabaseClientConfig."""
        return SupabaseClientConfig(
            # Connection settings
            url=self.supabase_url,
            anon_key=self.supabase_anon_key,
            service_key=self.supabase_service_key,
            jwt_secret=self.supabase_jwt_secret,
            
            # Database settings
            db_timeout=self.supabase_db_timeout,
            max_connections=self.supabase_max_connections,
            connection_retry_delay=self.supabase_connection_retry_delay,
            
            # Auth settings
            auth_timeout=self.supabase_auth_timeout,
            auto_refresh_token=self.supabase_auto_refresh_token,
            persist_session=self.supabase_persist_session,
            
            # Base client settings
            timeout=self.supabase_db_timeout,
            max_retries=self.supabase_max_retries,
            backoff_factor=self.supabase_backoff_factor,
            circuit_breaker_enabled=self.supabase_circuit_breaker_enabled,
            failure_threshold=self.supabase_failure_threshold,
            circuit_timeout=self.supabase_circuit_timeout,
        )