"""Son videonun arka planda üretilmesi: editör beklerken de düzenlemeye devam edebilir.

Her proje için en fazla bir iş. İş, başladığı andaki tasarımın kopyasını üretir; bitince yalnızca `rendered` imzasını
güncel `tasarim.json`'a yazar (bu sırada yapılan düzenlemeler ezilmez; imza tutmadığı için "işlenmedi" görünür).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from apps.axion_local.store import DESIGN_FILENAME, FINAL_VIDEO_FILENAME, ROUGH_CUT_FILENAME, NewsProject, load_project_json, save_project_json

from .design import Design, dump_design
from .pipeline import background_path, project_timing, signature
from .render import render_final


@dataclass
class Job:
    started: float = field(default_factory=time.monotonic)
    finished: float | None = None
    error: str | None = None
    encoder: str | None = None
    seen: bool = False  # sayfa bitişi gördü mü (bir kez yenilemek için)
    thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.finished is None

    @property
    def elapsed(self) -> float:
        return (self.finished or time.monotonic()) - self.started


_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()


def _run(project: NewsProject, design: Design, job: Job) -> None:
    try:
        fps, seconds = project_timing(project)
        job.encoder = render_final(project.folder / ROUGH_CUT_FILENAME, design, background_path(project, design), fps, seconds,
                                   project.folder / FINAL_VIDEO_FILENAME)
        stored = load_project_json(project, DESIGN_FILENAME)
        if not isinstance(stored, dict) or stored.get("version") != 2:  # henüz kaydedilmemiş/eski belge: bu tasarım yazılır
            stored = dump_design(design)
        stored["rendered"] = signature(project, design)
        save_project_json(project, DESIGN_FILENAME, stored)
    except Exception as error:  # noqa: BLE001 — hata sayfada gösterilir
        job.error = str(error) or error.__class__.__name__
    finally:
        job.finished = time.monotonic()


def start(project: NewsProject, design: Design) -> bool:
    """İşi başlatır; zaten çalışan varsa False."""
    with _LOCK:
        current = _JOBS.get(str(project.folder))
        if current and current.running:
            return False
        job = Job()
        job.thread = threading.Thread(target=_run, args=(project, design.model_copy(deep=True), job), daemon=True,
                                      name=f"axion-son-video-{project.id}")
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
