import json
import logging

from logging_utils import JsonLogFormatter, configure_json_logging


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonLogFormatter().format(record))


def _make_record(msg: str = "hello", **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="worker_app.runner", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formats_basic_fields_with_no_structured_extras():
    payload = _format(_make_record("plain startup message"))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "worker_app.runner"
    assert payload["message"] == "plain startup message"
    assert "timestamp" in payload
    # No structured fields supplied -> none of them appear at all, rather than being
    # padded in as nulls (a startup log genuinely has no analysis_id).
    for field in ("analysis_id", "repository", "issue_number", "node", "tool", "status"):
        assert field not in payload

def test_includes_only_the_structured_fields_actually_supplied():
    payload = _format(_make_record(
        "job_intake failed", analysis_id="a1", repository="acme/widgets",
        node="job_intake", status="failed",
    ))

    assert payload["analysis_id"] == "a1"
    assert payload["repository"] == "acme/widgets"
    assert payload["node"] == "job_intake"
    assert payload["status"] == "failed"
    # issue_number/tool/request_id weren't supplied -> still absent.
    assert "issue_number" not in payload
    assert "tool" not in payload
    assert "request_id" not in payload

def test_exc_info_populates_error_type_and_exc_text():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="worker_app.nodes.request_validator", level=logging.ERROR, pathname=__file__,
            lineno=1, msg="Repository validation failed", args=(), exc_info=sys.exc_info(),
        )
    payload = _format(record)

    assert payload["error_type"] == "ValueError"
    assert "boom" in payload["exc_text"]

def test_explicit_error_type_extra_is_not_overridden_by_exc_info():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="worker_app.runner", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="cleanup_workspace failed", args=(), exc_info=sys.exc_info(),
        )
        record.error_type = "CustomToolError"
    payload = _format(record)

    assert payload["error_type"] == "CustomToolError"

def test_configure_json_logging_installs_the_formatter_on_the_root_logger(capsys):
    configure_json_logging()
    logging.getLogger("test_logging_utils").info("hello structured world", extra={"analysis_id": "a2"})

    captured = capsys.readouterr()
    payload = json.loads(captured.err.strip().splitlines()[-1])

    assert payload["message"] == "hello structured world"
    assert payload["analysis_id"] == "a2"
