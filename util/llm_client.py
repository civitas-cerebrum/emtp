from util.utilities import get_config
from util.llm_providers.base import LLMProvider
from util.llm_providers.ollama import OllamaProvider


class LLMClient:
    """High-level LLM client that delegates to a provider."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def generate(self, prompt: str, model: str, format=None):
        return self.provider.generate(prompt=prompt, model=model, format=format)


def create_llm_client() -> LLMClient:
    """Factory: reads config and creates the appropriate LLM provider."""
    config = get_config()
    provider_type = config.get("DEFAULT", "llm_provider", fallback="ollama")

    if provider_type == "ollama":
        base_url = config["DEFAULT"]["owui_base_url"] + config["DEFAULT"]["ollama_uri"]
        token = config.get("DEFAULT", "authorization_token", fallback=None)
        timeout = config.getint("DEFAULT", "request_timeout", fallback=60)
        provider = OllamaProvider(base_url=base_url, authorization_token=token, timeout=timeout)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")

    return LLMClient(provider)
