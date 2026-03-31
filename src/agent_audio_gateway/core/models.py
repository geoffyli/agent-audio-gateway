from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskName(str, Enum):
    summarize = "summarize"
    describe = "describe"
    classify = "classify"
    extract_observations = "extract-observations"
    qa = "qa"


class AnalysisOptions(BaseModel):
    segment: bool = True
    max_chunk_seconds: float = 25.0
    overlap_seconds: float = 3.0


def _new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:8]}"


# ── Requests ─────────────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_path: str
    task: TaskName = TaskName.summarize
    instruction: str | None = Field(None, max_length=8192)
    prompt_file: str | None = None
    output_schema: dict[str, Any] | str | None = Field(None, alias="schema")
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class AskRequest(BaseModel):
    file_path: str
    question: str = Field(..., max_length=8192)
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class InspectRequest(BaseModel):
    file_path: str


# ── Response building blocks ──────────────────────────────────────────────────


class FileInfo(BaseModel):
    path: str
    format: str
    channels: int
    sample_rate: int
    duration_sec: float
    size_bytes: int


class Observation(BaseModel):
    timestamp: str | None = None
    type: str | None = None
    note: str


class AnalysisResult(BaseModel):
    task: str
    summary: str
    data: dict[str, Any] | None = None
    observations: list[Observation] = Field(
        default_factory=list,
        deprecated="This field is always empty and will be removed in a future version.",
    )


class InputMeta(BaseModel):
    file_path: str
    duration_sec: float
    segmented: bool
    chunk_count: int


# ── Top-level responses ───────────────────────────────────────────────────────


class InspectResponse(BaseModel):
    request_id: str = Field(default_factory=_new_request_id)
    status: str = "ok"
    file: FileInfo


class AnalyzeResponse(BaseModel):
    request_id: str = Field(default_factory=_new_request_id)
    status: str = "ok"
    input: InputMeta
    result: AnalysisResult
    meta: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    model: str
    version: str


class VersionResponse(BaseModel):
    version: str


# ── Error shapes ──────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    request_id: str = Field(default_factory=_new_request_id)
    status: str = "error"
    error: ErrorDetail
