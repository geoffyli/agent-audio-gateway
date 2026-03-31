# Local Server API Reference

The local server exposes the same functionality as the CLI through HTTP endpoints.

## Starting the server

```bash
uv run agent-audio-gateway serve                    # http://127.0.0.1:8000
uv run agent-audio-gateway serve --port 8080        # custom port
uv run agent-audio-gateway --config cfg.yaml serve  # with custom config
uv run agent-audio-gateway serve --host 0.0.0.0 --allow-remote  # intentionally expose (unsafe)
```

If `.venv` is activated, you can drop the `uv run` prefix.

The server binds to `127.0.0.1` by default. Binding to non-loopback hosts requires
`--allow-remote` because the server has no built-in authentication.

---

## Endpoints

### `GET /health`

Returns model info and status.

**Response:**
```json
{
  "status": "ok",
  "model": "google/gemini-3.1-flash-lite-preview",
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
  "schema": {
    "type": "object",
    "properties": {
      "summary": {"type": "string"}
    },
    "required": ["summary"]
  },
  "options": {
    "segment": true,
    "max_chunk_seconds": 25.0,
    "overlap_seconds": 3.0
  }
}
```

All fields except `file_path` are optional. `task` defaults to `"summarize"`.

**Field notes:**
- `instruction` — overrides the default analysis prompt; maximum 8192 characters.

Mode behavior:
- Standard mode: omit `schema` (or pass non-object metadata string) for existing text output behavior.
- Structured mode: pass a JSON schema object in `schema`; the model is constrained and parsed JSON is returned in `result.data`.
- Long audio: segmentation/chunking behavior remains enabled in both modes when `options.segment` is true.

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

**Field notes:**
- `question` — maximum 8192 characters.

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
- The server keeps one warm engine instance for all requests
- The server shares its config with the CLI when started via `agent-audio-gateway serve`
- **Request timeout:** Each endpoint has a server-side timeout (default 300s), configurable via `server.request_timeout_seconds`. Requests exceeding this limit return HTTP 500 with code `REQUEST_TIMEOUT`.
- **File access restriction (server mode):** When `server.permitted_audio_dir` is set in config, the `/inspect` and `/analyze` endpoints only allow files within that directory. Paths outside it return HTTP 422 with code `PATH_NOT_PERMITTED`. By default, no restriction is applied.
