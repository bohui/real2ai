"""
Configuration Validator for Prompt System
Validates that all compositions resolve to existing templates and fragments
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Set
import yaml
from .exceptions import PromptCompositionError

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates prompt system configuration files"""
    
    def __init__(self, templates_dir: Path, config_dir: Path):
        """Initialize validator
        
        Args:
            templates_dir: Directory containing prompt templates
            config_dir: Directory containing configuration files
        """
        self.templates_dir = Path(templates_dir)
        self.config_dir = Path(config_dir)
        
    def validate_all_configurations(self) -> Dict[str, Any]:
        """Validate all configuration files
        
        Returns:
            Validation results with any errors found
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "compositions_checked": 0,
            "templates_found": 0,
            "fragments_found": 0,
        }
        
        try:
            # Load composition rules
            composition_file = self.config_dir / "composition_rules.yaml"
            if not composition_file.exists():
                results["errors"].append(f"Composition rules file not found: {composition_file}")
                results["valid"] = False
                return results
                
            with open(composition_file, 'r') as f:
                composition_data = yaml.safe_load(f)
                
            # Validate each composition
            compositions = composition_data.get("compositions", {})
            results["compositions_checked"] = len(compositions)
            
            for comp_name, comp_config in compositions.items():
                comp_errors = self._validate_composition(comp_name, comp_config)
                if comp_errors:
                    results["errors"].extend(comp_errors)
                    results["valid"] = False
                    
            # Count existing templates and fragments
            results["templates_found"] = self._count_templates()
            results["fragments_found"] = self._count_fragments()
            
            logger.info(f"Configuration validation complete: {len(results['errors'])} errors found")
            
        except Exception as e:
            results["errors"].append(f"Validation failed with exception: {str(e)}")
            results["valid"] = False
            
        return results
    
    def _validate_composition(self, name: str, config: Dict[str, Any]) -> List[str]:
        """Validate a single composition
        
        Args:
            name: Composition name
            config: Composition configuration
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check system prompts
        system_prompts = config.get("system_prompts", [])
        for prompt in system_prompts:
            if isinstance(prompt, dict):
                path = prompt.get("path")
                if path and not self._template_exists(path):
                    errors.append(f"Composition '{name}': System prompt template not found: {path}")
            elif isinstance(prompt, str):
                if not self._template_exists(f"system/{prompt}.md"):
                    errors.append(f"Composition '{name}': System prompt template not found: system/{prompt}.md")
                    
        # Check workflow steps
        workflow_steps = config.get("workflow_steps", [])
        for step in workflow_steps:
            template = step.get("template")
            if template and not self._template_exists(f"user/{template}.md"):
                errors.append(f"Composition '{name}': Step template not found: user/{template}.md")
                
        return errors
    
    def _template_exists(self, template_path: str) -> bool:
        """Check if a template file exists
        
        Args:
            template_path: Relative path to template
            
        Returns:
            True if template exists
        """
        full_path = self.templates_dir / template_path
        return full_path.exists()
    
    def _count_templates(self) -> int:
        """Count total number of template files"""
        count = 0
        for pattern in ["**/*.md", "**/*.txt"]:
            count += len(list(self.templates_dir.glob(pattern)))
        return count
    
    def _count_fragments(self) -> int:
        """Count total number of fragment files"""
        fragments_dir = self.templates_dir / "fragments"
        if not fragments_dir.exists():
            return 0
        count = 0
        for pattern in ["**/*.md", "**/*.txt"]:
            count += len(list(fragments_dir.glob(pattern)))
        return count
    
    def validate_orchestrators(self) -> Dict[str, Any]:
        """Validate fragment orchestrator configurations
        
        Returns:
            Validation results for orchestrators
        """
        results = {
            "valid": True,
            "errors": [],
            "orchestrators_checked": 0,
        }
        
        try:
            # Find all orchestrator files
            orchestrator_files = list(self.config_dir.glob("*_orchestrator.yaml"))
            results["orchestrators_checked"] = len(orchestrator_files)
            
            for orch_file in orchestrator_files:
                with open(orch_file, 'r') as f:
                    orch_data = yaml.safe_load(f)
                    
                # Validate fragment references
                fragments = orch_data.get("fragments", {})
                for fragment_group, fragment_config in fragments.items():
                    mappings = fragment_config.get("mappings", {})
                    for condition, fragment_paths in mappings.items():
                        if isinstance(fragment_paths, list):
                            for fragment_path in fragment_paths:
                                if not self._template_exists(fragment_path):
                                    results["errors"].append(
                                        f"Orchestrator '{orch_file.name}': Fragment not found: {fragment_path}"
                                    )
                                    results["valid"] = False
                                    
        except Exception as e:
            results["errors"].append(f"Orchestrator validation failed: {str(e)}")
            results["valid"] = False
            
        return results


def validate_prompt_configurations(templates_dir: Path, config_dir: Path) -> Dict[str, Any]:
    """Convenience function to validate all prompt configurations
    
    Args:
        templates_dir: Directory containing prompt templates
        config_dir: Directory containing configuration files
        
    Returns:
        Comprehensive validation results
    """
    validator = ConfigValidator(templates_dir, config_dir)
    
    # Validate compositions
    comp_results = validator.validate_all_configurations()
    
    # Validate orchestrators
    orch_results = validator.validate_orchestrators()
    
    # Combine results
    combined_results = {
        "valid": comp_results["valid"] and orch_results["valid"],
        "compositions": comp_results,
        "orchestrators": orch_results,
        "summary": {
            "total_errors": len(comp_results["errors"]) + len(orch_results["errors"]),
            "compositions_checked": comp_results["compositions_checked"],
            "orchestrators_checked": orch_results["orchestrators_checked"],
            "templates_found": comp_results["templates_found"],
            "fragments_found": comp_results["fragments_found"],
        }
    }
    
    return combined_results