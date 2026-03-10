from __future__ import annotations

import logging

import numpy as np

from ..exceptions import PreprocessingError

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    def load(self, file_path: str) -> tuple[np.ndarray, int]:
        """Load an audio file at its native sample rate and convert to mono.

        Returns (audio_array, sample_rate).
        """
        soundfile_error = None
        try:
            audio, sr = self._load_with_soundfile(file_path)
            logger.debug(
                "Loaded %s via soundfile: %.2fs at %dHz (%d samples)",
                file_path,
                len(audio) / sr,
                sr,
                len(audio),
            )
            return audio, sr
        except Exception as e:
            soundfile_error = e
            logger.debug(
                "soundfile load failed for %s: %s; falling back to librosa",
                file_path,
                e,
            )

        try:
            audio, sr = self._load_with_librosa(file_path)
            logger.debug(
                "Loaded %s via librosa fallback: %.2fs at %dHz (%d samples)",
                file_path,
                len(audio) / sr,
                sr,
                len(audio),
            )
            return audio, sr
        except Exception as e:
            raise PreprocessingError(
                f"Failed to load audio (soundfile error: {soundfile_error}; librosa error: {e})",
                code="AUDIO_LOAD_ERROR",
            )

    @staticmethod
    def _load_with_soundfile(file_path: str) -> tuple[np.ndarray, int]:
        import soundfile as sf

        audio, sr = sf.read(file_path, dtype="float32", always_2d=True)
        if audio.size == 0:
            raise ValueError("Empty audio file")

        mono = audio.mean(axis=1, dtype=np.float32)
        return np.ascontiguousarray(mono), int(sr)

    @staticmethod
    def _load_with_librosa(file_path: str) -> tuple[np.ndarray, int]:
        import librosa

        audio, sr = librosa.load(file_path, sr=None, mono=True)
        if audio.size == 0:
            raise ValueError("Empty audio file")
        return np.ascontiguousarray(audio.astype(np.float32, copy=False)), int(sr)
