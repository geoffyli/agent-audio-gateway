# Quick Start

This guide gets you from zero to a successful local audio analysis in about 5 minutes.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- An [OpenRouter API key](https://openrouter.ai/keys)

## 1) Install

From the repository root:

```bash
uv venv
uv pip install -e .
```

## 2) Set your API key

```bash
export OPENROUTER_API_KEY=sk-or-...
```

## 3) Verify the CLI works

Use `uv run` so commands work even if `.venv/bin` is not on your shell `PATH`:

```bash
uv run agent-audio-gateway version
uv run agent-audio-gateway health --pretty
```

Expected shape:

- `version` returns `{"version":"0.1.0"}`
- `health` returns `{"status":"ok", ...}`

## 4) Run your first analysis

```bash
uv run agent-audio-gateway inspect /absolute/path/to/file.wav
uv run agent-audio-gateway analyze /absolute/path/to/file.wav --task summarize --pretty
uv run agent-audio-gateway ask /absolute/path/to/file.wav --question "What topics are discussed?" --pretty

# Structured mode (schema-constrained output)
uv run agent-audio-gateway analyze /absolute/path/to/file.wav \
  --schema '{"type":"object","properties":{"summary":{"type":"string"}},"required":["summary"]}' \
  --pretty
```

## 5) Optional: run the local server

```bash
uv run agent-audio-gateway serve
```

Then call the API:

```bash
curl http://127.0.0.1:8000/health
```

## Direct command mode (optional)

If you prefer calling `agent-audio-gateway` directly without `uv run`, activate the virtual environment first:

```bash
source .venv/bin/activate
agent-audio-gateway version
```

## Troubleshooting

- `zsh: command not found: agent-audio-gateway`
  - Use `uv run agent-audio-gateway ...`, or activate `.venv`.
- `MISSING_API_KEY`
  - Set `OPENROUTER_API_KEY`, or configure `model.api_key` in YAML.
- `FILE_NOT_FOUND`
  - Use an absolute file path and verify read permissions.

For deeper troubleshooting, see `skill/references/troubleshooting.md` and `docs/configuration.md`.
