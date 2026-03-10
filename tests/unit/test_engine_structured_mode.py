import numpy as np
import pytest

from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.engine import GatewayEngine
from agent_audio_gateway.core.exceptions import ModelError
from agent_audio_gateway.core.models import AnalysisOptions, AnalyzeRequest, FileInfo


class _FakeInspector:
    def __init__(self, duration_sec: float = 1.0):
        self.duration_sec = duration_sec

    def inspect(self, file_path: str) -> FileInfo:
        return FileInfo(
            path=file_path,
            format="wav",
            channels=1,
            sample_rate=16000,
            duration_sec=self.duration_sec,
            size_bytes=128,
        )


class _FakePreprocessor:
    def __init__(self, sample_count: int = 1600):
        self.sample_count = sample_count

    def load(self, _file_path: str):
        return np.zeros(self.sample_count, dtype=np.float32), 16000


class _FakeAdapter:
    model_name = "fake/model"

    def __init__(self, response: str):
        self.response = response
        self.last_schema = None
        self.last_synthesize_schema = None

    def analyze(self, _audio, _sr: int, _prompt: str, schema=None) -> str:
        self.last_schema = schema
        return self.response

    def synthesize(self, _text: str, schema=None) -> str:
        self.last_synthesize_schema = schema
        return self.response


def _make_engine_with_adapter(
    adapter: _FakeAdapter,
    *,
    duration_sec: float = 1.0,
    sample_count: int = 1600,
) -> GatewayEngine:
    engine = GatewayEngine(GatewayConfig())
    engine._inspector = _FakeInspector(duration_sec=duration_sec)
    engine._preprocessor = _FakePreprocessor(sample_count=sample_count)
    engine._ensure_adapter = lambda: adapter
    return engine


def test_analyze_structured_mode_parses_json_into_result_data() -> None:
    adapter = _FakeAdapter('{"title":"Quarterly update","score":7}')
    engine = _make_engine_with_adapter(adapter)
    schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}, "score": {"type": "number"}},
    }

    response = engine.analyze(
        AnalyzeRequest(
            file_path="audio.wav",
            output_schema=schema,
            options=AnalysisOptions(segment=False),
        )
    )

    assert adapter.last_schema == schema
    assert response.result.data == {"title": "Quarterly update", "score": 7}


def test_analyze_structured_mode_raises_when_model_output_not_json() -> None:
    engine = _make_engine_with_adapter(_FakeAdapter("not-json"))

    with pytest.raises(ModelError) as exc_info:
        engine.analyze(
            AnalyzeRequest(
                file_path="audio.wav",
                output_schema={"type": "object"},
                options=AnalysisOptions(segment=False),
            )
        )

    assert exc_info.value.code == "SCHEMA_VALIDATION_FAILED"


def test_analyze_request_accepts_schema_object_alias() -> None:
    request = AnalyzeRequest.model_validate(
        {
            "file_path": "audio.wav",
            "schema": {"type": "object", "properties": {"name": {"type": "string"}}},
        }
    )

    assert isinstance(request.output_schema, dict)
    assert request.output_schema["type"] == "object"


def test_analyze_structured_mode_segments_and_merges_with_schema() -> None:
    adapter = _FakeAdapter('{"summary":"ok"}')
    engine = _make_engine_with_adapter(
        adapter,
        duration_sec=120.0,
        sample_count=16000 * 120,
    )
    schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    }

    response = engine.analyze(
        AnalyzeRequest(
            file_path="audio.wav",
            output_schema=schema,
            options=AnalysisOptions(
                segment=True,
                max_chunk_seconds=25.0,
                overlap_seconds=3.0,
            ),
        )
    )

    assert response.input.segmented is True
    assert response.input.chunk_count > 1
    assert adapter.last_synthesize_schema == schema
    assert response.result.data == {"summary": "ok"}
