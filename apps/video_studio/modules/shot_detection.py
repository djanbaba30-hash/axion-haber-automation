from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .ffmpeg_runner import long_job_timeout, run_ffmpeg


# -------------------------------------------------
# Shot Detection ayarları
# -------------------------------------------------

PRIMARY_THRESHOLD = 10.0

FALLBACK_THRESHOLD = 7.0

FALLBACK_MIN_DURATION = 15.0

DEFAULT_MIN_SHOT_DURATION = 0.5


# -------------------------------------------------
# Ana Shot Detection
# -------------------------------------------------

def detect_shots(
    video_path: Path,
    duration_seconds: float,
    threshold: float = PRIMARY_THRESHOLD,
    min_shot_duration: float = DEFAULT_MIN_SHOT_DURATION,
) -> list[dict[str, Any]]:
    """
    FFmpeg scdet kullanarak videodaki sahne/shot
    değişimlerini tespit eder.

    İlk taramada standart threshold kullanılır.

    Uzun videoda hiç geçiş bulunamazsa daha hassas
    ikinci bir tarama yapılır.

    Bu fonksiyonun dışarıya verdiği yapı önceki
    sürümle aynıdır; app.py değişikliği gerektirmez.
    """

    if not video_path.exists():

        raise FileNotFoundError(
            f"Video bulunamadı: {video_path}"
        )

    if duration_seconds <= 0:

        return []

    # -------------------------------------------------
    # 1. Ana tarama
    # -------------------------------------------------

    timestamps = detect_scene_changes(
        video_path,
        threshold=threshold,
        duration_seconds=duration_seconds,
    )

    # -------------------------------------------------
    # 2. Uzun videoda geçiş bulunamadıysa
    #    daha hassas ikinci tarama
    # -------------------------------------------------

    if (
        not timestamps
        and duration_seconds
        >= FALLBACK_MIN_DURATION
        and threshold
        > FALLBACK_THRESHOLD
    ):

        fallback_timestamps = detect_scene_changes(
            video_path,
            threshold=FALLBACK_THRESHOLD,
            duration_seconds=duration_seconds,
        )

        timestamps = fallback_timestamps

    # -------------------------------------------------
    # 3. Shot sınırlarını oluştur
    # -------------------------------------------------

    boundaries = [0.0]

    for timestamp in timestamps:

        if timestamp <= 0:

            continue

        if timestamp >= duration_seconds:

            continue

        if (
            timestamp
            - boundaries[-1]
            < min_shot_duration
        ):

            continue

        boundaries.append(
            timestamp
        )

    # -------------------------------------------------
    # 4. Video sonunu ekle
    # -------------------------------------------------

    if (
        duration_seconds
        - boundaries[-1]
        >= min_shot_duration
    ):

        boundaries.append(
            duration_seconds
        )

    elif len(boundaries) > 1:

        boundaries[-1] = (
            duration_seconds
        )

    # -------------------------------------------------
    # 5. Shot kayıtlarını oluştur
    # -------------------------------------------------

    shots = []

    for index in range(
        len(boundaries) - 1
    ):

        start = boundaries[index]

        end = boundaries[
            index + 1
        ]

        shot_duration = (
            end - start
        )

        if shot_duration <= 0:

            continue

        shots.append(
            {
                "shot_number": index + 1,
                "start_seconds": round(
                    start,
                    3,
                ),
                "end_seconds": round(
                    end,
                    3,
                ),
                "duration_seconds": round(
                    shot_duration,
                    3,
                ),
                "start_formatted": format_timestamp(
                    start
                ),
                "end_formatted": format_timestamp(
                    end
                ),
                "duration_formatted": format_timestamp(
                    shot_duration
                ),
            }
        )

    return shots


# -------------------------------------------------
# FFmpeg scdet
# -------------------------------------------------

def detect_scene_changes(
    video_path: Path,
    threshold: float,
    duration_seconds: float | None = None,
) -> list[float]:
    """
    FFmpeg scdet filtresi ile scene-change
    zamanlarını tespit eder.

    scdet, threshold üzerindeki değişimleri
    stderr çıktısında şu yapıyla raporlar:

        lavfi.scd.score: ...
        lavfi.scd.time: ...

    Bu fonksiyon sadece zaman noktalarını döndürür.
    """

    command = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        str(video_path),
        "-vf",
        f"scdet=threshold={threshold}",
        "-an",
        "-f",
        "null",
        "-",
    ]

    result = run_ffmpeg(
        command,
        long_job_timeout(duration_seconds),
        "FFmpeg sahne tespiti",
    )

    # FFmpeg scdet çıktısı stderr üzerinden gelir.
    output = result.stderr

    timestamps = (
        extract_scdet_timestamps(
            output
        )
    )

    return timestamps


# -------------------------------------------------
# scdet zamanlarını çıkar
# -------------------------------------------------

def extract_scdet_timestamps(
    ffmpeg_output: str,
) -> list[float]:
    """
    FFmpeg scdet çıktısından scene-change
    zamanlarını çıkarır.

    Örnek çıktı:

        lavfi.scd.score: 15.123,
        lavfi.scd.time: 6.160000
    """

    pattern = re.compile(
        r"lavfi\.scd\.time:\s*"
        r"(\d+(?:\.\d+)?)"
    )

    timestamps = []

    for match in pattern.finditer(
        ffmpeg_output
    ):

        try:

            timestamp = float(
                match.group(1)
            )

            timestamps.append(
                timestamp
            )

        except ValueError:

            continue

    return sorted(
        set(timestamps)
    )


# -------------------------------------------------
# Zaman formatı
# -------------------------------------------------

def format_timestamp(
    seconds: float,
) -> str:
    """
    Saniyeyi MM:SS.xx formatına çevirir.
    """

    total_seconds = max(
        0.0,
        float(seconds),
    )

    minutes = int(
        total_seconds // 60
    )

    remaining = (
        total_seconds
        - (
            minutes
            * 60
        )
    )

    return (
        f"{minutes:02d}:"
        f"{remaining:05.2f}"
    )
