from pathlib import Path

import numpy as np
import soundfile as sf

from agent_audio_gateway.core.preprocessing.preprocessor import AudioPreprocessor


def test_soundfile_path_loads_and_downmixes_to_mono(tmp_path: Path) -> None:
    sr = 16000
    left = np.array([0.0, 0.5, -0.5, 1.0], dtype=np.float32)
    right = np.array([1.0, 0.5, 0.5, -1.0], dtype=np.float32)
    stereo = np.column_stack([left, right])

    wav_path = tmp_path / "stereo.wav"
    sf.write(str(wav_path), stereo, sr, format="WAV", subtype="FLOAT")

    audio, loaded_sr = AudioPreprocessor().load(str(wav_path))

    assert loaded_sr == sr
    assert audio.ndim == 1
    assert audio.dtype == np.float32
    assert np.allclose(audio, stereo.mean(axis=1, dtype=np.float32), atol=1e-6)
