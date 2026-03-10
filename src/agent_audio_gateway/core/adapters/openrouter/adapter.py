from __future__ import annotations

import base64
import io
import logging
import os

import httpx

from ...exceptions import ConfigError, ModelError
from ..base import BaseAudioAdapter

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)


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
    ):
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens

        # Resolve API key: non-empty config value takes precedence over env var.
        resolved_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not resolved_key:
            raise ConfigError(
                "OpenRouter API key not set. Provide model.api_key in config "
                "or set the OPENROUTER_API_KEY environment variable.",
                code="MISSING_API_KEY",
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
            timeout=_DEFAULT_TIMEOUT,
        )

    # ── Audio conversion ──────────────────────────────────────────────────────

    def _numpy_to_wav_base64(self, audio, sr: int) -> str:
        """Encode a float32 numpy array to a base64 WAV string in-memory."""
        import io
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    # ── HTTP helper ───────────────────────────────────────────────────────────

    def _post(self, messages: list[dict]) -> str:
        """POST to /chat/completions and return the text of choices[0].message.content."""
        payload = {
            "model": self._model_id,
            "messages": messages,
            "max_tokens": self._max_tokens,
        }
        try:
            response = self._client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as e:
            raise ModelError(
                f"OpenRouter request timed out: {e}",
                code="API_TIMEOUT",
                retryable=True,
            ) from e
        except httpx.NetworkError as e:
            raise ModelError(
                f"OpenRouter network error: {e}",
                code="API_NETWORK_ERROR",
                retryable=True,
            ) from e
        except httpx.HTTPError as e:
            raise ModelError(
                f"OpenRouter HTTP error: {e}",
                code="API_HTTP_ERROR",
                retryable=False,
            ) from e

        if response.status_code != 200:
            _raise_for_api_error(response)

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise ModelError(
                f"Unexpected OpenRouter response shape: {e}. Body: {response.text[:500]}",
                code="API_RESPONSE_PARSE_ERROR",
            ) from e

        if not isinstance(content, str):
            raise ModelError(
                f"OpenRouter returned non-string content: {type(content).__name__}",
                code="API_UNEXPECTED_CONTENT_TYPE",
            )
        return content.strip()

    # ── Public interface ──────────────────────────────────────────────────────

    def analyze(self, audio, sr: int, prompt: str) -> str:
        """Run audio + text inference via OpenRouter and return the response text."""
        logger.debug(
            "analyze: model=%s audio_samples=%d sr=%d",
            self._model_id, len(audio), sr,
        )
        try:
            wav_b64 = self._numpy_to_wav_base64(audio, sr)
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
            return self._post(messages)
        except ModelError:
            raise
        except Exception as e:
            raise ModelError(f"Inference failed: {e}", code="INFERENCE_ERROR") from e

    def synthesize(self, text: str) -> str:
        """Text-only call — used by ChunkAggregator to merge chunk results."""
        logger.debug("synthesize: model=%s text_len=%d", self._model_id, len(text))
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": text}],
            }
        ]
        try:
            return self._post(messages)
        except ModelError:
            raise
        except Exception as e:
            raise ModelError(f"Text synthesis failed: {e}", code="SYNTHESIS_ERROR") from e

    @property
    def model_name(self) -> str:
        return self._model_id


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
