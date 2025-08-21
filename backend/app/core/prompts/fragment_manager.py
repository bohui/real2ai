"""Fragment-based prompt composition system"""

import logging
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

from .context import PromptContext
from .context_matcher import ContextMatcher

logger = logging.getLogger(__name__)


@dataclass
class Fragment:
    """Individual prompt fragment with folder-derived grouping"""

    name: str
    path: Path
    content: str
    metadata: Dict[str, Any]
    group: str
    priority: int = 50

    @property
    def context(self) -> Dict[str, Any]:
        return self.metadata.get("context", {})


class FragmentManager:
    """Folder-structure-driven prompt fragment manager (legacy orchestrator removed)"""

    def __init__(self, fragments_dir: Path):
        self.fragments_dir = Path(fragments_dir)

        # Caches
        self._fragment_cache: Dict[str, Fragment] = {}
        self._groups_cache: Dict[str, List[Fragment]] = {}

        # Generic context matcher
        self.context_matcher = ContextMatcher()

        logger.info(
            f"FragmentManager (folder-driven) initialized with fragments from {fragments_dir}"
        )

    def get_available_groups(self) -> List[str]:
        """Get all available fragment groups from folder structure"""
        groups: List[str] = []
        if not self.fragments_dir.exists():
            logger.warning(f"Fragments directory does not exist: {self.fragments_dir}")
            return groups
        for item in self.fragments_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                groups.append(item.name)
        return sorted(groups)

    def load_fragments_for_group(self, group_name: str) -> List[Fragment]:
        """Load all fragments for a specific group"""
        if group_name in self._groups_cache:
            return self._groups_cache[group_name]

        group_dir = self.fragments_dir / group_name
        if not group_dir.exists():
            logger.warning(f"Group directory does not exist: {group_dir}")
            return []

        fragments: List[Fragment] = []
        for fragment_file in group_dir.rglob("*.md"):
            try:
                fragment = self._load_fragment_from_path(fragment_file, group_name)
                if fragment:
                    fragments.append(fragment)
            except Exception as e:
                logger.error(f"Failed to load fragment {fragment_file}: {e}")

        fragments.sort(key=lambda f: f.priority, reverse=True)
        self._groups_cache[group_name] = fragments
        return fragments

    def compose_fragments(
        self,
        runtime_context: Dict[str, Any],
        requested_groups: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Compose fragments into group variables based on runtime context."""
        if requested_groups is None:
            requested_groups = self.get_available_groups()

        group_variables: Dict[str, str] = {}
        for group_name in requested_groups:
            all_fragments = self.load_fragments_for_group(group_name)

            fragment_dicts = [
                {
                    "name": f.name,
                    "metadata": f.metadata,
                    "content": f.content,
                    "priority": f.priority,
                }
                for f in all_fragments
            ]

            matching_fragments = self.context_matcher.filter_fragments(
                fragment_dicts, runtime_context
            )

            logger.debug(f"Group '{group_name}' fragment matching decisions:")
            for fragment in all_fragments:
                fragment_context = fragment.metadata.get("context", {})
                matches = self.context_matcher.matches_context(
                    fragment_context, runtime_context
                )
                logger.debug(
                    f"  Fragment '{fragment.name}': {'MATCH' if matches else 'NO_MATCH'} "
                    f"(context: {fragment_context}, priority: {fragment.priority})"
                )

            matching_fragments.sort(key=lambda f: f["priority"], reverse=True)

            if matching_fragments:
                content_parts = [f["content"] for f in matching_fragments]
                group_variables[group_name] = "\n\n".join(content_parts)
                fragment_names = [f["name"] for f in matching_fragments]
                logger.info(
                    f"Group '{group_name}': {len(matching_fragments)} matching fragments "
                    f"(out of {len(all_fragments)} total) - included: {fragment_names}"
                )
            else:
                group_variables[group_name] = ""
                logger.info(f"Group '{group_name}': no matching fragments")

        return group_variables

    # Removed legacy resolve_fragments and compose_with_fragments in favor of folder-driven composition

    def compose_with_folder_fragments(
        self, base_template: str, context: PromptContext
    ) -> str:
        """Compose final prompt using folder-driven fragment grouping with generic context matching

        This is the new implementation following the delta plan that uses:
        - Folder structure as the single source of truth for template variables
        - Generic context matching with wildcards and lists
        - No hardcoded aliases or mappings

        Args:
            base_template: Base prompt template content
            context: Context for fragment resolution

        Returns:
            Composed prompt with fragments integrated
        """
        # Discover all fragments from folder structure
        all_fragments = []
        for fragment_file in self.fragments_dir.rglob("*.md"):
            try:
                relative_path = fragment_file.relative_to(self.fragments_dir)
                fragment = self._load_fragment(str(relative_path))
                if fragment:
                    all_fragments.append(fragment)
            except Exception as e:
                logger.warning(f"Could not load fragment {fragment_file}: {e}")

        # Convert context to dictionary for generic matcher
        runtime_context = context.to_dict()

        # Filter fragments using generic context matcher (dict-based API)
        fragment_dicts = [
            {
                "name": f.name,
                "metadata": f.metadata,
                "content": f.content,
                "priority": getattr(f, "priority", 50),
                "path": str(f.path),
            }
            for f in all_fragments
        ]
        matching_fragments = self.context_matcher.filter_fragments(
            fragment_dicts, runtime_context
        )

        # Group fragments by folder structure
        # - Provide variables for top-level folder (backward compatible)
        # - Also provide variables for the full directory path joined with underscores
        fragment_groups: Dict[str, List[str]] = {}
        for fragment in matching_fragments:
            try:
                full_path = Path(fragment.get("path", ""))
                relative_path = full_path.relative_to(self.fragments_dir)
                parts = list(relative_path.parts)
                dir_parts = parts[:-1] if len(parts) > 1 else []
                top_level = dir_parts[0] if dir_parts else "default"
                full_dir_key = "_".join(dir_parts) if dir_parts else "default"
            except Exception:
                top_level = "default"
                full_dir_key = "default"

            for key in {top_level, full_dir_key}:
                if key not in fragment_groups:
                    fragment_groups[key] = []
                # matching_fragments contains dicts (from context matcher), not Fragment objects
                fragment_groups[key].append(fragment["content"])

        # Prepare fragment variables for template rendering
        fragment_vars = {}
        for group_name, contents in fragment_groups.items():
            # Sort by priority if available, otherwise use original order
            # Note: Priority sorting is handled in filter_fragments
            fragment_vars[group_name] = "\n\n".join(contents)

        # Auto-discover all available directory groups (recursive) to provide empty defaults
        available_groups = set()
        for directory in self.fragments_dir.rglob("*"):
            if directory.is_dir() and not directory.name.startswith("."):
                # Add top-level name
                try:
                    relative = directory.relative_to(self.fragments_dir)
                    parts = list(relative.parts)
                    if parts:
                        available_groups.add(parts[0])
                        available_groups.add("_".join(parts))
                except Exception:
                    continue

        # Provide empty strings for all discovered groups not present
        for group_name in available_groups:
            if group_name and group_name not in fragment_vars:
                fragment_vars[group_name] = ""

        # Render template with fragment content
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

        # Add custom filters
        self._register_custom_filters(env)

        template = env.get_template("")

        # Merge context variables with fragment variables
        render_vars = runtime_context.copy()
        render_vars.update(fragment_vars)

        # Add helper functions
        from datetime import datetime, UTC

        render_vars["now"] = datetime.now(UTC)

        logger.info(
            f"Composed template with {len(fragment_groups)} fragment groups: {list(fragment_groups.keys())}"
        )

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

    def _load_fragment_from_path(
        self, fragment_path: Path, group_name: str
    ) -> Optional[Fragment]:
        """Load individual fragment from an absolute path and group name."""
        cache_key = str(fragment_path)
        if cache_key in self._fragment_cache:
            return self._fragment_cache[cache_key]

        try:
            content = fragment_path.read_text(encoding="utf-8")

            metadata: Dict[str, Any] = {}
            fragment_content = content
            if content.startswith("---"):
                end_pos = content.find("---", 3)
                if end_pos > 0:
                    frontmatter = content[3:end_pos].strip()
                    fragment_content = content[end_pos + 3 :].strip()
                    try:
                        metadata = yaml.safe_load(frontmatter) or {}
                    except yaml.YAMLError as e:
                        logger.warning(
                            f"Invalid YAML frontmatter in {fragment_path}: {e}"
                        )

            relative_path = fragment_path.relative_to(self.fragments_dir)
            fragment_name = metadata.get("name", str(relative_path))

            fragment = Fragment(
                name=fragment_name,
                path=fragment_path,
                content=fragment_content,
                metadata=metadata,
                group=group_name,
                priority=int(metadata.get("priority", 50)),
            )

            self._fragment_cache[cache_key] = fragment
            return fragment
        except Exception as e:
            logger.error(f"Failed to load fragment {fragment_path}: {e}")
            return None

    def _load_fragment(self, fragment_path: str) -> Optional[Fragment]:
        """Load individual fragment from a path relative to fragments_dir."""
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

            # Derive group from the first directory segment of the relative path
            try:
                first_segment = str(clean_path).split("/", 1)[0]
            except Exception:
                first_segment = "default"

            fragment = Fragment(
                name=fragment_name,
                path=full_path,
                content=fragment_content,
                metadata=metadata,
                group=first_segment or "default",
                priority=int(metadata.get("priority", 50)),
            )

            self._fragment_cache[fragment_path] = fragment
            return fragment

        except Exception as e:
            logger.error(f"Failed to load fragment {fragment_path}: {e}")
            return None

    def validate_group_structure(self) -> Dict[str, Any]:
        """Validate folder structure and fragment metadata"""
        issues: List[str] = []
        groups = self.get_available_groups()

        import re

        valid_name_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
        for group in groups:
            if not valid_name_pattern.match(group):
                issues.append(
                    f"Invalid group name: '{group}' (must start with letter, contain only letters, digits, underscore)"
                )

        fragment_count = 0
        deprecated_fields_found: List[str] = []
        for group in groups:
            fragments = self.load_fragments_for_group(group)
            fragment_count += len(fragments)
            for fragment in fragments:
                if "group" in fragment.metadata:
                    deprecated_fields_found.append(
                        f"{fragment.name}: 'group' field deprecated"
                    )
                if "domain" in fragment.metadata:
                    deprecated_fields_found.append(
                        f"{fragment.name}: 'domain' field deprecated"
                    )

                ctx = fragment.context
                if ctx:
                    for key, value in ctx.items():
                        if not isinstance(key, str):
                            issues.append(
                                f"{fragment.name}: context key must be string, got {type(key)}"
                            )
                        if not (
                            isinstance(value, str)
                            or isinstance(value, list)
                            or value == "*"
                        ):
                            issues.append(
                                f"{fragment.name}: context value must be string, list, or '*', got {type(value)}"
                            )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "deprecated_warnings": deprecated_fields_found,
            "total_groups": len(groups),
            "total_fragments": fragment_count,
            "groups": groups,
        }

    def clear_cache(self):
        """Clear fragment cache"""
        self._fragment_cache.clear()
        self._groups_cache.clear()
        logger.info("Fragment cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """Get fragment manager metrics"""
        groups = self.get_available_groups()
        total_fragments = sum(
            len(self.load_fragments_for_group(group)) for group in groups
        )
        return {
            "total_groups": len(groups),
            "total_fragments": total_fragments,
            "cached_fragments": len(self._fragment_cache),
            "cached_groups": len(self._groups_cache),
            "available_groups": groups,
        }
