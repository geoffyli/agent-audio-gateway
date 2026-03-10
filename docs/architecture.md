# Architecture

## Overview

`agent-audio-gateway` is a local runtime that gives tools and agents a stable interface for audio analysis.
It accepts local audio files, performs local validation/preprocessing/chunking, then sends inference requests to OpenRouter-compatible audio models and returns structured JSON.

---

## Layers

```
┌──────────────────────────────────────────────────────┐
│  Layer 4 — Downstream business logic                │
│  (coaching tools, interview assistants, etc.)       │
├──────────────────────────────────────────────────────┤
│  Layer 3 — Agent skill package                      │
│  (skill/SKILL.md + references)                      │
├──────────────────────────────────────────────────────┤
│  Layer 2 — Front doors                              │
│  CLI                         │ Local HTTP server     │
├──────────────────────────────────────────────────────┤
│  Layer 1 — Gateway core                             │
│  Inspection → Preprocessing → Segmentation          │
│  → OpenRouter adapter → Aggregation                 │
└──────────────────────────────────────────────────────┘
```

CLI and server both use the same `GatewayEngine`; there is no duplicated business logic.

---

## Component map

```
agent-audio-gateway/
└── src/agent_audio_gateway/
    ├── core/
    │   ├── engine.py
    │   ├── models.py
    │   ├── config.py
    │   ├── exceptions.py
    │   ├── inspection/
    │   ├── preprocessing/
    │   ├── segmentation/
    │   ├── aggregation/
    │   └── adapters/openrouter/
    ├── cli/main.py
    └── server/app.py
```

---

## Analysis pipeline

```
Input audio file
    │
    ▼
AudioInspector
    │  validate path/format + metadata
    ▼
AudioPreprocessor
    │  decode audio + convert to mono
    ▼
Should segment?
    ├── No  ───────────────────────────────────────┐
    │                                              │
    └── Yes                                       │
         │                                        │
         ▼                                        │
    AudioSegmenter      fixed-size windows        │
         │                with overlap            │
         ▼                                        │
    OpenRouterAdapter   per-chunk inference       │
    (parallel, bounded)                           │
         │                                        │
         ▼                                        │
    ChunkAggregator     text synthesis merge      │
         │                                        │
         └───────────────────────────────────────►│
                                                  ▼
                                         AnalyzeResponse (JSON)
```

---

## Segmentation strategy

- Trigger: file duration > `analysis.segment_threshold_seconds` (default `30`)
- Chunk size: `analysis.default_max_chunk_seconds` (default `25`)
- Overlap: `analysis.default_overlap_seconds` (default `3`)
- Parallelism: `analysis.max_parallel_chunks` (default `2`)

Chunk outputs are merged into one final response by a synthesis call.

---

## Adapter boundary

`BaseAudioAdapter` isolates model-provider specifics:

```python
class BaseAudioAdapter(ABC):
    def analyze(self, audio: np.ndarray, sr: int, prompt: str) -> str: ...
    def synthesize(self, text: str) -> str: ...
    def model_name(self) -> str: ...
```

`OpenRouterAdapter` handles:
- API key resolution
- request retries/backoff for retryable failures
- payload construction for audio and text requests

---

## Runtime and performance notes

- CLI mode starts a new process for each invocation (higher fixed overhead).
- Server mode (`serve`) keeps a warm engine in memory and is preferred for interactive workflows.
- Responses include `meta.timing_ms` to surface stage-level timing (`inspect`, `preprocess`, `segment`, `inference`, `aggregate`, `total`).

---

## Configuration flow

1. CLI/server loads YAML config (or defaults)
2. `GatewayConfig` is passed to `GatewayEngine`
3. Engine initializes sub-components from config
4. No global mutable config state inside core pipeline

---

## Security and privacy

- HTTP server binds to `127.0.0.1` by default.
- Input file paths are validated before processing.
- Audio data is sent to the configured model provider (OpenRouter) for inference.
- API key can come from config or `OPENROUTER_API_KEY` environment variable.
