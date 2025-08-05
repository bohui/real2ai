"""Main prompt management interface with versioning and caching"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime, UTC
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .loader import PromptLoader, LoaderConfig
from .template import PromptTemplate
from .context import PromptContext, ContextType, ContextBuilder, ContextPresets
from .validator import PromptValidator, ValidationResult
from .composer import PromptComposer, ComposedPrompt
from .exceptions import (
    PromptNotFoundError,
    PromptValidationError,
    PromptVersionError,
    PromptContextError,
    PromptCompositionError
)
from app.models.contract_state import AustralianState, ContractType

logger = logging.getLogger(__name__)


@dataclass
class PromptManagerConfig:
    """Configuration for prompt manager"""
    templates_dir: Path
    config_dir: Optional[Path] = None
    cache_enabled: bool = True
    validation_enabled: bool = True
    hot_reload_enabled: bool = False
    preload_templates: bool = True
    default_model: str = "gemini-2.5-pro"
    max_render_time_seconds: int = 30
    enable_metrics: bool = True
    enable_composition: bool = True


class PromptManager:
    """Central prompt management system with advanced features"""
    
    def __init__(self, config: PromptManagerConfig):
        self.config = config
        
        # Initialize components
        loader_config = LoaderConfig(
            cache_enabled=config.cache_enabled,
            hot_reload_enabled=config.hot_reload_enabled,
            preload_templates=config.preload_templates,
            validate_on_load=config.validation_enabled
        )
        
        self.loader = PromptLoader(config.templates_dir, loader_config)
        self.validator = PromptValidator() if config.validation_enabled else None
        
        # Initialize composition system
        if config.enable_composition and config.config_dir:
            self.composer = PromptComposer(config.templates_dir, config.config_dir)
        else:
            self.composer = None
        
        # Runtime state
        self._render_cache: Dict[str, Dict[str, Any]] = {}
        self._metrics = {
            "renders": 0,
            "cache_hits": 0,
            "validation_failures": 0,
            "errors": 0,
            "total_render_time": 0.0
        }
        
        logger.info(f"PromptManager initialized with templates from {config.templates_dir}")
    
    async def render(
        self,
        template_name: str,
        context: Union[PromptContext, Dict[str, Any]],
        version: str = None,
        model: str = None,
        validate: bool = None,
        cache_key: str = None,
        **kwargs
    ) -> str:
        """Render a prompt template with full validation and caching
        
        Args:
            template_name: Name of the template to render
            context: Prompt context or dictionary of variables
            version: Specific template version (defaults to latest)
            model: Target AI model for validation
            validate: Override validation setting
            cache_key: Custom cache key for result caching
            **kwargs: Additional template variables
        
        Returns:
            Rendered prompt string
        
        Raises:
            PromptNotFoundError: Template not found
            PromptValidationError: Validation failed
            PromptContextError: Context is invalid
        """
        start_time = datetime.now(UTC)
        
        try:
            # Convert dict to PromptContext if needed
            if isinstance(context, dict):
                context = PromptContext(
                    context_type=ContextType.USER,
                    variables=context
                )
            
            # Check render cache
            if self.config.cache_enabled and cache_key:
                cached_result = self._get_render_cache(cache_key)
                if cached_result:
                    self._metrics["cache_hits"] += 1
                    return cached_result["rendered"]
            
            # Load template
            template = await self.loader.load_template(template_name, version)
            
            # Validate context if enabled
            should_validate = validate if validate is not None else self.config.validation_enabled
            if should_validate and self.validator:
                context_validation = self.validator.validate_context(
                    context, template.metadata.required_variables
                )
                
                if not context_validation.is_valid:
                    self._metrics["validation_failures"] += 1
                    raise PromptContextError(
                        f"Context validation failed: {'; '.join([issue.message for issue in context_validation.issues])}",
                        prompt_id=template_name,
                        details={"validation_result": context_validation}
                    )
            
            # Render template
            rendered = template.render(context, **kwargs)
            
            # Validate rendered output if enabled
            if should_validate and self.validator:
                render_validation = self.validator.validate_rendered_prompt(
                    rendered, model or self.config.default_model
                )
                
                if render_validation.has_errors:
                    self._metrics["validation_failures"] += 1
                    raise PromptValidationError(
                        f"Rendered prompt validation failed: {'; '.join([issue.message for issue in render_validation.issues if issue.severity.value in ['error', 'critical']])}",
                        prompt_id=template_name,
                        details={"validation_result": render_validation}
                    )
                
                # Log warnings
                if render_validation.has_warnings:
                    warnings = [issue.message for issue in render_validation.issues if issue.severity.value == 'warning']
                    logger.warning(f"Prompt '{template_name}' validation warnings: {'; '.join(warnings)}")
            
            # Cache result
            if self.config.cache_enabled and cache_key:
                self._set_render_cache(cache_key, {
                    "rendered": rendered,
                    "template_name": template_name,
                    "version": version,
                    "rendered_at": datetime.now(UTC).isoformat()
                })
            
            # Update metrics
            render_time = (datetime.now(UTC) - start_time).total_seconds()
            self._metrics["renders"] += 1
            self._metrics["total_render_time"] += render_time
            
            logger.debug(f"Rendered template '{template_name}' in {render_time:.3f}s")
            
            return rendered
            
        except Exception as e:
            self._metrics["errors"] += 1
            
            if isinstance(e, (PromptNotFoundError, PromptValidationError, PromptContextError)):
                raise
            
            logger.error(f"Failed to render template '{template_name}': {e}")
            raise PromptValidationError(
                f"Template rendering failed: {str(e)}",
                prompt_id=template_name,
                details={"error_type": type(e).__name__}
            )
    
    async def validate_template(self, template_name: str, version: str = None) -> ValidationResult:
        """Validate a template without rendering"""
        if not self.validator:
            raise PromptValidationError("Validation is disabled")
        
        template = await self.loader.load_template(template_name, version)
        return self.validator.validate_template(template)
    
    async def validate_context(self, template_name: str, context: PromptContext, version: str = None) -> ValidationResult:
        """Validate context against template requirements"""
        if not self.validator:
            raise PromptValidationError("Validation is disabled")
        
        template = await self.loader.load_template(template_name, version)
        return self.validator.validate_context(context, template.metadata.required_variables)
    
    def create_context(self, context_type: ContextType) -> ContextBuilder:
        """Create a new context builder"""
        return ContextBuilder(context_type)
    
    def get_preset_context(self, preset_name: str, **kwargs) -> PromptContext:
        """Get a predefined context preset"""
        presets = {
            "contract_analysis": lambda: ContextPresets.contract_analysis(
                kwargs.get("australian_state", AustralianState.NSW),
                kwargs.get("contract_type", ContractType.PURCHASE_AGREEMENT),
                kwargs.get("user_type", "buyer"),
                kwargs.get("experience", "novice")
            ),
            "ocr_extraction": lambda: ContextPresets.ocr_extraction(
                kwargs.get("document_type", "contract"),
                kwargs.get("quality", "high"),
                kwargs.get("australian_state", AustralianState.NSW)
            ),
            "risk_assessment": lambda: ContextPresets.risk_assessment(
                kwargs.get("contract_type", ContractType.PURCHASE_AGREEMENT),
                kwargs.get("user_experience", "novice"),
                kwargs.get("focus_areas", [])
            ),
            "compliance_check": lambda: ContextPresets.compliance_check(
                kwargs.get("australian_state", AustralianState.NSW),
                kwargs.get("contract_type", ContractType.PURCHASE_AGREEMENT)
            )
        }
        
        if preset_name not in presets:
            raise PromptContextError(
                f"Unknown preset '{preset_name}'",
                details={"available_presets": list(presets.keys())}
            )
        
        return presets[preset_name]()
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with metadata"""
        return self.loader.list_templates()
    
    def search_templates(self, query: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Search templates by name, description, or tags"""
        return self.loader.search_templates(query, tags)
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a template"""
        templates = self.list_templates()
        for template in templates:
            if template["name"] == template_name:
                return template
        return None
    
    # Composition System Methods
    
    async def compose_prompt(
        self,
        composition_name: str,
        context: Union[PromptContext, Dict[str, Any]],
        variables: Dict[str, Any] = None,
        **kwargs
    ) -> ComposedPrompt:
        """Compose a complete prompt from system and user components
        
        Args:
            composition_name: Name of composition rule to use
            context: Context for rendering templates
            variables: Additional template variables
            **kwargs: Additional composition options
        
        Returns:
            ComposedPrompt with system and user content
            
        Raises:
            PromptCompositionError: If composition not enabled or fails
            PromptNotFoundError: If composition rule not found
        """
        if not self.composer:
            raise PromptCompositionError("Composition system not enabled")
        
        # Convert dict to PromptContext if needed
        if isinstance(context, dict):
            context = PromptContext(
                context_type=ContextType.USER,
                variables=context
            )
        
        return self.composer.compose(composition_name, context, variables, **kwargs)
    
    async def render_composed(
        self,
        composition_name: str,
        context: Union[PromptContext, Dict[str, Any]],
        variables: Dict[str, Any] = None,
        return_parts: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, str]]:
        """Compose and render a complete prompt
        
        Args:
            composition_name: Name of composition rule
            context: Context for rendering
            variables: Additional variables
            return_parts: If True, return dict with 'system' and 'user' keys
            **kwargs: Additional options
            
        Returns:
            Combined prompt string or dict with separate parts
        """
        composed = await self.compose_prompt(composition_name, context, variables, **kwargs)
        
        if return_parts:
            return {
                "system": composed.system_content,
                "user": composed.user_content,
                "metadata": composed.metadata
            }
        else:
            # Combine system and user content
            combined = f"{composed.system_content}\n\n---\n\n{composed.user_content}"
            return combined
    
    def list_compositions(self) -> List[Dict[str, Any]]:
        """List all available prompt compositions"""
        if not self.composer:
            return []
        return self.composer.list_compositions()
    
    def validate_composition(self, composition_name: str) -> Dict[str, Any]:
        """Validate that a composition can be executed"""
        if not self.composer:
            return {"valid": False, "error": "Composition system not enabled"}
        return self.composer.validate_composition(composition_name)
    
    def reload_templates(self):
        """Manually reload all templates from disk"""
        self.loader.reload_templates()
        self._render_cache.clear()
        logger.info("Templates reloaded and render cache cleared")
    
    def clear_cache(self):
        """Clear all caches"""
        self.loader.clear_cache()
        self._render_cache.clear()
        if self.composer:
            self.composer.clear_cache()
        logger.info("All caches cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        loader_metrics = self.loader.get_metrics()
        
        avg_render_time = (
            self._metrics["total_render_time"] / max(self._metrics["renders"], 1)
        )
        
        return {
            "prompt_manager": {
                **self._metrics,
                "avg_render_time_seconds": avg_render_time,
                "render_cache_size": len(self._render_cache),
                "validation_enabled": self.validator is not None,
            },
            "loader": loader_metrics,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "components": {}
        }
        
        # Check loader
        try:
            loader_metrics = self.loader.get_metrics()
            health["components"]["loader"] = {
                "status": "healthy",
                "total_templates": loader_metrics["total_templates"]
            }
        except Exception as e:
            health["components"]["loader"] = {
                "status": "error",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        # Check validator
        if self.validator:
            health["components"]["validator"] = {
                "status": "healthy",
                "enabled": True
            }
        else:
            health["components"]["validator"] = {
                "status": "disabled",
                "enabled": False
            }
        
        # Test template rendering
        try:
            # Try to render a simple test template
            test_context = PromptContext(
                context_type=ContextType.SYSTEM,
                variables={"test_var": "test_value"}
            )
            
            # This would need a test template to exist
            health["components"]["rendering"] = {
                "status": "not_tested",
                "reason": "No test template available"
            }
            
        except Exception as e:
            health["components"]["rendering"] = {
                "status": "error",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        return health
    
    def _get_render_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from render cache with TTL check"""
        if cache_key in self._render_cache:
            cached = self._render_cache[cache_key]
            # Simple TTL check - in production, you'd want more sophisticated caching
            cache_age = datetime.now(UTC) - datetime.fromisoformat(cached["rendered_at"])
            if cache_age.total_seconds() < 3600:  # 1 hour TTL
                return cached
            else:
                del self._render_cache[cache_key]
        return None
    
    def _set_render_cache(self, cache_key: str, data: Dict[str, Any]):
        """Set render cache with size limit"""
        # Simple size limit
        if len(self._render_cache) > 1000:
            # Remove oldest entry
            oldest_key = min(
                self._render_cache.keys(),
                key=lambda k: self._render_cache[k]["rendered_at"]
            )
            del self._render_cache[oldest_key]
        
        self._render_cache[cache_key] = data
    
    @asynccontextmanager
    async def render_context(self, template_name: str, **render_kwargs):
        """Context manager for template rendering with cleanup"""
        start_time = datetime.now(UTC)
        
        try:
            # Pre-render setup could go here
            logger.debug(f"Starting render context for template '{template_name}'")
            
            yield self  # Allow the caller to use the manager
            
        except Exception as e:
            logger.error(f"Error in render context for '{template_name}': {e}")
            raise
        
        finally:
            # Cleanup code
            render_time = (datetime.now(UTC) - start_time).total_seconds()
            logger.debug(f"Render context for '{template_name}' completed in {render_time:.3f}s")
    
    async def batch_render(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Render multiple templates concurrently
        
        Args:
            requests: List of render requests, each containing:
                - template_name: str
                - context: PromptContext or dict
                - version: str (optional)
                - model: str (optional)
                - **kwargs: additional template variables
            max_concurrent: Maximum concurrent renders
        
        Returns:
            List of results with same order as requests
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def render_single(request: Dict[str, Any], index: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.render(**request)
                    return {
                        "index": index,
                        "success": True,
                        "result": result,
                        "template_name": request["template_name"]
                    }
                except Exception as e:
                    return {
                        "index": index,
                        "success": False,
                        "error": str(e),
                        "template_name": request["template_name"]
                    }
        
        # Execute all renders concurrently
        tasks = [
            render_single(request, i) 
            for i, request in enumerate(requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sort results back to original order
        sorted_results = sorted(
            [r for r in results if isinstance(r, dict)],
            key=lambda x: x["index"]
        )
        
        return sorted_results


# Singleton instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(config: PromptManagerConfig = None) -> PromptManager:
    """Get or create the global prompt manager instance"""
    global _prompt_manager
    
    if _prompt_manager is None:
        if config is None:
            # Default configuration
            from pathlib import Path
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"
            config = PromptManagerConfig(
                templates_dir=prompts_dir,
                config_dir=prompts_dir / "config"
            )
        
        _prompt_manager = PromptManager(config)
    
    return _prompt_manager


def reset_prompt_manager():
    """Reset the global prompt manager (useful for testing)"""
    global _prompt_manager
    _prompt_manager = None
