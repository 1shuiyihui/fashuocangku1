from __future__ import annotations

import time
from typing import Any

import requests


class AIConfigurationError(RuntimeError):
    pass


class AIClient:
    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        http_session: Any | None = None,
        timeout: int = 60,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 1.0,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.http_session = http_session or requests.Session()
        self.timeout = timeout
        self.retry_attempts = max(1, retry_attempts)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def is_configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.is_configured():
            raise AIConfigurationError("请先在侧边栏配置 API Base、Model 和 API Key。")

        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = self.http_session.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.4,
                    },
                    timeout=self.timeout,
                )
                try:
                    response.raise_for_status()
                except Exception as exc:
                    if attempt < self.retry_attempts and self._is_retryable_response(response):
                        last_error = exc
                        self._sleep_before_retry(attempt)
                        continue
                    raise
                payload = response.json()
                return payload["choices"][0]["message"]["content"]
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.retry_attempts:
                    raise
                self._sleep_before_retry(attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("AI request failed without a response")

    @staticmethod
    def _is_retryable_response(response: Any) -> bool:
        status_code = int(getattr(response, "status_code", 0) or 0)
        return status_code == 429 or 500 <= status_code < 600

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_backoff_seconds <= 0:
            return
        time.sleep(self.retry_backoff_seconds * attempt)
