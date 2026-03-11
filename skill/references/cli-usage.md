# CLI Usage Reference

## Global Options

```
agent-audio-gateway [OPTIONS] COMMAND [ARGS]...

Options:
  --config PATH   Path to a YAML config file.
                  Also readable from env: AGENT_AUDIO_GATEWAY_CONFIG
```

Note: JSON is always emitted by default for CLI responses. There is no `--json` flag; use `--pretty` for formatted output.

---

## Commands

### `inspect FILE_PATH`
Inspect an audio file and return its metadata.

```bash
agent-audio-gateway inspect /path/to/file.wav
agent-audio-gateway inspect /path/to/file.wav --pretty
```

**Options:**
- `--pretty` — pretty-print JSON output

**Output:** `InspectResponse` — see [json-schemas.md](json-schemas.md)

---

### `analyze FILE_PATH`
Analyze an audio file using a named task.

```bash
agent-audio-gateway analyze /path/to/file.wav --task summarize
agent-audio-gateway analyze /path/to/file.wav --task extract-observations --pretty
agent-audio-gateway analyze /path/to/file.wav --instruction "Focus on the speaker's tone."
agent-audio-gateway analyze /path/to/file.wav --max-chunk-seconds 20 --overlap-seconds 2
agent-audio-gateway analyze /path/to/file.wav --schema '{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}'
```

**Options:**
- `--task TEXT` — task name: `summarize` | `describe` | `classify` | `extract-observations` | `qa` (default: `summarize`)
- `--instruction TEXT` — custom prompt that overrides the default task prompt
- `--prompt-file PATH` — path to a text file containing the custom prompt
- `--schema TEXT` — if JSON object string, enables structured mode; otherwise treated as informational metadata
- `--max-chunk-seconds N` — override max chunk duration in seconds
- `--overlap-seconds N` — override chunk overlap in seconds
- `--no-segment` — disable automatic segmentation
- `--pretty` — pretty-print JSON output

**Output:** `AnalyzeResponse` — see [json-schemas.md](json-schemas.md)

Mode behavior:
- Standard mode: no schema object; output is text-first in `result.summary`.
- Structured mode: schema object provided; parsed object is returned in `result.data`.

Long-audio chunking applies in both modes unless `--no-segment` is set.

---

### `ask FILE_PATH --question TEXT`
Ask a specific question about an audio file.

```bash
agent-audio-gateway ask /path/to/file.wav --question "What topics are discussed?"
agent-audio-gateway ask /path/to/file.wav --question "How many speakers are there?" --pretty
```

**Options:**
- `--question TEXT` *(required)* — the question to answer
- `--max-chunk-seconds N` — override max chunk duration in seconds
- `--overlap-seconds N` — override chunk overlap in seconds
- `--no-segment` — disable automatic segmentation
- `--pretty` — pretty-print JSON output

**Output:** `AnalyzeResponse` with `result.task = "qa"` — see [json-schemas.md](json-schemas.md)

---

### `health`
Return health and model information.

```bash
agent-audio-gateway health
agent-audio-gateway health --pretty
```

**Output:** `HealthResponse`

---

### `version`
Print the current version.

```bash
agent-audio-gateway version
```

**Output:** `{"version": "0.1.0"}`

---

### `serve`
Start the local HTTP server (default: `http://127.0.0.1:8000`).

```bash
agent-audio-gateway serve
agent-audio-gateway serve --host 127.0.0.1 --port 8080
agent-audio-gateway serve --host 0.0.0.0 --allow-remote  # intentionally expose (unsafe)
agent-audio-gateway serve --reload   # development mode
```

**Options:**
- `--host TEXT` — bind host (default: `127.0.0.1`)
- `--port INT` — bind port (default: `8000`)
- `--allow-remote` — required for non-loopback host binding
- `--reload` — enable auto-reload for development

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Invalid arguments (Click usage error) |
| `3` | File or input error (file not found, unsupported format) |
| `4` | Processing error (preprocessing, segmentation, aggregation) |
| `5` | Model inference error |
| `6` | Internal runtime or configuration error |
