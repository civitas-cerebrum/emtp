from typing import Protocol, Optional, Any


class LLMError(Exception):
    """Raised when an LLM API call fails after all retries."""
    pass


class LLMProvider(Protocol):
    def generate(
        self,
        prompt: str,
        model: str,
        format: Optional[dict[str, Any]] = None,
    ) -> dict | list | str:
        """Send a prompt to the LLM and return the parsed response."""
        ...
