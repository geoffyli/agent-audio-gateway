# CLI Reference

## Invocation modes

Examples in this document use `agent-audio-gateway ...` for readability.

- If the executable is already on your shell `PATH`, run commands directly.
- If you installed with `uv pip install -e .` and did not activate `.venv`, prefix commands with `uv run`.

Equivalent examples:

```bash
agent-audio-gateway health --pretty
uv run agent-audio-gateway health --pretty
```

## Design principles

- Predictable, strict argument handling
- Machine-friendly stdout (JSON only)
- Logs and diagnostics on stderr
- Deterministic exit codes
- Prefer `serve` for interactive agent loops to avoid per-command process cold starts

---

## Global options

```
agent-audio-gateway [OPTIONS] COMMAND [ARGS]...

Options:
  --config PATH   Path to a YAML config file.
                  Env: AGENT_AUDIO_GATEWAY_CONFIG
  --help          Show this message and exit.
```

---

## `inspect`

Inspect an audio file and return its metadata as JSON.

```bash
agent-audio-gateway inspect FILE_PATH [--pretty]
```

Use `inspect` when you need to confirm file properties (duration, format, sample rate) before deciding how to analyze it.

**Output:** [`InspectResponse`](schemas.md#inspectresponse)

---

## `analyze`

Analyze an audio file using a named task.

```bash
agent-audio-gateway analyze FILE_PATH [OPTIONS]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--task TEXT` | `summarize` | Task: `summarize`, `describe`, `classify`, `extract-observations`, `qa` |
| `--instruction TEXT` | — | Custom prompt override |
| `--prompt-file PATH` | — | Load custom prompt from a text file |
| `--schema TEXT` | — | Structured mode if JSON object string; otherwise kept as informational metadata |
| `--max-chunk-seconds N` | from config | Override max chunk duration |
| `--overlap-seconds N` | from config | Override chunk overlap |
| `--no-segment` | — | Disable chunking; analyze as a single unit |
| `--pretty` | — | Pretty-print JSON output |

**Examples:**

```bash
# Summarize
agent-audio-gateway analyze recording.wav --task summarize

# Extract timestamped observations
agent-audio-gateway analyze meeting.wav --task extract-observations --pretty

# Custom instruction
agent-audio-gateway analyze speech.wav --instruction "Identify the speaker's main argument."

# Disable chunking for a short file
agent-audio-gateway analyze short.wav --task describe --no-segment

# Structured mode (JSON schema string)
agent-audio-gateway analyze call.wav --schema '{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}'

# Use a config file with custom chunking
agent-audio-gateway --config my-config.yaml analyze long.wav --task summarize
```

**Output:** [`AnalyzeResponse`](schemas.md#analyzeresponse)

Mode behavior:
- Standard mode: no schema object provided; returns normal text in `result.summary`.
- Structured mode: schema JSON object provided via `--schema`; returns parsed object in `result.data`.
- Long audio: segmentation/chunking still applies in both modes unless `--no-segment` is set.

---

## `ask`

Answer a specific question about an audio file.

```bash
agent-audio-gateway ask FILE_PATH --question TEXT [OPTIONS]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--question TEXT` | *(required)* | The question to answer |
| `--max-chunk-seconds N` | from config | Override max chunk duration |
| `--overlap-seconds N` | from config | Override chunk overlap |
| `--no-segment` | — | Disable chunking |
| `--pretty` | — | Pretty-print JSON output |

**Examples:**

```bash
agent-audio-gateway ask meeting.wav --question "What decisions were made?"
agent-audio-gateway ask lecture.wav --question "What is the main topic?" --pretty
```

**Output:** [`AnalyzeResponse`](schemas.md#analyzeresponse) with `result.task = "qa"`

---

## `health`

Return health and model information.

```bash
agent-audio-gateway health [--pretty]
```

**Output:** [`HealthResponse`](schemas.md#healthresponse)

---

## `version`

Print the current version as JSON.

```bash
agent-audio-gateway version
```

**Output:** `{"version": "0.1.0"}`

---

## `serve`

Start the local HTTP server.

```bash
agent-audio-gateway serve [--host HOST] [--port PORT] [--allow-remote] [--reload]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--host TEXT` | `127.0.0.1` | Bind host |
| `--port INT` | `8000` | Bind port |
| `--allow-remote` | — | Required to bind non-loopback hosts; use only on trusted networks |
| `--reload` | — | Enable auto-reload (development only) |

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Invalid arguments |
| `3` | File or input error |
| `4` | Processing error (preprocessing, segmentation, aggregation) |
| `5` | Model inference error |
| `6` | Internal runtime or configuration error |

---

## Stdout / stderr contract

- **stdout** contains only the JSON result payload (or JSON error on failure)
- **stderr** contains log lines (suppressed unless logging level is set)

This makes it safe to pipe stdout to `jq` or other JSON tools without log contamination:

```bash
agent-audio-gateway analyze recording.wav --task summarize | jq '.result.summary'
```
