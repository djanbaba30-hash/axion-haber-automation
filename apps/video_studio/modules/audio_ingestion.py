from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .ffmpeg_runner import PROBE_TIMEOUT_SECONDS, run_ffmpeg


ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
}


def save_uploaded_audio(
    uploaded_file,
) -> Path:
    """
    Yüklenen TTS ses dosyasını geçici dosyaya kaydeder.
    """

    original_name = Path(
        uploaded_file.name
    ).name

    extension = (
        Path(original_name)
        .suffix
        .lower()
    )

    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Desteklenmeyen ses formatı: "
            f"{extension}"
        )

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension,
    )

    try:
        temp_file.write(
            uploaded_file.getbuffer()
        )

        temp_file.flush()

    finally:
        temp_file.close()

    return Path(
        temp_file.name
    )


def probe_audio(
    audio_path: Path,
) -> dict[str, Any]:
    """
    FFprobe ile TTS ses dosyasının teknik
    bilgilerini ve gerçek süresini okur.
    """

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Ses dosyası bulunamadı: "
            f"{audio_path}"
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(audio_path),
    ]

    result = run_ffmpeg(command, PROBE_TIMEOUT_SECONDS, "FFprobe ses analizi")

    if result.returncode != 0:

        error_message = (
            result.stderr.strip()
        )

        raise RuntimeError(
            "FFprobe ses bilgisini okuyamadı."
            + (
                f"\n\nFFprobe: "
                f"{error_message}"
                if error_message
                else ""
            )
        )

    try:

        data = json.loads(
            result.stdout
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "FFprobe çıktısı geçerli JSON değil."
        ) from error

    return build_audio_metadata(
        data,
        audio_path,
    )


def build_audio_metadata(
    probe_data: dict[str, Any],
    audio_path: Path,
) -> dict[str, Any]:

    audio_stream = None

    for stream in probe_data.get(
        "streams",
        [],
    ):

        if (
            stream.get("codec_type")
            == "audio"
        ):

            audio_stream = stream

            break

    format_data = probe_data.get(
        "format",
        {},
    )

    duration = safe_float(
        format_data.get(
            "duration"
        )
    )

    file_size_bytes = (
        audio_path.stat().st_size
    )

    return {
        "filename": audio_path.name,

        "duration_seconds": duration,

        "duration_formatted": (
            format_duration(
                duration
            )
        ),

        "file_size_bytes": (
            file_size_bytes
        ),

        "file_size_mb": round(
            file_size_bytes
            / (1024 * 1024),
            2,
        ),

        "codec": (
            audio_stream.get(
                "codec_name"
            )
            if audio_stream
            else None
        ),

        "sample_rate": (
            audio_stream.get(
                "sample_rate"
            )
            if audio_stream
            else None
        ),

        "channels": (
            audio_stream.get(
                "channels"
            )
            if audio_stream
            else None
        ),

        "channel_layout": (
            audio_stream.get(
                "channel_layout"
            )
            if audio_stream
            else None
        ),
    }


def safe_float(
    value: Any,
) -> float:

    if value is None:
        return 0.0

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def format_duration(
    seconds: float,
) -> str:

    total_seconds = max(
        0,
        int(round(seconds)),
    )

    minutes = (
        total_seconds // 60
    )

    remaining_seconds = (
        total_seconds % 60
    )

    return (
        f"{minutes:02d}:"
        f"{remaining_seconds:02d}"
    )
