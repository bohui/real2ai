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
        # Plain formatter that still tries to show extras in a best-effort way
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )

    # Target loggers: root, app namespace, uvicorn, and celery loggers if present
    target_logger_names: Iterable[str] = (
        "",  # root
        "app",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "celery",
        "celery.app.trace",
        "celery.worker",
    )

    for logger_name in target_logger_names:
        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
        logger.setLevel(level)
        _set_formatter_on_handlers(logger, formatter)
        # Ensure logs bubble up unless explicitly handled
        if logger_name.startswith("app") or logger_name.startswith("celery"):
            logger.propagate = True
