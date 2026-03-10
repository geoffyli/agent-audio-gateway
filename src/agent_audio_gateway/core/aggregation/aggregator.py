from __future__ import annotations

import logging

from ..adapters.base import BaseAudioAdapter
from ..exceptions import AggregationError

logger = logging.getLogger(__name__)


class ChunkAggregator:
    def __init__(self, adapter: BaseAudioAdapter):
        self._adapter = adapter

    def merge(
        self,
        chunk_results: list[str],
        task: str,
        schema: dict | None = None,
    ) -> str:
        """Merge per-chunk analysis results into a single coherent response.

        If there is only one chunk, return it directly.
        Otherwise, send all chunk outputs back through the adapter as a
        text-only synthesis call.
        """
        if not chunk_results:
            raise AggregationError("No chunk results to aggregate", code="EMPTY_CHUNKS")

        if len(chunk_results) == 1:
            return chunk_results[0]

        logger.debug(
            "Aggregating %d chunk results for task '%s'", len(chunk_results), task
        )

        numbered = "\n".join(
            f"[Chunk {i + 1}]\n{result}" for i, result in enumerate(chunk_results)
        )
        prompt = (
            f"The following are sequential analysis results from audio chunks for a '{task}' task. "
            f"Synthesize them into a single coherent, well-structured response. "
            f"Preserve important details and avoid repeating information.\n\n"
            f"{numbered}"
        )

        try:
            return self._adapter.synthesize(prompt, schema=schema)
        except Exception as e:
            raise AggregationError(
                f"Failed to synthesize chunk results: {e}",
                code="SYNTHESIS_FAILED",
            ) from e
