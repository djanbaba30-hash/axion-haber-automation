from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .ffmpeg_runner import FRAME_TIMEOUT_SECONDS, run_ffmpeg


# -------------------------------------------------
# Frame sayısı seçenekleri
# -------------------------------------------------

DEFAULT_FRAME_COUNT = 2

MIN_FRAME_COUNT = 1

MAX_FRAME_COUNT = 4


# -------------------------------------------------
# Ana fonksiyon
# -------------------------------------------------

def extract_representative_frames(
    video_path: Path,
    shots: list[dict[str, Any]],
    frame_count: int = DEFAULT_FRAME_COUNT,
) -> list[dict[str, Any]]:
    """
    Her shot için kullanıcı tarafından belirlenen
    sayıda temsilci frame çıkarır.

    Amaç:
        Shot'ın genel görsel içeriğini Luna'ya
        mümkün olan en az sayıda görüntüyle
        göstermek.

    Bu fonksiyon:
        - hareket analizi yapmaz
        - olay tespit etmez
        - kritik olay aramaz
        - OpenAI API kullanmaz

    Sadece temsilci frame seçer.
    """

    if not video_path.exists():

        raise FileNotFoundError(
            f"Video bulunamadı: {video_path}"
        )

    frame_count = validate_frame_count(
        frame_count
    )

    results = []

    for shot in shots:

        start_seconds = float(
            shot["start_seconds"]
        )

        end_seconds = float(
            shot["end_seconds"]
        )

        duration = (
            end_seconds - start_seconds
        )

        if duration <= 0:
            continue

        timestamps = (
            calculate_representative_timestamps(
                start_seconds,
                end_seconds,
                frame_count,
            )
        )

        frame_paths = []

        for frame_index, timestamp in enumerate(
            timestamps,
            start=1,
        ):

            frame_path = extract_single_frame(
                video_path,
                timestamp,
                shot["shot_number"],
                frame_index,
            )

            frame_paths.append(
                {
                    "frame_index": frame_index,
                    "timestamp_seconds": round(
                        timestamp,
                        3,
                    ),
                    "path": str(frame_path),
                }
            )

        shot_data = dict(shot)

        shot_data[
            "analysis_frames"
        ] = frame_paths

        shot_data[
            "sampling"
        ] = {
            "method": "representative",
            "frame_count": len(
                frame_paths
            ),
        }

        results.append(
            shot_data
        )

    return results


# -------------------------------------------------
# Frame sayısını doğrula
# -------------------------------------------------

def validate_frame_count(
    frame_count: int,
) -> int:
    """
    Frame sayısının 1–4 arasında olduğunu
    kontrol eder.
    """

    try:

        frame_count = int(
            frame_count
        )

    except (
        TypeError,
        ValueError,
    ):

        raise ValueError(
            "Frame sayısı geçerli bir sayı olmalıdır."
        )

    if not (
        MIN_FRAME_COUNT
        <= frame_count
        <= MAX_FRAME_COUNT
    ):

        raise ValueError(
            "Frame sayısı 1 ile 4 arasında olmalıdır."
        )

    return frame_count


# -------------------------------------------------
# Temsilci zaman noktaları
# -------------------------------------------------

def calculate_representative_timestamps(
    start_seconds: float,
    end_seconds: float,
    frame_count: int,
) -> list[float]:
    """
    Shot'ın tamamını temsil edecek şekilde
    eşit aralıklı frame zamanları oluşturur.

    Frame sayısı 1 ise:
        Shot'ın tam ortası alınır.

    Frame sayısı 2–4 ise:
        Shot içine eşit aralıklarla dağıtılır.

    Shot'ın tam ilk ve son karesi kullanılmaz.
    """

    duration = (
        end_seconds - start_seconds
    )

    if duration <= 0:

        return [start_seconds]

    frame_count = validate_frame_count(
        frame_count
    )

    timestamps = []

    for index in range(frame_count):

        ratio = (
            (index + 0.5)
            / frame_count
        )

        timestamp = (
            start_seconds
            + (
                duration
                * ratio
            )
        )

        timestamps.append(
            timestamp
        )

    return timestamps


# -------------------------------------------------
# Frame çıkarma
# -------------------------------------------------

def extract_single_frame(
    video_path: Path,
    timestamp: float,
    shot_number: int,
    frame_index: int,
) -> Path:
    """
    Belirli bir zaman noktasından JPG frame çıkarır.
    """

    frame_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=(
            f"_shot_{shot_number}"
            f"_frame_{frame_index}.jpg"
        ),
    )

    frame_file.close()

    frame_path = Path(
        frame_file.name
    )

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(timestamp),
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "4",
        str(frame_path),
    ]

    try:
        result = run_ffmpeg(command, FRAME_TIMEOUT_SECONDS, "FFmpeg frame çıkarma")
    except RuntimeError:
        frame_path.unlink(missing_ok=True)
        raise

    if result.returncode != 0:

        if frame_path.exists():
            frame_path.unlink()

        error_message = (
            result.stderr.strip()
        )

        raise RuntimeError(
            "FFmpeg temsilci frame "
            "oluşturamadı."
            + (
                f"\n\nFFmpeg: {error_message}"
                if error_message
                else ""
            )
        )

    if not frame_path.exists():

        raise RuntimeError(
            "FFmpeg tamamlandı ancak "
            "temsilci frame bulunamadı."
        )

    return frame_path
