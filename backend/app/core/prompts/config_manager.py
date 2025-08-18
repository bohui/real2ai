"""
Configuration Manager for PromptManager System
Handles service mappings, composition rules, and dynamic configuration
"""

import yaml
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, UTC
import hashlib

from .exceptions import PromptCompositionError, PromptServiceError

logger = logging.getLogger(__name__)


@dataclass
class ServiceMapping:
    """Service-to-template mapping configuration"""
    service_name: str
    primary_templates: List[Dict[str, Any]] = field(default_factory=list)
    compositions: List[Dict[str, Any]] = field(default_factory=list)
    fallback_templates: List[str] = field(default_factory=list)
    context_requirements: List[str] = field(default_factory=list)
    performance_targets: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class CompositionRule:
    """Prompt composition rule configuration"""
    name: str
    description: str
    version: str
    system_prompts: List[Dict[str, Any]] = field(default_factory=list)
    estimated_duration_seconds: int = 60
    max_tokens_total: int = 50000
    error_handling: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy support
    user_prompts: List[str] = field(default_factory=list)
    merge_strategy: str = "sequential"
    deprecated: bool = False
    replacement: Optional[str] = None


@dataclass 
class GlobalConfiguration:
    """Global configuration settings"""
    default_cache_ttl: int = 3600
    max_render_time_ms: int = 5000
    fallback_enabled: bool = True
    metrics_enabled: bool = True
    validation_enabled: bool = True
    max_parallel_steps: int = 3
    step_timeout_seconds: int = 30
    enable_step_caching: bool = True
    cache_ttl_seconds: int = 1800


class ConfigurationManager:
    """Manages all prompt system configurations"""
    
    def __init__(self, config_dir: Path):
        """Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._service_mappings: Dict[str, ServiceMapping] = {}
        self._composition_rules: Dict[str, CompositionRule] = {}
        self._global_config: GlobalConfiguration = GlobalConfiguration()
        self._discovery_rules: Dict[str, Any] = {}
        self._state_overrides: Dict[str, Any] = {}
        self._user_experience_adjustments: Dict[str, Any] = {}
        self._dynamic_compositions: Dict[str, Any] = {}
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._last_loaded: Dict[str, datetime] = {}
        
        logger.info(f"ConfigurationManager initialized with config directory: {config_dir}")
    
    async def initialize(self):
        """Initialize and load all configurations"""
        try:
            await self._load_all_configurations()
            await self._validate_configurations()
            logger.info("Configuration manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize configuration manager: {e}")
            raise PromptServiceError(
                f"Configuration initialization failed: {str(e)}",
                service_name="configuration_manager",
                details={'config_dir': str(self.config_dir)}
            )
    
    async def _load_all_configurations(self):
        """Load all configuration files"""
        config_files = {
            'service_mappings': 'service_mappings.yaml',
            'composition_rules': 'composition_rules.yaml',
            'global_config': 'global_config.yaml'  # Optional
        }
        
        for config_type, filename in config_files.items():
            config_path = self.config_dir / filename
            if config_path.exists():
                await self._load_config_file(config_type, config_path)
            elif config_type in ['service_mappings', 'composition_rules']:
                logger.warning(f"Required configuration file not found: {filename}")
    
    async def _load_config_file(self, config_type: str, config_path: Path):
        """Load a specific configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Cache raw config data
            self._config_cache[config_type] = config_data
            self._last_loaded[config_type] = datetime.now(UTC)
            
            # Process specific configuration types
            if config_type == 'service_mappings':
                await self._process_service_mappings(config_data)
            elif config_type == 'composition_rules':
                await self._process_composition_rules(config_data)
            elif config_type == 'global_config':
                await self._process_global_config(config_data)
            
            logger.debug(f"Loaded configuration: {config_type} from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load config file {config_path}: {e}")
            raise
    
    async def _process_service_mappings(self, config_data: Dict[str, Any]):
        """Process service mappings configuration"""
        mappings = config_data.get('mappings', {})
        
        for service_name, mapping_data in mappings.items():
            self._service_mappings[service_name] = ServiceMapping(
                service_name=service_name,
                primary_templates=mapping_data.get('primary_templates', []),
                compositions=mapping_data.get('compositions', []),
                fallback_templates=mapping_data.get('fallback_templates', []),
                context_requirements=mapping_data.get('context_requirements', []),
                performance_targets=mapping_data.get('performance_targets', {}),
                tags=mapping_data.get('tags', [])
            )
        
        # Store additional configuration sections
        self._discovery_rules = config_data.get('discovery_rules', {})
        
        logger.info(f"Loaded {len(self._service_mappings)} service mappings")
    
    async def _process_composition_rules(self, config_data: Dict[str, Any]):
        """Process composition rules configuration"""
        compositions = config_data.get('compositions', {})
        
        for comp_name, comp_data in compositions.items():
            self._composition_rules[comp_name] = CompositionRule(
                name=comp_name,
                description=comp_data.get('description', ''),
                version=comp_data.get('version', '1.0.0'),
                system_prompts=comp_data.get('system_prompts', []),
                estimated_duration_seconds=comp_data.get('estimated_duration_seconds', 60),
                max_tokens_total=comp_data.get('max_tokens_total', 50000),
                error_handling=comp_data.get('error_handling', {}),
                # Legacy support
                user_prompts=comp_data.get('user_prompts', []),
                merge_strategy=comp_data.get('merge_strategy', 'sequential'),
                deprecated=comp_data.get('deprecated', False),
                replacement=comp_data.get('replacement')
            )
        
        # Store additional configuration sections
        self._state_overrides = config_data.get('state_overrides', {})
        self._user_experience_adjustments = config_data.get('user_experience_adjustments', {})
        self._dynamic_compositions = config_data.get('dynamic_compositions', {})
        
        # Update global config from composition rules if present
        global_settings = config_data.get('global_settings', {})
        if global_settings:
            await self._update_global_config_from_dict(global_settings)
        
        logger.info(f"Loaded {len(self._composition_rules)} composition rules")
    
    async def _process_global_config(self, config_data: Dict[str, Any]):
        """Process global configuration"""
        await self._update_global_config_from_dict(config_data)
    
    async def _update_global_config_from_dict(self, config_data: Dict[str, Any]):
        """Update global configuration from dictionary"""
        if 'default_cache_ttl' in config_data:
            self._global_config.default_cache_ttl = config_data['default_cache_ttl']
        if 'max_render_time_ms' in config_data:
            self._global_config.max_render_time_ms = config_data['max_render_time_ms']
        if 'fallback_enabled' in config_data:
            self._global_config.fallback_enabled = config_data['fallback_enabled']
        if 'metrics_enabled' in config_data:
            self._global_config.metrics_enabled = config_data['metrics_enabled']
        if 'validation_enabled' in config_data:
            self._global_config.validation_enabled = config_data['validation_enabled']
        if 'max_parallel_steps' in config_data:
            self._global_config.max_parallel_steps = config_data['max_parallel_steps']
        if 'step_timeout_seconds' in config_data:
            self._global_config.step_timeout_seconds = config_data['step_timeout_seconds']
        if 'enable_step_caching' in config_data:
            self._global_config.enable_step_caching = config_data['enable_step_caching']
        if 'cache_ttl_seconds' in config_data:
            self._global_config.cache_ttl_seconds = config_data['cache_ttl_seconds']
    
    async def _validate_configurations(self):
        """Validate loaded configurations"""
        validation_errors = []
        
        # Validate service mappings
        for service_name, mapping in self._service_mappings.items():
            if not mapping.primary_templates:
                validation_errors.append(f"Service '{service_name}' has no primary templates")
            
            # Validate composition references
            for comp in mapping.compositions:
                comp_name = comp.get('name')
                if comp_name and comp_name not in self._composition_rules:
                    validation_errors.append(
                        f"Service '{service_name}' references unknown composition: {comp_name}"
                    )
        
        # Validate composition rules
        for comp_name, rule in self._composition_rules.items():
            if not rule.system_prompts:
                validation_errors.append(f"Composition '{comp_name}' has no system prompts")
        
        if validation_errors:
            error_msg = f"Configuration validation failed: {'; '.join(validation_errors)}"
            logger.error(error_msg)
            raise PromptCompositionError(error_msg)
        
        logger.info("Configuration validation passed")
    
    # Service Configuration Methods
    
    def get_service_mapping(self, service_name: str) -> Optional[ServiceMapping]:
        """Get service mapping configuration"""
        return self._service_mappings.get(service_name)
    
    def get_service_templates(self, service_name: str) -> List[Dict[str, Any]]:
        """Get templates available to a service"""
        mapping = self.get_service_mapping(service_name)
        if not mapping:
            return []
        
        templates = []
        
        # Add primary templates
        for template in mapping.primary_templates:
            templates.append(template)
        
        # Add templates based on discovery rules
        discovery_rules = self._discovery_rules
        global_tags = discovery_rules.get('global_tags', [])
        service_patterns = discovery_rules.get('service_tag_patterns', {})
        
        service_tags = service_patterns.get(service_name, [])
        all_service_tags = global_tags + service_tags + mapping.tags
        
        return templates
    
    def get_service_compositions(self, service_name: str) -> List[Dict[str, Any]]:
        """Get compositions available to a service"""
        mapping = self.get_service_mapping(service_name)
        if not mapping:
            return []
        
        return mapping.compositions
    
    def get_service_performance_targets(self, service_name: str) -> Dict[str, Any]:
        """Get performance targets for a service"""
        mapping = self.get_service_mapping(service_name)
        if not mapping:
            return {}
        
        return mapping.performance_targets
    
    def validate_service_context(
        self, 
        service_name: str, 
        context_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate context against service requirements"""
        mapping = self.get_service_mapping(service_name)
        if not mapping:
            return {'valid': True, 'missing_variables': []}
        
        missing_variables = []
        for required_var in mapping.context_requirements:
            if required_var not in context_variables:
                missing_variables.append(required_var)
        
        return {
            'valid': len(missing_variables) == 0,
            'missing_variables': missing_variables,
            'required_variables': mapping.context_requirements
        }
    
    # Composition Configuration Methods
    
    def get_composition_rule(self, composition_name: str) -> Optional[CompositionRule]:
        """Get composition rule configuration"""
        return self._composition_rules.get(composition_name)
    
    # Workflow configuration removed - LangGraph handles orchestration
    
    def _apply_context_overrides(
        self, 
        rule: CompositionRule, 
        context: Dict[str, Any]
    ) -> CompositionRule:
        """Apply context-based overrides to composition rule"""
        # Create a copy of the rule
        effective_rule = CompositionRule(
            name=rule.name,
            description=rule.description,
            version=rule.version,
            system_prompts=rule.system_prompts.copy(),
            estimated_duration_seconds=rule.estimated_duration_seconds,
            max_tokens_total=rule.max_tokens_total,
            error_handling=rule.error_handling.copy()
        )
        
        # Apply state-specific overrides
        australian_state = context.get('australian_state')
        if australian_state and australian_state in self._state_overrides:
            state_config = self._state_overrides[australian_state]
            
            # Apply system prompt overrides
            prompt_overrides = state_config.get('system_prompt_overrides', {})
            for i, prompt in enumerate(effective_rule.system_prompts):
                prompt_name = prompt.get('name')
                if prompt_name in prompt_overrides:
                    effective_rule.system_prompts[i] = {
                        **prompt,
                        'path': prompt_overrides[prompt_name]
                    }
        
        # Apply user experience level adjustments - removed workflow_steps references
        
        return effective_rule
    
    def list_available_compositions(self, service_name: str = None) -> List[Dict[str, Any]]:
        """List available composition rules"""
        compositions = []
        
        for comp_name, rule in self._composition_rules.items():
            comp_info = {
                'name': comp_name,
                'description': rule.description,
                'version': rule.version,
                'deprecated': rule.deprecated,
                'replacement': rule.replacement,
                'estimated_duration_seconds': rule.estimated_duration_seconds
            }
            
            # Filter by service if specified
            if service_name:
                mapping = self.get_service_mapping(service_name)
                if mapping:
                    service_compositions = {comp['name'] for comp in mapping.compositions}
                    if comp_name not in service_compositions:
                        continue
            
            compositions.append(comp_info)
        
        return compositions
    
    # Global Configuration Methods
    
    def get_global_config(self) -> GlobalConfiguration:
        """Get global configuration"""
        return self._global_config
    
    def update_global_config(self, **kwargs):
        """Update global configuration"""
        for key, value in kwargs.items():
            if hasattr(self._global_config, key):
                setattr(self._global_config, key, value)
    
    # Cache and Reload Methods
    
    async def reload_configurations(self):
        """Reload all configurations from disk"""
        try:
            await self._load_all_configurations()
            await self._validate_configurations()
            logger.info("Configurations reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload configurations: {e}")
            raise
    
    def clear_config_cache(self):
        """Clear configuration cache"""
        self._config_cache.clear()
        self._last_loaded.clear()
        logger.info("Configuration cache cleared")
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration manager information"""
        return {
            'config_dir': str(self.config_dir),
            'service_mappings_count': len(self._service_mappings),
            'composition_rules_count': len(self._composition_rules),
            'last_loaded': {
                config_type: timestamp.isoformat() 
                for config_type, timestamp in self._last_loaded.items()
            },
            'global_config': {
                'default_cache_ttl': self._global_config.default_cache_ttl,
                'max_render_time_ms': self._global_config.max_render_time_ms,
                'validation_enabled': self._global_config.validation_enabled,
                'metrics_enabled': self._global_config.metrics_enabled
            }
        }
    
    def get_configuration_hash(self) -> str:
        """Get hash of current configuration state"""
        config_data = {
            'service_mappings': len(self._service_mappings),
            'composition_rules': len(self._composition_rules),
            'last_loaded': self._last_loaded
        }
        
        config_string = str(sorted(config_data.items()))
        return hashlib.md5(config_string.encode()).hexdigest()[:8]