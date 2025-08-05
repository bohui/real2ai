"""Intelligent prompt loader with caching and hot-reloading"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass, field
from threading import Lock
import hashlib
import json

from .template import PromptTemplate, TemplateLibrary, TemplateMetadata
from .context import PromptContext
from .exceptions import PromptNotFoundError, PromptLoadError

logger = logging.getLogger(__name__)


@dataclass
class LoaderConfig:
    """Configuration for prompt loader"""
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    hot_reload_enabled: bool = False
    watch_interval_seconds: int = 5
    max_cache_size: int = 1000
    preload_templates: bool = True
    validate_on_load: bool = True


@dataclass
class CachedTemplate:
    """Cached template with metadata"""
    template: PromptTemplate
    loaded_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    file_hash: Optional[str] = None
    file_path: Optional[Path] = None


class PromptLoader:
    """Advanced prompt loader with caching, validation, and hot-reloading"""
    
    def __init__(self, templates_dir: Path, config: LoaderConfig = None):
        self.templates_dir = Path(templates_dir)
        self.config = config or LoaderConfig()
        
        # Caching
        self._cache: Dict[str, CachedTemplate] = {}
        self._cache_lock = Lock()
        
        # File watching for hot reload
        self._file_watchers: Dict[Path, datetime] = {}
        self._watch_task: Optional[asyncio.Task] = None
        
        # Template library
        self._library: Optional[TemplateLibrary] = None
        
        # Metrics
        self._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "loads": 0,
            "errors": 0,
            "hot_reloads": 0
        }
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the loader"""
        try:
            # Create templates directory if it doesn't exist
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            
            # Load template library
            self._library = TemplateLibrary(self.templates_dir)
            
            # Preload templates if enabled
            if self.config.preload_templates:
                self._preload_all_templates()
            
            # Start hot reload if enabled
            if self.config.hot_reload_enabled:
                self._start_hot_reload()
            
            logger.info(
                f"PromptLoader initialized with {len(self._library.templates)} templates"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize PromptLoader: {e}")
            raise PromptLoadError(f"Loader initialization failed: {str(e)}")
    
    async def load_template(self, name: str, version: str = None) -> PromptTemplate:
        """Load a template by name with caching"""
        cache_key = f"{name}:{version or 'latest'}"
        
        # Check cache first
        if self.config.cache_enabled:
            cached = self._get_from_cache(cache_key)
            if cached:
                self._metrics["cache_hits"] += 1
                return cached.template
        
        self._metrics["cache_misses"] += 1
        
        try:
            # Load from library
            template = self._library.get(name)
            if not template:
                raise PromptNotFoundError(
                    f"Template '{name}' not found",
                    prompt_id=name,
                    details={"available_templates": self._library.list_templates()}
                )
            
            # Version check if specified
            if version and template.metadata.version != version:
                raise PromptNotFoundError(
                    f"Template '{name}' version '{version}' not found. "
                    f"Available version: {template.metadata.version}",
                    prompt_id=name,
                    details={"requested_version": version, "available_version": template.metadata.version}
                )
            
            # Validate if enabled
            if self.config.validate_on_load:
                self._validate_template(template)
            
            # Cache the template
            if self.config.cache_enabled:
                self._add_to_cache(cache_key, template)
            
            self._metrics["loads"] += 1
            logger.debug(f"Loaded template: {name}")
            
            return template
            
        except Exception as e:
            self._metrics["errors"] += 1
            if isinstance(e, (PromptNotFoundError, PromptLoadError)):
                raise
            
            logger.error(f"Failed to load template '{name}': {e}")
            raise PromptLoadError(
                f"Failed to load template '{name}': {str(e)}",
                prompt_id=name,
                details={"error_type": type(e).__name__}
            )
    
    async def render_template(
        self, 
        name: str, 
        context: PromptContext, 
        version: str = None,
        **kwargs
    ) -> str:
        """Load and render a template in one call"""
        template = await self.load_template(name, version)
        return template.render(context, **kwargs)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with metadata"""
        templates = []
        for name, template in self._library.templates.items():
            templates.append({
                "name": name,
                "version": template.metadata.version,
                "description": template.metadata.description,
                "required_variables": template.metadata.required_variables,
                "optional_variables": template.metadata.optional_variables or [],
                "tags": template.metadata.tags or [],
                "model_compatibility": template.metadata.model_compatibility or [],
                "max_tokens": template.metadata.max_tokens,
            })
        return templates
    
    def search_templates(self, query: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Search templates by name, description, or tags"""
        results = []
        query_lower = query.lower()
        
        for name, template in self._library.templates.items():
            match_score = 0
            
            # Name match
            if query_lower in name.lower():
                match_score += 10
            
            # Description match
            if query_lower in template.metadata.description.lower():
                match_score += 5
            
            # Tag match
            if tags and template.metadata.tags:
                matching_tags = set(tags) & set(template.metadata.tags)
                match_score += len(matching_tags) * 3
            
            if match_score > 0:
                results.append({
                    "name": name,
                    "version": template.metadata.version,
                    "description": template.metadata.description,
                    "match_score": match_score,
                    "tags": template.metadata.tags or [],
                })
        
        # Sort by match score
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get loader performance metrics"""
        total_requests = self._metrics["cache_hits"] + self._metrics["cache_misses"]
        cache_hit_rate = (
            self._metrics["cache_hits"] / total_requests if total_requests > 0 else 0
        )
        
        return {
            **self._metrics,
            "cache_hit_rate": cache_hit_rate,
            "cached_templates": len(self._cache),
            "total_templates": len(self._library.templates) if self._library else 0,
            "hot_reload_active": self._watch_task is not None and not self._watch_task.done(),
        }
    
    def clear_cache(self):
        """Clear the template cache"""
        with self._cache_lock:
            self._cache.clear()
        logger.info("Template cache cleared")
    
    def reload_templates(self):
        """Manually reload all templates from disk"""
        try:
            self._library = TemplateLibrary(self.templates_dir)
            self.clear_cache()
            
            if self.config.preload_templates:
                self._preload_all_templates()
            
            logger.info(f"Reloaded {len(self._library.templates)} templates")
            
        except Exception as e:
            logger.error(f"Failed to reload templates: {e}")
            raise PromptLoadError(f"Template reload failed: {str(e)}")
    
    def _get_from_cache(self, cache_key: str) -> Optional[CachedTemplate]:
        """Get template from cache with TTL check"""
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            
            if cached:
                # Check TTL
                age = datetime.now(UTC) - cached.loaded_at
                if age.total_seconds() > self.config.cache_ttl_seconds:
                    # Expired
                    del self._cache[cache_key]
                    return None
                
                # Update access stats
                cached.access_count += 1
                cached.last_accessed = datetime.now(UTC)
                return cached
        
        return None
    
    def _add_to_cache(self, cache_key: str, template: PromptTemplate):
        """Add template to cache with size limit"""
        with self._cache_lock:
            # Check cache size limit
            if len(self._cache) >= self.config.max_cache_size:
                # Remove least recently used
                lru_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].last_accessed
                )
                del self._cache[lru_key]
            
            # Add to cache
            self._cache[cache_key] = CachedTemplate(
                template=template,
                loaded_at=datetime.now(UTC)
            )
    
    def _validate_template(self, template: PromptTemplate):
        """Validate template structure and metadata"""
        if not template.metadata.name:
            raise PromptLoadError("Template must have a name")
        
        if not template.metadata.description:
            logger.warning(f"Template '{template.metadata.name}' has no description")
        
        if not template.metadata.required_variables:
            logger.warning(f"Template '{template.metadata.name}' has no required variables defined")
    
    def _preload_all_templates(self):
        """Preload all templates into cache"""
        if not self._library:
            return
        
        for name in self._library.list_templates():
            try:
                template = self._library.get(name)
                if template:
                    cache_key = f"{name}:latest"
                    self._add_to_cache(cache_key, template)
            except Exception as e:
                logger.warning(f"Failed to preload template '{name}': {e}")
        
        logger.info(f"Preloaded {len(self._cache)} templates")
    
    def _start_hot_reload(self):
        """Start hot reload monitoring"""
        if not self.config.hot_reload_enabled:
            return
        
        # Initialize file watchers
        for template_file in self.templates_dir.rglob("*.md"):
            self._file_watchers[template_file] = datetime.fromtimestamp(
                template_file.stat().st_mtime, tz=UTC
            )
        
        # Start watch task
        self._watch_task = asyncio.create_task(self._watch_files())
        logger.info("Hot reload monitoring started")
    
    async def _watch_files(self):
        """Watch files for changes and reload"""
        while True:
            try:
                await asyncio.sleep(self.config.watch_interval_seconds)
                
                changes_detected = False
                
                # Check existing files
                for template_file, last_modified in list(self._file_watchers.items()):
                    if template_file.exists():
                        current_modified = datetime.fromtimestamp(
                            template_file.stat().st_mtime, tz=UTC
                        )
                        
                        if current_modified > last_modified:
                            logger.info(f"Template file changed: {template_file}")
                            self._file_watchers[template_file] = current_modified
                            changes_detected = True
                    else:
                        # File deleted
                        logger.info(f"Template file deleted: {template_file}")
                        del self._file_watchers[template_file]
                        changes_detected = True
                
                # Check for new files
                for template_file in self.templates_dir.rglob("*.md"):
                    if template_file not in self._file_watchers:
                        logger.info(f"New template file: {template_file}")
                        self._file_watchers[template_file] = datetime.fromtimestamp(
                            template_file.stat().st_mtime, tz=UTC
                        )
                        changes_detected = True
                
                # Reload if changes detected
                if changes_detected:
                    self.reload_templates()
                    self._metrics["hot_reloads"] += 1
                    
            except Exception as e:
                logger.error(f"Error in file watcher: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file contents"""
        if not file_path.exists():
            return ""
        
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()
    
    def __del__(self):
        """Cleanup on destruction"""
        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()
