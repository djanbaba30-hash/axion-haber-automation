from __future__ import annotations

import math
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

# Uzun shot'lar (ör. 70 sn röportaj) bu uzunlukta pencerelere bölünür;
# "kare sayısı" pencere başına uygulanır.
WINDOW_SECONDS = 10.0

ANALYSIS_FRAME_WIDTH = 640


# -------------------------------------------------
# Ana fonksiyon
# -------------------------------------------------

def extract_representative_frames(
    video_path: Path,
    shots: list[dict[str, Any]],
    frame_count: int = DEFAULT_FRAME_COUNT,
) -> list[dict[str, Any]]:
    """
    Her shot'ı en fazla WINDOW_SECONDS uzunlukta pencerelere böler
    ve her pencere için kullanıcı tarafından belirlenen sayıda
    temsilci frame çıkarır.

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
    created: list[Path] = []

    try:
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

            windows = []
            frame_paths = []
            frame_index = 0

            for window_start, window_end in split_into_windows(
                start_seconds,
                end_seconds,
            ):

                window_frames = []

                for timestamp in calculate_representative_timestamps(
                    window_start,
                    window_end,
                    frame_count,
                ):

                    frame_index += 1

                    frame_path = extract_single_frame(
                        video_path,
                        timestamp,
                        shot["shot_number"],
                        frame_index,
                    )
                    created.append(frame_path)

                    frame = {
                        "frame_index": frame_index,
                        "timestamp_seconds": round(
                            timestamp,
                            3,
                        ),
                        "path": str(frame_path),
                    }
                    window_frames.append(frame)
                    frame_paths.append(frame)

                windows.append(
                    {
                        "start_seconds": round(window_start, 3),
                        "end_seconds": round(window_end, 3),
                        "frames": window_frames,
                    }
                )

            shot_data = dict(shot)

            shot_data[
                "analysis_windows"
            ] = windows

            shot_data[
                "analysis_frames"
            ] = frame_paths

            shot_data[
                "sampling"
            ] = {
                "method": "representative",
                "window_count": len(windows),
                "frame_count": len(
                    frame_paths
                ),
            }

            results.append(
                shot_data
            )
    except Exception:
        # Yarıda kalırsa o ana kadar çıkarılan kareler geçici klasörde kalmasın.
        for path in created:
            path.unlink(missing_ok=True)
        raise

    return results


# -------------------------------------------------
# Uzun shot'ı pencerelere böl
# -------------------------------------------------

def split_into_windows(
    start_seconds: float,
    end_seconds: float,
    max_seconds: float = WINDOW_SECONDS,
) -> list[tuple[float, float]]:
    """Shot'ı en fazla max_seconds uzunlukta, eşit pencerelere böler (deterministik)."""

    duration = end_seconds - start_seconds
    count = max(1, math.ceil(duration / max_seconds - 1e-9))
    step = duration / count
    bounds = [start_seconds + step * index for index in range(count)] + [end_seconds]
    return list(zip(bounds[:-1], bounds[1:]))


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
        # Luna'ya küçük kare: token tasarrufu (kare başına ~yarı), sahne tanıma için yeterli.
        "-vf",
        f"scale={ANALYSIS_FRAME_WIDTH}:-2",
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
