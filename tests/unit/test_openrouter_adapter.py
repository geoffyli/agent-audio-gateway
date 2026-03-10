import numpy as np

from agent_audio_gateway.core.adapters.openrouter.adapter import OpenRouterAdapter


class _FakeResponse:
    def __init__(self, payload: dict):
        self.status_code = 200
        self._payload = payload
        self.text = "ok"

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self):
        self.last_json = None

    def post(self, _path: str, json: dict):
        self.last_json = json
        return _FakeResponse({"choices": [{"message": {"content": '{"ok":true}'}}]})

    def close(self) -> None:
        return


def _make_adapter() -> OpenRouterAdapter:
    return OpenRouterAdapter(
        model_id="fake/model",
        api_key="test-key",
        base_url="https://example.com",
        max_tokens=128,
        connect_timeout_seconds=1.0,
        read_timeout_seconds=1.0,
        write_timeout_seconds=1.0,
        pool_timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        target_sample_rate_hz=16000,
    )


def test_analyze_adds_response_format_payload_when_schema_provided() -> None:
    adapter = _make_adapter()
    fake_client = _FakeClient()
    adapter._client = fake_client

    adapter.analyze(
        np.zeros(800, dtype=np.float32),
        16000,
        "Summarize audio",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert fake_client.last_json is not None
    assert fake_client.last_json["response_format"]["type"] == "json_schema"
    assert (
        fake_client.last_json["response_format"]["json_schema"]["schema"]["type"]
        == "object"
    )
    assert fake_client.last_json["provider"]["require_parameters"] is True


def test_analyze_keeps_standard_payload_without_schema() -> None:
    adapter = _make_adapter()
    fake_client = _FakeClient()
    adapter._client = fake_client

    adapter.analyze(np.zeros(800, dtype=np.float32), 16000, "Summarize audio")

    assert fake_client.last_json is not None
    assert "response_format" not in fake_client.last_json
    assert "provider" not in fake_client.last_json


def test_synthesize_adds_response_format_when_schema_provided() -> None:
    adapter = _make_adapter()
    fake_client = _FakeClient()
    adapter._client = fake_client

    adapter.synthesize(
        "Merge these chunk summaries",
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert fake_client.last_json is not None
    assert fake_client.last_json["response_format"]["type"] == "json_schema"
    assert fake_client.last_json["provider"]["require_parameters"] is True
