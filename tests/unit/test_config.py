import io

import pytest
import yaml
from pydantic import ValidationError

from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.models import AnalyzeRequest, AskRequest


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


def test_max_tokens_upper_bound_rejected() -> None:
    """max_tokens above 32768 must be rejected."""
    with pytest.raises(ValidationError):
        GatewayConfig.model_validate({"model": {"max_tokens": 100000}})


def test_target_sample_rate_upper_bound_rejected() -> None:
    """target_sample_rate_hz above 48000 must be rejected."""
    with pytest.raises(ValidationError):
        GatewayConfig.model_validate({"analysis": {"target_sample_rate_hz": 96000}})


def test_max_parallel_chunks_upper_bound_rejected() -> None:
    """max_parallel_chunks above 32 must be rejected."""
    with pytest.raises(ValidationError):
        GatewayConfig.model_validate({"analysis": {"max_parallel_chunks": 100}})


def test_cache_key_in_yaml_loads_without_error() -> None:
    """A YAML config containing a 'cache' key must load silently (unknown fields ignored)."""
    yaml_text = """
model:
  api_key: "test-key"
cache:
  enabled: true
  dir: /tmp/cache
"""
    data = yaml.safe_load(io.StringIO(yaml_text))
    # Should not raise — Pydantic ignores unknown fields by default
    config = GatewayConfig.model_validate(data)
    assert config.model.api_key == "test-key"


def test_server_config_defaults() -> None:
    """ServerConfig defaults must be sane out-of-the-box."""
    config = GatewayConfig()
    assert config.server.permitted_audio_dir is None
    assert config.server.request_timeout_seconds == 300.0


def test_analyze_request_instruction_too_long_rejected() -> None:
    """instruction exceeding 8192 characters must be rejected."""
    with pytest.raises(ValidationError):
        AnalyzeRequest(file_path="audio.wav", instruction="x" * 8193)


def test_analyze_request_instruction_at_limit_accepted() -> None:
    """instruction at exactly 8192 characters must be accepted."""
    req = AnalyzeRequest(file_path="audio.wav", instruction="x" * 8192)
    assert len(req.instruction) == 8192


def test_ask_request_question_too_long_rejected() -> None:
    """question exceeding 8192 characters must be rejected."""
    with pytest.raises(ValidationError):
        AskRequest(file_path="audio.wav", question="x" * 8193)


def test_ask_request_question_at_limit_accepted() -> None:
    """question at exactly 8192 characters must be accepted."""
    req = AskRequest(file_path="audio.wav", question="x" * 8192)
    assert len(req.question) == 8192
