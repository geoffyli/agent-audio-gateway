# Agent Audio Gateway

A local audio capability runtime. Use this skill when you need to understand, analyze, or query a local audio file using native audio reasoning rather than transcript-only approaches.

---

## Use this skill when

- The user asks you to understand or analyze a local audio file
- Native audio understanding is preferable to transcript-only reasoning
- You need to summarize, describe, classify, or extract observations from an audio recording
- You need to answer a specific question about the content of an audio file
- You have shell access and `agent-audio-gateway` is installed on the machine

---

## Requirements

- Shell execution capability is available
- The target audio file path is accessible and readable
- The `agent-audio-gateway` CLI is installed (`uv run agent-audio-gateway --help` should succeed)
- The `OPENROUTER_API_KEY` environment variable is set (or `model.api_key` is configured)

---

## Preferred workflow

1. **Verify the file** — if the file path or format is uncertain, run `inspect` first.
2. **Choose the right command** — use `analyze` for open-ended tasks, `ask` for specific questions.
3. **Choose analysis mode**:
   - Standard mode: no schema object, text-first result in `result.summary`.
   - Structured mode: provide a JSON schema object via `--schema` JSON string, parsed object in `result.data`.
4. **Use JSON output** (the CLI default) to keep responses machine-readable.
5. **Treat CLI output as authoritative** — do not invent analysis results.
6. **Preserve timestamps and uncertainty** — surface them faithfully when they appear in the output.
7. **Do not claim to have directly listened to the audio** unless you used this gateway.

---

## Commands

### Inspect a file
```bash
agent-audio-gateway inspect /absolute/path/to/file.wav
```
Returns: file format, channels, sample rate, duration, size.

### Analyze a file
```bash
agent-audio-gateway analyze /absolute/path/to/file.wav --task summarize
agent-audio-gateway analyze /absolute/path/to/file.wav --task describe
agent-audio-gateway analyze /absolute/path/to/file.wav --task classify
agent-audio-gateway analyze /absolute/path/to/file.wav --task extract-observations

# Structured mode (schema-constrained)
agent-audio-gateway analyze /absolute/path/to/file.wav \
  --schema '{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}'
```
Returns: structured analysis result with summary and observations.

### Ask a question
```bash
agent-audio-gateway ask /absolute/path/to/file.wav --question "What is happening in this recording?"
```
Returns: a direct answer to the question based on the audio content.

### Health check
```bash
agent-audio-gateway health
```
Returns: model info and status.

---

## Available tasks

| Task | Description |
|------|-------------|
| `summarize` | High-level summary of the audio content |
| `describe` | Detailed description including sounds, tone, structure |
| `classify` | Content type classification (speech, music, ambient, etc.) |
| `extract-observations` | Timestamped observations and events |
| `qa` | Used internally by `ask` — question answering |

---

## Options

| Flag | Description |
|------|-------------|
| `--pretty` | Pretty-print the JSON output |
| `--instruction TEXT` | Custom prompt override |
| `--prompt-file PATH` | Load a custom prompt from a file |
| `--schema TEXT` | JSON object string enables structured mode; non-object text is metadata only |
| `--max-chunk-seconds N` | Override the maximum chunk size (default: 25s) |
| `--overlap-seconds N` | Override chunk overlap (default: 3s) |
| `--no-segment` | Disable chunking — analyze as a single unit |
| `--config PATH` | Path to a custom YAML config file |

Long-audio segmentation works in both standard mode and structured mode unless `--no-segment` is used.

---

## Error handling

- If the file does not exist, explain the path issue clearly.
- If the command returns a JSON error response, surface the `error.code` and `error.message`.
- If `error.retryable` is `true`, you may retry once after a short wait.
- Do not invent analysis results when the command fails.
- Do not silently fall back to transcript-only workflows unless the user explicitly requests it.

---

## References

- [CLI Usage Reference](references/cli-usage.md)
- [JSON Schemas](references/json-schemas.md)
- [Troubleshooting](references/troubleshooting.md)
