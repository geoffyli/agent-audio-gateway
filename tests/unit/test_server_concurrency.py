"""Tests for the thread-safe engine singleton in the server."""
from __future__ import annotations

import threading
from typing import Any

from agent_audio_gateway.server import app as app_module


def _reset_engine(monkeypatch) -> None:
    """Force the engine singleton back to None between tests."""
    monkeypatch.setattr(app_module, "_engine", None)


def test_get_engine_is_idempotent_under_concurrent_calls(monkeypatch, tmp_path) -> None:
    """Concurrent calls to _get_engine must create the engine exactly once."""
    # Create a minimal valid config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "model:\n  api_key: test-key\nlogging:\n  level: warning\n"
    )
    monkeypatch.setenv("AGENT_AUDIO_GATEWAY_CONFIG", str(config_file))
    _reset_engine(monkeypatch)

    results: list[Any] = []
    errors: list[Exception] = []

    def _get_and_store():
        try:
            results.append(app_module._get_engine())
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_get_and_store) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Threads raised: {errors}"
    assert len(results) == 10

    # All references must point to the same object
    ids = {id(r) for r in results}
    assert len(ids) == 1, "Engine was created more than once"


def test_close_engine_under_concurrent_get(monkeypatch, tmp_path) -> None:
    """Interleaved get/close calls from multiple threads must not raise."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "model:\n  api_key: test-key\nlogging:\n  level: warning\n"
    )
    monkeypatch.setenv("AGENT_AUDIO_GATEWAY_CONFIG", str(config_file))
    _reset_engine(monkeypatch)

    errors: list[Exception] = []

    def _cycle():
        try:
            app_module._get_engine()
            app_module._close_engine()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_cycle) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Threads raised: {errors}"
