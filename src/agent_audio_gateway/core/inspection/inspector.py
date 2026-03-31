from __future__ import annotations

import logging
from pathlib import Path

from ..exceptions import InputError
from ..models import FileInfo

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus"}


class AudioInspector:
    def __init__(self, permitted_base: Path | None = None) -> None:
        """
        Args:
            permitted_base: When set, file paths must resolve to within this
                directory. Paths outside it raise InputError with PATH_NOT_PERMITTED.
                Pass None (default) to allow any path (CLI mode).
        """
        self._permitted_base_resolved = (
            permitted_base.resolve() if permitted_base is not None else None
        )

    def inspect(self, file_path: str) -> FileInfo:
        path = Path(file_path)

        if self._permitted_base_resolved is not None:
            try:
                path.resolve().relative_to(self._permitted_base_resolved)
            except ValueError:
                raise InputError(
                    f"Access to path '{file_path}' is not permitted.",
                    code="PATH_NOT_PERMITTED",
                ) from None

        if not path.exists():
            raise InputError(
                f"File not found: {file_path}",
                code="FILE_NOT_FOUND",
            )

        if not path.is_file():
            raise InputError(
                f"Path is not a file: {file_path}",
                code="NOT_A_FILE",
            )

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise InputError(
                f"Unsupported audio format '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
                code="UNSUPPORTED_FORMAT",
            )

        try:
            import soundfile as sf
            info = sf.info(str(path))
        except Exception as e:
            raise InputError(
                f"Could not read audio file metadata: {e}",
                code="METADATA_READ_ERROR",
            ) from e

        logger.debug(
            "Inspected %s: duration=%.2fs channels=%d sr=%d",
            path.name,
            info.duration,
            info.channels,
            info.samplerate,
        )

        return FileInfo(
            path=str(path.absolute()),
            format=suffix.lstrip("."),
            channels=info.channels,
            sample_rate=info.samplerate,
            duration_sec=round(info.duration, 3),
            size_bytes=path.stat().st_size,
        )
