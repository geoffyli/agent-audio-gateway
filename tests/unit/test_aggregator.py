"""Tests for ChunkAggregator empty-string filtering."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_audio_gateway.core.aggregation.aggregator import ChunkAggregator
from agent_audio_gateway.core.exceptions import AggregationError


def _make_aggregator(synthesize_response: str = "synthesized") -> tuple[ChunkAggregator, MagicMock]:
    adapter = MagicMock()
    adapter.synthesize.return_value = synthesize_response
    return ChunkAggregator(adapter=adapter), adapter


def test_merge_single_non_empty_returns_directly() -> None:
    """A single non-empty chunk must be returned directly without a synthesis call."""
    agg, adapter = _make_aggregator()

    result = agg.merge(["good result"], task="summarize")

    assert result == "good result"
    adapter.synthesize.assert_not_called()


def test_merge_filters_empty_strings_before_synthesis() -> None:
    """Empty and whitespace-only strings must be filtered before synthesis."""
    agg, adapter = _make_aggregator()

    agg.merge(["first result", "", "   ", "second result"], task="summarize")

    # Synthesize should have been called with only the two non-empty chunks
    call_args = adapter.synthesize.call_args[0][0]
    assert "first result" in call_args
    assert "second result" in call_args
    # Empty entries must not appear as [Chunk N] blocks
    assert "[Chunk 2]\n\n" not in call_args
    assert "[Chunk 3]\n   \n" not in call_args


def test_merge_filters_to_single_non_empty_returns_directly() -> None:
    """If filtering leaves exactly one result, it must be returned without synthesis."""
    agg, adapter = _make_aggregator()

    result = agg.merge(["", "only valid result", "  "], task="summarize")

    assert result == "only valid result"
    adapter.synthesize.assert_not_called()


def test_merge_all_empty_raises_aggregation_error() -> None:
    """All-empty chunk results must raise AggregationError with EMPTY_CHUNKS."""
    agg, adapter = _make_aggregator()

    with pytest.raises(AggregationError) as exc_info:
        agg.merge(["", "   ", ""], task="summarize")

    assert exc_info.value.code == "EMPTY_CHUNKS"
    adapter.synthesize.assert_not_called()


def test_merge_no_chunks_raises_aggregation_error() -> None:
    """An empty list must raise AggregationError with EMPTY_CHUNKS."""
    agg, adapter = _make_aggregator()

    with pytest.raises(AggregationError) as exc_info:
        agg.merge([], task="summarize")

    assert exc_info.value.code == "EMPTY_CHUNKS"
