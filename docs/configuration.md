# Configuration Reference

## Config file

`agent-audio-gateway` accepts a YAML config file. Copy `config.default.yaml` as a starting point:

```bash
cp config.default.yaml my-config.yaml
agent-audio-gateway --config my-config.yaml analyze /path/to/file.wav --task summarize
```

The config path can also be set via the environment variable:

```bash
export AGENT_AUDIO_GATEWAY_CONFIG=/path/to/my-config.yaml
agent-audio-gateway analyze /path/to/file.wav --task summarize
```

If no config is provided, all defaults are used.

---

## Full reference

```yaml
model:
  # Which backend to use (currently only openrouter is supported)
  backend: openrouter

  # OpenRouter model identifier — see https://openrouter.ai/models for options
  # Must support audio input (e.g. Gemini 2.0/2.5 Flash, GPT-4o audio)
  id: google/gemini-2.0-flash-001

  # OpenRouter API key. Leave blank to use the OPENROUTER_API_KEY env var (recommended).
  # Never commit a real key to version control.
  api_key: ""

  # OpenRouter API base URL. Change only if using a compatible proxy.
  base_url: https://openrouter.ai/api/v1

  # Maximum tokens to generate per inference call
  max_tokens: 1024

analysis:
  # Files longer than this (in seconds) are split into chunks
  segment_threshold_seconds: 30.0

  # Default maximum chunk duration in seconds
  # Can be overridden per-call with --max-chunk-seconds
  default_max_chunk_seconds: 25.0

  # Default overlap between consecutive chunks in seconds
  # Can be overridden per-call with --overlap-seconds
  default_overlap_seconds: 3.0

output:
  # Always output JSON (currently always true)
  default_json: true

logging:
  # Log level: debug, info, warning, error
  # Logs are written to stderr
  level: info

cache:
  # Enable caching of analysis results (not yet implemented)
  enabled: false

  # Directory for cached results
  dir: ~/.agent-audio-gateway/cache
```

---

## CLI overrides

Some config values can be overridden per-command:

| Config key | CLI flag |
|------------|----------|
| `analysis.default_max_chunk_seconds` | `--max-chunk-seconds` |
| `analysis.default_overlap_seconds` | `--overlap-seconds` |
| `analysis.segment_threshold_seconds` | disable with `--no-segment` |

---

## Model configuration notes

- **API key** — set `OPENROUTER_API_KEY` in your environment (recommended) or put the key directly in `model.api_key`. Environment variable takes effect when `api_key` is blank.
- **Switching models** — change `model.id` to any OpenRouter model that supports audio input. Models with audio token pricing on [openrouter.ai/models](https://openrouter.ai/models) support audio.
- **`max_tokens`** — controls the length of generated responses. Increase for longer summaries; decrease to reduce latency and cost.
- **Server restarts** — changing `model.id` or `model.api_key` takes effect on the next server start.
