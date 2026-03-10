# Troubleshooting

## The command is not found

```
zsh: command not found: agent-audio-gateway
```

The package is not installed. Install it with:

```bash
uv pip install -e /path/to/agent-audio-gateway
```

Or ensure the virtualenv that has the package installed is active.

---

## FILE_NOT_FOUND

```json
{"status":"error","error":{"code":"FILE_NOT_FOUND","message":"File not found: ...","retryable":false}}
```

- Verify the path is absolute and correct.
- Ensure the file exists and the process has read access.
- On macOS, check Full Disk Access permissions if the file is outside the home directory.

---

## UNSUPPORTED_FORMAT

```json
{"status":"error","error":{"code":"UNSUPPORTED_FORMAT","retryable":false}}
```

Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.opus`.

Convert to a supported format first if needed:
```bash
ffmpeg -i input.file output.wav
```

---

## MODEL_LOAD_ERROR

```json
{"status":"error","error":{"code":"MODEL_LOAD_ERROR","retryable":false}}
```

The Qwen2-Audio model could not be loaded. Check:

1. The model has been downloaded locally (e.g., via `huggingface-cli download Qwen/Qwen2-Audio-7B-Instruct`)
2. Sufficient RAM/VRAM is available (~14 GB for the 7B model)
3. The `transformers` and `torch` packages are installed
4. If using a custom model name, verify it in `config.default.yaml` or via `--config`

---

## MISSING_DEPENDENCY

```json
{"status":"error","error":{"code":"MISSING_DEPENDENCY","retryable":false}}
```

Install the required packages:

```bash
uv pip install transformers torch
```

---

## INFERENCE_ERROR

```json
{"status":"error","error":{"code":"INFERENCE_ERROR","retryable":false}}
```

The model failed during inference. Common causes:

- Out of memory — try `--no-segment` for short files, or reduce `--max-chunk-seconds`
- Corrupted audio — verify the file with `agent-audio-gateway inspect`
- CUDA error — check GPU memory and driver status

---

## INVALID_CHUNK_PARAMS

```json
{"status":"error","error":{"code":"INVALID_CHUNK_PARAMS","retryable":false}}
```

`--overlap-seconds` must be less than `--max-chunk-seconds`. Adjust the values.

---

## The model takes a very long time to respond

This is expected on first load (~14 GB model) and for longer audio files. Use `--no-segment` to skip chunking for short files, which reduces overhead.

---

## JSON output contains no observations

The `result.observations` array may be empty if the model did not produce structured observation data for the given task. This is normal — the `summary` field always contains the primary output.
