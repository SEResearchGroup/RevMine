"""
Structured JSON logging formatter for the Authentication service.
"""
import json
import logging
import traceback
from datetime import datetime, timezone

_RESERVED_FIELDS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname",
    "filename", "module", "exc_info", "exc_text", "stack_info",
    "lineno", "funcName", "created", "msecs", "relativeCreated",
    "thread", "threadName", "processName", "process", "taskName",
    "message", "asctime",
})


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record for Loki/Grafana ingestion."""

    def __init__(self, service: str = "authentication", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.levelno <= logging.DEBUG:
            obj["file"] = record.pathname
            obj["line"] = record.lineno
            obj["func"] = record.funcName

        for key, value in record.__dict__.items():
            if key not in _RESERVED_FIELDS:
                obj[key] = value

        if record.exc_info:
            obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(obj, default=str, ensure_ascii=False)
