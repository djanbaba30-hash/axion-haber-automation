"""Kaynak sesli kesitler: editörün seslendirmeden önce/sonra kendi sesiyle eklediği video parçaları.

Örnek: dikkat çekici bir an (seslendirme öncesi) veya röportaj kısımları (seslendirme sonrası).
Kesitler proje klasöründe `kesitler.json`'da tutulur; analizden önce de işaretlenebilir.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .ffmpeg_runner import long_job_timeout, run_ffmpeg

SOUNDBITES_FILENAME = "kesitler.json"
PREVIEW_DIR = "onizleme"
PREVIEW_HEIGHT = 360  # Tarayıcıda hızlı açılsın: 200 MB'lık kaynak yerine birkaç MB'lık önizleme.

Placement = Literal["before", "after"]
PLACEMENT_LABELS = {"before": "Seslendirmeden önce", "after": "Seslendirmeden sonra"}


class Soundbite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    filename: str
    start_s: float
    end_s: float
    placement: Placement

    @model_validator(mode="after")
    def valid_range(self) -> "Soundbite":
        if self.start_s < 0 or self.end_s <= self.start_s:
            raise ValueError("Kesit başlangıcı bitişinden önce olmalı.")
        return self

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


def ordered(soundbites: list[Soundbite], placement: Placement) -> list[Soundbite]:
    return [bite for bite in soundbites if bite.placement == placement]


def total_seconds(soundbites: list[Soundbite]) -> float:
    return sum(bite.duration_s for bite in soundbites)


def parse_soundbites(data) -> list[Soundbite]:
    """Kayıtlı kesitler; bozuk kayıtlar atlanır."""
    result = []
    for item in data or []:
        try:
            result.append(Soundbite.model_validate(item))
        except ValueError:
            continue
    return result


def preview_path(source: Path, project_folder: Path) -> Path:
    key = hashlib.sha1(f"{source.resolve()}|{source.stat().st_size}".encode()).hexdigest()[:12]
    return project_folder / PREVIEW_DIR / f"{source.stem[:40]}_{key}.mp4"


def make_preview(source: Path, project_folder: Path, duration_seconds: float | None = None) -> Path:
    """Kesit seçerken izlemek için küçük (360p, sesli) önizleme; bir kez üretilir."""
    target = preview_path(source, project_folder)
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".yaziliyor.mp4")
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vf", f"scale=-2:{PREVIEW_HEIGHT}", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(partial),
    ]
    result = run_ffmpeg(command, long_job_timeout(duration_seconds), "Önizleme hazırlama")
    if result.returncode != 0 or not partial.exists():
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Önizleme hazırlanamadı.\n\n{result.stderr.strip()[-800:]}")
    partial.replace(target)
    return target
