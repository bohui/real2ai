import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Iterable


# Attributes present on every LogRecord by default.
_STANDARD_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "lineno",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


class JSONExtraFormatter(logging.Formatter):
    """Formatter that emits JSON and includes any extra LogRecord attributes.

    This ensures that `logger.info("msg", extra={...})` context is preserved.
    """

    def __init__(self, *, include_time: bool = True, time_key: str = "timestamp"):
        super().__init__()
        self.include_time = include_time
        self.time_key = time_key

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if self.include_time:
            # ISO8601 with timezone naive UTC-style timestamp
            log_obj[self.time_key] = (
                datetime.utcfromtimestamp(record.created).isoformat() + "Z"
            )

        # Collect extra attributes added via `extra={}`
        extras: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and key not in ("message",):
                extras[key] = value

        if extras:
            log_obj["extra"] = extras

        # Exception / stack information
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_obj["stack_info"] = self.formatStack(record.stack_info)

        try:
            return json.dumps(log_obj, ensure_ascii=False, default=str)
        except Exception:
            # Fallback to basic formatting if JSON serialization fails
            return f"{record.levelname} {record.name}: {record.getMessage()} extras={extras}"


class ConsoleExtraFormatter(logging.Formatter):
    """Human-friendly console formatter that preserves newlines in messages and shows extras.

    - Keeps `record.getMessage()` as-is (so embedded \n render as real newlines)
    - Appends extras as JSON on a new line when provided
    - Includes exception/stack info on separate lines
    """

    def __init__(self, *, include_time: bool = True):
        super().__init__()
        self.include_time = include_time

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp in UTC similar to JSON formatter for consistency
        if self.include_time:
            ts = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
            header = f"{ts} {record.levelname} {record.name}: "
        else:
            header = f"{record.levelname} {record.name}: "

        message = record.getMessage()
        is_exception = bool(record.exc_info or record.stack_info)
        # For non-exception logs, collapse newlines so each log is single-line
        if not is_exception and ("\n" in message or "\r" in message):
            message = (
                message.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
            )

        # Collect extras similar to JSON formatter
        extras: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and key not in ("message",):
                extras[key] = value

        # Start with single-line body (message plus inline extras)
        first_line = header + message
        if extras:
            try:
                extras_json = json.dumps(extras, ensure_ascii=False, default=str)
            except Exception:
                extras_json = str(extras)
            first_line = f"{first_line} {extras_json}"

        # Append multi-line exception/stack only when present
        if is_exception:
            extra_lines = []
            if record.exc_info:
                extra_lines.append(self.formatException(record.exc_info))
            if record.stack_info:
                extra_lines.append(self.formatStack(record.stack_info))
            return "\n".join([first_line] + extra_lines)

        return first_line


def _set_formatter_on_handlers(
    logger: logging.Logger, formatter: logging.Formatter
) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return
    for handler in logger.handlers:
        handler.setFormatter(formatter)


def _clear_handlers(logger: logging.Logger) -> None:
    """Remove all handlers from a logger."""
    for h in list(logger.handlers):
        logger.removeHandler(h)


def configure_logging(level: int | str | None = None, *, use_json: bool = True) -> None:
    """Configure logging so that `extra` dicts are visible in output.

    - If `use_json` is True, installs `JSONExtraFormatter` on root and common uvicorn loggers.
    - If `level` is provided, sets the level on root and key app/uvicorn loggers.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    if level is None:
        level = logging.INFO

    formatter: logging.Formatter
    if use_json:
        formatter = JSONExtraFormatter()
    else:
        formatter = ConsoleExtraFormatter()

    # Configure root logger with a single stdout handler
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    _set_formatter_on_handlers(root_logger, formatter)

    # Ensure app, uvicorn, celery loggers do not have their own handlers to avoid duplicates
    child_logger_names: Iterable[str] = (
        "app",
        "uvicorn",
        "uvicorn.access",
        "celery",
        "celery.app.trace",
        "celery.worker",
        "app.core.prompts",
    )
    for name in child_logger_names:
        lgr = logging.getLogger(name)
        lgr.setLevel(level)
        _clear_handlers(lgr)
        lgr.propagate = True
