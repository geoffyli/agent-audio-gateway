from __future__ import annotations

import json
import logging
import sys
from typing import Optional

import click

from agent_audio_gateway import __version__
from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.engine import GatewayEngine
from agent_audio_gateway.core.exceptions import GatewayError
from agent_audio_gateway.core.models import AnalysisOptions, AnalyzeRequest, AskRequest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _setup_logging(level: str) -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        stream=sys.stderr,
        level=numeric,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _emit(data: dict, pretty: bool) -> None:
    """Write JSON to stdout."""
    indent = 2 if pretty else None
    click.echo(json.dumps(data, indent=indent))


def _emit_model(model, pretty: bool) -> None:
    _emit(json.loads(model.model_dump_json()), pretty)


def _emit_error(e: GatewayError, pretty: bool) -> None:
    payload = {
        "status": "error",
        "error": {
            "code": e.code,
            "message": e.message,
            "retryable": e.retryable,
        },
    }
    _emit(payload, pretty)


def _make_engine(config_path: Optional[str]) -> GatewayEngine:
    config = GatewayConfig.load(config_path)
    _setup_logging(config.logging.level)
    return GatewayEngine(config)


# ── CLI group ─────────────────────────────────────────────────────────────────


@click.group()
@click.option(
    "--config",
    "config_path",
    default=None,
    envvar="AGENT_AUDIO_GATEWAY_CONFIG",
    help="Path to a YAML config file.",
    metavar="PATH",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str]) -> None:
    """agent-audio-gateway — local audio capability runtime."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


# ── inspect ───────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("file_path")
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
@click.pass_context
def inspect(ctx: click.Context, file_path: str, pretty: bool) -> None:
    """Inspect an audio file and return its metadata as JSON."""
    try:
        engine = _make_engine(ctx.obj.get("config_path"))
        result = engine.inspect(file_path)
        _emit_model(result, pretty)
    except GatewayError as e:
        _emit_error(e, pretty)
        sys.exit(e.exit_code)


# ── analyze ───────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("file_path")
@click.option(
    "--task",
    default="summarize",
    show_default=True,
    type=click.Choice(
        ["summarize", "describe", "classify", "extract-observations", "qa"],
        case_sensitive=False,
    ),
    help="Analysis task to perform.",
)
@click.option("--instruction", default=None, help="Custom instruction / prompt override.")
@click.option("--prompt-file", default=None, metavar="PATH", help="Path to a prompt text file.")
@click.option("--schema", default=None, help="Output schema identifier (informational).")
@click.option(
    "--max-chunk-seconds",
    default=None,
    type=float,
    metavar="N",
    help="Maximum chunk length in seconds (overrides config).",
)
@click.option(
    "--overlap-seconds",
    default=None,
    type=float,
    metavar="N",
    help="Overlap between chunks in seconds (overrides config).",
)
@click.option(
    "--no-segment",
    is_flag=True,
    default=False,
    help="Disable automatic segmentation and analyze the file as a single unit.",
)
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
@click.pass_context
def analyze(
    ctx: click.Context,
    file_path: str,
    task: str,
    instruction: Optional[str],
    prompt_file: Optional[str],
    schema: Optional[str],
    max_chunk_seconds: Optional[float],
    overlap_seconds: Optional[float],
    no_segment: bool,
    pretty: bool,
) -> None:
    """Analyze an audio file and return structured JSON."""
    try:
        engine = _make_engine(ctx.obj.get("config_path"))
        options = AnalysisOptions(
            segment=not no_segment,
            max_chunk_seconds=max_chunk_seconds or engine.config.analysis.default_max_chunk_seconds,
            overlap_seconds=overlap_seconds or engine.config.analysis.default_overlap_seconds,
        )
        request = AnalyzeRequest(
            file_path=file_path,
            task=task,
            instruction=instruction,
            prompt_file=prompt_file,
            output_schema=schema,
            options=options,
        )
        result = engine.analyze(request)
        _emit_model(result, pretty)
    except GatewayError as e:
        _emit_error(e, pretty)
        sys.exit(e.exit_code)


# ── ask ───────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("file_path")
@click.option(
    "--question",
    required=True,
    help="Question to answer about the audio file.",
)
@click.option(
    "--max-chunk-seconds",
    default=None,
    type=float,
    metavar="N",
    help="Maximum chunk length in seconds (overrides config).",
)
@click.option(
    "--overlap-seconds",
    default=None,
    type=float,
    metavar="N",
    help="Overlap between chunks in seconds (overrides config).",
)
@click.option(
    "--no-segment",
    is_flag=True,
    default=False,
    help="Disable automatic segmentation.",
)
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
@click.pass_context
def ask(
    ctx: click.Context,
    file_path: str,
    question: str,
    max_chunk_seconds: Optional[float],
    overlap_seconds: Optional[float],
    no_segment: bool,
    pretty: bool,
) -> None:
    """Ask a question about an audio file and return a JSON answer."""
    try:
        engine = _make_engine(ctx.obj.get("config_path"))
        options = AnalysisOptions(
            segment=not no_segment,
            max_chunk_seconds=max_chunk_seconds or engine.config.analysis.default_max_chunk_seconds,
            overlap_seconds=overlap_seconds or engine.config.analysis.default_overlap_seconds,
        )
        request = AskRequest(file_path=file_path, question=question, options=options)
        result = engine.ask(request)
        _emit_model(result, pretty)
    except GatewayError as e:
        _emit_error(e, pretty)
        sys.exit(e.exit_code)


# ── health ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
@click.pass_context
def health(ctx: click.Context, pretty: bool) -> None:
    """Return health and model information as JSON."""
    try:
        engine = _make_engine(ctx.obj.get("config_path"))
        result = engine.health()
        _emit_model(result, pretty)
    except GatewayError as e:
        _emit_error(e, pretty)
        sys.exit(e.exit_code)


# ── version ───────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
def version(pretty: bool) -> None:
    """Print the current version as JSON."""
    _emit({"version": __version__}, pretty)


# ── serve ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (development).")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, reload: bool) -> None:
    """Start the local HTTP server."""
    import os

    config_path = ctx.obj.get("config_path")
    if config_path:
        os.environ.setdefault("AGENT_AUDIO_GATEWAY_CONFIG", config_path)

    import uvicorn

    uvicorn.run(
        "agent_audio_gateway.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None,  # use our own logging setup
    )
