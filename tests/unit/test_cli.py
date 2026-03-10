import json
import os
import sys
import types
from types import SimpleNamespace

from click.testing import CliRunner

from agent_audio_gateway.cli import main
from agent_audio_gateway.core.models import AnalyzeResponse, AnalysisResult, InputMeta


def _fake_response(task: str = "summarize") -> AnalyzeResponse:
    return AnalyzeResponse(
        input=InputMeta(
            file_path="input.wav",
            duration_sec=1.0,
            segmented=False,
            chunk_count=1,
        ),
        result=AnalysisResult(task=task, summary="ok"),
    )


class _FakeEngine:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            analysis=SimpleNamespace(
                default_max_chunk_seconds=25.0,
                default_overlap_seconds=3.0,
            )
        )
        self.analyze_request = None
        self.ask_request = None

    def analyze(self, request):
        self.analyze_request = request
        return _fake_response(task=request.task.value)

    def ask(self, request):
        self.ask_request = request
        return _fake_response(task="qa")

    def inspect(self, _file_path: str):
        raise RuntimeError("boom")


def test_analyze_preserves_zero_overlap_override(monkeypatch) -> None:
    engine = _FakeEngine()
    monkeypatch.setattr(main, "_make_engine", lambda _config_path: engine)

    result = CliRunner().invoke(
        main.cli,
        ["analyze", "audio.wav", "--overlap-seconds", "0", "--no-segment"],
    )

    assert result.exit_code == 0
    assert engine.analyze_request is not None
    assert engine.analyze_request.options.overlap_seconds == 0.0


def test_ask_preserves_zero_overlap_override(monkeypatch) -> None:
    engine = _FakeEngine()
    monkeypatch.setattr(main, "_make_engine", lambda _config_path: engine)

    result = CliRunner().invoke(
        main.cli,
        [
            "ask",
            "audio.wav",
            "--question",
            "What happened?",
            "--overlap-seconds",
            "0",
            "--no-segment",
        ],
    )

    assert result.exit_code == 0
    assert engine.ask_request is not None
    assert engine.ask_request.options.overlap_seconds == 0.0


def test_serve_config_overrides_existing_env(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=fake_run))
    monkeypatch.setenv("AGENT_AUDIO_GATEWAY_CONFIG", "old.yaml")

    result = CliRunner().invoke(
        main.cli,
        ["--config", "new.yaml", "serve"],
    )

    assert result.exit_code == 0
    assert captured["kwargs"]["host"] == "127.0.0.1"
    assert captured["kwargs"]["port"] == 8000
    assert captured["kwargs"]["reload"] is False
    assert os.environ["AGENT_AUDIO_GATEWAY_CONFIG"] == "new.yaml"


def test_serve_blocks_non_loopback_without_allow_remote() -> None:
    result = CliRunner().invoke(main.cli, ["serve", "--host", "0.0.0.0"])

    assert result.exit_code != 0
    assert "--allow-remote" in result.output


def test_serve_allows_non_loopback_with_allow_remote(monkeypatch) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured["kwargs"] = kwargs

    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=fake_run))

    result = CliRunner().invoke(
        main.cli,
        ["serve", "--host", "0.0.0.0", "--allow-remote"],
    )

    assert result.exit_code == 0
    assert captured["kwargs"]["host"] == "0.0.0.0"


def test_cli_unhandled_error_returns_internal_error_json(monkeypatch) -> None:
    engine = _FakeEngine()
    monkeypatch.setattr(main, "_make_engine", lambda _config_path: engine)

    result = CliRunner().invoke(main.cli, ["inspect", "audio.wav"])

    assert result.exit_code == 6
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "INTERNAL_ERROR"
