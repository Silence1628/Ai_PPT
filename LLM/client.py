from openai import OpenAI
from openai import APIError, RateLimitError
import os
import time
import threading
from dotenv import load_dotenv

load_dotenv()


class MiniMaxClient:
    """MiniMax API client using OpenAI SDK compatible mode."""

    def __init__(self, api_key: str = None, model: str = "MiniMax-M2.7"):
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url="https://api.minimaxi.com/v1"
        )
        self.model = model
        self._lock = threading.Lock()

    def chat(self, messages: list[dict], temperature: float = 1.0,
             reasoning_split: bool = False, max_retries: int = 3, **kwargs) -> str:
        """Send a chat request with exponential backoff retry, return text content."""
        extra_body = {"reasoning_split": reasoning_split} if reasoning_split else {}
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
                return response.choices[0].message.content
            except (RateLimitError, APIError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                continue

        raise RuntimeError(f"MiniMax API 调用失败（已重试 {max_retries} 次）: {last_error}")

    def chat_stream(self, messages: list[dict], reasoning_split: bool = False):
        """Streaming response version."""
        extra_body = {"reasoning_split": reasoning_split} if reasoning_split else {}
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            extra_body=extra_body
        )
