"""Context and output enums."""

from enum import Enum


class ContextType(Enum):
    """Context types"""

    USER_PROFILE = "user_profile"
    PROPERTY_CONTEXT = "property_context"
    MARKET_CONTEXT = "market_context"
    DOCUMENT_CONTEXT = "document_context"
    SESSION_CONTEXT = "session_context"


class OutputFormat(str, Enum):
    """Output format types"""

    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
