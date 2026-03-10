from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

from .exceptions import ConfigError


class ModelConfig(BaseModel):
    backend: str = "openrouter"
    id: str = "google/gemini-2.0-flash-001"
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 1024


class AnalysisConfig(BaseModel):
    default_max_chunk_seconds: float = 25.0
    default_overlap_seconds: float = 3.0
    segment_threshold_seconds: float = 30.0


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
