from __future__ import annotations

import logging

from ..exceptions import PreprocessingError

logger = logging.getLogger(__name__)

class AudioPreprocessor:
    def load(self, file_path: str) -> tuple:
        """Load an audio file at its native sample rate and convert to mono.

        Returns (audio_array, sample_rate).
        """
        try:
            import librosa
            audio, sr = librosa.load(file_path, sr=None, mono=True)
            logger.debug(
                "Loaded %s: %.2fs at %dHz (%d samples)",
                file_path,
                len(audio) / sr,
                sr,
                len(audio),
            )
            return audio, sr
        except Exception as e:
            raise PreprocessingError(
                f"Failed to load audio: {e}",
                code="AUDIO_LOAD_ERROR",
            )
