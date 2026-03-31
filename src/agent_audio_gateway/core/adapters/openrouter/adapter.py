from __future__ import annotations

import base64
import logging
import os
import random
import time
from typing import Any

import httpx
import numpy as np

from ...exceptions import ConfigError, ModelError
from ..base import BaseAudioAdapter

logger = logging.getLogger(__name__)


class OpenRouterAdapter(BaseAudioAdapter):
    """Adapter for OpenRouter cloud API (OpenAI-compatible endpoint).

    Audio is encoded as base64 WAV and sent as an input_audio content block.
    Text-only synthesis uses the same endpoint with a plain text content block.
    """

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str,
        max_tokens: int,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        write_timeout_seconds: float,
        pool_timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        target_sample_rate_hz: int,
    ):
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._target_sample_rate_hz = target_sample_rate_hz

        # Resolve API key: non-empty config value takes precedence over env var.
        resolved_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not resolved_key:
            raise ConfigError(
                "OpenRouter API key not set. Provide model.api_key in config "
                "or set the OPENROUTER_API_KEY environment variable.",
                code="MISSING_API_KEY",
            )
        if api_key:
            import warnings

            warnings.warn(
                "Setting model.api_key in the config file is discouraged. "
                "Use the OPENROUTER_API_KEY environment variable instead to avoid "
                "accidentally committing credentials.",
                UserWarning,
                stacklevel=3,
            )
        self._api_key = resolved_key

        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/agent-audio-gateway",
                "X-Title": "agent-audio-gateway",
            },
            timeout=httpx.Timeout(
                connect=connect_timeout_seconds,
                read=read_timeout_seconds,
                write=write_timeout_seconds,
                pool=pool_timeout_seconds,
            ),
        )

    # ── Audio conversion ──────────────────────────────────────────────────────

    def _numpy_to_wav_base64(self, audio, sr: int) -> str:
        """Encode a float32 numpy array to a base64 WAV string in-memory."""
        import io

        import soundfile as sf

        buf = io.BytesIO()
        clipped = np.clip(audio, -1.0, 1.0)
        sf.write(buf, clipped, sr, format="WAV", subtype="PCM_16")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    def _resample_for_upload(
        self, audio: np.ndarray, sr: int
    ) -> tuple[np.ndarray, int]:
        target_sr = self._target_sample_rate_hz
        if sr == target_sr:
            return audio, sr

        if len(audio) == 0:
            return audio, target_sr

        duration_sec = len(audio) / sr
        target_samples = max(1, int(round(duration_sec * target_sr)))

        source_positions = np.arange(len(audio), dtype=np.float64)
        target_positions = np.arange(target_samples, dtype=np.float64) * (
            sr / target_sr
        )
        resampled = np.interp(target_positions, source_positions, audio).astype(
            np.float32
        )
        return np.ascontiguousarray(resampled), target_sr

    # ── HTTP helper ───────────────────────────────────────────────────────────

    def _post(self, messages: list[dict], schema: dict[str, Any] | None = None) -> str:
        """POST to /chat/completions and return the text of choices[0].message.content."""
        payload = {
            "model": self._model_id,
            "messages": messages,
            "max_tokens": self._max_tokens,
        }
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "analysis_output",
                    "strict": True,
                    "schema": schema,
                },
            }
            payload["provider"] = {"require_parameters": True}
        attempt = 0

        while True:
            try:
                response = self._client.post("/chat/completions", json=payload)
            except httpx.TimeoutException as e:
                if attempt >= self._max_retries:
                    raise ModelError(
                        f"OpenRouter request timed out: {e}",
                        code="API_TIMEOUT",
                        retryable=True,
                    ) from e
                self._sleep_before_retry(attempt)
                attempt += 1
                continue
            except httpx.NetworkError as e:
                if attempt >= self._max_retries:
                    raise ModelError(
                        f"OpenRouter network error: {e}",
                        code="API_NETWORK_ERROR",
                        retryable=True,
                    ) from e
                self._sleep_before_retry(attempt)
                attempt += 1
                continue
            except httpx.HTTPError as e:
                raise ModelError(
                    f"OpenRouter HTTP error: {e}",
                    code="API_HTTP_ERROR",
                    retryable=False,
                ) from e

            if response.status_code == 200:
                break

            retryable_status = (
                response.status_code == 429 or response.status_code >= 500
            )
            if retryable_status and attempt < self._max_retries:
                self._sleep_before_retry(attempt)
                attempt += 1
                continue

            _raise_for_api_error(response)

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise ModelError(
                f"Unexpected OpenRouter response shape: {e}. Body: {response.text[:500]}",
                code="API_RESPONSE_PARSE_ERROR",
            ) from e

        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )

        if not isinstance(content, str):
            raise ModelError(
                f"OpenRouter returned non-string content: {type(content).__name__}",
                code="API_UNEXPECTED_CONTENT_TYPE",
            )
        return content.strip()

    # ── Public interface ──────────────────────────────────────────────────────

    def analyze(
        self,
        audio,
        sr: int,
        prompt: str,
        schema: dict[str, Any] | None = None,
    ) -> str:
        """Run audio + text inference via OpenRouter and return the response text."""
        logger.debug(
            "analyze: model=%s audio_samples=%d sr=%d",
            self._model_id,
            len(audio),
            sr,
        )
        try:
            normalized_audio, normalized_sr = self._resample_for_upload(audio, sr)
            wav_b64 = self._numpy_to_wav_base64(normalized_audio, normalized_sr)
        except Exception as e:
            raise ModelError(
                f"Failed to encode audio to WAV base64: {e}",
                code="AUDIO_ENCODE_ERROR",
            ) from e

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": wav_b64,
                            "format": "wav",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ]
        try:
            return self._post(messages, schema=schema)
        except ModelError:
            raise
        except Exception as e:
            raise ModelError(f"Inference failed: {e}", code="INFERENCE_ERROR") from e

    def synthesize(self, text: str, schema: dict[str, Any] | None = None) -> str:
        """Text-only call — used by ChunkAggregator to merge chunk results."""
        logger.debug("synthesize: model=%s text_len=%d", self._model_id, len(text))
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": text}],
            }
        ]
        try:
            return self._post(messages, schema=schema)
        except ModelError:
            raise
        except Exception as e:
            raise ModelError(
                f"Text synthesis failed: {e}", code="SYNTHESIS_ERROR"
            ) from e

    @property
    def model_name(self) -> str:
        return self._model_id

    def _sleep_before_retry(self, attempt: int) -> None:
        if self._retry_backoff_seconds <= 0:
            return
        delay = self._retry_backoff_seconds * (2**attempt)
        delay += random.uniform(0.0, 0.1)
        logger.debug(
            "Retrying OpenRouter request in %.2fs (attempt %d)", delay, attempt + 1
        )
        time.sleep(delay)

    def close(self) -> None:
        self._client.close()


# ── Error surfacing helper ────────────────────────────────────────────────────


def _raise_for_api_error(response: httpx.Response) -> None:
    """Parse OpenRouter error body and raise ModelError with a useful message."""
    status = response.status_code
    try:
        body = response.json()
        err = body.get("error", {})
        api_message = err.get("message", response.text[:300])
        api_code = err.get("code", str(status))
    except ValueError:
        api_message = response.text[:300]
        api_code = str(status)

    retryable = status == 429 or status >= 500
    raise ModelError(
        f"OpenRouter API error {status}: {api_message}",
        code=f"API_ERROR_{api_code}",
        retryable=retryable,
    )
