from __future__ import annotations

import logging
from pathlib import Path

from ..exceptions import InputError
from ..models import FileInfo

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus"}


class AudioInspector:
    def inspect(self, file_path: str) -> FileInfo:
        path = Path(file_path)

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
            )

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
