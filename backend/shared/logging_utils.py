import json
import logging

# design.md §12's structured-log field list. A field is only written to the JSON payload
# when the log call actually supplies it (via `extra={...}`) -- routine/info logs that
# have no analysis_id (e.g. a startup message) simply omit it rather than padding every
# line with nulls.
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
    # force=True: a repeated call (e.g. FastAPI's create_app() factory, invoked once for
    # real startup and again per-test via TestClient(create_app())) must actually replace
    # any handler installed by an earlier call/import, not silently no-op the way bare
    # logging.basicConfig() does once the root logger already has a handler.
    logging.basicConfig(level=level, handlers=[handler], force=True)
