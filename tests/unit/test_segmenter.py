import numpy as np
import pytest

from agent_audio_gateway.core.exceptions import SegmentationError
from agent_audio_gateway.core.segmentation.segmenter import AudioSegmenter


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
    audio = np.zeros(16000, dtype=np.float32)

    with pytest.raises(SegmentationError):
        AudioSegmenter().segment(
            audio=audio,
            sr=16000,
            max_chunk_seconds=max_chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
