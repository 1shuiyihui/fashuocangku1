import pytest

from services.ai_client import AIClient, AIConfigurationError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, json, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "第一个问题：构成要件是什么？",
                        }
                    }
                ]
            }
        )


def test_missing_api_key_raises_configuration_error():
    client = AIClient(api_base="https://api.example.com/v1", api_key="", model="test-model")

    with pytest.raises(AIConfigurationError):
        client.chat([{"role": "user", "content": "hello"}])


def test_chat_sends_openai_compatible_request():
    session = FakeSession()
    client = AIClient(
        api_base="https://api.example.com/v1",
        api_key="key-123",
        model="test-model",
        http_session=session,
    )

    content = client.chat([{"role": "user", "content": "请开始追问"}])

    assert content == "第一个问题：构成要件是什么？"
    assert session.calls[0]["url"] == "https://api.example.com/v1/chat/completions"
    assert session.calls[0]["headers"]["Authorization"] == "Bearer key-123"
    assert session.calls[0]["json"]["model"] == "test-model"
    assert session.calls[0]["json"]["messages"][0]["content"] == "请开始追问"
