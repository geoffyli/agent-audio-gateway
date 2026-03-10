from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from ..exceptions import SegmentationError

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    audio: np.ndarray
    start_sec: float
    end_sec: float
    index: int

    @property
    def timestamp_label(self) -> str:
        def fmt(s: float) -> str:
            m, sec = divmod(int(s), 60)
            return f"{m:02d}:{sec:02d}"

        return f"{fmt(self.start_sec)}-{fmt(self.end_sec)}"


class AudioSegmenter:
    def should_segment(self, duration_sec: float, threshold_sec: float) -> bool:
        return duration_sec > threshold_sec

    def segment(
        self,
        audio: np.ndarray,
        sr: int,
        max_chunk_seconds: float,
        overlap_seconds: float,
    ) -> list[AudioChunk]:
        if overlap_seconds >= max_chunk_seconds:
            raise SegmentationError(
                "overlap_seconds must be less than max_chunk_seconds",
                code="INVALID_CHUNK_PARAMS",
            )

        chunk_samples = int(max_chunk_seconds * sr)
        overlap_samples = int(overlap_seconds * sr)
        step = chunk_samples - overlap_samples

        if step <= 0:
            raise SegmentationError(
                "Chunk step is non-positive — check max_chunk_seconds and overlap_seconds",
                code="INVALID_CHUNK_PARAMS",
            )

        chunks: list[AudioChunk] = []
        start = 0
        idx = 0

        while start < len(audio):
            end = min(start + chunk_samples, len(audio))
            chunks.append(
                AudioChunk(
                    audio=audio[start:end],
                    start_sec=round(start / sr, 3),
                    end_sec=round(end / sr, 3),
                    index=idx,
                )
            )
            if end == len(audio):
                break
            start += step
            idx += 1

        logger.debug(
            "Segmented audio into %d chunk(s) (max=%.1fs overlap=%.1fs)",
            len(chunks),
            max_chunk_seconds,
            overlap_seconds,
        )
        return chunks
