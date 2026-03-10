# Architecture

## Overview

`agent-audio-gateway` is a **capability runtime** — a local layer between agent systems and audio files. It accepts local audio, routes it through a native audio model, handles chunking and aggregation, and returns structured JSON.

---

## Layers

```
┌─────────────────────────────────────────────┐
│  Layer 4 — Downstream business logic        │
│  (speech coaching, interview tools, etc.)   │
├─────────────────────────────────────────────┤
│  Layer 3 — Agent skill package              │
│  (SKILL.md — how to use the CLI)            │
├─────────────────────────────────────────────┤
│  Layer 2 — Front doors                      │
│  CLI                │  Local server API     │
├─────────────────────────────────────────────┤
│  Layer 1 — Gateway Core (engine)            │
│  Inspection → Preprocessing → Segmentation  │
│  → Qwen2-Audio Adapter → Aggregation        │
└─────────────────────────────────────────────┘
```

The CLI and server **share the same core engine** — there is no duplicated logic between them.

---

## Component map

```
agent-audio-gateway/
└── src/agent_audio_gateway/
    ├── core/
    │   ├── engine.py           ← GatewayEngine: top-level orchestrator
    │   ├── models.py           ← Pydantic request/response types
    │   ├── config.py           ← GatewayConfig (YAML → Pydantic)
    │   ├── exceptions.py       ← typed exception hierarchy
    │   ├── inspection/         ← AudioInspector
    │   ├── preprocessing/      ← AudioPreprocessor
    │   ├── segmentation/       ← AudioSegmenter + AudioChunk
    │   ├── aggregation/        ← ChunkAggregator
    │   └── adapters/
    │       ├── base.py         ← BaseAudioAdapter ABC
    │       └── qwen2_audio/    ← Qwen2AudioAdapter
    ├── cli/main.py             ← Click CLI
    └── server/app.py           ← FastAPI server
```

---

## Analysis pipeline

```
Input audio file
    │
    ▼
AudioInspector          ← validate path, format, extract metadata
    │
    ▼
AudioPreprocessor       ← librosa.load → 16 kHz mono numpy array
    │
    ▼
Should segment?
    ├── No  ──────────────────────────────────────┐
    │                                              │
    └── Yes                                       │
         │                                        │
         ▼                                        │
    AudioSegmenter      ← fixed-window chunks     │
         │                with overlap            │
         ▼                                        │
    Qwen2AudioAdapter   ← per-chunk inference     │
    (analyze × N)                                 │
         │                                        │
         ▼                                        │
    ChunkAggregator     ← synthesize via LLM      │
         │                                        │
         └───────────────────────────────────────►│
                                                  ▼
                                         AnalyzeResponse (JSON)
```

---

## Segmentation strategy

Longer recordings are split into fixed-size overlapping windows:

- **Trigger:** file duration > `segment_threshold_seconds` (default: 30 s)
- **Window size:** `max_chunk_seconds` (default: 25 s)
- **Overlap:** `overlap_seconds` (default: 3 s)
- **Step:** `max_chunk_seconds − overlap_seconds`

Each chunk is analyzed independently. Results are then synthesized into a coherent final response via a text-only LLM call (Qwen2-Audio's underlying language model).

---

## Adapter pattern

The `BaseAudioAdapter` ABC isolates all model-specific code:

```python
class BaseAudioAdapter(ABC):
    def analyze(self, audio: np.ndarray, sr: int, prompt: str) -> str: ...
    def synthesize(self, text: str) -> str: ...
    def model_name(self) -> str: ...
```

`Qwen2AudioAdapter` implements this contract. Future adapters (other local models, cloud fallbacks) can be added without changing the engine.

The model is **lazy-loaded** on the first inference call to avoid loading ~14 GB into memory until actually needed.

---

## Agent-agnostic design

The runtime has no dependency on any specific agent framework:

- The **CLI** is the primary agent integration boundary (portable across any shell-capable agent)
- The **server** provides programmatic access for future UI apps or tool wrappers
- The **skill package** is portable markdown instructions, not framework-specific code

Business logic (speech coaching, interview analysis, etc.) lives in downstream skills built on top of the gateway — never inside the gateway itself.

---

## Configuration flow

1. CLI/server startup reads a YAML config (or uses defaults)
2. `GatewayConfig` is passed into `GatewayEngine`
3. The engine distributes config values to sub-components at construction time
4. No global mutable config state

---

## Security and privacy

- The server binds to `127.0.0.1` only (no external exposure by default)
- File paths are validated before use
- All inference runs locally — no audio is uploaded externally
- Cached artifacts (if enabled) stay in `~/.agent-audio-gateway/cache`
