"""
Service Mixin for Standardized PromptManager Integration
Provides consistent prompt consumption patterns across all services
"""

from abc import ABC
from typing import Dict, Any, Union, Optional, List
from datetime import datetime
import hashlib
import logging

from .manager import get_prompt_manager, PromptManager
from .context import PromptContext, ContextType
from .exceptions import PromptServiceError

logger = logging.getLogger(__name__)


class PromptEnabledService(ABC):
    """Base class for services that use PromptManager
    
    Provides standardized methods for prompt rendering, caching, and performance tracking.
    All services should inherit from this class to ensure consistent prompt management.
    """
    
    def __init__(self):
        """Initialize service with PromptManager integration"""
        self.prompt_manager: PromptManager = get_prompt_manager()
        self._service_name = self.__class__.__name__.lower().replace('service', '')
        self._render_stats = {
            'total_renders': 0,
            'cache_hits': 0,
            'errors': 0,
            'avg_render_time': 0.0
        }
        
        logger.info(f"Initialized PromptEnabledService: {self._service_name}")
    
    async def render_prompt(
        self,
        template_name: str,
        context: Union[Dict[str, Any], PromptContext],
        version: str = None,
        model: str = None,
        validate: bool = None,
        use_cache: bool = True,
        output_parser: Optional['BaseOutputParser'] = None,
        **kwargs
    ) -> str:
        """Render a single prompt template
        
        Args:
            template_name: Name of the template to render
            context: Context variables or PromptContext object
            version: Specific template version (optional)
            model: Target AI model for validation (optional)
            validate: Override validation setting (optional)
            use_cache: Whether to use caching (default: True)
            output_parser: Optional output parser for structured output
            **kwargs: Additional template variables
            
        Returns:
            Rendered prompt string
            
        Raises:
            PromptServiceError: If rendering fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate cache key if caching enabled
            cache_key = None
            if use_cache:
                cache_key = self._generate_cache_key(template_name, context, version, kwargs)
            
            # Convert dict to PromptContext if needed
            if isinstance(context, dict):
                context = self._dict_to_context(context)
            
            # Add service metadata to context
            context.variables.setdefault('service_name', self._service_name)
            context.variables.setdefault('timestamp', datetime.utcnow().isoformat())
            
            # Render prompt
            result = await self.prompt_manager.render(
                template_name=template_name,
                context=context,
                version=version,
                model=model,
                validate=validate,
                cache_key=cache_key,
                service_name=self._service_name,
                output_parser=output_parser,
                **kwargs
            )
            
            # Update statistics
            render_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_render_stats(render_time, cache_hit=cache_key is not None)
            
            logger.debug(f"Rendered prompt '{template_name}' for {self._service_name} in {render_time:.3f}s")
            
            return result
            
        except Exception as e:
            self._render_stats['errors'] += 1
            logger.error(f"Failed to render prompt '{template_name}' for {self._service_name}: {e}")
            raise PromptServiceError(
                f"Prompt rendering failed for service '{self._service_name}': {str(e)}",
                service_name=self._service_name,
                template_name=template_name,
                details={'error_type': type(e).__name__}
            )
    
    async def render_composed(
        self,
        composition_name: str,
        context: Union[Dict[str, Any], PromptContext],
        variables: Dict[str, Any] = None,
        return_parts: bool = True,
        **kwargs
    ) -> Union[str, Dict[str, str]]:
        """Render system+user composed prompts
        
        Args:
            composition_name: Name of composition rule
            context: Context variables or PromptContext object
            variables: Additional template variables
            return_parts: If True, return dict with 'system' and 'user' keys
            **kwargs: Additional composition options
            
        Returns:
            Combined prompt string or dict with separate parts
            
        Raises:
            PromptServiceError: If composition fails
        """
        try:
            # Convert dict to PromptContext if needed
            if isinstance(context, dict):
                context = self._dict_to_context(context)
            
            # Add service metadata
            context.variables.setdefault('service_name', self._service_name)
            context.variables.setdefault('timestamp', datetime.utcnow().isoformat())
            
            # Merge additional variables
            if variables:
                context.variables.update(variables)
            
            # Render composed prompt
            result = await self.prompt_manager.render_composed(
                composition_name=composition_name,
                context=context,
                variables=variables,
                return_parts=return_parts,
                **kwargs
            )
            
            logger.debug(f"Rendered composition '{composition_name}' for {self._service_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to render composition '{composition_name}' for {self._service_name}: {e}")
            raise PromptServiceError(
                f"Prompt composition failed for service '{self._service_name}': {str(e)}",
                service_name=self._service_name,
                composition_name=composition_name,
                details={'error_type': type(e).__name__}
            )
    
    async def execute_workflow(
        self,
        composition_name: str,
        context: Union[Dict[str, Any], PromptContext],
        variables: Dict[str, Any] = None,
        workflow_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a workflow composition
        
        Args:
            composition_name: Name of composition to execute
            context: Context variables or PromptContext object
            variables: Additional variables
            workflow_id: Optional workflow ID for tracking
            **kwargs: Additional workflow options
            
        Returns:
            Workflow execution results
            
        Raises:
            PromptServiceError: If workflow execution fails
        """
        try:
            # Convert dict to PromptContext if needed
            if isinstance(context, dict):
                context = self._dict_to_context(context)
            
            # Add service metadata
            context.variables.setdefault('service_name', self._service_name)
            context.variables.setdefault('timestamp', datetime.utcnow().isoformat())
            
            # Merge additional variables
            if variables:
                context.variables.update(variables)
            
            # Execute workflow
            result = await self.prompt_manager.execute_workflow(
                composition_name=composition_name,
                context=context,
                variables=variables,
                workflow_id=workflow_id,
                service_name=self._service_name,
                **kwargs
            )
            
            logger.info(f"Executed workflow '{composition_name}' for {self._service_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute workflow '{composition_name}' for {self._service_name}: {e}")
            raise PromptServiceError(
                f"Workflow execution failed for service '{self._service_name}': {str(e)}",
                service_name=self._service_name,
                composition_name=composition_name,
                details={'error_type': type(e).__name__}
            )
    
    async def batch_render(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Render multiple prompts concurrently
        
        Args:
            requests: List of render requests
            max_concurrent: Maximum concurrent renders
            
        Returns:
            List of render results
        """
        try:
            # Add service name to all requests
            for request in requests:
                if 'context' in request:
                    if isinstance(request['context'], dict):
                        request['context']['service_name'] = self._service_name
                    elif isinstance(request['context'], PromptContext):
                        request['context'].variables['service_name'] = self._service_name
            
            results = await self.prompt_manager.batch_render(
                requests=requests,
                max_concurrent=max_concurrent
            )
            
            logger.info(f"Batch rendered {len(requests)} prompts for {self._service_name}")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch render failed for {self._service_name}: {e}")
            raise PromptServiceError(
                f"Batch prompt rendering failed for service '{self._service_name}': {str(e)}",
                service_name=self._service_name,
                details={'error_type': type(e).__name__, 'request_count': len(requests)}
            )
    
    async def render_with_parser(
        self,
        template_name: str,
        context: Union[Dict[str, Any], PromptContext],
        output_parser: 'BaseOutputParser',
        version: str = None,
        model: str = None,
        validate: bool = None,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """Render prompt with automatic format instructions injection
        
        Args:
            template_name: Name of template to render
            context: Context variables or PromptContext object
            output_parser: Output parser for structured output
            version: Specific template version (optional)
            model: Target AI model for validation (optional)
            validate: Override validation setting (optional)
            use_cache: Whether to use caching (default: True)
            **kwargs: Additional template variables
            
        Returns:
            Rendered prompt string with format instructions
        """
        return await self.render_prompt(
            template_name=template_name,
            context=context,
            version=version,
            model=model,
            validate=validate,
            use_cache=use_cache,
            output_parser=output_parser,
            **kwargs
        )
    
    async def parse_ai_response(
        self,
        template_name: str,
        ai_response: str,
        output_parser: 'BaseOutputParser',
        version: str = None,
        use_retry: bool = True
    ) -> 'ParsingResult':
        """Parse AI response using specified parser
        
        Args:
            template_name: Name of template used for the response
            ai_response: Raw AI response text
            output_parser: Parser for structured output
            version: Template version used (optional)
            use_retry: Whether to use retry mechanism (default: True)
            
        Returns:
            ParsingResult with parsed data or error information
        """
        try:
            result = await self.prompt_manager.parse_ai_response(
                template_name=template_name,
                ai_response=ai_response,
                output_parser=output_parser,
                version=version,
                use_retry=use_retry
            )
            
            if result.success:
                logger.debug(f"Successfully parsed AI response for {self._service_name}")
            else:
                logger.warning(f"Failed to parse AI response for {self._service_name}: {result.parsing_errors}")
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error parsing AI response for {self._service_name}: {e}")
            from .output_parser import ParsingResult
            return ParsingResult(
                success=False,
                raw_output=ai_response,
                parsing_errors=[f"Service parsing error: {str(e)}"]
            )
    
    async def render_and_expect_structured(
        self,
        template_name: str,
        context: Union[Dict[str, Any], PromptContext],
        pydantic_model: type,
        version: str = None,
        model: str = None,
        validate: bool = None,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """Convenience method: render prompt with auto-created parser
        
        Args:
            template_name: Name of template to render
            context: Context variables or PromptContext object
            pydantic_model: Pydantic model class for output parsing
            version: Specific template version (optional)
            model: Target AI model for validation (optional)
            validate: Override validation setting (optional)
            use_cache: Whether to use caching (default: True)
            **kwargs: Additional template variables
            
        Returns:
            Rendered prompt string with format instructions
        """
        from .output_parser import create_parser
        
        # Create parser for the Pydantic model
        parser = create_parser(pydantic_model)
        
        return await self.render_with_parser(
            template_name=template_name,
            context=context,
            output_parser=parser,
            version=version,
            model=model,
            validate=validate,
            use_cache=use_cache,
            **kwargs
        )
    
    def create_context(
        self,
        context_type: ContextType = ContextType.USER,
        **variables
    ) -> PromptContext:
        """Create context with service-specific defaults
        
        Args:
            context_type: Type of context (USER, SYSTEM, etc.)
            **variables: Context variables
            
        Returns:
            PromptContext with service metadata
        """
        # Add service-specific defaults
        variables.setdefault('service_name', self._service_name)
        variables.setdefault('timestamp', datetime.utcnow().isoformat())
        
        return PromptContext(
            context_type=context_type,
            variables=variables
        )
    
    def get_available_templates(
        self, 
        category: str = None,
        include_fallbacks: bool = False
    ) -> List[Dict[str, Any]]:
        """Get available templates for this service
        
        Args:
            category: Filter by template category (optional)
            include_fallbacks: Include fallback templates
            
        Returns:
            List of available templates
        """
        # Use service-specific templates if available
        try:
            service_templates = self.prompt_manager.get_service_templates(
                self._service_name, 
                include_fallbacks=include_fallbacks
            )
            if service_templates:
                # Filter by category if specified
                if category:
                    filtered_templates = []
                    for template in service_templates:
                        tags = template.get('tags', [])
                        if category in tags:
                            filtered_templates.append(template)
                    return filtered_templates
                return service_templates
        except Exception as e:
            logger.warning(f"Failed to get service-specific templates: {e}")
        
        # Fallback to general template discovery
        all_templates = self.prompt_manager.list_templates()
        
        # Filter by service-relevant templates
        service_templates = []
        for template in all_templates:
            # Include templates that match service name or are general purpose
            tags = template.get('tags', [])
            if (self._service_name in tags or 
                'general' in tags or 
                'shared' in tags or
                (category and category in tags)):
                service_templates.append(template)
        
        return service_templates
    
    def get_available_compositions(self) -> List[Dict[str, Any]]:
        """Get available prompt compositions"""
        try:
            # Use service-specific compositions if available
            service_compositions = self.prompt_manager.get_service_compositions(self._service_name)
            if service_compositions:
                return service_compositions
        except Exception as e:
            logger.warning(f"Failed to get service-specific compositions: {e}")
        
        # Fallback to all compositions
        return self.prompt_manager.list_compositions()
    
    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """Get available workflow compositions"""
        try:
            return self.prompt_manager.get_available_workflows(self._service_name)
        except Exception as e:
            logger.warning(f"Failed to get available workflows: {e}")
            return []
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution"""
        try:
            return self.prompt_manager.get_workflow_status(workflow_id)
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return None
    
    def get_service_performance_targets(self) -> Dict[str, Any]:
        """Get performance targets for this service"""
        try:
            return self.prompt_manager.get_service_performance_targets(self._service_name)
        except Exception as e:
            logger.warning(f"Failed to get service performance targets: {e}")
            return {}
    
    def get_render_stats(self) -> Dict[str, Any]:
        """Get rendering statistics for this service
        
        Returns:
            Dictionary with rendering statistics
        """
        return {
            'service_name': self._service_name,
            **self._render_stats,
            'cache_hit_rate': (
                self._render_stats['cache_hits'] / max(self._render_stats['total_renders'], 1)
            ),
            'error_rate': (
                self._render_stats['errors'] / max(self._render_stats['total_renders'], 1)
            )
        }
    
    async def validate_template(
        self,
        template_name: str,
        context: Union[Dict[str, Any], PromptContext] = None,
        version: str = None
    ) -> Dict[str, Any]:
        """Validate a template for this service
        
        Args:
            template_name: Name of template to validate
            context: Context for validation (optional)
            version: Template version (optional)
            
        Returns:
            Validation results
        """
        try:
            if context:
                # Convert and add service metadata
                if isinstance(context, dict):
                    context = self._dict_to_context(context)
                context.variables.setdefault('service_name', self._service_name)
                
                validation_result = await self.prompt_manager.validate_context(
                    template_name=template_name,
                    context=context,
                    version=version
                )
            else:
                validation_result = await self.prompt_manager.validate_template(
                    template_name=template_name,
                    version=version
                )
            
            return {
                'valid': validation_result.is_valid,
                'issues': [
                    {
                        'message': issue.message,
                        'severity': issue.severity.value,
                        'field': getattr(issue, 'field', None)
                    }
                    for issue in validation_result.issues
                ]
            }
            
        except Exception as e:
            logger.error(f"Template validation failed for {self._service_name}: {e}")
            return {
                'valid': False,
                'issues': [{'message': str(e), 'severity': 'error', 'field': None}]
            }
    
    def _dict_to_context(self, data: Dict[str, Any]) -> PromptContext:
        """Convert dictionary to PromptContext"""
        return PromptContext(
            context_type=ContextType.USER,
            variables=data
        )
    
    def _generate_cache_key(
        self,
        template_name: str,
        context: Union[Dict[str, Any], PromptContext],
        version: str = None,
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Generate cache key for prompt rendering"""
        # Create stable hash from all inputs
        cache_data = {
            'service': self._service_name,
            'template': template_name,
            'version': version or 'latest',
            'context': context.variables if isinstance(context, PromptContext) else context,
            'kwargs': kwargs or {}
        }
        
        cache_string = str(sorted(cache_data.items()))
        return f"{self._service_name}_{template_name}_{hashlib.md5(cache_string.encode()).hexdigest()[:8]}"
    
    def _update_render_stats(self, render_time: float, cache_hit: bool = False):
        """Update rendering statistics"""
        self._render_stats['total_renders'] += 1
        
        if cache_hit:
            self._render_stats['cache_hits'] += 1
        
        # Update rolling average render time
        current_avg = self._render_stats['avg_render_time']
        total_renders = self._render_stats['total_renders']
        
        self._render_stats['avg_render_time'] = (
            (current_avg * (total_renders - 1) + render_time) / total_renders
        )