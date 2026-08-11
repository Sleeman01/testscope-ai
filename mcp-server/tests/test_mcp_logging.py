import json
import logging

from mcp_logging import JsonLogFormatter, configure_json_logging


def _format(record: logging.LogRecord) -> dict:
    return json.loads(JsonLogFormatter().format(record))


def _make_record(msg: str = "hello", **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="server", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formats_basic_fields_with_no_structured_extras():
    payload = _format(_make_record("startup"))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "server"
    assert payload["message"] == "startup"
    assert "analysis_id" not in payload

def test_includes_only_the_structured_fields_actually_supplied():
    payload = _format(_make_record("find_test_files failed", analysis_id="a1", tool="find_test_files"))

    assert payload["analysis_id"] == "a1"
    assert payload["tool"] == "find_test_files"
    assert "node" not in payload

def test_exc_info_populates_error_type_and_exc_text():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="server", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="clone failed", args=(), exc_info=sys.exc_info(),
        )
    payload = _format(record)

    assert payload["error_type"] == "ValueError"
    assert "boom" in payload["exc_text"]

def test_configure_json_logging_installs_the_formatter_on_the_root_logger(capsys):
    configure_json_logging()
    logging.getLogger("test_mcp_logging").info("hello", extra={"tool": "cleanup_workspace"})

    captured = capsys.readouterr()
    payload = json.loads(captured.err.strip().splitlines()[-1])

    assert payload["message"] == "hello"
    assert payload["tool"] == "cleanup_workspace"
