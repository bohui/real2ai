"""
Configuration for Enhanced Contract Analysis Workflow
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os

from app.core.prompts import PromptManagerConfig


@dataclass
class EnhancedWorkflowConfig:
    """Configuration for Enhanced Contract Analysis Workflow"""
    
    # Core workflow settings
    enable_validation: bool = True
    enable_quality_checks: bool = True
    enable_prompt_manager: bool = True
    enable_structured_parsing: bool = True
    
    # Performance settings
    max_retries: int = 3
    retry_exponential_backoff: bool = True
    parsing_timeout_seconds: int = 30
    
    # Quality thresholds
    min_document_quality_score: float = 0.5
    min_extraction_confidence: float = 0.4
    min_parsing_confidence: float = 0.6
    min_overall_confidence: float = 0.7
    
    # Validation settings
    validation_step_timeout: int = 10
    require_mandatory_terms: bool = True
    validate_state_compliance: bool = True
    
    # Prompt manager settings
    prompt_templates_dir: Optional[Path] = None
    prompt_config_dir: Optional[Path] = None
    enable_prompt_caching: bool = True
    enable_hot_reload: bool = False
    
    # Parser settings
    parser_strict_mode: bool = False
    parser_retry_on_failure: bool = True
    parser_max_retries: int = 2
    
    # Logging and monitoring
    enable_performance_metrics: bool = True
    enable_detailed_logging: bool = True
    log_parsing_failures: bool = True
    log_fallback_usage: bool = True
    
    # Feature flags
    enable_enhanced_error_handling: bool = True
    enable_fallback_mechanisms: bool = True
    enable_confidence_scoring: bool = True
    enable_quality_indicators: bool = True
    
    @classmethod
    def from_environment(cls) -> 'EnhancedWorkflowConfig':
        """Create configuration from environment variables"""
        
        # Get base directories
        base_dir = Path(__file__).parent.parent
        prompts_dir = base_dir / "prompts"
        
        return cls(
            # Core settings from environment
            enable_validation=os.getenv("ENHANCED_WORKFLOW_VALIDATION", "true").lower() == "true",
            enable_quality_checks=os.getenv("ENHANCED_WORKFLOW_QUALITY_CHECKS", "true").lower() == "true",
            enable_prompt_manager=os.getenv("ENHANCED_WORKFLOW_PROMPT_MANAGER", "true").lower() == "true",
            enable_structured_parsing=os.getenv("ENHANCED_WORKFLOW_STRUCTURED_PARSING", "true").lower() == "true",
            
            # Performance settings
            max_retries=int(os.getenv("ENHANCED_WORKFLOW_MAX_RETRIES", "3")),
            retry_exponential_backoff=os.getenv("ENHANCED_WORKFLOW_EXPONENTIAL_BACKOFF", "true").lower() == "true",
            parsing_timeout_seconds=int(os.getenv("ENHANCED_WORKFLOW_PARSING_TIMEOUT", "30")),
            
            # Quality thresholds
            min_document_quality_score=float(os.getenv("ENHANCED_WORKFLOW_MIN_DOC_QUALITY", "0.5")),
            min_extraction_confidence=float(os.getenv("ENHANCED_WORKFLOW_MIN_EXTRACTION_CONFIDENCE", "0.4")),
            min_parsing_confidence=float(os.getenv("ENHANCED_WORKFLOW_MIN_PARSING_CONFIDENCE", "0.6")),
            min_overall_confidence=float(os.getenv("ENHANCED_WORKFLOW_MIN_OVERALL_CONFIDENCE", "0.7")),
            
            # Prompt manager paths
            prompt_templates_dir=prompts_dir / "templates",
            prompt_config_dir=prompts_dir / "config",
            enable_prompt_caching=os.getenv("ENHANCED_WORKFLOW_PROMPT_CACHING", "true").lower() == "true",
            enable_hot_reload=os.getenv("ENHANCED_WORKFLOW_HOT_RELOAD", "false").lower() == "true",
            
            # Parser settings
            parser_strict_mode=os.getenv("ENHANCED_WORKFLOW_PARSER_STRICT", "false").lower() == "true",
            parser_retry_on_failure=os.getenv("ENHANCED_WORKFLOW_PARSER_RETRY", "true").lower() == "true",
            parser_max_retries=int(os.getenv("ENHANCED_WORKFLOW_PARSER_MAX_RETRIES", "2")),
            
            # Monitoring
            enable_performance_metrics=os.getenv("ENHANCED_WORKFLOW_METRICS", "true").lower() == "true",
            enable_detailed_logging=os.getenv("ENHANCED_WORKFLOW_DETAILED_LOGGING", "true").lower() == "true",
            log_parsing_failures=os.getenv("ENHANCED_WORKFLOW_LOG_PARSING_FAILURES", "true").lower() == "true",
            log_fallback_usage=os.getenv("ENHANCED_WORKFLOW_LOG_FALLBACK_USAGE", "true").lower() == "true",
        )
    
    def to_prompt_manager_config(self) -> PromptManagerConfig:
        """Convert to PromptManagerConfig"""
        
        if not self.prompt_templates_dir:
            base_dir = Path(__file__).parent.parent
            self.prompt_templates_dir = base_dir / "prompts" / "templates"
        
        if not self.prompt_config_dir:
            base_dir = Path(__file__).parent.parent
            self.prompt_config_dir = base_dir / "prompts" / "config"
        
        return PromptManagerConfig(
            templates_dir=self.prompt_templates_dir,
            config_dir=self.prompt_config_dir,
            cache_enabled=self.enable_prompt_caching,
            validation_enabled=self.enable_validation,
            hot_reload_enabled=self.enable_hot_reload,
            preload_templates=True,
            default_model="gpt-4",
            max_render_time_seconds=self.parsing_timeout_seconds,
            enable_metrics=self.enable_performance_metrics,
            enable_composition=True,
            enable_workflows=True,
            enable_service_integration=True
        )
    
    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get quality threshold configuration"""
        return {
            "document_quality": self.min_document_quality_score,
            "extraction_confidence": self.min_extraction_confidence,
            "parsing_confidence": self.min_parsing_confidence,
            "overall_confidence": self.min_overall_confidence
        }
    
    def get_parser_config(self) -> Dict[str, Any]:
        """Get parser configuration"""
        return {
            "strict_mode": self.parser_strict_mode,
            "retry_on_failure": self.parser_retry_on_failure,
            "max_retries": self.parser_max_retries,
            "timeout_seconds": self.parsing_timeout_seconds
        }
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration"""
        return {
            "enabled": self.enable_validation,
            "quality_checks": self.enable_quality_checks,
            "step_timeout": self.validation_step_timeout,
            "require_mandatory_terms": self.require_mandatory_terms,
            "validate_state_compliance": self.validate_state_compliance
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return {
            "max_retries": self.max_retries,
            "exponential_backoff": self.retry_exponential_backoff,
            "timeout_seconds": self.parsing_timeout_seconds,
            "enable_metrics": self.enable_performance_metrics
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "detailed_logging": self.enable_detailed_logging,
            "log_parsing_failures": self.log_parsing_failures,
            "log_fallback_usage": self.log_fallback_usage,
            "enable_metrics": self.enable_performance_metrics
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled"""
        feature_map = {
            "validation": self.enable_validation,
            "quality_checks": self.enable_quality_checks,
            "prompt_manager": self.enable_prompt_manager,
            "structured_parsing": self.enable_structured_parsing,
            "enhanced_error_handling": self.enable_enhanced_error_handling,
            "fallback_mechanisms": self.enable_fallback_mechanisms,
            "confidence_scoring": self.enable_confidence_scoring,
            "quality_indicators": self.enable_quality_indicators,
            "performance_metrics": self.enable_performance_metrics
        }
        
        return feature_map.get(feature, False)
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        issues = []
        warnings = []
        
        # Check template directories exist
        if self.enable_prompt_manager:
            if not self.prompt_templates_dir or not self.prompt_templates_dir.exists():
                issues.append(f"Prompt templates directory not found: {self.prompt_templates_dir}")
            
            if not self.prompt_config_dir or not self.prompt_config_dir.exists():
                warnings.append(f"Prompt config directory not found: {self.prompt_config_dir}")
        
        # Check threshold values
        if not 0 <= self.min_document_quality_score <= 1:
            issues.append("min_document_quality_score must be between 0 and 1")
        
        if not 0 <= self.min_extraction_confidence <= 1:
            issues.append("min_extraction_confidence must be between 0 and 1")
        
        if not 0 <= self.min_parsing_confidence <= 1:
            issues.append("min_parsing_confidence must be between 0 and 1")
        
        if not 0 <= self.min_overall_confidence <= 1:
            issues.append("min_overall_confidence must be between 0 and 1")
        
        # Check retry limits
        if self.max_retries < 1 or self.max_retries > 10:
            warnings.append("max_retries should be between 1 and 10")
        
        if self.parser_max_retries < 1 or self.parser_max_retries > 5:
            warnings.append("parser_max_retries should be between 1 and 5")
        
        # Check timeout values
        if self.parsing_timeout_seconds < 5 or self.parsing_timeout_seconds > 300:
            warnings.append("parsing_timeout_seconds should be between 5 and 300")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "config_summary": {
                "validation_enabled": self.enable_validation,
                "quality_checks_enabled": self.enable_quality_checks,
                "prompt_manager_enabled": self.enable_prompt_manager,
                "structured_parsing_enabled": self.enable_structured_parsing,
                "performance_metrics_enabled": self.enable_performance_metrics
            }
        }


# Configuration instances
DEFAULT_CONFIG = EnhancedWorkflowConfig()
ENVIRONMENT_CONFIG = EnhancedWorkflowConfig.from_environment()

# Configuration factory function
def get_enhanced_workflow_config(use_environment: bool = True) -> EnhancedWorkflowConfig:
    """Get enhanced workflow configuration"""
    if use_environment:
        return ENVIRONMENT_CONFIG
    else:
        return DEFAULT_CONFIG


def validate_workflow_configuration(config: EnhancedWorkflowConfig) -> Dict[str, Any]:
    """Validate workflow configuration and return results"""
    return config.validate_config()


# Export configuration classes and functions
__all__ = [
    'EnhancedWorkflowConfig',
    'DEFAULT_CONFIG',
    'ENVIRONMENT_CONFIG',
    'get_enhanced_workflow_config',
    'validate_workflow_configuration'
]