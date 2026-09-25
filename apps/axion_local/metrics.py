"""Adım süreleri (geliştirici için; editörün görmesi gerekmez): data/olcumler.jsonl, satır başına bir ölçüm.

Hangi adımın ne kadar sürdüğü (haber yazımı, seslendirme, analiz, kurgu, son video) gerçek kullanımdan görülsün,
optimizasyon ona göre seçilsin. Hiçbir zaman hata fırlatmaz; dosya 2 MB'ı geçince eskisi .1 olarak saklanır.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .store import data_dir

FILENAME = "olcumler.jsonl"
MAX_BYTES = 2_000_000
_LOCK = threading.Lock()


def path() -> Path:
    return data_dir() / FILENAME


def record(step: str, seconds: float, project: str | None = None, **extra: Any) -> None:
    line = {"zaman": datetime.now().isoformat(timespec="seconds"), "adim": step, "sn": round(seconds, 2),
            "haber": project, **{k: v for k, v in extra.items() if v is not None}}
    try:
        with _LOCK:
            target = path()
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.stat().st_size > MAX_BYTES:
                target.replace(target.with_suffix(".jsonl.1"))
            with target.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError):
        pass


class timed:
    """`with timed("seslendirme", haber=...) as extra:` — blok süresi kaydedilir; `extra` dict'ine ek bilgi yazılabilir."""

    def __init__(self, step: str, project: str | None = None, **extra: Any) -> None:
        self.step, self.project, self.extra = step, project, dict(extra)

    def __enter__(self) -> dict[str, Any]:
        self.started = time.monotonic()
        return self.extra

    def __exit__(self, kind, error, trace) -> None:
        record(self.step, time.monotonic() - self.started, self.project, hata=kind.__name__ if kind else None, **self.extra)
