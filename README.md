# agent-audio-gateway

An agent-oriented audio capability runtime. `agent-audio-gateway` gives shell-capable agent systems a reliable way to process audio files through a stable local interface backed by cloud audio inference via [OpenRouter](https://openrouter.ai).

---

## What it provides

- **CLI** — primary interface for humans, scripts, and agents
- **Local HTTP server** — programmatic access mirroring the CLI
- **Agent skill package** — portable instructions for agent systems that support shell execution

## What it is not

- A speech-coaching product
- Tied to any specific agent framework
- A local/on-device inference system — audio analysis is performed via the OpenRouter API

---

## Quick start

**Requirements:** Python 3.10+, [uv](https://github.com/astral-sh/uv), an [OpenRouter API key](https://openrouter.ai/keys)

```bash
# Install
uv venv && uv pip install -e .

# Set your API key
export OPENROUTER_API_KEY=sk-or-...

# Inspect a file
agent-audio-gateway inspect /path/to/file.wav

# Summarize a file
agent-audio-gateway analyze /path/to/file.wav --task summarize

# Ask a question
agent-audio-gateway ask /path/to/file.wav --question "What topics are discussed?"

# Check status
agent-audio-gateway health --pretty

# Start the local server
agent-audio-gateway serve
```

---

## Commands

| Command | Description |
|---------|-------------|
| `inspect <file>` | Extract audio file metadata (format, duration, sample rate, etc.) |
| `analyze <file>` | Analyze audio using a named task (summarize, describe, classify, etc.) |
| `ask <file> --question TEXT` | Answer a specific question about the audio |
| `health` | Return model info and status |
| `version` | Print the current version |
| `serve` | Start the local HTTP server |

All commands output JSON to stdout. Logs and diagnostics go to stderr.

---

## Tasks

| Task | Description |
|------|-------------|
| `summarize` | High-level summary of content |
| `describe` | Detailed description including sounds, tone, structure |
| `classify` | Content type classification |
| `extract-observations` | Timestamped observations and events |
| `qa` | Used by the `ask` command for question answering |

---

## Configuration

Copy `config.default.yaml` and pass it with `--config`:

```bash
agent-audio-gateway --config my-config.yaml analyze /path/to/file.wav --task summarize
```

Minimal config most users need:

```yaml
model:
  backend: openrouter
  id: google/gemini-3.1-flash-lite-preview   # any OpenRouter model with audio support

analysis:
  segment_threshold_seconds: 30.0   # files longer than this are chunked
  default_max_chunk_seconds: 25.0
  default_overlap_seconds: 3.0
```

Advanced tuning knobs (timeouts, retries, upload sample rate, chunk parallelism) are documented in [`docs/configuration.md`](docs/configuration.md).

The config path can also be set via the `AGENT_AUDIO_GATEWAY_CONFIG` environment variable.

### API key resolution

The OpenRouter API key is resolved in this order:

1. `model.api_key` in the config file
2. `OPENROUTER_API_KEY` environment variable

If neither is set, analysis operations (`analyze`, `ask`, and API equivalents) fail with
`MISSING_API_KEY` (exit code 6 on CLI).

---

## Local server

```bash
agent-audio-gateway serve               # http://127.0.0.1:8000
agent-audio-gateway serve --port 8080   # custom port
agent-audio-gateway serve --host 0.0.0.0 --allow-remote  # intentionally expose (unsafe)
```

For interactive agent workflows, prefer `serve` mode to avoid per-command CLI cold starts.

Endpoints: `GET /health`, `GET /version`, `POST /inspect`, `POST /analyze`, `POST /ask`

The server binds to `127.0.0.1` by default. Binding to non-loopback hosts requires
`--allow-remote` because the server has no built-in authentication.

---

## Agent skill package

See [`skill/SKILL.md`](skill/SKILL.md) for ready-to-use instructions that teach an agent system when and how to invoke the CLI safely.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System design, layers, and data flow |
| [docs/cli.md](docs/cli.md) | Full CLI reference |
| [docs/api.md](docs/api.md) | Local server API reference |
| [docs/schemas.md](docs/schemas.md) | JSON request and response schemas |
| [docs/configuration.md](docs/configuration.md) | Configuration reference |

---

## Project layout

```
agent-audio-gateway/
├── src/agent_audio_gateway/
│   ├── core/                  ← engine, models, config, exceptions
│   │   ├── inspection/        ← file validation and metadata
│   │   ├── preprocessing/     ← audio loading
│   │   ├── segmentation/      ← chunking for long audio
│   │   ├── aggregation/       ← merging chunk results
│   │   └── adapters/openrouter/ ← OpenRouter API adapter
│   ├── cli/                   ← Click CLI
│   └── server/                ← FastAPI local server
├── skill/                     ← portable agent skill package
├── tests/
├── docs/
└── config.default.yaml
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Bad arguments |
| 3 | Input error (file not found, unsupported format) |
| 4 | Processing error |
| 5 | Model / API error |
| 6 | Internal / configuration error |
