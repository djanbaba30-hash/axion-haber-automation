from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

FFMPEG_TIMEOUT_SECONDS = 120


ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}


def save_uploaded_video(uploaded_file) -> Path:
    """
    Streamlit UploadedFile nesnesini geçici çalışma alanına kaydeder.
    """

    original_name = Path(uploaded_file.name).name
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Desteklenmeyen video formatı: {extension}"
        )

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension,
    )

    try:
        temp_file.write(uploaded_file.getbuffer())
        temp_file.flush()
    finally:
        temp_file.close()

    return Path(temp_file.name)


def probe_video(video_path: Path) -> dict[str, Any]:
    """
    FFprobe kullanarak videonun teknik metadata bilgisini çıkarır.
    """

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(video_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=FFMPEG_TIMEOUT_SECONDS,
    )

    if result.returncode != 0:
        error_message = result.stderr.strip()

        raise RuntimeError(
            "FFprobe video bilgisini okuyamadı."
            + (
                f"\n\nFFprobe: {error_message}"
                if error_message
                else ""
            )
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "FFprobe çıktısı geçerli JSON değil."
        ) from error

    return build_metadata(data, video_path)


def build_metadata(
    probe_data: dict[str, Any],
    video_path: Path,
) -> dict[str, Any]:
    """
    FFprobe çıktısını uygulamanın kullanacağı metadata yapısına dönüştürür.
    """

    video_stream = None
    audio_stream = None

    for stream in probe_data.get("streams", []):

        codec_type = stream.get("codec_type")

        if codec_type == "video" and video_stream is None:
            video_stream = stream

        elif codec_type == "audio" and audio_stream is None:
            audio_stream = stream

    format_data = probe_data.get("format", {})

    duration = safe_float(
        format_data.get("duration")
    )

    file_size_bytes = video_path.stat().st_size

    metadata = {
        "duration_seconds": duration,
        "duration_formatted": format_duration(duration),
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(
            file_size_bytes / (1024 * 1024),
            2,
        ),
        "has_video": video_stream is not None,
        "has_audio": audio_stream is not None,
        "video": {},
        "audio": {},
    }

    if video_stream:

        metadata["video"] = {
            "codec": video_stream.get("codec_name"),
            "codec_long_name": video_stream.get(
                "codec_long_name"
            ),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": parse_fps(
                video_stream.get("r_frame_rate")
            ),
            "pixel_format": video_stream.get(
                "pix_fmt"
            ),
        }

    if audio_stream:

        metadata["audio"] = {
            "codec": audio_stream.get("codec_name"),
            "sample_rate": audio_stream.get(
                "sample_rate"
            ),
            "channels": audio_stream.get(
                "channels"
            ),
            "channel_layout": audio_stream.get(
                "channel_layout"
            ),
        }

    return metadata


def create_proxy(
    video_path: Path,
    width: int = 960,
) -> Path:
    """
    Orijinal videodan düşük çözünürlüklü proxy oluşturur.
    """

    proxy_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4",
    )

    proxy_file.close()

    proxy_path = Path(proxy_file.name)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"scale={width}:-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(proxy_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:

        if proxy_path.exists():
            proxy_path.unlink()

        error_message = result.stderr.strip()

        raise RuntimeError(
            "FFmpeg proxy oluşturamadı."
            + (
                f"\n\nFFmpeg: {error_message}"
                if error_message
                else ""
            )
        )

    if not proxy_path.exists():
        raise RuntimeError(
            "FFmpeg tamamlandı ancak proxy dosyası bulunamadı."
        )

    return proxy_path


def safe_float(value: Any) -> float:
    """Değeri güvenli şekilde float'a çevirir."""

    if value is None:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_fps(value: str | None) -> float | None:
    """
    FFprobe'un 30000/1001 gibi FPS değerlerini sayıya çevirir.
    """

    if not value:
        return None

    try:
        numerator, denominator = value.split("/")

        numerator = float(numerator)
        denominator = float(denominator)

        if denominator == 0:
            return None

        return round(
            numerator / denominator,
            3,
        )

    except (ValueError, ZeroDivisionError):
        return None


def format_duration(seconds: float) -> str:
    """
    Saniyeyi HH:MM:SS formatına çevirir.
    """

    total_seconds = max(
        0,
        int(round(seconds)),
    )

    hours = total_seconds // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    remaining_seconds = (
        total_seconds % 60
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{remaining_seconds:02d}"
    )
