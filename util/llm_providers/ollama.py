import json
import time
import logging
import requests

from typing import Optional, Any
from .base import LLMError

log = logging.getLogger(f"emtp.{__name__}")


class OllamaProvider:
    """LLM provider for Ollama-compatible APIs."""

    def __init__(
        self,
        base_url: str,
        authorization_token: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        if authorization_token:
            self.session.headers["Authorization"] = f"Bearer {authorization_token}"

    def generate(
        self,
        prompt: str,
        model: str,
        format: Optional[dict[str, Any]] = None,
    ) -> dict | list | str:
        """
        Send a prompt to the LLM and return the parsed response.
        Retries on transient failures with exponential backoff.
        """
        request_body = {
            "model": model,
            "keep_alive": 0,
            "prompt": prompt,
            "stream": False,
            "images": None,
            "options": None,
            "format": format,
        }

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    self.base_url, json=request_body, timeout=self.timeout
                )

                # Retry on 429 or 5xx
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = LLMError(
                        f"HTTP {response.status_code} from {self.base_url}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.backoff_base * (2 ** attempt))
                        continue
                    raise last_error

                # No retry on other 4xx
                response.raise_for_status()

                return self._parse_response(response.json())

            except requests.exceptions.HTTPError as e:
                raise LLMError(f"HTTP error: {e}") from e
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.backoff_base * (2 ** attempt))
                    continue
                raise LLMError(
                    f"Failed after {self.max_retries} retries: {e}"
                ) from e

        raise LLMError(f"Failed after {self.max_retries} retries: {last_error}")

    def _parse_response(self, json_response: dict) -> dict | list | str:
        """Unwrap and parse the Ollama response format."""
        if "response" not in json_response:
            raise LLMError(
                f"Missing 'response' key in API response: {list(json_response.keys())}"
            )

        raw = json_response["response"]

        if isinstance(raw, (dict, list)):
            return raw

        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise LLMError(f"Failed to parse LLM response as JSON: {e}") from e

        return raw
