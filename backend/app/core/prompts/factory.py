"""
PromptManager Factory
Provides factory methods for creating pre-configured PromptManager instances
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .manager import PromptManager, PromptManagerConfig

logger = logging.getLogger(__name__)


class PromptManagerFactory:
    """Factory for creating PromptManager instances with standard configurations"""

    @staticmethod
    def create_default(
        templates_dir: Path, config_dir: Optional[Path] = None, **overrides
    ) -> PromptManager:
        """Create PromptManager with default configuration

        Args:
            templates_dir: Directory containing prompt templates
            config_dir: Directory containing configuration files (optional)
            **overrides: Configuration overrides

        Returns:
            Configured PromptManager instance
        """
        # Set default config directory if not provided
        if config_dir is None and templates_dir:
            config_dir = templates_dir.parent / "config"
            if not config_dir.exists():
                config_dir = templates_dir / "config"

        config = PromptManagerConfig(
            templates_dir=templates_dir,
            config_dir=config_dir,
            cache_enabled=True,
            validation_enabled=True,
            hot_reload_enabled=False,
            preload_templates=True,
            default_model="gemini-2.5-flash",
            max_render_time_seconds=30,
            enable_metrics=True,
            enable_composition=True,
            enable_workflows=True,
            enable_service_integration=True,
            **overrides,
        )

        return PromptManager(config)

    @staticmethod
    def create_development(
        templates_dir: Path, config_dir: Optional[Path] = None, **overrides
    ) -> PromptManager:
        """Create PromptManager optimized for development

        Args:
            templates_dir: Directory containing prompt templates
            config_dir: Directory containing configuration files (optional)
            **overrides: Configuration overrides

        Returns:
            Development-optimized PromptManager instance
        """
        if config_dir is None and templates_dir:
            config_dir = templates_dir.parent / "config"
            if not config_dir.exists():
                config_dir = templates_dir / "config"

        config = PromptManagerConfig(
            templates_dir=templates_dir,
            config_dir=config_dir,
            cache_enabled=True,
            validation_enabled=True,
            hot_reload_enabled=True,  # Enable hot reload for development
            preload_templates=False,  # Don't preload for faster startup
            default_model="gemini-2.5-flash",
            max_render_time_seconds=60,  # More generous timeout
            enable_metrics=True,
            enable_composition=True,
            enable_workflows=True,
            enable_service_integration=True,
            **overrides,
        )

        return PromptManager(config)

    @staticmethod
    def create_production(
        templates_dir: Path, config_dir: Optional[Path] = None, **overrides
    ) -> PromptManager:
        """Create PromptManager optimized for production

        Args:
            templates_dir: Directory containing prompt templates
            config_dir: Directory containing configuration files (optional)
            **overrides: Configuration overrides

        Returns:
            Production-optimized PromptManager instance
        """
        if config_dir is None and templates_dir:
            config_dir = templates_dir.parent / "config"
            if not config_dir.exists():
                config_dir = templates_dir / "config"

        config = PromptManagerConfig(
            templates_dir=templates_dir,
            config_dir=config_dir,
            cache_enabled=True,
            validation_enabled=True,
            hot_reload_enabled=False,  # Disable hot reload for stability
            preload_templates=True,  # Preload for performance
            default_model="gemini-2.5-flash",
            max_render_time_seconds=15,  # Strict timeout for production
            enable_metrics=True,
            enable_composition=True,
            enable_workflows=True,
            enable_service_integration=True,
            **overrides,
        )

        return PromptManager(config)

    @staticmethod
    def create_testing(
        templates_dir: Path, config_dir: Optional[Path] = None, **overrides
    ) -> PromptManager:
        """Create PromptManager optimized for testing

        Args:
            templates_dir: Directory containing prompt templates
            config_dir: Directory containing configuration files (optional)
            **overrides: Configuration overrides

        Returns:
            Testing-optimized PromptManager instance
        """
        if config_dir is None and templates_dir:
            config_dir = templates_dir.parent / "config"
            if not config_dir.exists():
                config_dir = templates_dir / "config"

        config = PromptManagerConfig(
            templates_dir=templates_dir,
            config_dir=config_dir,
            cache_enabled=False,  # Disable cache for predictable tests
            validation_enabled=False,  # Disable validation for faster tests
            hot_reload_enabled=False,
            preload_templates=False,  # Don't preload for faster test startup
            default_model="gemini-2.5-flash",
            max_render_time_seconds=5,  # Short timeout for tests
            enable_metrics=False,  # Disable metrics for cleaner tests
            enable_composition=True,
            enable_workflows=True,
            enable_service_integration=False,  # Disable for isolated tests
            **overrides,
        )

        return PromptManager(config)

    @staticmethod
    def create_minimal(templates_dir: Path, **overrides) -> PromptManager:
        """Create minimal PromptManager with basic functionality only

        Args:
            templates_dir: Directory containing prompt templates
            **overrides: Configuration overrides

        Returns:
            Minimal PromptManager instance
        """
        config = PromptManagerConfig(
            templates_dir=templates_dir,
            config_dir=None,  # No config directory
            cache_enabled=False,
            validation_enabled=False,
            hot_reload_enabled=False,
            preload_templates=False,
            default_model="gemini-2.5-flash",
            max_render_time_seconds=10,
            enable_metrics=False,
            enable_composition=False,  # Disable composition
            enable_workflows=False,  # Disable workflows
            enable_service_integration=False,  # Disable service integration
            **overrides,
        )

        return PromptManager(config)

    @staticmethod
    async def create_and_initialize(
        factory_method: str,
        templates_dir: Path,
        config_dir: Optional[Path] = None,
        **overrides,
    ) -> PromptManager:
        """Create and initialize PromptManager in one call

        Args:
            factory_method: Name of factory method ('default', 'development', 'production', 'testing', 'minimal')
            templates_dir: Directory containing prompt templates
            config_dir: Directory containing configuration files (optional)
            **overrides: Configuration overrides

        Returns:
            Initialized PromptManager instance

        Raises:
            ValueError: If factory method is unknown
        """
        factory_methods = {
            "default": PromptManagerFactory.create_default,
            "development": PromptManagerFactory.create_development,
            "production": PromptManagerFactory.create_production,
            "testing": PromptManagerFactory.create_testing,
            "minimal": PromptManagerFactory.create_minimal,
        }

        if factory_method not in factory_methods:
            raise ValueError(
                f"Unknown factory method '{factory_method}'. "
                f"Available methods: {', '.join(factory_methods.keys())}"
            )

        # Create manager instance
        if factory_method == "minimal":
            manager = factory_methods[factory_method](templates_dir, **overrides)
        else:
            manager = factory_methods[factory_method](
                templates_dir, config_dir, **overrides
            )

        # Initialize async components
        await manager.initialize()

        logger.info(
            f"PromptManager created and initialized using '{factory_method}' configuration"
        )

        return manager

    @staticmethod
    def get_recommended_config(environment: str) -> Dict[str, Any]:
        """Get recommended configuration for different environments

        Args:
            environment: Environment name ('development', 'staging', 'production', 'testing')

        Returns:
            Recommended configuration dictionary
        """
        configs = {
            "development": {
                "cache_enabled": True,
                "validation_enabled": True,
                "hot_reload_enabled": True,
                "preload_templates": False,
                "max_render_time_seconds": 60,
                "enable_metrics": True,
                "enable_composition": True,
                "enable_workflows": True,
                "enable_service_integration": True,
            },
            "staging": {
                "cache_enabled": True,
                "validation_enabled": True,
                "hot_reload_enabled": False,
                "preload_templates": True,
                "max_render_time_seconds": 30,
                "enable_metrics": True,
                "enable_composition": True,
                "enable_workflows": True,
                "enable_service_integration": True,
            },
            "production": {
                "cache_enabled": True,
                "validation_enabled": True,
                "hot_reload_enabled": False,
                "preload_templates": True,
                "max_render_time_seconds": 15,
                "enable_metrics": True,
                "enable_composition": True,
                "enable_workflows": True,
                "enable_service_integration": True,
            },
            "testing": {
                "cache_enabled": False,
                "validation_enabled": False,
                "hot_reload_enabled": False,
                "preload_templates": False,
                "max_render_time_seconds": 5,
                "enable_metrics": False,
                "enable_composition": True,
                "enable_workflows": True,
                "enable_service_integration": False,
            },
        }

        return configs.get(environment, configs["development"])


# Convenience functions for common use cases


async def create_prompt_manager_for_app(
    app_root: Path, environment: str = "production"
) -> PromptManager:
    """Create PromptManager for application with standard directory structure

    Args:
        app_root: Application root directory
        environment: Environment configuration to use

    Returns:
        Initialized PromptManager instance
    """
    templates_dir = app_root / "prompts"
    config_dir = app_root / "prompts" / "config"

    # Ensure directories exist
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    # Use recommended config for environment
    config_overrides = PromptManagerFactory.get_recommended_config(environment)

    if environment == "testing":
        factory_method = "testing"
    elif environment == "development":
        factory_method = "development"
    else:
        factory_method = "production"

    return await PromptManagerFactory.create_and_initialize(
        factory_method=factory_method,
        templates_dir=templates_dir,
        config_dir=config_dir,
        **config_overrides,
    )


async def create_service_prompt_manager(
    service_name: str,
    templates_dir: Path,
    config_dir: Optional[Path] = None,
    environment: str = "production",
) -> PromptManager:
    """Create PromptManager specifically configured for a service

    Args:
        service_name: Name of the service
        templates_dir: Directory containing prompt templates
        config_dir: Directory containing configuration files
        environment: Environment configuration to use

    Returns:
        Service-specific PromptManager instance
    """
    config_overrides = PromptManagerFactory.get_recommended_config(environment)

    # Add service-specific optimizations
    config_overrides.update(
        {"enable_service_integration": True, "enable_workflows": True}
    )

    if environment == "testing":
        factory_method = "testing"
    elif environment == "development":
        factory_method = "development"
    else:
        factory_method = "production"

    manager = await PromptManagerFactory.create_and_initialize(
        factory_method=factory_method,
        templates_dir=templates_dir,
        config_dir=config_dir,
        **config_overrides,
    )

    logger.info(f"Service-specific PromptManager created for '{service_name}'")

    return manager
