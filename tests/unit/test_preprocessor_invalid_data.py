"""Tests for NaN/inf audio validation in AudioPreprocessor."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from agent_audio_gateway.core.exceptions import PreprocessingError
from agent_audio_gateway.core.preprocessing.preprocessor import AudioPreprocessor


def _write_wav(path: Path, audio: np.ndarray, sr: int = 16000) -> None:
    sf.write(str(path), audio, sr)


def test_preprocessor_raises_on_nan_audio(tmp_path: Path) -> None:
    """Preprocessor must raise PreprocessingError if audio contains NaN."""
    preprocessor = AudioPreprocessor()

    good_audio = np.zeros(16000, dtype=np.float32)
    audio_file = tmp_path / "audio.wav"
    _write_wav(audio_file, good_audio)

    # Patch _load_with_soundfile to return an array with NaN
    nan_audio = np.array([0.0, float("nan"), 0.5], dtype=np.float32)
    with patch.object(
        AudioPreprocessor,
        "_load_with_soundfile",
        return_value=(nan_audio, 16000),
    ), pytest.raises(PreprocessingError) as exc_info:
        preprocessor.load(str(audio_file))

    assert exc_info.value.code == "AUDIO_INVALID_DATA"


def test_preprocessor_raises_on_inf_audio(tmp_path: Path) -> None:
    """Preprocessor must raise PreprocessingError if audio contains infinity."""
    preprocessor = AudioPreprocessor()

    good_audio = np.zeros(16000, dtype=np.float32)
    audio_file = tmp_path / "audio.wav"
    _write_wav(audio_file, good_audio)

    inf_audio = np.array([0.0, float("inf"), 0.5], dtype=np.float32)
    with patch.object(
        AudioPreprocessor,
        "_load_with_soundfile",
        return_value=(inf_audio, 16000),
    ), pytest.raises(PreprocessingError) as exc_info:
        preprocessor.load(str(audio_file))

    assert exc_info.value.code == "AUDIO_INVALID_DATA"


def test_preprocessor_valid_audio_passes(tmp_path: Path) -> None:
    """Valid audio (all finite values) must load without error."""
    preprocessor = AudioPreprocessor()

    good_audio = np.linspace(-0.5, 0.5, 16000, dtype=np.float32)
    audio_file = tmp_path / "audio.wav"
    _write_wav(audio_file, good_audio)

    audio_out, sr = preprocessor.load(str(audio_file))

    assert np.isfinite(audio_out).all()
    assert sr == 16000
