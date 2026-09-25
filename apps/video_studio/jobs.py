"""Videoyu (kaba kurgu + Axion şablonlu son video) arka planda üretme.

Sayfa beklemez: editör tabletten çalışırken ekran kapansa ya da bağlantı kopsa da üretim evdeki bilgisayarda sürer;
sayfa yeniden açılınca sonucu gösterir. Proje başına tek iş. Aynı haberin Tasarım Stüdyosu'nda süren son video üretimi
önce durdurulur (kurgu değişti; ikisi aynı dosyaya yazmasın).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from apps.axion_local.store import ROUGH_CUT_FILENAME, NewsProject
from apps.design_studio import jobs as design_jobs
from apps.design_studio import pipeline

from .modules import render

STAGES = {"kurgu": "Kurgu", "sablon": "Axion şablonu"}


@dataclass
class Job:
    started: float = field(default_factory=time.monotonic)
    finished: float | None = None
    stage: str = "kurgu"
    encoder: str | None = None
    error: str | None = None        # kurgu üretilemedi
    final_error: str | None = None  # kurgu hazır, şablon uygulanamadı
    seen: bool = False              # sayfa sonucu bir kez gösterdi mi
    thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.finished is None

    @property
    def elapsed(self) -> float:
        return (self.finished or time.monotonic()) - self.started


_JOBS: dict[str, Job] = {}
_LOCK = design_jobs.START_LOCK  # iki stüdyonun başlatması tek kilitte


def _run(project: NewsProject, edit_project: dict[str, Any], media_library: dict[str, Any], job: Job) -> None:
    try:
        job.encoder = render.render_rough_cut(edit_project, media_library, project.folder / ROUGH_CUT_FILENAME)
        job.stage = "sablon"
        if not design_jobs.cancel(project):
            job.final_error = "Tasarım Stüdyosu'ndaki üretim durdurulamadı; son videoyu orada yeniden oluştur."
            return
        try:
            pipeline.render_project_final(project)
        except (RuntimeError, ValueError, FileNotFoundError) as error:
            job.final_error = str(error)
    except Exception as error:  # noqa: BLE001 — sayfada gösterilir
        job.error = str(error) or error.__class__.__name__
    finally:
        job.finished = time.monotonic()


def busy(project: NewsProject | None = None) -> bool:
    """Video üretiliyor mu (verilen haber için ya da herhangi biri)."""
    if project is not None:
        job = get(project)
        return bool(job and job.running)
    return any(job.running for job in _JOBS.values())


def start(project: NewsProject, edit_project: dict[str, Any], media_library: dict[str, Any]) -> bool:
    """İşi başlatır; zaten çalışan varsa False."""
    with _LOCK:
        current = _JOBS.get(str(project.folder))
        if current and current.running:
            return False
        job = Job()
        job.thread = threading.Thread(target=_run, args=(project, edit_project, media_library, job), daemon=True,
                                      name=f"axion-video-{project.id}")
        _JOBS[str(project.folder)] = job
        job.thread.start()
        return True


def get(project: NewsProject) -> Job | None:
    return _JOBS.get(str(project.folder))


def wait(project: NewsProject, timeout: float = 30.0) -> None:
    """Testler için: iş bitene kadar bekle."""
    job = get(project)
    if job and job.thread:
        job.thread.join(timeout)
