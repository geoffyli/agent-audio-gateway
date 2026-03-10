from __future__ import annotations

from fastapi.testclient import TestClient

from agent_audio_gateway.core.exceptions import InputError
from agent_audio_gateway.server import app as app_module


class _FailingEngine:
    def close(self) -> None:
        return

    def health(self):
        return type("Health", (), {"model_dump": lambda self: {"status": "ok"}})()

    def analyze(self, _request):
        raise RuntimeError("unexpected")

    def ask(self, _request):
        raise RuntimeError("unexpected")

    def inspect(self, _file_path: str):
        raise InputError("bad file", code="FILE_NOT_FOUND")


def test_server_wraps_unhandled_exceptions_as_internal_error() -> None:
    original_engine = app_module._engine
    app_module._engine = _FailingEngine()

    try:
        with TestClient(app_module.app, raise_server_exceptions=False) as client:
            response = client.post("/analyze", json={"file_path": "audio.wav"})
    finally:
        app_module._engine = original_engine

    assert response.status_code == 500
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "INTERNAL_ERROR"


def test_server_maps_gateway_input_error_to_422() -> None:
    original_engine = app_module._engine
    app_module._engine = _FailingEngine()

    try:
        with TestClient(app_module.app, raise_server_exceptions=False) as client:
            response = client.post("/inspect", json={"file_path": "missing.wav"})
    finally:
        app_module._engine = original_engine

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "FILE_NOT_FOUND"
