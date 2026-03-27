import pytest
from unittest.mock import patch, MagicMock
import configparser
import logging

from util.utilities import validate_config


def _make_config(keys: dict) -> configparser.ConfigParser:
    """Helper to build a ConfigParser with given DEFAULT keys."""
    config = configparser.ConfigParser()
    for k, v in keys.items():
        config.set("DEFAULT", k, str(v))
    return config


class TestValidateConfig:
    def test_all_required_keys_present(self):
        config = _make_config({
            "owui_base_url": "http://localhost:8080/",
            "ollama_uri": "api/generate",
            "model_name": "gemma3:4b",
        })
        validate_config(config)

    def test_missing_required_key_exits(self):
        config = _make_config({
            "owui_base_url": "http://localhost:8080/",
        })
        with pytest.raises(SystemExit):
            validate_config(config)

    def test_missing_optional_key_warns(self, caplog):
        config = _make_config({
            "owui_base_url": "http://localhost:8080/",
            "ollama_uri": "api/generate",
            "model_name": "gemma3:4b",
        })
        with caplog.at_level(logging.WARNING):
            validate_config(config)
        assert "request_timeout" in caplog.text

    def test_all_keys_present_no_warnings(self, caplog):
        config = _make_config({
            "owui_base_url": "http://localhost:8080/",
            "ollama_uri": "api/generate",
            "model_name": "gemma3:4b",
            "authorization_token": "sk-test",
            "request_timeout": "60",
            "conversation_batch_size": "8",
            "search_result_count": "10",
            "model_expertise": "QA",
            "llm_provider": "ollama",
        })
        with caplog.at_level(logging.WARNING):
            validate_config(config)
        assert "Missing" not in caplog.text
