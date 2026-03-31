# Security

This document covers the security model for `agent-audio-gateway` and guidance for safe deployment.

---

## Network exposure

The server binds to `127.0.0.1` (loopback) by default. It has **no authentication** built in — it is intended for local use only.

To bind to a non-loopback address, `--allow-remote` is required:

```bash
uv run agent-audio-gateway serve --host 0.0.0.0 --allow-remote
```

This will print a security warning at startup. **Do not expose the server on untrusted networks without adding a reverse proxy with authentication** (e.g. nginx with HTTP basic auth or mTLS).

---

## File system access

By default, the server will attempt to access any file path submitted in a request body. On a shared or networked machine, this means any caller can read arbitrary audio-compatible files (and trigger path existence checks on any path).

To restrict access to a specific directory, set `server.permitted_audio_dir` in your config:

```yaml
server:
  permitted_audio_dir: /home/user/audio
```

With this set, any request with a file path outside that directory will return HTTP 422 with error code `PATH_NOT_PERMITTED`. Symlinks are followed and resolved before the check, so symlink escapes are also blocked.

The CLI is not affected by this setting — it uses whatever path the user provides.

---

## API key management

OpenRouter API keys should be provided via the `OPENROUTER_API_KEY` environment variable:

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Setting `model.api_key` in a config file also works but emits a deprecation warning at runtime, because config files are commonly committed to version control or shared across machines, where a plain-text key may be inadvertently exposed.

**Never commit a config file containing a real API key.**

---

## Prompt injection

The `--instruction` flag (CLI) and `instruction` field (HTTP request) allow callers to override the analysis prompt. This text is passed directly to the model. There is a length limit of 8192 characters.

If the server is accessible by untrusted callers, be aware that a crafted instruction could influence the model's behavior or attempt prompt injection. This is a known trade-off with LLM-backed APIs — treat caller-supplied instructions with the same skepticism as any other user input.
