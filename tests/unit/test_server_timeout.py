"""Tests for server-side request timeout in _run_sync."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from agent_audio_gateway.core.config import GatewayConfig, ServerConfig
from agent_audio_gateway.core.exceptions import GatewayError
from agent_audio_gateway.server import app as app_module
from agent_audio_gateway.server.app import _run_sync


@pytest.mark.asyncio
async def test_run_sync_raises_gateway_error_on_timeout() -> None:
    """_run_sync must raise GatewayError(REQUEST_TIMEOUT) when the operation hangs."""

    def _hang():
        time.sleep(10)

    with pytest.raises(GatewayError) as exc_info:
        await _run_sync(_hang, timeout=0.05)

    assert exc_info.value.code == "REQUEST_TIMEOUT"
    assert exc_info.value.retryable is True


def test_server_analyze_returns_500_on_timeout(monkeypatch) -> None:
    """A request that exceeds the timeout must return a 500 with REQUEST_TIMEOUT code."""

    class _HangingEngine:
        config = GatewayConfig(server=ServerConfig(request_timeout_seconds=0.05))

        def close(self) -> None:
            return

        def health(self):
            from agent_audio_gateway.core.models import HealthResponse

            return HealthResponse(model="test", version="0")

        def analyze(self, _request):
            time.sleep(10)

        def ask(self, _request):
            time.sleep(10)

        def inspect(self, _file_path: str):
            time.sleep(10)

    monkeypatch.setattr(app_module, "_engine", _HangingEngine())

    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        response = client.post("/analyze", json={"file_path": "audio.wav"})

    monkeypatch.setattr(app_module, "_engine", None)

    assert response.status_code == 500
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "REQUEST_TIMEOUT"
