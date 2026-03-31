"""Tests for path traversal protection in AudioInspector."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from agent_audio_gateway.core.exceptions import InputError
from agent_audio_gateway.core.inspection.inspector import AudioInspector


def _write_wav(path: Path) -> None:
    audio = np.zeros(16000, dtype=np.float32)
    sf.write(str(path), audio, 16000)


def test_inspector_blocks_path_outside_permitted_base(tmp_path: Path) -> None:
    """Inspector with permitted_base must block paths outside that directory."""
    permitted_dir = tmp_path / "allowed"
    permitted_dir.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "audio.wav"
    _write_wav(outside_file)

    inspector = AudioInspector(permitted_base=permitted_dir)

    with pytest.raises(InputError) as exc_info:
        inspector.inspect(str(outside_file))

    assert exc_info.value.code == "PATH_NOT_PERMITTED"


def test_inspector_allows_path_inside_permitted_base(tmp_path: Path) -> None:
    """Inspector with permitted_base must allow paths within that directory."""
    permitted_dir = tmp_path / "allowed"
    permitted_dir.mkdir()

    audio_file = permitted_dir / "audio.wav"
    _write_wav(audio_file)

    inspector = AudioInspector(permitted_base=permitted_dir)
    result = inspector.inspect(str(audio_file))

    assert result.duration_sec > 0


def test_inspector_without_permitted_base_allows_any_path(tmp_path: Path) -> None:
    """Default inspector (no permitted_base) allows any accessible path."""
    audio_file = tmp_path / "audio.wav"
    _write_wav(audio_file)

    inspector = AudioInspector()  # no permitted_base
    result = inspector.inspect(str(audio_file))

    assert result.format == "wav"


def test_inspector_blocks_path_traversal_symlink(tmp_path: Path) -> None:
    """A symlink pointing outside the permitted directory must be blocked."""
    permitted_dir = tmp_path / "allowed"
    permitted_dir.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "audio.wav"
    _write_wav(outside_file)

    # symlink inside permitted_dir pointing to the outside file
    symlink = permitted_dir / "escape.wav"
    symlink.symlink_to(outside_file)

    inspector = AudioInspector(permitted_base=permitted_dir)

    # resolve() follows symlinks, so this must be blocked
    with pytest.raises(InputError) as exc_info:
        inspector.inspect(str(symlink))

    assert exc_info.value.code == "PATH_NOT_PERMITTED"
