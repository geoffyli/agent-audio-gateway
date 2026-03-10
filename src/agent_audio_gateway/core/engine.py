from __future__ import annotations

import logging
import uuid
from pathlib import Path

from .adapters.openrouter.adapter import OpenRouterAdapter
from .aggregation.aggregator import ChunkAggregator
from .config import GatewayConfig
from .exceptions import InputError
from .inspection.inspector import AudioInspector
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResult,
    AskRequest,
    HealthResponse,
    InputMeta,
    InspectResponse,
)
from .preprocessing.preprocessor import AudioPreprocessor
from .segmentation.segmenter import AudioSegmenter

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
        "Classify this audio. Identify the primary content type (e.g. speech, music, ambient noise, "
        "interview, lecture, conversation) and list its key attributes."
    ),
    "extract-observations": (
        "Extract important observations from this audio. For each significant event, speaker turn, "
        "topic, or sound, note what it is and when it occurs (with approximate timestamps if possible)."
    ),
    "qa": (
        "Answer the following question about the audio faithfully based only on what you hear."
    ),
}


class GatewayEngine:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self._inspector = AudioInspector()
        self._preprocessor = AudioPreprocessor()
        self._segmenter = AudioSegmenter()
        self._adapter = OpenRouterAdapter(
            model_id=config.model.id,
            api_key=config.model.api_key,
            base_url=config.model.base_url,
            max_tokens=config.model.max_tokens,
        )
        self._aggregator = ChunkAggregator(adapter=self._adapter)

    # ── Public API ────────────────────────────────────────────────────────────

    def inspect(self, file_path: str) -> InspectResponse:
        file_info = self._inspector.inspect(file_path)
        return InspectResponse(file=file_info)

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        request_id = f"req_{uuid.uuid4().hex[:8]}"

        # Resolve optional prompt file
        prompt_override = request.instruction
        if request.prompt_file and not prompt_override:
            prompt_override = self._load_prompt_file(request.prompt_file)

        # Inspect
        file_info = self._inspector.inspect(request.file_path)

        # Build the inference prompt
        task_key = request.task.value
        prompt = prompt_override or TASK_PROMPTS.get(task_key, TASK_PROMPTS["summarize"])

        # Load + preprocess audio
        audio, sr = self._preprocessor.load(request.file_path)

        # Decide whether to segment
        threshold = self.config.analysis.segment_threshold_seconds
        max_chunk = request.options.max_chunk_seconds
        overlap = request.options.overlap_seconds
        do_segment = (
            request.options.segment
            and self._segmenter.should_segment(file_info.duration_sec, threshold)
        )

        if do_segment:
            chunks = self._segmenter.segment(audio, sr, max_chunk, overlap)
            logger.info(
                "Analyzing %d chunk(s) for task '%s'", len(chunks), task_key
            )
            chunk_results = [
                self._adapter.analyze(chunk.audio, sr, prompt) for chunk in chunks
            ]
            summary = self._aggregator.merge(chunk_results, task_key)
            chunk_count = len(chunks)
        else:
            logger.info("Analyzing single segment for task '%s'", task_key)
            summary = self._adapter.analyze(audio, sr, prompt)
            chunk_count = 1

        return AnalyzeResponse(
            request_id=request_id,
            input=InputMeta(
                file_path=request.file_path,
                duration_sec=file_info.duration_sec,
                segmented=do_segment,
                chunk_count=chunk_count,
            ),
            result=AnalysisResult(task=task_key, summary=summary),
            meta={
                "model": self._adapter.model_name,
                "schema": request.output_schema,
                "backend": self.config.model.backend,
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

        return HealthResponse(
            model=self._adapter.model_name,
            version=__version__,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_prompt_file(prompt_file: str) -> str:
        path = Path(prompt_file)
        if not path.exists():
            raise InputError(
                f"Prompt file not found: {prompt_file}",
                code="PROMPT_FILE_NOT_FOUND",
            )
        return path.read_text().strip()
