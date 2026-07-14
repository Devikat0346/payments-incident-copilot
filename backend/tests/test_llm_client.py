import httpx
import pytest

from app import config
from app.llm_client import LLMRateLimitedError, _call_groq, _extract_json


class FakeGroqResponse:
    def __init__(self, status_code, json_body=None, headers=None):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Client error '{self.status_code}' for url 'https://api.groq.com/openai/v1/chat/completions'",
                request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._json_body


def _success_response():
    return FakeGroqResponse(200, {"choices": [{"message": {"content": '{"summary": "ok"}'}}]})


class FakeGroqClient:
    """Serves a scripted sequence of responses, one per POST call, in place
    of a real httpx.AsyncClient — no network calls, no real waiting."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        resp = self._responses[self.calls]
        self.calls += 1
        return resp


async def _no_sleep(_seconds):
    pass


class TestCallGroqRetry:
    @pytest.mark.asyncio
    async def test_succeeds_immediately_when_not_rate_limited(self, monkeypatch):
        monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
        fake_client = FakeGroqClient([_success_response()])
        monkeypatch.setattr("app.llm_client.httpx.AsyncClient", lambda **kwargs: fake_client)

        result = await _call_groq("hello")

        assert result == '{"summary": "ok"}'
        assert fake_client.calls == 1

    @pytest.mark.asyncio
    async def test_retries_on_429_then_succeeds(self, monkeypatch):
        monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
        monkeypatch.setattr("app.llm_client.asyncio.sleep", _no_sleep)
        fake_client = FakeGroqClient([FakeGroqResponse(429), _success_response()])
        monkeypatch.setattr("app.llm_client.httpx.AsyncClient", lambda **kwargs: fake_client)

        result = await _call_groq("hello")

        assert result == '{"summary": "ok"}'
        assert fake_client.calls == 2

    @pytest.mark.asyncio
    async def test_raises_clean_error_after_exhausting_retries(self, monkeypatch):
        monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
        monkeypatch.setattr("app.llm_client.asyncio.sleep", _no_sleep)
        fake_client = FakeGroqClient([FakeGroqResponse(429), FakeGroqResponse(429), FakeGroqResponse(429)])
        monkeypatch.setattr("app.llm_client.httpx.AsyncClient", lambda **kwargs: fake_client)

        with pytest.raises(LLMRateLimitedError):
            await _call_groq("hello")

        assert fake_client.calls == 3

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self, monkeypatch):
        monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
        slept_for = []

        async def fake_sleep(seconds):
            slept_for.append(seconds)

        monkeypatch.setattr("app.llm_client.asyncio.sleep", fake_sleep)
        fake_client = FakeGroqClient([FakeGroqResponse(429, headers={"retry-after": "7"}), _success_response()])
        monkeypatch.setattr("app.llm_client.httpx.AsyncClient", lambda **kwargs: fake_client)

        await _call_groq("hello")

        assert slept_for == [7.0]


class TestExtractJson:
    def test_plain_json_object(self):
        result = _extract_json('{"summary": "all good", "severity": "low"}')
        assert result == {"summary": "all good", "severity": "low"}

    def test_json_wrapped_in_markdown_fences(self):
        text = '```json\n{"summary": "elevated declines", "severity": "high"}\n```'
        result = _extract_json(text)
        assert result["summary"] == "elevated declines"

    def test_json_with_leading_and_trailing_prose(self):
        text = 'Here is my analysis:\n{"summary": "ok", "severity": "medium"}\nHope that helps!'
        result = _extract_json(text)
        assert result["summary"] == "ok"

    def test_no_json_object_raises(self):
        with pytest.raises(ValueError):
            _extract_json("I couldn't analyze this incident.")

    def test_nested_json_object(self):
        text = '{"summary": "ok", "recommended_actions": ["a", "b"], "nested": {"x": 1}}'
        result = _extract_json(text)
        assert result["nested"] == {"x": 1}
        assert result["recommended_actions"] == ["a", "b"]
