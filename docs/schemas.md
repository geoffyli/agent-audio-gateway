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
- `input.segmented` — `true` if the file was split before analysis
- `input.chunk_count` — 1 if not segmented
- `result.observations` — may be empty; depends on task and model output
- `result.observations[].timestamp` — optional; present when the model infers timing
- `meta.schema` — the `--schema` value passed by the caller, or `null`

---

## HealthResponse

```json
{
  "status": "ok",
  "model": "Qwen/Qwen2-Audio-7B-Instruct",
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
| `INVALID_CHUNK_PARAMS` | 4 | `overlap_seconds >= max_chunk_seconds` |
| `MODEL_LOAD_ERROR` | 5 | The model could not be loaded |
| `MISSING_DEPENDENCY` | 5 | A required Python package is not installed |
| `INFERENCE_ERROR` | 5 | Model inference failed |
| `SYNTHESIS_ERROR` | 5 | Text synthesis for aggregation failed |
| `PROMPT_FILE_NOT_FOUND` | 3 | The `--prompt-file` path does not exist |
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
