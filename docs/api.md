# Local Server API Reference

The local server exposes the same functionality as the CLI through HTTP endpoints.

## Starting the server

```bash
agent-audio-gateway serve                    # http://127.0.0.1:8000
agent-audio-gateway serve --port 8080        # custom port
agent-audio-gateway --config cfg.yaml serve  # with custom config
```

The server binds to `127.0.0.1` only.

---

## Endpoints

### `GET /health`

Returns model info and status.

**Response:**
```json
{
  "status": "ok",
  "model": "Qwen/Qwen2-Audio-7B-Instruct",
  "version": "0.1.0"
}
```

---

### `GET /version`

Returns the current version.

**Response:**
```json
{"version": "0.1.0"}
```

---

### `POST /inspect`

Inspect an audio file and return its metadata.

**Request body:**
```json
{"file_path": "/absolute/path/to/file.wav"}
```

**Response:** [`InspectResponse`](schemas.md#inspectresponse)

**Error HTTP codes:** `422` for input errors (file not found, unsupported format)

---

### `POST /analyze`

Analyze an audio file using a named task.

**Request body:**
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

All fields except `file_path` are optional. `task` defaults to `"summarize"`.

**Response:** [`AnalyzeResponse`](schemas.md#analyzeresponse)

**Error HTTP codes:** `422` for input errors, `503` for model errors, `500` for internal errors

---

### `POST /ask`

Answer a question about an audio file.

**Request body:**
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

**Response:** [`AnalyzeResponse`](schemas.md#analyzeresponse) with `result.task = "qa"`

---

## Error response shape

All errors follow this shape:

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

See [schemas.md](schemas.md#errorcodes) for the full list of error codes.

---

## Example: curl

```bash
# Health check
curl http://127.0.0.1:8000/health

# Inspect a file
curl -X POST http://127.0.0.1:8000/inspect \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/file.wav"}'

# Analyze
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/file.wav",
    "task": "summarize",
    "options": {"segment": true}
  }'

# Ask a question
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/file.wav",
    "question": "How many speakers are there?"
  }'
```

---

## Notes

- Inference runs on the server's thread pool — requests are non-blocking at the HTTP layer
- The model is lazy-loaded on the first inference request
- The server shares its config with the CLI when started via `agent-audio-gateway serve`
