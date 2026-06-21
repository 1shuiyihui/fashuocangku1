from __future__ import annotations

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
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.http_session = http_session or requests.Session()
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.is_configured():
            raise AIConfigurationError("请先在侧边栏配置 API Base、Model 和 API Key。")

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
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
