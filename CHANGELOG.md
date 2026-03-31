# Changelog

All notable changes to this project are documented here.

---

## [Unreleased]

### Security
- **Path traversal protection:** Server mode now supports `server.permitted_audio_dir` config field. When set, file paths outside the configured directory are rejected with `PATH_NOT_PERMITTED` (HTTP 422). Symlinks are resolved before the check.
- **API key deprecation warning:** Setting `model.api_key` in the config file now emits a `UserWarning` recommending use of the `OPENROUTER_API_KEY` environment variable instead.
- **Remote binding warning:** Starting the server with `--allow-remote` now prints a security warning to stderr.

### Features
- **Server request timeout:** Each server endpoint now enforces a configurable timeout (`server.request_timeout_seconds`, default 300s). Requests that exceed the timeout return HTTP 500 with error code `REQUEST_TIMEOUT`.
- **Server logging:** The server now configures the root logger via `_configure_logging()` at startup, so log output is consistent with CLI mode.

### Bug Fixes
- **Engine singleton race condition:** The server's `_engine` global is now protected by `threading.Lock()` using double-checked locking, preventing multiple engine instances from being created under concurrent requests.
- **httpx.Client resource leak guard:** A `try/except` block now closes the httpx client if any subsequent initialization step raises, preventing connection handle leaks.
- **ThreadPoolExecutor exception logging:** When parallel chunk analysis fails, the cancellation attempt now logs how many futures were cancelled vs. still running in background (in-flight httpx calls cannot be interrupted).
- **Empty chunk filtering:** `ChunkAggregator` now filters out empty and whitespace-only strings from chunk results before synthesis. All-empty results raise `AggregationError(EMPTY_CHUNKS)`.
- **NaN/inf audio validation:** `AudioPreprocessor` now validates loaded audio arrays for NaN or infinite values, raising `PreprocessingError(AUDIO_INVALID_DATA)` rather than propagating invalid data to the API.

### Configuration changes
- **New `ServerConfig`** section with two fields: `permitted_audio_dir` (default `null`) and `request_timeout_seconds` (default `300.0`).
- **Removed `CacheConfig`**: The `cache:` section has been removed from `GatewayConfig` and `config.default.yaml`. It was defined but never implemented. Existing YAML files with a `cache:` key will continue to load without error (Pydantic ignores unknown fields by default).
- **Numeric upper bounds added:**
  - `model.max_tokens`: max 32768
  - `analysis.target_sample_rate_hz`: max 48000
  - `analysis.max_parallel_chunks`: max 32
  - Values above these limits now raise a `ValidationError` at config load time.

### Deprecations
- `AnalysisResult.observations` — this field is always empty and will be removed in a future version. It is marked as deprecated in the Pydantic model.

### Breaking changes (minor)
- `instruction` field in `AnalyzeRequest` (CLI `--instruction`, HTTP `instruction`) is now capped at 8192 characters. Requests with longer instructions will fail validation.
- Config files with `model.api_key` set now emit a `UserWarning` at runtime. No behavior change, but scripts that treat warnings as errors (e.g. `PYTHONWARNINGS=error`) will need to migrate to the env var.

### Dependencies
- All runtime dependencies now have upper-bound version constraints to prevent accidental major-version upgrades.
- Added dev dependencies: `ruff>=0.4`, `mypy>=1.9`, `pytest-asyncio>=0.23`.

### Tests
- Added 31 new tests covering: server singleton concurrency, server request timeout, path traversal protection, aggregator empty-string filtering, NaN/inf audio validation, config upper bounds, segmentation logic, server success paths, and CLI flags.
