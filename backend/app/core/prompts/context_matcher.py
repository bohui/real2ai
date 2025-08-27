"""Generic context matcher for fragment applicability.

Supports:
- Wildcard "*" (matches any value)
- List any-match (["purchase", "option"]) with case-insensitive comparison
- List intersection (fragment list intersects with runtime list)
- Scalar equality with case-insensitive comparison for strings

Enhanced to handle diagram_type filtering where fragment specifies a list of
applicable diagram types and runtime provides a list of actual diagram types.
Fragment is included if any diagram types intersect.

Logs match decisions to aid debugging.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ContextMatcher:
    """Evaluate whether a fragment applies to the current runtime context."""

    def __init__(self) -> None:
        pass

    def filter_fragments(
        self, fragments: List[Any], runtime_context: Dict[str, Any]
    ) -> List[Any]:
        """Return fragments whose metadata.context matches the runtime_context.

        Respects optional numeric 'priority' in fragment metadata (higher first).
        """
        matched: List[Any] = []
        for fragment in fragments:
            fragment_context = {}
            try:
                fragment_context = fragment.metadata.get("context", {}) or {}
            except Exception:
                fragment_context = {}

            if self._matches_context(fragment_context, runtime_context):
                matched.append(fragment)
            else:
                logger.debug(
                    "Fragment skipped due to context mismatch",
                    extra={
                        "fragment_path": str(getattr(fragment, "path", "")),
                        "fragment_context": fragment_context,
                        "runtime_context": runtime_context,
                    },
                )

        # Sort by metadata priority desc if available
        def get_priority(f: Any) -> int:
            try:
                return int(f.metadata.get("priority", 0))
            except Exception:
                return 0

        matched.sort(key=get_priority, reverse=True)
        return matched

    def _matches_context(
        self, fragment_context: Dict[str, Any], runtime_context: Dict[str, Any]
    ) -> bool:
        if not fragment_context:
            return True

        for key, required in fragment_context.items():
            # Wildcard matches anything
            if required == "*":
                continue

            actual = runtime_context.get(key)
            if actual is None:
                return False

            if isinstance(required, list):
                if not self._list_contains(required, actual):
                    return False
            else:
                if not self._equals(required, actual):
                    return False

        return True

    def _equals(self, a: Any, b: Any) -> bool:
        if isinstance(a, str) and isinstance(b, str):
            return a.lower() == b.lower()
        return a == b

    def _list_contains(self, items: List[Any], value: Any) -> bool:
        # Handle list intersection - if runtime value is a list, check if any items intersect
        if isinstance(value, list):
            return self._lists_intersect(items, value)

        # Original single value logic
        if isinstance(value, str):
            value_lower = value.lower()
            for item in items:
                if isinstance(item, str) and item.lower() == value_lower:
                    return True
                if item == value:
                    return True
            return False
        else:
            return value in items

    def _lists_intersect(
        self, fragment_list: List[Any], runtime_list: List[Any]
    ) -> bool:
        """Check if two lists have any common elements (case-insensitive for strings)"""
        for fragment_item in fragment_list:
            for runtime_item in runtime_list:
                if self._equals(fragment_item, runtime_item):
                    return True
        return False
