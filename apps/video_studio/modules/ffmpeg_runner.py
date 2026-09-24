from __future__ import annotations

import subprocess


PROBE_TIMEOUT_SECONDS = 60.0
FRAME_TIMEOUT_SECONDS = 60.0
LONG_JOB_MIN_TIMEOUT_SECONDS = 300.0
LONG_JOB_MAX_TIMEOUT_SECONDS = 3600.0
LONG_JOB_REALTIME_FACTOR = 4.0


def long_job_timeout(duration_seconds: float | None) -> float:
    """Proxy/scdet gibi tüm videoyu işleyen işler için süreye orantılı timeout."""
    try:
        duration = float(duration_seconds or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        return LONG_JOB_MAX_TIMEOUT_SECONDS
    return min(
        LONG_JOB_MAX_TIMEOUT_SECONDS,
        max(LONG_JOB_MIN_TIMEOUT_SECONDS, duration * LONG_JOB_REALTIME_FACTOR),
    )


def run_ffmpeg(
    command: list[str],
    timeout_seconds: float,
    label: str,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Windows'ta Türkçe dosya adları konsol kod sayfasında çözülemeyebilir.
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"{label} {timeout_seconds:.0f} saniye içinde tamamlanamadı. "
            "Dosya çok uzun, çok büyük veya bozuk olabilir."
        ) from error
