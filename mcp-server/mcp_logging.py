import json
import logging

# mcp-server has no dependency on backend/shared (see mcp_metrics.py's own header comment
# for the full reasoning) -- so this is a local copy of backend/shared/logging_utils.py,
# not an import of it. Named mcp_logging.py, not logging_utils.py, for the exact same
# reason mcp_metrics.py isn't named metrics.py: both backend/shared and mcp-server are
# editable-installed as flat py-modules into the same shared .venv, and a bare top-level
# `logging_utils.py` in both would collide exactly like Task 18's app/app collision.

STRUCTURED_FIELDS = (
    "analysis_id", "request_id", "repository", "issue_number",
    "node", "tool", "duration", "retry_count", "error_type", "status",
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload.setdefault("error_type", record.exc_info[0].__name__)
            payload["exc_text"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_json_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
