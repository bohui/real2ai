"""Output format enums."""

from enum import Enum


class OutputFormat(str, Enum):
    """Output format types"""

    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
