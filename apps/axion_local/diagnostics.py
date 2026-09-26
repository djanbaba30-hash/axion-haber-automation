"""Teşhis dosyası (editör, v3.6.1): tablette tek dokunuşla indirilir, editör geliştiriciye (Claude/GPT) sohbette yollar.

Hiçbir şey internete gönderilmez (editörün seçimi; repo herkese açık). Tek JSON dosyası: projenin kurgu dosyaları ve
günlüğün sonu. Tablete inen dosya küçüktür (videolar ve ses yok).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.axion_local.store import data_dir

PROJECT_FILES = ("news_package.json", "media_library.json", "edit_project.json", "kesitler.json", "kurgu_plani.json",
                 "tasarim.json")
LOG_FILES = ("axion.log", "axion.onceki.log", "olcumler.jsonl")
LOG_TAIL_BYTES = 60_000


def _tail(path: Path) -> str:
    with path.open("rb") as handle:
        handle.seek(max(0, path.stat().st_size - LOG_TAIL_BYTES))
        return handle.read().decode("utf-8", errors="replace")


def package(folder: Path, version: str | None = None) -> bytes:
    """Projenin teşhis dosyası (JSON, UTF-8): {"surum", "tarih", "proje", "dosyalar": {ad: içerik}, "gunluk": {ad: son kısım}}."""
    files: dict[str, Any] = {}
    for name in PROJECT_FILES:
        path = folder / name
        if path.is_file():
            try:
                files[name] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                files[name] = f"okunamadı: {error}"
    logs = {name: _tail(data_dir() / name) for name in LOG_FILES if (data_dir() / name).is_file()}
    return json.dumps({"surum": version, "tarih": datetime.now().isoformat(timespec="seconds"), "proje": folder.name,
                       "dosyalar": files, "gunluk": logs}, ensure_ascii=False, indent=1).encode("utf-8")


def filename(folder: Path) -> str:
    return f"teshis_{folder.name[:60]}.json"
