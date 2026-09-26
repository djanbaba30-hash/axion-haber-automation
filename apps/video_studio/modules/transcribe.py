"""Yerel yazıya dökme (v4.0.0-alpha.7; API yok, token yok, bilgisayarda çalışır): kaynak videodaki konuşma → zamanlı
cümleler. Editör kaynak sesli kesiti cümleye dokunarak seçer; ileride altyazı temeli (altyazı şu an ürün kararı gereği
yok).

Motor: faster-whisper (Whisper large-v3-turbo, CTranslate2, işlemcide int8; Türkçe sabit). Model ilk kullanımda bir kez
iner (~1,6 GB, `data/modeller`), sonra internetsiz çalışır. faster-whisper yalnız kullanılırken yüklenir: kurulamazsa
Axion yine açılır, bu özellik "kurulu değil" der. Sonuç projede `yazi/` altında saklanır: aynı video yeniden dökülmez.
Uzun sürebildiği için arka planda (`start`), tablet kapansa da sürer.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from apps.axion_local.store import data_dir

MODEL = "large-v3-turbo"
LANGUAGE = "tr"
FOLDER = "yazi"
_MODELS: dict[str, Any] = {}
_LOCK = threading.Lock()  # model tek; iki döküm aynı anda işlemciyi bölmesin


@dataclass
class Job:
    progress: float = 0.0  # 0–1 (videonun dökülen kısmı)
    started: float = field(default_factory=time.monotonic)
    error: str | None = None
    done: bool = False
    thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


_JOBS: dict[str, Job] = {}


def available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def model_ready() -> bool:
    """Model bu bilgisayara inmiş mi (ilk döküm uzun sürer: indirme)."""
    folder = data_dir() / "modeller"
    return folder.is_dir() and any(folder.rglob("model.bin"))


def _key(source: Path) -> str:
    stat = source.stat()
    return hashlib.sha1(f"{source.name}|{stat.st_size}|{int(stat.st_mtime)}|{MODEL}".encode()).hexdigest()[:16]


def _path(folder: Path, source: Path) -> Path:
    return folder / FOLDER / f"{source.stem[:40]}_{_key(source)}.json"


def load(folder: Path, source: Path) -> dict[str, Any] | None:
    """Kayıtlı döküm: {"model", "sure_sn", "video_sn", "cumleler": [{"bas", "son", "metin"}]}; yoksa None."""
    try:
        return json.loads(_path(folder, source).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_model():
    if MODEL not in _MODELS:
        from faster_whisper import WhisperModel

        folder = data_dir() / "modeller"
        folder.mkdir(parents=True, exist_ok=True)
        _MODELS[MODEL] = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root=str(folder))
    return _MODELS[MODEL]


def transcribe(source: Path, folder: Path, progress: Callable[[float], None] = lambda share: None,
               model: Any = None) -> dict[str, Any]:
    """Videonun konuşmasını cümlelere döker ve kaydeder. Sessiz yerler atlanır (VAD); dil Türkçe."""
    started = time.monotonic()
    with _LOCK:
        model = model or _load_model()
        segments, info = model.transcribe(str(source), language=LANGUAGE, vad_filter=True, beam_size=5,
                                          condition_on_previous_text=False)
        sentences = []
        for segment in segments:  # üreteç: döküm ilerledikçe gelir
            text = segment.text.strip()
            if text:
                sentences.append({"bas": round(segment.start, 2), "son": round(segment.end, 2), "metin": text})
            if info.duration:
                progress(min(1.0, segment.end / info.duration))
    result = {"model": MODEL, "sure_sn": round(time.monotonic() - started, 1),
              "video_sn": round(float(info.duration or 0), 1), "cumleler": sentences}
    path = _path(folder, source)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def start(source: Path, folder: Path, model: Any = None) -> Job:
    """Arka planda döker (zaten sürüyorsa onu döndürür)."""
    key = str(_path(folder, source))
    job = _JOBS.get(key)
    if job and job.running:
        return job
    job = Job()

    def run() -> None:
        try:
            transcribe(source, folder, lambda share: setattr(job, "progress", share), model)
        except Exception as error:  # noqa: BLE001 — model inemedi, ses okunamadı: sayfada gösterilir
            job.error = str(error)[:400]
        finally:
            job.done = True

    job.thread = threading.Thread(target=run, daemon=True, name="axion-yazi")
    _JOBS[key] = job
    job.thread.start()
    return job


def job(source: Path, folder: Path) -> Job | None:
    return _JOBS.get(str(_path(folder, source)))


def span(sentences: list[dict[str, Any]], first: int, last: int) -> tuple[float, float]:
    """İki cümle arası (ikisi dahil) kaynak aralığı; sıra fark etmez."""
    low, high = sorted((first, last))
    return sentences[low]["bas"], sentences[high]["son"]
