"""Prompt composition system for combining system and user prompts"""

import logging
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, UTC

from .template import PromptTemplate, TemplateMetadata
from .context import PromptContext, ContextType
from .fragment_manager import FragmentManager
from .exceptions import PromptCompositionError, PromptNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class CompositionRule:
    """Rule for combining prompts"""

    name: str
    description: str
    system_prompts: List[
        Dict[str, Any]
    ]  # List of dicts with name, path, priority, required
    user_prompts: List[str]  # List of prompt names as strings
    merge_strategy: str = "sequential"  # sequential, parallel, hierarchical
    priority_order: List[str] = None
    version: str = ""


@dataclass
class ComposedPrompt:
    """Result of prompt composition"""

    name: str
    system_content: str
    user_content: str
    metadata: Dict[str, Any]
    composition_rule: CompositionRule
    composed_at: datetime


class PromptComposer:
    """Advanced prompt composition system"""

    def __init__(self, prompts_dir: Path, config_dir: Path):
        self.prompts_dir = Path(prompts_dir)
        self.config_dir = Path(config_dir)

        # Initialize unified folder-driven fragment manager
        self.fragment_manager = FragmentManager(fragments_dir=prompts_dir / "fragments")

        # Load configuration
        self.composition_rules = self._load_composition_rules()
        self.prompt_registry = self._load_prompt_registry()

        # Cache for loaded templates
        self._template_cache: Dict[str, PromptTemplate] = {}

        logger.info(
            f"PromptComposer initialized with {len(self.composition_rules)} composition rules"
        )

    def compose(
        self,
        composition_name: str,
        context: PromptContext,
        variables: Dict[str, Any] = None,
        **kwargs,
    ) -> ComposedPrompt:
        """Compose a complete prompt from multiple components

        Args:
            composition_name: Name of composition rule to use
            context: Context for rendering templates
            variables: Additional template variables
            **kwargs: Additional composition options

        Returns:
            ComposedPrompt with system and user content

        Raises:
            PromptCompositionError: If composition fails
            PromptNotFoundError: If required prompts not found
        """
        if composition_name not in self.composition_rules:
            raise PromptCompositionError(
                f"Unknown composition rule: {composition_name}",
                details={"available_compositions": list(self.composition_rules.keys())},
            )

        rule = self.composition_rules[composition_name]
        logger.debug(f"Composing prompt using rule: {composition_name}")

        try:
            # Compose system prompts
            system_content = self._compose_system_prompts(
                rule, context, variables, **kwargs
            )

            # Compose user prompts (with fragment support)
            user_content = self._compose_user_prompts(
                rule, context, variables, **kwargs
            )

            # Create metadata with version info
            system_versions: Dict[str, str] = {}
            user_versions: Dict[str, str] = {}
            try:
                for sp_obj in rule.system_prompts:
                    sp_name = (
                        sp_obj["name"] if isinstance(sp_obj, dict) else str(sp_obj)
                    )
                    t = self._load_template(sp_name, "system")
                    system_versions[sp_name] = getattr(t.metadata, "version", "")
                for up_name in rule.user_prompts:
                    t = self._load_template(up_name, "user")
                    user_versions[up_name] = getattr(t.metadata, "version", "")
            except Exception:
                pass

            metadata = self._create_composition_metadata(
                rule, context, system_versions, user_versions
            )

            composed = ComposedPrompt(
                name=composition_name,
                system_content=system_content,
                user_content=user_content,
                metadata=metadata,
                composition_rule=rule,
                composed_at=datetime.now(UTC),
            )

            logger.debug(f"Successfully composed prompt: {composition_name}")
            return composed

        except Exception as e:
            logger.error(f"Failed to compose prompt {composition_name}: {e}")
            raise PromptCompositionError(
                f"Composition failed: {str(e)}",
                composition_name=composition_name,
                details={"error_type": type(e).__name__},
            )

    def _compose_system_prompts(
        self,
        rule: CompositionRule,
        context: PromptContext,
        variables: Dict[str, Any] = None,
        **kwargs,
    ) -> str:
        """Compose system prompts according to rule"""
        system_parts = []

        # Extract prompt names from system prompt objects and sort by priority
        system_prompt_names = [prompt["name"] for prompt in rule.system_prompts]
        system_prompts = self._sort_by_priority(system_prompt_names, "system")

        for prompt_name in system_prompts:
            try:
                template = self._load_template(prompt_name, "system")

                # Create system context
                variables_copy = (
                    context.variables.copy()
                    if isinstance(context.variables, dict)
                    else {}
                )
                system_context = PromptContext(
                    context_type=ContextType.SYSTEM, variables=variables_copy
                )
                if variables:
                    system_context.variables.update(variables)

                rendered = template.render(system_context, **kwargs)
                system_parts.append(rendered)

            except Exception as e:
                logger.error(f"Failed to render system prompt {prompt_name}: {e}")
                raise PromptCompositionError(
                    f"System prompt rendering failed: {prompt_name}",
                    composition_name=rule.name,
                    details={"failed_prompt": prompt_name, "error": str(e)},
                )

        return self._merge_prompt_parts(system_parts, rule.merge_strategy)

    def _compose_user_prompts(
        self,
        rule: CompositionRule,
        context: PromptContext,
        variables: Dict[str, Any] = None,
        **kwargs,
    ) -> str:
        """Compose user prompts according to rule"""
        user_parts = []

        for prompt_name in rule.user_prompts:
            try:
                template = self._load_template(prompt_name, "user")

                # Create user context
                variables_copy = (
                    context.variables.copy()
                    if isinstance(context.variables, dict)
                    else {}
                )
                user_context = PromptContext(
                    context_type=ContextType.USER, variables=variables_copy
                )
                if variables:
                    user_context.variables.update(variables)

                # Check if template has fragment orchestration
                orchestration_id = None
                if hasattr(template.metadata, "tags") and template.metadata.tags:
                    # Look for fragment orchestration in metadata
                    for tag in template.metadata.tags:
                        if tag.startswith("fragment_orchestration:"):
                            orchestration_id = tag.split(":", 1)[1]
                            break

                # Also check in the parsed metadata directly (from frontmatter)
                if not orchestration_id:
                    # We need to check the raw metadata from the file
                    orchestration_id = getattr(
                        template, "_fragment_orchestration", None
                    )

                if orchestration_id:
                    # Use new folder-driven fragments logic (ignores orchestrator mappings)
                    rendered = self.fragment_manager.compose_with_folder_fragments(
                        base_template=template.content,
                        context=user_context,
                    )
                else:
                    # Standard template rendering
                    rendered = template.render(user_context, **kwargs)

                user_parts.append(rendered)

            except Exception as e:
                logger.error(f"Failed to render user prompt {prompt_name}: {e}")
                raise PromptCompositionError(
                    f"User prompt rendering failed: {prompt_name}",
                    composition_name=rule.name,
                    details={"failed_prompt": prompt_name, "error": str(e)},
                )

        return self._merge_prompt_parts(user_parts, rule.merge_strategy)

    def _register_custom_filters(self, env):
        """Register custom filters for template rendering"""
        import json

        def currency_filter(value):
            """Format value as Australian currency"""
            if isinstance(value, (int, float)):
                return f"${value:,.2f}"
            return str(value)

        def legal_format(text):
            """Format text for legal documents"""
            if not text:
                return ""
            return text.strip().replace("\n", " ").replace("  ", " ")

        def australian_date(date_obj):
            """Format date in Australian format"""
            if isinstance(date_obj, str):
                return date_obj
            if hasattr(date_obj, "strftime"):
                return date_obj.strftime("%d/%m/%Y")
            return str(date_obj)

        def tojsonpretty(value):
            """Convert value to pretty-printed JSON"""
            try:
                return json.dumps(value, indent=2, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                return str(value)

        # Register filters
        env.filters["currency"] = currency_filter
        env.filters["legal_format"] = legal_format
        env.filters["australian_date"] = australian_date
        env.filters["tojsonpretty"] = tojsonpretty

    def _load_template(self, prompt_name: str, prompt_type: str) -> PromptTemplate:
        """Load and cache template"""
        cache_key = f"{prompt_type}:{prompt_name}"

        if cache_key not in self._template_cache:
            # Find prompt path in registry
            if prompt_type == "system":
                if prompt_name not in self.prompt_registry.get("system_prompts", {}):
                    raise PromptNotFoundError(f"System prompt not found: {prompt_name}")
                prompt_info = self.prompt_registry["system_prompts"][prompt_name]
            else:
                if prompt_name not in self.prompt_registry.get("user_prompts", {}):
                    raise PromptNotFoundError(f"User prompt not found: {prompt_name}")
                prompt_info = self.prompt_registry["user_prompts"][prompt_name]

            prompt_path = self.prompts_dir / prompt_info["path"]

            if not prompt_path.exists():
                raise PromptNotFoundError(f"Prompt file not found: {prompt_path}")

            # Load template
            content = prompt_path.read_text(encoding="utf-8")

            # Parse metadata and content
            metadata, template_content, raw_metadata = self._parse_prompt_file(
                content, prompt_name
            )

            # Create template
            template = PromptTemplate(
                template_content=template_content,
                metadata=metadata,
                template_dir=self.prompts_dir,
            )

            # Store raw metadata for fragment orchestration
            template._raw_metadata = raw_metadata
            template._fragment_orchestration = raw_metadata.get(
                "fragment_orchestration"
            )

            self._template_cache[cache_key] = template

        return self._template_cache[cache_key]

    def _parse_prompt_file(
        self, content: str, prompt_name: str
    ) -> tuple[TemplateMetadata, str, Dict[str, Any]]:
        """Parse prompt file with frontmatter"""
        raw_metadata = {}

        if content.startswith("---"):
            end_pos = content.find("---", 3)
            if end_pos > 0:
                frontmatter = content[3:end_pos].strip()
                template_content = content[end_pos + 3 :].strip()

                try:
                    raw_metadata = yaml.safe_load(frontmatter)
                    metadata = TemplateMetadata(
                        name=raw_metadata.get("name", prompt_name),
                        version=raw_metadata.get("version", "1.0"),
                        description=raw_metadata.get("description", ""),
                        required_variables=raw_metadata.get("required_variables", []),
                        optional_variables=raw_metadata.get("optional_variables", []),
                        model_compatibility=raw_metadata.get("model_compatibility", []),
                        max_tokens=raw_metadata.get("max_tokens"),
                        temperature_range=tuple(
                            raw_metadata.get("temperature_range", [0.0, 1.0])
                        ),
                        tags=raw_metadata.get("tags", []),
                    )
                    return metadata, template_content, raw_metadata

                except yaml.YAMLError as e:
                    logger.warning(f"Invalid YAML frontmatter in {prompt_name}: {e}")

        # Fallback metadata
        metadata = TemplateMetadata(
            name=prompt_name, version="1.0", description="", required_variables=[]
        )
        return metadata, content, raw_metadata

    def _sort_by_priority(self, prompt_names: List[str], prompt_type: str) -> List[str]:
        """Sort prompts by priority"""
        registry_key = f"{prompt_type}_prompts"
        registry = self.prompt_registry.get(registry_key, {})

        def get_priority(name: str) -> int:
            return registry.get(name, {}).get("priority", 50)

        return sorted(prompt_names, key=get_priority, reverse=True)

    def _merge_prompt_parts(self, parts: List[str], strategy: str) -> str:
        """Merge prompt parts using specified strategy"""
        if not parts:
            return ""

        if strategy == "sequential":
            return "\n\n---\n\n".join(parts)
        elif strategy == "parallel":
            # For parallel, we might want different formatting
            return "\n\n".join(parts)
        elif strategy == "hierarchical":
            # Hierarchical could have different indentation levels
            formatted_parts = []
            for i, part in enumerate(parts):
                if i == 0:
                    formatted_parts.append(part)
                else:
                    # Indent subsequent parts
                    indented = "\n".join(f"  {line}" for line in part.split("\n"))
                    formatted_parts.append(indented)
            return "\n\n".join(formatted_parts)
        else:
            logger.warning(f"Unknown merge strategy: {strategy}, using sequential")
            return "\n\n---\n\n".join(parts)

    def _create_composition_metadata(
        self,
        rule: CompositionRule,
        context: PromptContext,
        system_versions: Dict[str, str],
        user_versions: Dict[str, str],
    ) -> Dict[str, Any]:
        """Create metadata for composed prompt"""
        return {
            "composition_rule": rule.name,
            "composition_version": getattr(rule, "version", ""),
            "system_prompts": rule.system_prompts,
            "user_prompts": rule.user_prompts,
            "system_prompt_versions": system_versions,
            "user_prompt_versions": user_versions,
            "context_type": context.context_type.value,
            "merge_strategy": rule.merge_strategy,
            "composed_at": datetime.now(UTC).isoformat(),
            "total_system_prompts": len(rule.system_prompts),
            "total_user_prompts": len(rule.user_prompts),
        }

    def _load_composition_rules(self) -> Dict[str, CompositionRule]:
        """Load composition rules from config"""
        rules_file = self.config_dir / "composition_rules.yaml"

        if not rules_file.exists():
            logger.warning(f"Composition rules file not found: {rules_file}")
            return {}

        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            rules = {}
            for name, rule_data in config.get("compositions", {}).items():
                rules[name] = CompositionRule(
                    name=name,
                    description=rule_data.get("description", ""),
                    system_prompts=rule_data.get("system_prompts", []),
                    user_prompts=rule_data.get("user_prompts", []),
                    merge_strategy=rule_data.get("merge_strategy", "sequential"),
                    priority_order=rule_data.get("priority_order"),
                    version=rule_data.get("version", ""),
                )

            logger.info(f"Loaded {len(rules)} composition rules")
            return rules

        except Exception as e:
            logger.error(f"Failed to load composition rules: {e}")
            return {}

    def _load_prompt_registry(self) -> Dict[str, Any]:
        """Load prompt registry from config"""
        registry_file = self.config_dir / "prompt_registry.yaml"

        if not registry_file.exists():
            logger.warning(f"Prompt registry file not found: {registry_file}")
            return {}

        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = yaml.safe_load(f) or {}

            # Some registry files may nest content under a top-level 'registry' key
            if isinstance(registry, dict) and "registry" in registry:
                registry = registry["registry"] or {}

            if not isinstance(registry, dict):
                logger.error(
                    "Prompt registry file has invalid format (expected mapping)"
                )
                return {}

            system_count = len(registry.get("system_prompts", {}) or {})
            user_count = len(registry.get("user_prompts", {}) or {})

            logger.info(
                f"Loaded prompt registry with {system_count} system prompts, {user_count} user prompts"
            )
            return registry

        except Exception as e:
            logger.error(f"Failed to load prompt registry: {e}")
            return {}

    def list_compositions(self) -> List[Dict[str, Any]]:
        """List all available compositions"""
        return [
            {
                "name": rule.name,
                "description": rule.description,
                "system_prompts": rule.system_prompts,
                "user_prompts": rule.user_prompts,
                "merge_strategy": rule.merge_strategy,
            }
            for rule in self.composition_rules.values()
        ]

    def validate_composition(self, composition_name: str) -> Dict[str, Any]:
        """Validate that a composition can be executed"""
        if composition_name not in self.composition_rules:
            return {"valid": False, "error": f"Unknown composition: {composition_name}"}

        rule = self.composition_rules[composition_name]
        issues = []

        # Check system prompts exist
        for prompt_obj in rule.system_prompts:
            prompt_name = prompt_obj["name"]
            if prompt_name not in self.prompt_registry.get("system_prompts", {}):
                issues.append(f"System prompt not found: {prompt_name}")

        # Check user prompts exist (these are strings)
        for prompt_name in rule.user_prompts:
            if prompt_name not in self.prompt_registry.get("user_prompts", {}):
                issues.append(f"User prompt not found: {prompt_name}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_prompts": len(rule.system_prompts) + len(rule.user_prompts),
        }

    def clear_cache(self):
        """Clear template cache"""
        self._template_cache.clear()
        if self.fragment_manager:
            self.fragment_manager.clear_cache()
        logger.info("Template cache cleared")

    def reload_config(self):
        """Reload configuration files"""
        self.composition_rules = self._load_composition_rules()
        self.prompt_registry = self._load_prompt_registry()
        self.clear_cache()
        logger.info("Configuration reloaded")
