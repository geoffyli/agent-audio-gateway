from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent_audio_gateway import __version__
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


def _get_engine() -> GatewayEngine:
    global _engine
    if _engine is None:
        config_path = os.environ.get("AGENT_AUDIO_GATEWAY_CONFIG")
        config = GatewayConfig.load(config_path)
        _engine = GatewayEngine(config)
    return _engine


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("agent-audio-gateway server starting (v%s)", __version__)
    try:
        _get_engine()  # initialise config eagerly; model loads lazily on first request
    except GatewayError as e:
        logger.error("Startup failed: [%s] %s", e.code, e.message)
        raise
    yield
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


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError) -> JSONResponse:
    status_code = _STATUS_MAP.get(type(exc), 500)
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


# ── Thread-pool helper ────────────────────────────────────────────────────────


async def _run_sync(fn, *args: Any) -> Any:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args))


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
    result = await _run_sync(engine.inspect, body.file_path)
    return result.model_dump()


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    engine = _get_engine()
    result = await _run_sync(engine.analyze, request)
    return result.model_dump()


@app.post("/ask")
async def ask(request: AskRequest):
    engine = _get_engine()
    result = await _run_sync(engine.ask, request)
    return result.model_dump()
