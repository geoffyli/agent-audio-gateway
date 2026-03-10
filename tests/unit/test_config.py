import pytest
from pydantic import ValidationError

from agent_audio_gateway.core.config import GatewayConfig


def test_rejects_invalid_default_chunk_overlap_relation() -> None:
    with pytest.raises(ValidationError):
        GatewayConfig.model_validate(
            {
                "analysis": {
                    "default_max_chunk_seconds": 5.0,
                    "default_overlap_seconds": 5.0,
                }
            }
        )
