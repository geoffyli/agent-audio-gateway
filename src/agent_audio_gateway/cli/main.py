from __future__ import annotations

import ipaddress
import json
import logging
import sys
from collections.abc import Callable
from typing import Any

import click

from agent_audio_gateway import __version__
from agent_audio_gateway.core._logging import setup_logging
from agent_audio_gateway.core.config import GatewayConfig
from agent_audio_gateway.core.engine import GatewayEngine
from agent_audio_gateway.core.exceptions import GatewayError, InputError
from agent_audio_gateway.core.models import AnalysisOptions, AnalyzeRequest, AskRequest

# ── Helpers ───────────────────────────────────────────────────────────────────


def _setup_logging(level: str) -> None:
    setup_logging(level)


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


def _emit_internal_error(pretty: bool) -> None:
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled CLI error")
    error = GatewayError(
        "An unexpected internal error occurred.",
        code="INTERNAL_ERROR",
    )
    _emit_error(error, pretty)


def _run_json_command(pretty: bool, action: Callable[[], Any]) -> None:
    try:
        result = action()
        _emit_model(result, pretty)
    except GatewayError as e:
        _emit_error(e, pretty)
        sys.exit(e.exit_code)
    except Exception:
        _emit_internal_error(pretty)
        sys.exit(6)


def _resolve_analysis_options(
    engine: GatewayEngine,
    *,
    no_segment: bool,
    max_chunk_seconds: float | None,
    overlap_seconds: float | None,
) -> AnalysisOptions:
    return AnalysisOptions(
        segment=not no_segment,
        max_chunk_seconds=(
            max_chunk_seconds
            if max_chunk_seconds is not None
            else engine.config.analysis.default_max_chunk_seconds
        ),
        overlap_seconds=(
            overlap_seconds
            if overlap_seconds is not None
            else engine.config.analysis.default_overlap_seconds
        ),
    )


def _is_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _make_engine(config_path: str | None) -> GatewayEngine:
    config = GatewayConfig.load(config_path)
    _setup_logging(config.logging.level)
    return GatewayEngine(config)


def _parse_schema_option(schema: str | None) -> dict[str, Any] | str | None:
    if schema is None:
        return None
    trimmed = schema.strip()
    if not trimmed:
        return schema
    if not trimmed.startswith("{"):
        return schema
    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as e:
        raise InputError(
            f"Invalid JSON schema: {e}",
            code="SCHEMA_INVALID",
        ) from e
    if not isinstance(parsed, dict):
        raise InputError(
            "Schema must be a JSON object.",
            code="SCHEMA_INVALID",
        )
    return parsed


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
def cli(ctx: click.Context, config_path: str | None) -> None:
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
    _run_json_command(
        pretty,
        lambda: _make_engine(ctx.obj.get("config_path")).inspect(file_path),
    )


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
@click.option(
    "--instruction", default=None, help="Custom instruction / prompt override."
)
@click.option(
    "--prompt-file", default=None, metavar="PATH", help="Path to a prompt text file."
)
@click.option(
    "--schema", default=None, help="Output schema identifier (informational)."
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
    help="Disable automatic segmentation and analyze the file as a single unit.",
)
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
@click.pass_context
def analyze(
    ctx: click.Context,
    file_path: str,
    task: str,
    instruction: str | None,
    prompt_file: str | None,
    schema: str | None,
    max_chunk_seconds: float | None,
    overlap_seconds: float | None,
    no_segment: bool,
    pretty: bool,
) -> None:
    """Analyze an audio file and return structured JSON."""

    def _action():
        engine = _make_engine(ctx.obj.get("config_path"))
        options = _resolve_analysis_options(
            engine,
            no_segment=no_segment,
            max_chunk_seconds=max_chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
        request = AnalyzeRequest(
            file_path=file_path,
            task=task,
            instruction=instruction,
            prompt_file=prompt_file,
            output_schema=_parse_schema_option(schema),
            options=options,
        )
        return engine.analyze(request)

    _run_json_command(pretty, _action)


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
    max_chunk_seconds: float | None,
    overlap_seconds: float | None,
    no_segment: bool,
    pretty: bool,
) -> None:
    """Ask a question about an audio file and return a JSON answer."""

    def _action():
        engine = _make_engine(ctx.obj.get("config_path"))
        options = _resolve_analysis_options(
            engine,
            no_segment=no_segment,
            max_chunk_seconds=max_chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
        request = AskRequest(file_path=file_path, question=question, options=options)
        return engine.ask(request)

    _run_json_command(pretty, _action)


# ── health ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
@click.pass_context
def health(ctx: click.Context, pretty: bool) -> None:
    """Return health and model information as JSON."""
    _run_json_command(
        pretty,
        lambda: _make_engine(ctx.obj.get("config_path")).health(),
    )


# ── version ───────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--pretty", is_flag=True, default=False, help="Pretty-print JSON output.")
def version(pretty: bool) -> None:
    """Print the current version as JSON."""
    _emit({"version": __version__}, pretty)


# ── serve ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=click.IntRange(1, 65535),
    help="Bind port.",
)
@click.option(
    "--allow-remote",
    is_flag=True,
    default=False,
    help="Allow binding to non-loopback hosts (unsafe on untrusted networks).",
)
@click.option(
    "--reload", is_flag=True, default=False, help="Enable auto-reload (development)."
)
@click.pass_context
def serve(
    ctx: click.Context,
    host: str,
    port: int,
    allow_remote: bool,
    reload: bool,
) -> None:
    """Start the local HTTP server."""
    import os

    if not _is_loopback_host(host) and not allow_remote:
        raise click.UsageError(
            "Refusing to bind to non-loopback host without --allow-remote. "
            "This server has no authentication and is intended for local use."
        )

    if not _is_loopback_host(host) and allow_remote:
        print(
            f"WARNING: server bound to '{host}' with no authentication. "
            "Do not expose on untrusted networks.",
            file=sys.stderr,
        )

    config_path = ctx.obj.get("config_path")
    if config_path:
        os.environ["AGENT_AUDIO_GATEWAY_CONFIG"] = config_path

    import uvicorn

    uvicorn.run(
        "agent_audio_gateway.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None,  # use our own logging setup
    )
