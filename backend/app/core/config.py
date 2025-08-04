"""
Configuration management for Real2.AI
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from app.models.contract_state import AustralianState


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    environment: str = "development"
    debug: bool = True

    # Database
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    database_url: Optional[str] = None

    # AI Services
    openai_api_key: str
    openai_api_base: Optional[str] = None
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "real2ai-development"

    # External APIs
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    domain_api_key: Optional[str] = None
    corelogic_api_key: Optional[str] = None

    # Redis Cache
    redis_url: str = "redis://localhost:6379"

    # File Storage
    max_file_size: int = 52428800  # 50MB
    allowed_file_types: str = "pdf,doc,docx"

    # Monitoring
    sentry_dsn: Optional[str] = None
    log_level: str = "INFO"

    # Australian Specific
    default_australian_state: AustralianState = AustralianState.NSW
    enable_stamp_duty_calculation: bool = True
    enable_cooling_off_validation: bool = True

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list"""
        if isinstance(self.allowed_file_types, str):
            return [ft.strip() for ft in self.allowed_file_types.split(",")]
        return self.allowed_file_types

    class Config:
        env_file = [".env", ".env.local", "env.local"]
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields like old JWT settings


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
