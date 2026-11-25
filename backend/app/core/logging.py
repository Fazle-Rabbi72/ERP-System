"""Structured logging with automatic redaction of sensitive fields."""

import logging
import sys

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

REDACTED = "***REDACTED***"
_SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "otp",
)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS)


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def redact_sensitive(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """structlog processor: mask values whose key looks like a credential."""
    for key in list(event_dict):
        if _is_sensitive(key):
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _redact(event_dict[key])
    return event_dict


def configure_logging(level: str, *, json_logs: bool) -> None:
    """Route structlog and stdlib (uvicorn, sqlalchemy) logs through one pipeline."""
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_sensitive,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    final_processors: list[Processor] = [structlog.stdlib.ProcessorFormatter.remove_processors_meta]
    if json_logs:
        final_processors += [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        final_processors.append(structlog.dev.ConsoleRenderer())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=final_processors,
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        framework_logger = logging.getLogger(name)
        framework_logger.handlers.clear()
        framework_logger.propagate = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)
