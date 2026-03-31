from __future__ import annotations

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .adapters.openrouter.adapter import OpenRouterAdapter
from .aggregation.aggregator import ChunkAggregator
from .config import GatewayConfig
from .exceptions import InputError, ModelError
from .inspection.inspector import AudioInspector
from .models import (
    AnalysisResult,
    AnalyzeRequest,
    AnalyzeResponse,
    AskRequest,
    HealthResponse,
    InputMeta,
    InspectResponse,
)
from .preprocessing.preprocessor import AudioPreprocessor
from .segmentation.segmenter import AudioChunk, AudioSegmenter

logger = logging.getLogger(__name__)

TASK_PROMPTS: dict[str, str] = {
    "summarize": (
        "Summarize the content of this audio. Include major topics, any speakers present, "
        "key points, and the overall structure of the recording."
    ),
    "describe": (
        "Describe what you hear in this audio in detail. Include speech, environmental sounds, "
        "music, emotional tone, and any notable events or changes."
    ),
    "classify": (
        "Classify this audio. Identify the primary content type "
        "(e.g. speech, music, ambient noise, interview, lecture, conversation) "
        "and list its key attributes."
    ),
    "extract-observations": (
        "Extract important observations from this audio. For each significant event, "
        "speaker turn, topic, or sound, note what it is and when it occurs "
        "(with approximate timestamps if possible)."
    ),
    "qa": (
        "Answer the following question about the audio faithfully based only on what you hear."
    ),
}


class GatewayEngine:
    def __init__(self, config: GatewayConfig):
        self.config = config
        permitted = (
            Path(config.server.permitted_audio_dir)
            if config.server.permitted_audio_dir
            else None
        )
        self._inspector = AudioInspector(permitted_base=permitted)
        self._preprocessor = AudioPreprocessor()
        self._segmenter = AudioSegmenter()
        self._adapter: OpenRouterAdapter | None = None
        self._aggregator: ChunkAggregator | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def inspect(self, file_path: str) -> InspectResponse:
        file_info = self._inspector.inspect(file_path)
        return InspectResponse(file=file_info)

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        total_start = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        adapter = self._ensure_adapter()

        # Resolve optional prompt file
        prompt_override = request.instruction
        if request.prompt_file and not prompt_override:
            prompt_override = self._load_prompt_file(request.prompt_file)

        # Inspect
        inspect_start = time.perf_counter()
        file_info = self._inspector.inspect(request.file_path)
        inspect_elapsed = (time.perf_counter() - inspect_start) * 1000

        # Build the inference prompt
        task_key = request.task.value
        prompt = prompt_override or TASK_PROMPTS.get(
            task_key, TASK_PROMPTS["summarize"]
        )
        structured_schema = (
            request.output_schema if isinstance(request.output_schema, dict) else None
        )
        structured_mode = structured_schema is not None

        # Load + preprocess audio
        preprocess_start = time.perf_counter()
        audio, sr = self._preprocessor.load(request.file_path)
        preprocess_elapsed = (time.perf_counter() - preprocess_start) * 1000

        # Decide whether to segment
        threshold = self.config.analysis.segment_threshold_seconds
        max_chunk = request.options.max_chunk_seconds
        overlap = request.options.overlap_seconds
        do_segment = request.options.segment and self._segmenter.should_segment(
            file_info.duration_sec, threshold
        )

        if do_segment:
            segment_start = time.perf_counter()
            chunks = self._segmenter.segment(audio, sr, max_chunk, overlap)
            segment_elapsed = (time.perf_counter() - segment_start) * 1000
            logger.info("Analyzing %d chunk(s) for task '%s'", len(chunks), task_key)

            inference_start = time.perf_counter()
            max_workers = min(self.config.analysis.max_parallel_chunks, len(chunks))
            if max_workers <= 1:
                chunk_results = [
                    adapter.analyze(chunk.audio, sr, prompt, schema=structured_schema)
                    for chunk in chunks
                ]
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    indexed_futures = {
                        executor.submit(
                            self._analyze_chunk, chunk, sr, prompt, structured_schema
                        ): i
                        for i, chunk in enumerate(chunks)
                    }
                    chunk_results = [""] * len(chunks)
                    try:
                        for future in as_completed(indexed_futures):
                            chunk_index = indexed_futures[future]
                            chunk_results[chunk_index] = future.result()
                    except Exception:
                        # Cancel futures that have not yet started. Futures already
                        # executing a blocking httpx call cannot be interrupted; those
                        # API calls will run to completion but results will be discarded.
                        cancelled = sum(1 for f in indexed_futures if f.cancel())
                        logger.warning(
                            "Chunk analysis failed; cancelled %d pending future(s); "
                            "%d may still be running in background.",
                            cancelled,
                            len(indexed_futures) - cancelled,
                        )
                        raise
            inference_elapsed = (time.perf_counter() - inference_start) * 1000

            aggregate_start = time.perf_counter()
            summary = self._ensure_aggregator().merge(
                chunk_results,
                task_key,
                schema=structured_schema,
            )
            aggregate_elapsed = (time.perf_counter() - aggregate_start) * 1000
            chunk_count = len(chunks)
        else:
            segment_elapsed = 0.0
            logger.info("Analyzing single segment for task '%s'", task_key)

            inference_start = time.perf_counter()
            summary = adapter.analyze(audio, sr, prompt, schema=structured_schema)
            inference_elapsed = (time.perf_counter() - inference_start) * 1000

            aggregate_elapsed = 0.0
            max_workers = 1
            chunk_count = 1

        result_data = None
        if structured_mode:
            try:
                parsed = json.loads(summary)
            except json.JSONDecodeError as e:
                raise ModelError(
                    f"Structured output was not valid JSON: {e}",
                    code="SCHEMA_VALIDATION_FAILED",
                ) from e
            if not isinstance(parsed, dict):
                raise ModelError(
                    "Structured output must be a JSON object.",
                    code="SCHEMA_VALIDATION_FAILED",
                )
            result_data = parsed

        total_elapsed = (time.perf_counter() - total_start) * 1000

        return AnalyzeResponse(
            request_id=request_id,
            input=InputMeta(
                file_path=request.file_path,
                duration_sec=file_info.duration_sec,
                segmented=do_segment,
                chunk_count=chunk_count,
            ),
            result=AnalysisResult(task=task_key, summary=summary, data=result_data),
            meta={
                "model": adapter.model_name,
                "schema": request.output_schema,
                "backend": self.config.model.backend,
                "timing_ms": {
                    "inspect": round(inspect_elapsed, 1),
                    "preprocess": round(preprocess_elapsed, 1),
                    "segment": round(segment_elapsed, 1),
                    "inference": round(inference_elapsed, 1),
                    "aggregate": round(aggregate_elapsed, 1),
                    "total": round(total_elapsed, 1),
                },
                "parallel_chunks": max_workers,
                "target_sample_rate_hz": self.config.analysis.target_sample_rate_hz,
            },
        )

    def ask(self, request: AskRequest) -> AnalyzeResponse:
        """Answer a question about an audio file."""
        analyze_request = AnalyzeRequest(
            file_path=request.file_path,
            task="qa",
            instruction=f"{TASK_PROMPTS['qa']} Question: {request.question}",
            options=request.options,
        )
        return self.analyze(analyze_request)

    def health(self) -> HealthResponse:
        from agent_audio_gateway import __version__

        model_name = (
            self._adapter.model_name
            if self._adapter is not None
            else self.config.model.id
        )
        return HealthResponse(
            model=model_name,
            version=__version__,
        )

    def close(self) -> None:
        if self._adapter is None:
            return
        self._adapter.close()
        self._adapter = None
        self._aggregator = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_prompt_file(prompt_file: str) -> str:
        path = Path(prompt_file)
        if not path.exists():
            raise InputError(
                f"Prompt file not found: {prompt_file}",
                code="PROMPT_FILE_NOT_FOUND",
            )
        if not path.is_file():
            raise InputError(
                f"Prompt path is not a file: {prompt_file}",
                code="NOT_A_FILE",
            )
        try:
            return path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as e:
            raise InputError(
                f"Failed to read prompt file: {e}",
                code="PROMPT_FILE_READ_ERROR",
            ) from e

    def _analyze_chunk(
        self,
        chunk: AudioChunk,
        sr: int,
        prompt: str,
        schema: dict | None = None,
    ) -> str:
        return self._ensure_adapter().analyze(chunk.audio, sr, prompt, schema=schema)

    def _ensure_adapter(self) -> OpenRouterAdapter:
        if self._adapter is not None:
            return self._adapter

        config = self.config
        self._adapter = OpenRouterAdapter(
            model_id=config.model.id,
            api_key=config.model.api_key,
            base_url=config.model.base_url,
            max_tokens=config.model.max_tokens,
            connect_timeout_seconds=config.model.connect_timeout_seconds,
            read_timeout_seconds=config.model.read_timeout_seconds,
            write_timeout_seconds=config.model.write_timeout_seconds,
            pool_timeout_seconds=config.model.pool_timeout_seconds,
            max_retries=config.model.max_retries,
            retry_backoff_seconds=config.model.retry_backoff_seconds,
            target_sample_rate_hz=config.analysis.target_sample_rate_hz,
        )
        return self._adapter

    def _ensure_aggregator(self) -> ChunkAggregator:
        if self._aggregator is None:
            self._aggregator = ChunkAggregator(adapter=self._ensure_adapter())
        return self._aggregator
