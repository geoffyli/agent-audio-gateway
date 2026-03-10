# JSON Schemas Reference

All responses from both the CLI and local server follow the shapes defined here.

---

## InspectResponse

Returned by `inspect` (CLI) and `POST /inspect` (server).

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

Returned by `analyze`, `ask` (CLI) and `POST /analyze`, `POST /ask` (server).

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
- `input.segmented` — `true` if the file was split into chunks before analysis
- `input.chunk_count` — number of chunks analyzed (1 if not segmented)
- `result.observations` — may be empty `[]` depending on task and model output
- `result.observations[].timestamp` — optional; present when the model infers timing
- `meta.schema` — the `--schema` value passed by the caller, or `null`
- `meta.timing_ms` — stage timings in milliseconds for troubleshooting and tuning

---

## HealthResponse

Returned by `health` (CLI) and `GET /health` (server).

```json
{
  "status": "ok",
  "model": "google/gemini-3.1-flash-lite-preview",
  "version": "0.1.0"
}
```

---

## VersionResponse

Returned by `version` (CLI) and `GET /version` (server).

```json
{
  "version": "0.1.0"
}
```

---

## ErrorResponse

Returned when any command fails. On the CLI, this goes to stdout. On the server, it is returned with an appropriate HTTP status code.

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

### Error codes

| Code | Cause |
|------|-------|
| `FILE_NOT_FOUND` | The specified file path does not exist |
| `NOT_A_FILE` | The path exists but is not a regular file |
| `UNSUPPORTED_FORMAT` | The file extension is not supported |
| `METADATA_READ_ERROR` | Could not extract audio metadata from the file |
| `AUDIO_LOAD_ERROR` | Failed to load or decode the audio |
| `INVALID_CHUNK_PARAMS` | Invalid chunk options (for example overlap >= chunk size) |
| `AUDIO_ENCODE_ERROR` | Failed to encode upload audio payload |
| `INFERENCE_ERROR` | Audio inference failed |
| `SYNTHESIS_ERROR` | Text synthesis call failed |
| `SYNTHESIS_FAILED` | Aggregation merge step failed |
| `EMPTY_CHUNKS` | Aggregation received no chunk results |
| `API_TIMEOUT` | Provider request timed out |
| `API_NETWORK_ERROR` | Provider network request failed |
| `API_HTTP_ERROR` | Provider request failed before a response body was parsed |
| `API_RESPONSE_PARSE_ERROR` | Provider response shape was invalid |
| `API_UNEXPECTED_CONTENT_TYPE` | Provider content type did not match expected text payload |
| `API_ERROR_*` | Provider returned a non-200 API error code |
| `MISSING_API_KEY` | API key missing in config and environment |
| `PROMPT_FILE_NOT_FOUND` | The file given to `--prompt-file` does not exist |
| `CONFIG_NOT_FOUND` | The config file specified via `--config` does not exist |
| `CONFIG_PARSE_ERROR` | The config file contains invalid YAML |
| `CONFIG_LOAD_ERROR` | The config file could not be loaded |
| `INTERNAL_ERROR` | Unexpected runtime error |

---

## Server request bodies

### `POST /inspect`
```json
{ "file_path": "/absolute/path/to/file.wav" }
```

### `POST /analyze`
```json
{
  "file_path": "/absolute/path/to/file.wav",
  "task": "summarize",
  "instruction": null,
  "prompt_file": null,
  "schema": null,
  "options": {
    "segment": true,
    "max_chunk_seconds": 25.0,
    "overlap_seconds": 3.0
  }
}
```

### `POST /ask`
```json
{
  "file_path": "/absolute/path/to/file.wav",
  "question": "What is the main topic discussed?",
  "options": {
    "segment": true,
    "max_chunk_seconds": 25.0,
    "overlap_seconds": 3.0
  }
}
```
