from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from .exceptions import ConfigError


class ModelConfig(BaseModel):
    backend: str = "openrouter"
    id: str = "google/gemini-3.1-flash-lite-preview"
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    connect_timeout_seconds: float = Field(default=10.0, gt=0)
    read_timeout_seconds: float = Field(default=120.0, gt=0)
    write_timeout_seconds: float = Field(default=30.0, gt=0)
    pool_timeout_seconds: float = Field(default=10.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=0.75, ge=0)


class AnalysisConfig(BaseModel):
    default_max_chunk_seconds: float = Field(default=25.0, gt=0)
    default_overlap_seconds: float = Field(default=3.0, ge=0)
    segment_threshold_seconds: float = Field(default=30.0, ge=0)
    target_sample_rate_hz: int = Field(default=16000, ge=8000, le=48000)
    max_parallel_chunks: int = Field(default=2, ge=1, le=32)

    @model_validator(mode="after")
    def validate_chunk_defaults(self) -> AnalysisConfig:
        if self.default_overlap_seconds >= self.default_max_chunk_seconds:
            raise ValueError(
                "analysis.default_overlap_seconds must be less than "
                "analysis.default_max_chunk_seconds"
            )
        return self


class OutputConfig(BaseModel):
    default_json: bool = True


class LoggingConfig(BaseModel):
    level: str = "info"


class ServerConfig(BaseModel):
    permitted_audio_dir: str | None = None
    request_timeout_seconds: float = Field(default=300.0, gt=0)


class GatewayConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    @classmethod
    def load(cls, path: str | None = None) -> GatewayConfig:
        if path is None:
            return cls()
        config_path = Path(path)
        if not config_path.exists():
            raise ConfigError(
                f"Config file not found: {path}",
                code="CONFIG_NOT_FOUND",
            )
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
            return cls.model_validate(data or {})
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config: {e}", code="CONFIG_PARSE_ERROR") from e
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}", code="CONFIG_LOAD_ERROR") from e
