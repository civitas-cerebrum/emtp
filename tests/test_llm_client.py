import json
import pytest
from unittest.mock import patch, MagicMock

from util.llm_providers.base import LLMError
from util.llm_providers.ollama import OllamaProvider
from util.llm_client import LLMClient, create_llm_client


class TestOllamaProviderGenerate:
    def setup_method(self):
        self.provider = OllamaProvider(
            base_url="http://fake:8080/api/generate",
            timeout=10,
            max_retries=2,
            backoff_base=0.01,
        )

    def _mock_response(self, data, status_code=200):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = {"response": json.dumps(data) if not isinstance(data, str) else data}
        mock.raise_for_status.return_value = None
        return mock

    def test_happy_path_dict_response(self):
        data = {"qnaList": [{"q": "Q?", "a": "A"}]}
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = self._mock_response(data)
        result = self.provider.generate(prompt="test", model="gemma3:4b")
        assert result == data
        self.provider.session.post.assert_called_once()

    def test_happy_path_list_response(self):
        data = [{"question": "Q?", "category": "Test"}]
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = self._mock_response(data)
        result = self.provider.generate(prompt="test", model="gemma3:4b")
        assert result == data

    def test_dict_response_not_string(self):
        data = {"qnaList": [{"q": "Q?", "a": "A"}]}
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"response": data}
        mock.raise_for_status.return_value = None
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = mock
        result = self.provider.generate(prompt="test", model="gemma3:4b")
        assert result == data

    def test_missing_response_key_raises(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"something_else": "data"}
        mock.raise_for_status.return_value = None
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = mock
        with pytest.raises(LLMError, match="Missing 'response' key"):
            self.provider.generate(prompt="test", model="gemma3:4b")

    def test_invalid_json_string_raises(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {"response": "not valid json {{{"}
        mock.raise_for_status.return_value = None
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = mock
        with pytest.raises(LLMError, match="Failed to parse"):
            self.provider.generate(prompt="test", model="gemma3:4b")

    def test_format_passed_in_request_body(self):
        schema = {"type": "array", "items": {"type": "object"}}
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = self._mock_response([])
        self.provider.generate(prompt="test", model="gemma3:4b", format=schema)
        call_kwargs = self.provider.session.post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["format"] == schema

    def test_request_body_structure(self):
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = self._mock_response({"key": "val"})
        self.provider.generate(prompt="my prompt", model="gemma3:4b")
        call_kwargs = self.provider.session.post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["model"] == "gemma3:4b"
        assert body["prompt"] == "my prompt"
        assert body["stream"] is False
        assert body["keep_alive"] == 0


class TestOllamaProviderRetry:
    def setup_method(self):
        self.provider = OllamaProvider(
            base_url="http://fake:8080/api/generate",
            timeout=10,
            max_retries=2,
            backoff_base=0.01,
        )

    def test_retries_on_connection_error(self):
        import requests as req
        good_mock = MagicMock()
        good_mock.status_code = 200
        good_mock.json.return_value = {"response": json.dumps({"ok": True})}
        good_mock.raise_for_status.return_value = None
        self.provider.session = MagicMock()
        self.provider.session.post.side_effect = [
            req.exceptions.ConnectionError("refused"),
            good_mock,
        ]
        result = self.provider.generate(prompt="test", model="m")
        assert result == {"ok": True}
        assert self.provider.session.post.call_count == 2

    def test_retries_on_500(self):
        error_mock = MagicMock()
        error_mock.status_code = 500
        good_mock = MagicMock()
        good_mock.status_code = 200
        good_mock.json.return_value = {"response": json.dumps({"ok": True})}
        good_mock.raise_for_status.return_value = None
        self.provider.session = MagicMock()
        self.provider.session.post.side_effect = [error_mock, error_mock, good_mock]
        result = self.provider.generate(prompt="test", model="m")
        assert result == {"ok": True}
        assert self.provider.session.post.call_count == 3

    def test_retries_on_429(self):
        rate_mock = MagicMock()
        rate_mock.status_code = 429
        good_mock = MagicMock()
        good_mock.status_code = 200
        good_mock.json.return_value = {"response": json.dumps({"ok": True})}
        good_mock.raise_for_status.return_value = None
        self.provider.session = MagicMock()
        self.provider.session.post.side_effect = [rate_mock, good_mock]
        result = self.provider.generate(prompt="test", model="m")
        assert result == {"ok": True}

    def test_no_retry_on_400(self):
        import requests as req
        error_mock = MagicMock()
        error_mock.status_code = 400
        error_mock.raise_for_status.side_effect = req.exceptions.HTTPError("400 Bad Request")
        self.provider.session = MagicMock()
        self.provider.session.post.return_value = error_mock
        with pytest.raises(LLMError):
            self.provider.generate(prompt="test", model="m")
        assert self.provider.session.post.call_count == 1

    def test_max_retries_exceeded_raises(self):
        import requests as req
        self.provider.session = MagicMock()
        self.provider.session.post.side_effect = req.exceptions.ConnectionError("refused")
        with pytest.raises(LLMError, match="Failed after"):
            self.provider.generate(prompt="test", model="m")
        assert self.provider.session.post.call_count == 3


class TestOllamaProviderSession:
    def test_auth_header_set(self):
        provider = OllamaProvider(base_url="http://fake:8080", authorization_token="sk-test123")
        assert provider.session.headers["Authorization"] == "Bearer sk-test123"

    def test_no_auth_header_when_none(self):
        provider = OllamaProvider(base_url="http://fake:8080")
        assert "Authorization" not in provider.session.headers

    def test_content_type_set(self):
        provider = OllamaProvider(base_url="http://fake:8080")
        assert provider.session.headers["Content-Type"] == "application/json"


class TestLLMClient:
    def test_delegates_to_provider(self):
        mock_provider = MagicMock()
        mock_provider.generate.return_value = {"key": "value"}
        client = LLMClient(mock_provider)
        result = client.generate(prompt="test", model="m", format=None)
        assert result == {"key": "value"}
        mock_provider.generate.assert_called_once_with(prompt="test", model="m", format=None)


class TestCreateLLMClient:
    @patch("util.llm_client.get_config")
    def test_creates_ollama_provider(self, mock_config):
        config = MagicMock()
        config.__getitem__ = lambda self, key: {
            "DEFAULT": {
                "owui_base_url": "http://localhost:8080/",
                "ollama_uri": "api/generate",
                "authorization_token": "sk-test",
            }
        }[key]
        config.get = lambda section, key, fallback=None: {
            ("DEFAULT", "llm_provider"): "ollama",
            ("DEFAULT", "authorization_token"): "sk-test",
        }.get((section, key), fallback)
        config.getint = lambda section, key, fallback=60: fallback
        mock_config.return_value = config
        client = create_llm_client()
        assert isinstance(client, LLMClient)
        assert isinstance(client.provider, OllamaProvider)

    @patch("util.llm_client.get_config")
    def test_unknown_provider_raises(self, mock_config):
        config = MagicMock()
        config.get = lambda s, k, fallback=None: "unsupported" if k == "llm_provider" else fallback
        mock_config.return_value = config
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_client()
