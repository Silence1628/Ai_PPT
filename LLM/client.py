from openai import OpenAI
from openai import APIError, RateLimitError
import os
import time
import threading
from dotenv import load_dotenv

load_dotenv()

# Provider configs
PROVIDERS = {
    "minimax": {
        "base_url": "https://api.minimaxi.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "MiniMax-M2.7",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
}


def _get_provider_config(provider: str = None):
    """Resolve provider name and return (provider, config dict)."""
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "minimax")
    provider = provider.lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider}. Choices: {list(PROVIDERS)}")
    return provider, PROVIDERS[provider]


class LLMClient:
    """Multi-provider LLM client (MiniMax / DeepSeek), OpenAI SDK compatible."""

    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        pname, cfg = _get_provider_config(provider)
        self.provider = pname
        key = api_key or os.getenv(cfg["env_key"])
        if not key:
            raise ValueError(
                f"Missing API key for {pname}. Set {cfg['env_key']} env var or pass api_key."
            )
        self.client = OpenAI(api_key=key, base_url=cfg["base_url"])
        self.model = model or cfg["default_model"]
        self._lock = threading.Lock()
        self.last_usage = None

    def chat(self, messages: list[dict], temperature: float = 1.0,
             max_retries: int = 3, **kwargs) -> str:
        result = self.chat_with_stats(messages, temperature, max_retries, **kwargs)
        return result["content"]

    def chat_with_stats(self, messages: list[dict], temperature: float = 1.0,
                        max_retries: int = 3, **kwargs) -> dict:
        # MiniMax-specific extra_body — always strip from kwargs
        extra_body = {}
        if kwargs.pop("reasoning_split", False):
            if self.provider == "minimax":
                extra_body["reasoning_split"] = True

        last_error = None
        for attempt in range(max_retries):
            try:
                with self._lock:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        extra_body=extra_body,
                        **kwargs
                    )
                self.last_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                return {"content": response.choices[0].message.content, "usage": self.last_usage}
            except (RateLimitError, APIError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"{self.provider} API call failed (retried {max_retries}×): {last_error}")

    def chat_stream(self, messages: list[dict]):
        extra_body = {}
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            extra_body=extra_body
        )


# Backward-compatible alias
MiniMaxClient = LLMClient
