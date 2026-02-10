"""Tests for logging configuration."""

import json
import logging

from src.logging_config import JSONFormatter, setup_logging


class TestJSONFormatter:
    def test_format_basic(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed


class TestSetupLogging:
    def test_setup_text_format(self):
        setup_logging(level="DEBUG", json_format=False)
        logger = logging.getLogger()
        assert logger.level == logging.DEBUG

    def test_setup_json_format(self):
        setup_logging(level="INFO", json_format=True)
        logger = logging.getLogger()
        assert logger.level == logging.INFO
        # Check that handler has JSONFormatter
        assert any(
            isinstance(h.formatter, JSONFormatter) for h in logger.handlers
        )
