# JSON Schemas

All CLI output and server responses follow the shapes defined here.

---

## InspectResponse

```json
{
  "request_id": "req_a1b2c3d4",
  "status": "ok",
  "file": {
    "path": "/absolute/path/to/file.wav",
    "format": "wav",
    "channels": 1,
    "sample_rate": 16000,
    "duration_sec": 95.7,
    "size_bytes": 3055221
  }
}
```

---

## AnalyzeResponse

Returned by `analyze`, `ask`, `POST /analyze`, and `POST /ask`.

```json
{
  "request_id": "req_a1b2c3d4",
  "status": "ok",
  "input": {
    "file_path": "/absolute/path/to/file.wav",
    "duration_sec": 83.2,
    "segmented": true,
    "chunk_count": 4
  },
  "result": {
    "task": "summarize",
    "summary": "A speaker introduces a topic, followed by a Q&A session.",
    "data": null,
    "observations": [
      {
        "timestamp": "00:00-00:18",
        "type": "speech",
        "note": "The speaker opens with an introduction."
      }
    ]
  },
  "meta": {
    "model": "google/gemini-3.1-flash-lite-preview",
    "schema": null,
    "backend": "openrouter",
    "parallel_chunks": 2,
    "target_sample_rate_hz": 16000,
    "timing_ms": {
      "inspect": 2.4,
      "preprocess": 34.7,
      "segment": 0.9,
      "inference": 842.1,
      "aggregate": 104.8,
      "total": 985.6
    }
  }
}
```

**Field notes:**
- `input.segmented` — `true` if the file was split before analysis
- `input.chunk_count` — 1 if not segmented
- `result.summary` — text output in standard mode; in structured mode, contains the raw model JSON text
- `result.data` — parsed JSON object in structured mode; `null` in standard mode
- `result.observations` — may be empty; depends on task and model output
- `result.observations[].timestamp` — optional; present when the model infers timing
- `meta.schema` — caller schema metadata or schema object (`null` when not provided)
- `meta.timing_ms` — stage timings in milliseconds for troubleshooting and tuning

---

## HealthResponse

```json
{
  "status": "ok",
  "model": "google/gemini-3.1-flash-lite-preview",
  "version": "0.1.0"
}
```

---

## ErrorResponse

Returned on failure. On the CLI, written to stdout. On the server, returned with an HTTP error status.

```json
{
  "status": "error",
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "File not found: /path/to/missing.wav",
    "retryable": false
  }
}
```

---

## Error codes

| Code | Exit code | Cause |
|------|-----------|-------|
| `FILE_NOT_FOUND` | 3 | The specified file path does not exist |
| `NOT_A_FILE` | 3 | The path exists but is not a regular file |
| `UNSUPPORTED_FORMAT` | 3 | The file extension is not supported |
| `METADATA_READ_ERROR` | 3 | Could not extract audio metadata |
| `AUDIO_LOAD_ERROR` | 4 | Failed to load or decode the audio |
| `INVALID_CHUNK_PARAMS` | 4 | Invalid chunk options (for example overlap >= chunk size) |
| `AUDIO_ENCODE_ERROR` | 5 | Failed to encode upload audio payload |
| `INFERENCE_ERROR` | 5 | Audio inference failed |
| `SYNTHESIS_ERROR` | 5 | Text synthesis call failed |
| `SYNTHESIS_FAILED` | 4 | Aggregation merge step failed |
| `EMPTY_CHUNKS` | 4 | Aggregation received no chunk results |
| `API_TIMEOUT` | 5 | Provider request timed out |
| `API_NETWORK_ERROR` | 5 | Provider network request failed |
| `API_HTTP_ERROR` | 5 | Provider request failed before a response body was parsed |
| `API_RESPONSE_PARSE_ERROR` | 5 | Provider response shape was invalid |
| `API_UNEXPECTED_CONTENT_TYPE` | 5 | Provider content type did not match expected text payload |
| `SCHEMA_INVALID` | 3 | CLI `--schema` looked like JSON but was invalid, or was not a JSON object |
| `SCHEMA_VALIDATION_FAILED` | 5 | Structured mode model output was not valid JSON object |
| `API_ERROR_*` | 5 | Provider returned a non-200 API error code |
| `MISSING_API_KEY` | 6 | API key missing in config and environment |
| `PROMPT_FILE_NOT_FOUND` | 3 | The `--prompt-file` path does not exist |
| `PROMPT_FILE_READ_ERROR` | 3 | The `--prompt-file` path could not be read as UTF-8 text |
| `CONFIG_NOT_FOUND` | 6 | The `--config` file does not exist |
| `CONFIG_PARSE_ERROR` | 6 | The config file contains invalid YAML |
| `CONFIG_LOAD_ERROR` | 6 | The config file could not be loaded |
| `INTERNAL_ERROR` | 6 | Unexpected runtime error |

---

## Supported audio formats

`.wav` `.mp3` `.flac` `.ogg` `.m4a` `.aac` `.opus`

---

## Task vocabulary

| Task | Description |
|------|-------------|
| `summarize` | High-level summary of content |
| `describe` | Detailed description including sounds, tone, structure |
| `classify` | Content type classification |
| `extract-observations` | Timestamped observations and events |
| `qa` | Question answering (used by `ask` command) |
