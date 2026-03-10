from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAudioAdapter(ABC):
    @abstractmethod
    def analyze(self, audio, sr: int, prompt: str) -> str:
        """Run inference on an audio chunk and return raw text output."""
        ...

    @abstractmethod
    def synthesize(self, text: str) -> str:
        """Text-only LLM call — used by the aggregator to merge chunk results."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier."""
        ...

    def close(self) -> None:
        """Release adapter resources."""
        return
