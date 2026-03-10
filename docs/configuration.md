# Configuration Reference

Most users do not need to tune this system.

If you set `OPENROUTER_API_KEY` and use defaults, the gateway is ready to run.

---

## Basic setup (recommended)

```bash
export OPENROUTER_API_KEY=sk-or-...
agent-audio-gateway analyze /path/to/file.wav --task summarize
```

Use a config file only when you want custom behavior:

```bash
cp config.default.yaml my-config.yaml
agent-audio-gateway --config my-config.yaml analyze /path/to/file.wav --task summarize
```

You can also point to a config path via environment:

```bash
export AGENT_AUDIO_GATEWAY_CONFIG=/path/to/my-config.yaml
```

---

## Minimal config most teams need

```yaml
model:
  id: google/gemini-3.1-flash-lite-preview

analysis:
  segment_threshold_seconds: 30.0
  default_max_chunk_seconds: 25.0
  default_overlap_seconds: 3.0
```

Keep everything else at defaults unless you have a specific operational reason.

---

## Advanced controls (optional)

These are operator knobs for production tuning, not required user inputs.

| Key | Default | Tune when |
|-----|---------|-----------|
| `model.max_tokens` | `1024` | Responses are too short/long or you need cost control |
| `model.connect_timeout_seconds` | `10.0` | Network connect is slow or unstable |
| `model.read_timeout_seconds` | `120.0` | Upstream model responses are timing out |
| `model.write_timeout_seconds` | `30.0` | Upload requests fail on slower links |
| `model.pool_timeout_seconds` | `10.0` | High local request concurrency causes client pool waits |
| `model.max_retries` | `2` | You need more/less resilience to transient `429`/`5xx` |
| `model.retry_backoff_seconds` | `0.75` | You need gentler or faster retry behavior |
| `analysis.target_sample_rate_hz` | `16000` | You need to trade fidelity vs latency/payload size |
| `analysis.max_parallel_chunks` | `2` | Long audio is slow (increase) or rate-limited (decrease) |

---

## Full default config

```yaml
model:
  backend: openrouter
  id: google/gemini-3.1-flash-lite-preview
  api_key: ""
  base_url: https://openrouter.ai/api/v1
  max_tokens: 1024
  connect_timeout_seconds: 10.0
  read_timeout_seconds: 120.0
  write_timeout_seconds: 30.0
  pool_timeout_seconds: 10.0
  max_retries: 2
  retry_backoff_seconds: 0.75

analysis:
  segment_threshold_seconds: 30.0
  default_max_chunk_seconds: 25.0
  default_overlap_seconds: 3.0
  target_sample_rate_hz: 16000
  max_parallel_chunks: 2

output:
  default_json: true

logging:
  level: info

cache:
  enabled: false
  dir: ~/.agent-audio-gateway/cache
```

---

## CLI overrides

Some analysis values can be overridden per-command:

| Config key | CLI flag |
|------------|----------|
| `analysis.default_max_chunk_seconds` | `--max-chunk-seconds` |
| `analysis.default_overlap_seconds` | `--overlap-seconds` |
| `analysis.segment_threshold_seconds` | disable with `--no-segment` |

---

## Model notes

- API key resolution order: `model.api_key` -> `OPENROUTER_API_KEY`.
- Change `model.id` to any OpenRouter model that supports audio input.
- Restart the server after changing model settings (`id`, `api_key`, timeouts, retries).
