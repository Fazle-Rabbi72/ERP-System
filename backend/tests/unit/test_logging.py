import json
import logging
from collections.abc import Iterator

import pytest
import structlog

from app.core.logging import REDACTED, configure_logging, get_logger, redact_sensitive

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    structlog.reset_defaults()


def test_redacts_sensitive_keys_recursively() -> None:
    event = {
        "event": "login",
        "password": "hunter2",
        "Authorization": "Bearer abc",
        "payload": {"refresh_token": "r", "name": "x", "items": [{"api_key": "k", "n": 1}]},
    }
    result = redact_sensitive(None, "info", event)
    assert result["password"] == REDACTED
    assert result["Authorization"] == REDACTED
    assert result["payload"] == {
        "refresh_token": REDACTED,
        "name": "x",
        "items": [{"api_key": REDACTED, "n": 1}],
    }


def test_json_output_never_contains_secret(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_logs=True)
    get_logger("unit.test").info("hello", password="hunter2", user="amina")
    output = capsys.readouterr().out
    assert "hunter2" not in output
    record = json.loads(output.strip().splitlines()[-1])
    assert record["event"] == "hello"
    assert record["user"] == "amina"
    assert record["password"] == REDACTED
    assert record["level"] == "info"


def test_stdlib_logs_are_redacted_too(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_logs=True)
    logging.getLogger("uvicorn.error").warning("stdlib message")
    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert record["event"] == "stdlib message"


def test_log_level_is_respected(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("ERROR", json_logs=True)
    get_logger("unit.test").info("quiet")
    assert capsys.readouterr().out == ""
