"""Prompt Management System for Real2.AI

Advanced prompt management with versioning, templating, validation,
service integration, and workflow execution capabilities.

Phase 1 Features:
- Enhanced PromptManager with service integration
- Workflow execution engine for complex prompt compositions
- Configuration management for service mappings and composition rules
- Service mixin for standardized prompt consumption
- Factory methods for easy setup
"""

# Core components
from .manager import PromptManager, PromptManagerConfig, get_prompt_manager
from .loader import PromptLoader
from .validator import PromptValidator
from .template import PromptTemplate
from .context import PromptContext, ContextType, ContextBuilder, ContextPresets

# Phase 1 enhancements
from .service_mixin import PromptEnabledService
from .workflow_engine import WorkflowExecutionEngine, WorkflowConfiguration, WorkflowStep
from .config_manager import ConfigurationManager, ServiceMapping, CompositionRule
from .factory import PromptManagerFactory, create_prompt_manager_for_app, create_service_prompt_manager

# Exceptions
from .exceptions import (
    PromptError,
    PromptNotFoundError,
    PromptValidationError,
    PromptTemplateError,
    PromptVersionError,
    PromptContextError,
    PromptCompositionError,
    PromptServiceError,
)

# Convenience imports for backward compatibility
try:
    from .composer import PromptComposer, ComposedPrompt
except ImportError:
    # Composer may not be available in minimal installations
    PromptComposer = None
    ComposedPrompt = None

__version__ = "2.0.0-phase1"

__all__ = [
    # Core components
    "PromptManager",
    "PromptManagerConfig",
    "get_prompt_manager",
    "PromptLoader",
    "PromptValidator", 
    "PromptTemplate",
    "PromptContext",
    "ContextType",
    "ContextBuilder",
    "ContextPresets",
    
    # Phase 1 enhancements
    "PromptEnabledService",
    "WorkflowExecutionEngine",
    "WorkflowConfiguration",
    "WorkflowStep",
    "ConfigurationManager",
    "ServiceMapping",
    "CompositionRule",
    "PromptManagerFactory",
    "create_prompt_manager_for_app",
    "create_service_prompt_manager",
    
    # Exceptions
    "PromptError",
    "PromptNotFoundError",
    "PromptValidationError",
    "PromptTemplateError",
    "PromptVersionError",
    "PromptContextError",
    "PromptCompositionError",
    "PromptServiceError",
]

# Add composer components if available
if PromptComposer is not None:
    __all__.extend(["PromptComposer", "ComposedPrompt"])


# Phase 1 Quick Start Guide
def quick_start_guide():
    """Display quick start guide for Phase 1 PromptManager system"""
    guide = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                   PromptManager Phase 1 Quick Start             ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                  ║
    ║  1. Create PromptManager Instance:                              ║
    ║     manager = await create_prompt_manager_for_app(              ║
    ║         app_root=Path("/path/to/app"),                          ║
    ║         environment="development"                               ║
    ║     )                                                           ║
    ║                                                                  ║
    ║  2. Create Service with Prompt Integration:                     ║
    ║     class MyService(PromptEnabledService):                      ║
    ║         async def process(self, data):                          ║
    ║             result = await self.render_prompt(                  ║
    ║                 template_name="my_template",                    ║
    ║                 context={"data": data}                          ║
    ║             )                                                   ║
    ║             return result                                       ║
    ║                                                                  ║
    ║  3. Execute Workflows:                                          ║
    ║     workflow_result = await service.execute_workflow(           ║
    ║         composition_name="my_workflow",                         ║
    ║         context={"input_data": data}                            ║
    ║     )                                                           ║
    ║                                                                  ║
    ║  4. Monitor and Manage:                                         ║
    ║     health = await manager.health_check()                       ║
    ║     metrics = manager.get_metrics()                             ║
    ║     status = manager.get_workflow_status(workflow_id)           ║
    ║                                                                  ║
    ║  See examples.py for detailed usage examples                    ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(guide)


# Make quick start guide easily accessible
__all__.append("quick_start_guide")