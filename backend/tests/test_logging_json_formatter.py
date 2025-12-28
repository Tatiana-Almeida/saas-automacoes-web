import json
import logging

from apps.core.logging_utils import JSONFormatter


def test_json_formatter_outputs_valid_json():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    out = formatter.format(record)
    data = json.loads(out)
    assert data["level"] == "INFO"
    assert data["logger"] == "test"
    assert data["message"] == "hello world"
    assert "ts" in data
