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
    "model": "Qwen/Qwen2-Audio-7B-Instruct",
    "schema": null,
    "backend": "qwen2-audio"
  }
}
```

**Field notes:**
- `input.segmented` — `true` if the file was split into chunks before analysis
- `input.chunk_count` — number of chunks analyzed (1 if not segmented)
- `result.observations` — may be empty `[]` depending on task and model output
- `result.observations[].timestamp` — optional; present when the model infers timing
- `meta.schema` — the `--schema` value passed by the caller, or `null`

---

## HealthResponse

Returned by `health` (CLI) and `GET /health` (server).

```json
{
  "status": "ok",
  "model": "Qwen/Qwen2-Audio-7B-Instruct",
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

Returned when any command fails. On the CLI, this goes to stdout when `--json` is active. On the server, it is returned with an appropriate HTTP status code.

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
| `INVALID_CHUNK_PARAMS` | overlap_seconds >= max_chunk_seconds |
| `MODEL_LOAD_ERROR` | The model could not be loaded (check setup) |
| `MISSING_DEPENDENCY` | A required Python package is not installed |
| `INFERENCE_ERROR` | Model inference failed for a chunk |
| `SYNTHESIS_ERROR` | Text-only synthesis for aggregation failed |
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
