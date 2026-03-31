import numpy as np
import pytest

from agent_audio_gateway.core.exceptions import SegmentationError
from agent_audio_gateway.core.segmentation.segmenter import AudioSegmenter

SR = 16000


@pytest.mark.parametrize(
    ("max_chunk_seconds", "overlap_seconds"),
    [
        (0.0, 0.0),
        (10.0, -1.0),
        (10.0, 10.0),
    ],
)
def test_invalid_chunk_parameters_raise(
    max_chunk_seconds: float, overlap_seconds: float
) -> None:
    audio = np.zeros(SR, dtype=np.float32)

    with pytest.raises(SegmentationError):
        AudioSegmenter().segment(
            audio=audio,
            sr=SR,
            max_chunk_seconds=max_chunk_seconds,
            overlap_seconds=overlap_seconds,
        )


def test_segment_short_audio_produces_single_chunk() -> None:
    """Audio shorter than max_chunk_seconds must yield exactly one chunk."""
    audio = np.zeros(SR * 5, dtype=np.float32)  # 5 seconds

    chunks = AudioSegmenter().segment(audio, SR, max_chunk_seconds=10.0, overlap_seconds=0.0)

    assert len(chunks) == 1
    assert chunks[0].index == 0


def test_segment_exact_boundary_produces_single_chunk() -> None:
    """Audio exactly equal to max_chunk_seconds must yield exactly one chunk."""
    audio = np.zeros(SR * 10, dtype=np.float32)  # exactly 10 seconds

    chunks = AudioSegmenter().segment(audio, SR, max_chunk_seconds=10.0, overlap_seconds=0.0)

    assert len(chunks) == 1


def test_segment_two_chunks_no_overlap() -> None:
    """Audio twice the chunk size with zero overlap must yield two non-overlapping chunks."""
    audio = np.zeros(SR * 20, dtype=np.float32)  # 20 seconds

    chunks = AudioSegmenter().segment(audio, SR, max_chunk_seconds=10.0, overlap_seconds=0.0)

    assert len(chunks) == 2
    assert chunks[0].start_sec == pytest.approx(0.0, abs=0.01)
    assert chunks[0].end_sec == pytest.approx(10.0, abs=0.1)
    assert chunks[1].start_sec == pytest.approx(10.0, abs=0.1)


def test_segment_overlap_produces_correct_start_end_values() -> None:
    """With overlap, chunks must have the correct start and end timestamps."""
    sr = 16000
    audio = np.zeros(sr * 30, dtype=np.float32)  # 30 seconds

    chunks = AudioSegmenter().segment(audio, sr, max_chunk_seconds=10.0, overlap_seconds=2.0)

    # With 10s chunks and 2s overlap, step is 8s
    # Chunk 0: 0–10s, chunk 1: 8–18s, chunk 2: 16–26s, chunk 3: 24–30s (partial)
    assert len(chunks) >= 3
    assert chunks[0].start_sec == pytest.approx(0.0, abs=0.01)
    assert chunks[1].start_sec == pytest.approx(8.0, abs=0.1)
    assert chunks[2].start_sec == pytest.approx(16.0, abs=0.1)

    # No chunk end should exceed audio duration
    duration = len(audio) / sr
    for chunk in chunks:
        assert chunk.end_sec <= duration + 0.01
