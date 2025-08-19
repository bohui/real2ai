"""Fragment-based prompt composition system"""

import logging
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

from .template import PromptTemplate, TemplateMetadata
from .context import PromptContext
from .exceptions import PromptCompositionError

logger = logging.getLogger(__name__)


@dataclass
class FragmentRule:
    """Rule for including fragments based on conditions"""

    condition: Optional[str] = None
    composition: str = "replace"  # replace, union, intersection
    mappings: Dict[str, List[str]] = None
    always_include: List[str] = None
    priority: int = 50

    def __post_init__(self):
        if self.mappings is None:
            self.mappings = {}
        if self.always_include is None:
            self.always_include = []


@dataclass
class Fragment:
    """Individual prompt fragment"""

    name: str
    path: Path
    content: str
    metadata: Dict[str, Any]
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class FragmentManager:
    """Advanced fragment-based prompt composition"""

    def __init__(self, fragments_dir: Path, config_dir: Path):
        self.fragments_dir = Path(fragments_dir)
        self.config_dir = Path(config_dir)

        # Fragment cache
        self._fragment_cache: Dict[str, Fragment] = {}
        self._orchestration_configs: Dict[str, Dict[str, Any]] = {}

        logger.info(f"FragmentManager initialized with fragments from {fragments_dir}")

    def resolve_fragments(
        self, orchestration_id: str, context: PromptContext
    ) -> List[Fragment]:
        """Resolve fragments based on orchestration rules and context

        Args:
            orchestration_id: ID of orchestration configuration
            context: Context containing variables for condition evaluation

        Returns:
            List of resolved fragments in priority order
        """
        config = self._load_orchestration_config(orchestration_id)
        resolved_fragments = []

        # Process each fragment rule
        for rule_name, rule_config in config.get("fragments", {}).items():
            rule = FragmentRule(
                condition=rule_config.get("condition"),
                composition=rule_config.get("composition", "replace"),
                mappings=rule_config.get("mappings", {}),
                always_include=rule_config.get("always_include", []),
                priority=rule_config.get("priority", 50),
            )

            # Always include fragments
            if rule.always_include:
                for fragment_path in rule.always_include:
                    fragment = self._load_fragment(fragment_path)
                    if fragment:
                        resolved_fragments.append(fragment)

            # Conditional fragments (only if condition exists)
            if rule.condition and rule.mappings:
                condition_value = self._evaluate_condition(rule.condition, context)
                if condition_value and condition_value in rule.mappings:
                    fragment_paths = rule.mappings[condition_value]

                    for fragment_path in fragment_paths:
                        fragment = self._load_fragment(fragment_path)
                        if fragment:
                            resolved_fragments.append(fragment)

        # Sort by priority and remove duplicates
        unique_fragments = {}
        for fragment in resolved_fragments:
            if fragment.name not in unique_fragments:
                unique_fragments[fragment.name] = fragment

        return list(unique_fragments.values())

    def compose_with_fragments(
        self, base_template: str, orchestration_id: str, context: PromptContext
    ) -> str:
        """Compose final prompt with base template and resolved fragments

        Args:
            base_template: Base prompt template content
            orchestration_id: Orchestration configuration ID
            context: Context for fragment resolution

        Returns:
            Composed prompt with fragments integrated
        """
        fragments = self.resolve_fragments(orchestration_id, context)

        # Build fragment content by category
        fragment_content = {}
        for fragment in fragments:
            category = fragment.metadata.get("category", "default")
            if category not in fragment_content:
                fragment_content[category] = []
            fragment_content[category].append(fragment.content)

        # Prepare fragment variables for template rendering
        fragment_vars = {}
        for category, contents in fragment_content.items():
            fragment_vars[f"{category}_fragments"] = "\n\n".join(contents)

        # Provide default empty values for expected fragment variables to prevent template errors
        expected_fragments = [
            "state_legal_requirements_fragments",
            "consumer_protection_fragments",
            "contract_type_specific_fragments",
            "experience_level_guidance_fragments",
            "analysis_depth_fragments",
            "state_specific_fragments",
            "contract_type_fragments",
            "quality_requirements_fragments",
            "user_experience_fragments",
            "financial_risk_fragments",
            "experience_level_fragments",
            "state_specific_analysis_fragments",
            "state_compliance_fragments",
        ]

        for fragment_var in expected_fragments:
            if fragment_var not in fragment_vars:
                fragment_vars[fragment_var] = ""

        # Render base template with fragment content
        from jinja2 import Environment, BaseLoader, Undefined

        class StringLoader(BaseLoader):
            def get_source(self, environment, template):
                return base_template, None, lambda: True

        env = Environment(
            loader=StringLoader(),
            undefined=Undefined,  # Allow undefined variables to render as empty strings
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters (similar to PromptTemplate)
        self._register_custom_filters(env)

        template = env.get_template("")

        # Merge context variables with fragment variables
        render_vars = context.to_dict()
        render_vars.update(fragment_vars)

        # Add helper functions
        from datetime import datetime, UTC

        render_vars["now"] = datetime.now(UTC)

        return template.render(**render_vars)

    def _register_custom_filters(self, env):
        """Register custom filters for fragment composition"""
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

    def _load_orchestration_config(self, orchestration_id: str) -> Dict[str, Any]:
        """Load orchestration configuration"""
        if orchestration_id not in self._orchestration_configs:
            # Accept both raw IDs (e.g., "contract_analysis") and fully-suffixed IDs
            # (e.g., "contract_analysis_orchestrator"). Normalize to a single filename.
            filename = orchestration_id
            if not filename.endswith("_orchestrator"):
                filename = f"{filename}_orchestrator"
            config_file = self.config_dir / f"{filename}.yaml"

            if not config_file.exists():
                raise PromptCompositionError(
                    f"Orchestration config not found: {config_file}",
                    composition_name=orchestration_id,
                )

            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                self._orchestration_configs[orchestration_id] = config

            except Exception as e:
                raise PromptCompositionError(
                    f"Failed to load orchestration config: {e}",
                    composition_name=orchestration_id,
                )

        return self._orchestration_configs[orchestration_id]

    def _load_fragment(self, fragment_path: str) -> Optional[Fragment]:
        """Load individual fragment from file"""
        if fragment_path in self._fragment_cache:
            return self._fragment_cache[fragment_path]

        # Strip leading "fragments/" if present to avoid double path issues
        clean_path = fragment_path
        if fragment_path.startswith("fragments/"):
            clean_path = fragment_path[10:]  # Remove "fragments/" prefix
            logger.debug(
                f"Stripped 'fragments/' prefix: '{fragment_path}' -> '{clean_path}'"
            )

        full_path = self.fragments_dir / clean_path
        logger.debug(f"Resolving fragment path: '{fragment_path}' -> '{full_path}'")

        if not full_path.exists():
            logger.warning(f"Fragment not found: {full_path}")
            # Log additional context for debugging
            if not self.fragments_dir.exists():
                logger.error(
                    f"Fragments directory does not exist: {self.fragments_dir}"
                )
            elif not (self.fragments_dir / clean_path).parent.exists():
                logger.warning(
                    f"Fragment directory does not exist: {(self.fragments_dir / clean_path).parent}"
                )
            return None

        try:
            content = full_path.read_text(encoding="utf-8")

            # Parse frontmatter if present
            metadata = {}
            if content.startswith("---"):
                end_pos = content.find("---", 3)
                if end_pos > 0:
                    frontmatter = content[3:end_pos].strip()
                    fragment_content = content[end_pos + 3 :].strip()
                    try:
                        metadata = yaml.safe_load(frontmatter)
                    except yaml.YAMLError:
                        pass
                else:
                    fragment_content = content
            else:
                fragment_content = content

            # Use fragment_path as name if not provided in metadata
            fragment_name = metadata.get("name", fragment_path)

            fragment = Fragment(
                name=fragment_name,
                path=full_path,
                content=fragment_content,
                metadata=metadata,
                tags=metadata.get("tags", []),
            )

            self._fragment_cache[fragment_path] = fragment
            return fragment

        except Exception as e:
            logger.error(f"Failed to load fragment {fragment_path}: {e}")
            return None

    def _evaluate_condition(
        self, condition: Optional[str], context: PromptContext
    ) -> Optional[str]:
        """Evaluate condition against context variables"""
        variables = context.variables

        # Simple variable lookup
        if condition and condition in variables:
            return str(variables[condition])

        # Support for complex conditions (future enhancement)
        # Could support expressions like "australian_state && contract_type"

        return None

    def list_available_fragments(self) -> List[Dict[str, Any]]:
        """List all available fragments with metadata"""
        fragments = []

        for fragment_file in self.fragments_dir.rglob("*.md"):
            try:
                relative_path = fragment_file.relative_to(self.fragments_dir)
                fragment = self._load_fragment(str(relative_path))

                if fragment:
                    fragments.append(
                        {
                            "name": fragment.name,
                            "path": str(fragment.path),
                            "category": fragment.metadata.get(
                                "category", "uncategorized"
                            ),
                            "tags": fragment.tags or [],
                            "description": fragment.metadata.get("description", ""),
                        }
                    )

            except Exception as e:
                logger.warning(f"Could not process fragment {fragment_file}: {e}")

        return fragments

    def validate_orchestration(self, orchestration_id: str) -> Dict[str, Any]:
        """Validate orchestration configuration"""
        try:
            config = self._load_orchestration_config(orchestration_id)
            issues = []

            # Check base template exists
            base_template = config.get("base_template")
            if base_template:
                base_path = self.fragments_dir.parent / base_template
                if not base_path.exists():
                    issues.append(f"Base template not found: {base_template}")

            # Check all fragment references
            for rule_name, rule_config in config.get("fragments", {}).items():
                mappings = rule_config.get("mappings", {})
                always_include = rule_config.get("always_include", [])

                # Check always_include fragments
                for fragment_path in always_include:
                    if not (self.fragments_dir / fragment_path).exists():
                        issues.append(f"Fragment not found: {fragment_path}")

                # Check mapping fragments
                for condition_value, fragment_paths in mappings.items():
                    for fragment_path in fragment_paths:
                        if not (self.fragments_dir / fragment_path).exists():
                            issues.append(f"Fragment not found: {fragment_path}")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "fragment_count": len(config.get("fragments", {})),
            }

        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Configuration error: {str(e)}"],
                "fragment_count": 0,
            }

    def clear_cache(self):
        """Clear fragment cache"""
        self._fragment_cache.clear()
        self._orchestration_configs.clear()
        logger.info("Fragment cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """Get fragment manager metrics"""
        return {
            "cached_fragments": len(self._fragment_cache),
            "cached_orchestrations": len(self._orchestration_configs),
            "total_available_fragments": len(self.list_available_fragments()),
        }
