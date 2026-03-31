from __future__ import annotations

import logging
import sys


def setup_logging(level: str, *, force: bool = False) -> None:
    """Configure the root logger to write to stderr with a standard format.

    Args:
        level: Log level name (e.g. "info", "debug"). Case-insensitive.
        force: When True, replaces any existing handlers (use in server mode,
               where uvicorn may have installed its own handlers at startup).
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        stream=sys.stderr,
        level=numeric,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        force=force,
    )
