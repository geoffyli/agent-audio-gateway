# Troubleshooting

## The command is not found

```
zsh: command not found: agent-audio-gateway
```

Install the package into your active environment:

```bash
uv pip install -e /path/to/agent-audio-gateway
```

Then either run with `uv run`:

```bash
uv run agent-audio-gateway version
```

Or activate the virtual environment where it is already installed:

```bash
source .venv/bin/activate
agent-audio-gateway version
```

---

## FILE_NOT_FOUND

```json
{"status":"error","error":{"code":"FILE_NOT_FOUND","message":"File not found: ...","retryable":false}}
```

- Verify the file path is correct and absolute.
- Confirm the process has read permission.

---

## UNSUPPORTED_FORMAT

```json
{"status":"error","error":{"code":"UNSUPPORTED_FORMAT","retryable":false}}
```

Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.opus`.

Convert unsupported files first:

```bash
ffmpeg -i input.file output.wav
```

---

## MISSING_API_KEY

```json
{"status":"error","error":{"code":"MISSING_API_KEY","retryable":false}}
```

Provide an API key via config or environment:

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Or set `model.api_key` in your YAML config.

---

## API timeout / network / rate limit errors

Examples:

```json
{"status":"error","error":{"code":"API_TIMEOUT","retryable":true}}
{"status":"error","error":{"code":"API_NETWORK_ERROR","retryable":true}}
{"status":"error","error":{"code":"API_ERROR_429","retryable":true}}
```

- Retry once after a short delay.
- Reduce `analysis.max_parallel_chunks` if rate-limited.
- Lower `model.max_tokens` for shorter responses.
- Check local network and provider status.

---

## API_HTTP_ERROR / API_ERROR_*

```json
{"status":"error","error":{"code":"API_HTTP_ERROR","retryable":false}}
{"status":"error","error":{"code":"API_ERROR_429","retryable":true}}
```

- `API_ERROR_429` and most `API_ERROR_5xx` are retryable; back off and retry once.
- For `API_ERROR_4xx` (except 429), fix request/auth/model settings before retrying.
- Check model id and base URL in config if errors persist.

---

## API_RESPONSE_PARSE_ERROR / API_UNEXPECTED_CONTENT_TYPE

```json
{"status":"error","error":{"code":"API_RESPONSE_PARSE_ERROR","retryable":false}}
{"status":"error","error":{"code":"API_UNEXPECTED_CONTENT_TYPE","retryable":false}}
```

The upstream API response format was not what the runtime expected.

- Capture full response context/logs for diagnosis.
- Verify the configured endpoint is OpenRouter-compatible.
- Retry once; if persistent, treat as provider/compatibility issue.

---

## SCHEMA_INVALID

```json
{"status":"error","error":{"code":"SCHEMA_INVALID","retryable":false}}
```

- `--schema` looked like JSON but was invalid, or it parsed to a non-object value.
- Pass a valid JSON object string.

Example:

```bash
agent-audio-gateway analyze audio.wav --schema '{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}'
```

---

## SCHEMA_VALIDATION_FAILED

```json
{"status":"error","error":{"code":"SCHEMA_VALIDATION_FAILED","retryable":false}}
```

- Structured mode was requested, but model output was not a valid JSON object.
- Retry once, then simplify the schema if needed.

---

## INFERENCE_ERROR

```json
{"status":"error","error":{"code":"INFERENCE_ERROR","retryable":false}}
```

The model failed during inference. Common causes:

- Corrupted or malformed audio — verify the file with `agent-audio-gateway inspect`
- Upstream provider instability
- Unexpected adapter/runtime exception

---

## AUDIO_ENCODE_ERROR

```json
{"status":"error","error":{"code":"AUDIO_ENCODE_ERROR","retryable":false}}
```

The runtime failed to encode decoded audio to WAV/base64 before sending to the API.

- Re-encode the source file (e.g., with ffmpeg) and retry.
- Verify local audio dependencies (`soundfile`, codec support) are installed correctly.

---

## The system feels slow

Most common causes:

1. Repeated CLI cold starts in interactive loops.
2. Large/long audio triggering many chunks.
3. Upstream model latency.

Tips:

- Use `agent-audio-gateway serve` for interactive workflows.
- Inspect `meta.timing_ms` in responses to locate bottlenecks.
- Tune chunking (`--max-chunk-seconds`, `--overlap-seconds`) and parallelism (`analysis.max_parallel_chunks`).

---

## JSON output contains no observations

The `result.observations` array is schema-supported but typically empty in the current runtime. This is normal — the `summary` field contains the primary output.
