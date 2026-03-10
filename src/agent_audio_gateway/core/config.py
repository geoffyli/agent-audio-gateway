from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, model_validator

from .exceptions import ConfigError


class ModelConfig(BaseModel):
    backend: str = "openrouter"
    id: str = "google/gemini-3.1-flash-lite-preview"
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = Field(default=1024, ge=1)
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
    target_sample_rate_hz: int = Field(default=16000, ge=8000)
    max_parallel_chunks: int = Field(default=2, ge=1)

    @model_validator(mode="after")
    def validate_chunk_defaults(self) -> "AnalysisConfig":
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


class CacheConfig(BaseModel):
    enabled: bool = False
    dir: str = "~/.agent-audio-gateway/cache"


class GatewayConfig(BaseModel):
    model: ModelConfig = ModelConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    output: OutputConfig = OutputConfig()
    logging: LoggingConfig = LoggingConfig()
    cache: CacheConfig = CacheConfig()

    @classmethod
    def load(cls, path: Optional[str] = None) -> "GatewayConfig":
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
            raise ConfigError(f"Invalid YAML in config: {e}", code="CONFIG_PARSE_ERROR")
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}", code="CONFIG_LOAD_ERROR")
