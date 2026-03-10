from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.engine import GatewayEngine
from agent_audio_gateway.core.exceptions import InputError


def test_load_prompt_file_missing_raises_input_error() -> None:
    with pytest.raises(InputError) as exc_info:
        GatewayEngine._load_prompt_file("/path/does/not/exist.txt")

    assert exc_info.value.code == "PROMPT_FILE_NOT_FOUND"


def test_load_prompt_file_directory_raises_input_error(tmp_path: Path) -> None:
    with pytest.raises(InputError) as exc_info:
        GatewayEngine._load_prompt_file(str(tmp_path))

    assert exc_info.value.code == "NOT_A_FILE"


def test_load_prompt_file_decode_error_raises_input_error(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.bin"
    prompt_path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(InputError) as exc_info:
        GatewayEngine._load_prompt_file(str(prompt_path))

    assert exc_info.value.code == "PROMPT_FILE_READ_ERROR"


def test_load_prompt_file_success_returns_trimmed_text(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("  Hello prompt  \n", encoding="utf-8")

    result = GatewayEngine._load_prompt_file(str(prompt_path))

    assert result == "Hello prompt"


def test_inspect_does_not_require_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    wav_path = tmp_path / "test.wav"
    sf.write(wav_path, np.zeros(160, dtype=np.float32), 16000)

    engine = GatewayEngine(GatewayConfig())
    result = engine.inspect(str(wav_path))

    assert result.status == "ok"
    assert result.file.format == "wav"
