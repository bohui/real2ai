"""
Configuration for Google Gemini client.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings

from ..base.client import ClientConfig

# Constants to replace magic numbers
DEFAULT_MAX_FILE_SIZE_MB = 50
DEFAULT_PROCESSING_TIMEOUT_SECONDS = 120
DEFAULT_RATE_LIMIT_RPM = 60
DEFAULT_CIRCUIT_TIMEOUT_SECONDS = 300  # 5 minutes for AI services
BYTES_PER_MB = 1024 * 1024


@dataclass(kw_only=True)
class GeminiClientConfig(ClientConfig):
    """Configuration for Google Gemini client with service role authentication."""

    # Gemini API settings
    model_name: str = "gemini-2.5-pro"

    # Service role authentication settings (required)
    credentials_path: Optional[str] = None
    project_id: Optional[str] = None

    # Safety settings
    harm_block_threshold: str = "BLOCK_NONE"

    # OCR specific settings
    max_file_size: int = DEFAULT_MAX_FILE_SIZE_MB * BYTES_PER_MB  # 50MB
    supported_formats: set = None
    ocr_confidence_threshold: float = 0.7

    # Performance settings
    processing_timeout: int = DEFAULT_PROCESSING_TIMEOUT_SECONDS
    rate_limit_rpm: Optional[int] = DEFAULT_RATE_LIMIT_RPM

    # Enhancement settings
    enable_image_enhancement: bool = True
    enable_text_enhancement: bool = True

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = {
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "webp",
                "gif",
                "bmp",
                "tiff",
            }


class GeminiSettings(BaseSettings):
    """Pydantic settings for Gemini configuration from environment."""

    gemini_model_name: str = "gemini-2.5-pro"

    # Service role authentication settings (required)
    gemini_credentials_path: Optional[str] = None
    gemini_project_id: Optional[str] = None

    # Safety settings
    gemini_harm_block_threshold: str = "BLOCK_NONE"

    # OCR settings
    gemini_max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB
    gemini_ocr_confidence_threshold: float = 0.7
    gemini_processing_timeout: int = DEFAULT_PROCESSING_TIMEOUT_SECONDS
    gemini_rate_limit_rpm: Optional[int] = DEFAULT_RATE_LIMIT_RPM

    # Enhancement settings
    gemini_enable_image_enhancement: bool = True
    gemini_enable_text_enhancement: bool = True

    # Base client settings
    gemini_max_retries: int = 3
    gemini_backoff_factor: float = 2.0
    gemini_circuit_breaker_enabled: bool = True
    gemini_failure_threshold: int = 5
    gemini_circuit_timeout: int = (
        DEFAULT_CIRCUIT_TIMEOUT_SECONDS  # 5 minutes for AI services
    )

    class Config:
        env_file = [".env", ".env.local"]
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables

    def to_client_config(self) -> GeminiClientConfig:
        """Convert to GeminiClientConfig."""
        return GeminiClientConfig(
            # API settings
            model_name=self.gemini_model_name,
            # Service role authentication settings
            credentials_path=self.gemini_credentials_path,
            project_id=self.gemini_project_id,
            # Safety settings
            harm_block_threshold=self.gemini_harm_block_threshold,
            # OCR settings
            max_file_size=self.gemini_max_file_size_mb * BYTES_PER_MB,
            ocr_confidence_threshold=self.gemini_ocr_confidence_threshold,
            processing_timeout=self.gemini_processing_timeout,
            rate_limit_rpm=self.gemini_rate_limit_rpm,
            # Enhancement settings
            enable_image_enhancement=self.gemini_enable_image_enhancement,
            enable_text_enhancement=self.gemini_enable_text_enhancement,
            # Base client settings
            timeout=self.gemini_processing_timeout,
            max_retries=self.gemini_max_retries,
            backoff_factor=self.gemini_backoff_factor,
            circuit_breaker_enabled=self.gemini_circuit_breaker_enabled,
            failure_threshold=self.gemini_failure_threshold,
            circuit_timeout=self.gemini_circuit_timeout,
        )
