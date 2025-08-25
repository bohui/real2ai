"""Generic context matcher for fragment applicability.

Supports:
- Wildcard "*" (matches any value)
- List any-match (["purchase", "option"]) with case-insensitive comparison
- Scalar equality with case-insensitive comparison for strings

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

    def filter_fragments(self, fragments: List[Any], runtime_context: Dict[str, Any]) -> List[Any]:
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

    def _matches_context(self, fragment_context: Dict[str, Any], runtime_context: Dict[str, Any]) -> bool:
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

"""Generic context matching system for fragment selection"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ContextMatcher:
    """Generic context matching with wildcard and list support"""

    def matches_context(self, fragment_context: Dict[str, Any], runtime_context: Dict[str, Any]) -> bool:
        """
        Check if fragment context matches runtime context
        
        Args:
            fragment_context: Context requirements from fragment metadata
            runtime_context: Runtime context values
            
        Returns:
            True if fragment should be included, False otherwise
        """
        if not fragment_context:
            return True

        for key, required in fragment_context.items():
            # Wildcard matches anything
            if required == "*":
                continue

            actual = runtime_context.get(key)
            if actual is None:
                return False

            # Normalize strings for case-insensitive comparison
            def norm(v):
                return v.lower() if isinstance(v, str) else v

            if isinstance(required, list):
                if norm(actual) not in [norm(x) for x in required]:
                    return False
            else:
                if norm(actual) != norm(required):
                    return False

        return True

    def filter_fragments(
        self, 
        fragments: List[Dict[str, Any]], 
        runtime_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter fragments based on context matching
        
        Args:
            fragments: List of fragments with metadata
            runtime_context: Runtime context values
            
        Returns:
            List of matching fragments
        """
        matching_fragments = []
        
        for fragment in fragments:
            fragment_context = fragment.get('metadata', {}).get('context', {})
            
            if self.matches_context(fragment_context, runtime_context):
                matching_fragments.append(fragment)
                logger.debug(
                    f"✅ Fragment {fragment.get('name', 'unknown')} MATCHES: "
                    f"fragment_context={fragment_context}, runtime_context={runtime_context}"
                )
            else:
                # Log specific reason for non-match
                mismatch_reason = self._get_mismatch_reason(fragment_context, runtime_context)
                logger.debug(
                    f"❌ Fragment {fragment.get('name', 'unknown')} NO MATCH: {mismatch_reason} "
                    f"(fragment_context={fragment_context}, runtime_context={runtime_context})"
                )
        
        return matching_fragments

    def _get_mismatch_reason(self, fragment_context: Dict[str, Any], runtime_context: Dict[str, Any]) -> str:
        """Get specific reason why fragment context doesn't match runtime context"""
        if not fragment_context:
            return "empty fragment context should match all"
        
        for key, required in fragment_context.items():
            if required == "*":
                continue
                
            actual = runtime_context.get(key)
            if actual is None:
                return f"missing runtime key '{key}'"
                
            # Normalize for comparison
            def norm(v):
                return v.lower() if isinstance(v, str) else v
                
            if isinstance(required, list):
                if norm(actual) not in [norm(x) for x in required]:
                    return f"'{key}': '{actual}' not in required list {required}"
            else:
                if norm(actual) != norm(required):
                    return f"'{key}': '{actual}' != '{required}'"
        
        return "unknown mismatch"