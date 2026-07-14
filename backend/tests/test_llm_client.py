import pytest

from app.llm_client import _extract_json


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
