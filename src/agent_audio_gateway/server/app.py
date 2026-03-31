from __future__ import annotations

import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent_audio_gateway import __version__
from agent_audio_gateway.core._logging import setup_logging
from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.engine import GatewayEngine
from agent_audio_gateway.core.exceptions import (
    GatewayError,
    InputError,
    ModelError,
)
from agent_audio_gateway.core.models import (
    AnalyzeRequest,
    AskRequest,
    InspectRequest,
)

logger = logging.getLogger(__name__)

# ── Engine singleton ──────────────────────────────────────────────────────────

_engine: GatewayEngine | None = None
_engine_lock = threading.Lock()


def _get_engine() -> GatewayEngine:
    global _engine
    if _engine is not None:  # fast path — no lock needed once initialized
        return _engine
    with _engine_lock:
        if _engine is None:  # second check under the lock
            config_path = os.environ.get("AGENT_AUDIO_GATEWAY_CONFIG")
            config = GatewayConfig.load(config_path)
            _engine = GatewayEngine(config)
    return _engine


def _close_engine() -> None:
    global _engine
    with _engine_lock:
        if _engine is None:
            return
        _engine.close()
        _engine = None


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        engine = _get_engine()  # initialise config eagerly; model loads lazily on first request
    except GatewayError as e:
        logger.error("Startup failed: [%s] %s", e.code, e.message)
        raise
    if hasattr(engine, "config"):
        setup_logging(engine.config.logging.level, force=True)
    logger.info("agent-audio-gateway server starting (v%s)", __version__)
    yield
    _close_engine()
    logger.info("agent-audio-gateway server shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="agent-audio-gateway",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


# ── Error handling ────────────────────────────────────────────────────────────

_STATUS_MAP: dict[type, int] = {
    InputError: 422,
    ModelError: 503,
}


def _gateway_status_code(exc: GatewayError) -> int:
    for error_type, status_code in _STATUS_MAP.items():
        if isinstance(exc, error_type):
            return status_code
    return 500


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    status_code = _gateway_status_code(exc)
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {
                "code": exc.code,
                "message": exc.message,
                "retryable": exc.retryable,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled server error while processing %s",
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected internal error occurred.",
                "retryable": False,
            },
        },
    )


# ── Thread-pool helper ────────────────────────────────────────────────────────


async def _run_sync(fn, *args: Any, timeout: float = 300.0) -> Any:
    """Run a synchronous function in the thread pool with a configurable timeout.

    Raises GatewayError(REQUEST_TIMEOUT) if the operation exceeds `timeout` seconds.
    Uses asyncio.wait_for for Python 3.10 compatibility (asyncio.timeout is 3.11+).
    """
    loop = asyncio.get_running_loop()
    coro = loop.run_in_executor(None, partial(fn, *args))
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise GatewayError(
            f"Request timed out after {timeout:.0f}s",
            code="REQUEST_TIMEOUT",
            retryable=True,
        ) from None


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    engine = _get_engine()
    result = engine.health()
    return result.model_dump()


@app.get("/version")
async def version():
    return {"version": __version__}


@app.post("/inspect")
async def inspect(body: InspectRequest):
    engine = _get_engine()
    result = await _run_sync(
        engine.inspect, body.file_path,
        timeout=engine.config.server.request_timeout_seconds,
    )
    return result.model_dump()


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    engine = _get_engine()
    result = await _run_sync(
        engine.analyze, request,
        timeout=engine.config.server.request_timeout_seconds,
    )
    return result.model_dump()


@app.post("/ask")
async def ask(request: AskRequest):
    engine = _get_engine()
    result = await _run_sync(
        engine.ask, request,
        timeout=engine.config.server.request_timeout_seconds,
    )
    return result.model_dump()
