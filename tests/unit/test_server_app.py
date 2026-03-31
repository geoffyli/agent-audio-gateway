from __future__ import annotations

from fastapi.testclient import TestClient

from agent_audio_gateway import __version__
from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.exceptions import InputError
from agent_audio_gateway.core.models import (
    AnalysisResult,
    AnalyzeRequest,
    AnalyzeResponse,
    FileInfo,
    HealthResponse,
    InputMeta,
    InspectResponse,
)
from agent_audio_gateway.server import app as app_module


class _FailingEngine:
    config = GatewayConfig()

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


class _SuccessEngine:
    config = GatewayConfig()

    def close(self) -> None:
        return

    def health(self) -> HealthResponse:
        return HealthResponse(model="test-model", version=__version__)

    def inspect(self, file_path: str) -> InspectResponse:
        return InspectResponse(
            file=FileInfo(
                path=file_path,
                format="wav",
                channels=1,
                sample_rate=16000,
                duration_sec=5.0,
                size_bytes=80044,
            )
        )

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        return AnalyzeResponse(
            input=InputMeta(
                file_path=request.file_path,
                duration_sec=5.0,
                segmented=False,
                chunk_count=1,
            ),
            result=AnalysisResult(task="summarize", summary="Test summary"),
        )

    def ask(self, _request) -> AnalyzeResponse:
        return AnalyzeResponse(
            input=InputMeta(
                file_path="audio.wav",
                duration_sec=5.0,
                segmented=False,
                chunk_count=1,
            ),
            result=AnalysisResult(task="qa", summary="Test answer"),
        )


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


def test_health_returns_ok() -> None:
    original_engine = app_module._engine
    app_module._engine = _SuccessEngine()

    try:
        with TestClient(app_module.app) as client:
            response = client.get("/health")
    finally:
        app_module._engine = original_engine

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model"] == "test-model"


def test_version_returns_version_string() -> None:
    original_engine = app_module._engine
    app_module._engine = _SuccessEngine()

    try:
        with TestClient(app_module.app) as client:
            response = client.get("/version")
    finally:
        app_module._engine = original_engine

    assert response.status_code == 200
    assert response.json()["version"] == __version__


def test_inspect_success_path() -> None:
    original_engine = app_module._engine
    app_module._engine = _SuccessEngine()

    try:
        with TestClient(app_module.app) as client:
            response = client.post("/inspect", json={"file_path": "audio.wav"})
    finally:
        app_module._engine = original_engine

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["file"]["format"] == "wav"


def test_analyze_success_path() -> None:
    original_engine = app_module._engine
    app_module._engine = _SuccessEngine()

    try:
        with TestClient(app_module.app) as client:
            response = client.post("/analyze", json={"file_path": "audio.wav"})
    finally:
        app_module._engine = original_engine

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["result"]["summary"] == "Test summary"


def test_ask_success_path() -> None:
    original_engine = app_module._engine
    app_module._engine = _SuccessEngine()

    try:
        with TestClient(app_module.app) as client:
            response = client.post(
                "/ask", json={"file_path": "audio.wav", "question": "What is said?"}
            )
    finally:
        app_module._engine = original_engine

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["result"]["task"] == "qa"
