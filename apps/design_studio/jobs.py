"""Son videonun arka planda üretilmesi: editör beklerken de düzenlemeye devam edebilir.

Her proje için en fazla bir iş. İş, başladığı andaki tasarımın kopyasını üretir; bitince yalnızca `rendered` imzasını
güncel `tasarim.json`'a yazar (bu sırada yapılan düzenlemeler ezilmez; imza tutmadığı için "işlenmedi" görünür).
Editör iş sürerken tasarımı değiştirip yeniden başlatırsa eski iş durdurulur (FFmpeg öldürülür), yenisi onun
bitmesini bekleyip başlar: eski tasarımın bitmesi beklenmez.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from apps.axion_local.metrics import timed
from apps.axion_local.store import FINAL_VIDEO_FILENAME, ROUGH_CUT_FILENAME, NewsProject

from .design import Design
from .pipeline import background_path, mark_rendered, project_timing, signature
from .render import Cancelled, render_final


@dataclass
class Job:
    started: float = field(default_factory=time.monotonic)
    finished: float | None = None
    error: str | None = None
    encoder: str | None = None
    seen: bool = False  # sayfa bitişi gördü mü (bir kez yenilemek için)
    signature: str | None = None  # üretilen tasarımın imzası (editör sonradan değiştirdi mi)
    cancelled: bool = False
    cancel: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.finished is None

    @property
    def elapsed(self) -> float:
        return (self.finished or time.monotonic()) - self.started


_JOBS: dict[str, Job] = {}
# Video Stüdyosu da bunu kullanır: iki stüdyonun "üretiyor mu → başlat" adımı tek kilitte (aynı haberde yarış olmasın).
START_LOCK = threading.Lock()


def _run(project: NewsProject, design: Design, job: Job, previous: Job | None) -> None:
    try:
        if previous and previous.thread:
            previous.thread.join()  # aynı geçici dosyaya iki FFmpeg yazmasın; eski iş durdurulduğu için kısa sürer
        fps, seconds = project_timing(project)
        with timed("tasarim_son_video", project.id, blur=len(design.blurs)) as info:
            job.encoder = info["kodlayici"] = render_final(
                project.folder / ROUGH_CUT_FILENAME, design, background_path(project, design), fps, seconds,
                project.folder / FINAL_VIDEO_FILENAME, cancel=job.cancel)
        mark_rendered(project, design)
    except Cancelled:
        job.cancelled = True
    except Exception as error:  # noqa: BLE001 — hata sayfada gösterilir
        job.error = str(error) or error.__class__.__name__
    finally:
        job.finished = time.monotonic()


def start(project: NewsProject, design: Design, restart: bool = False) -> bool:
    """İşi başlatır. Çalışan iş varsa: `restart` ile onu durdurup yenisini başlatır, yoksa False.

    Video Stüdyosu bu haberin videosunu üretiyorsa False (son videoyu o da yazacak).
    """
    from apps.video_studio import jobs as video_jobs  # döngüsel import olmasın diye burada

    with START_LOCK:
        if video_jobs.busy(project):  # Video Stüdyosu bu haberin son videosunu zaten üretecek
            return False
        current = _JOBS.get(str(project.folder))
        previous = None
        if current and current.running:
            if not restart:
                return False
            current.cancel.set()
            previous = current
        job = Job(signature=signature(project, design))
        job.thread = threading.Thread(target=_run, args=(project, design.model_copy(deep=True), job, previous), daemon=True,
                                      name=f"axion-son-video-{project.id}")
        _JOBS[str(project.folder)] = job
        job.thread.start()
        return True


def cancel(project: NewsProject, timeout: float = 60.0) -> bool:
    """Çalışan işi durdurur ve bitmesini bekler (Video Stüdyosu kurguyu yeniden üretirken: aynı dosyaya iki üretim yazmasın).

    İş durduysa (ya da hiç yoksa) True; süre içinde durmadıysa False: çağıran son videoyu yazmamalı.
    """
    job = get(project)
    if job and job.running:
        job.cancel.set()
        if job.thread:
            job.thread.join(timeout)
    return not (job and job.running)


def busy() -> bool:
    """Herhangi bir haberin son videosu üretiliyor mu (Axion kapatılırken uyarı için)."""
    return any(job.running for job in _JOBS.values())


def finished_since(since: float) -> list[tuple[str, Job]]:
    """Bu andan sonra biten işler (proje klasörü, iş): her sayfada "video hazır" bildirimi için."""
    return [(folder, job) for folder, job in list(_JOBS.items()) if job.finished is not None and job.finished >= since]


def get(project: NewsProject) -> Job | None:
    return _JOBS.get(str(project.folder))


def wait(project: NewsProject, timeout: float = 30.0) -> None:
    """Testler için: iş bitene kadar bekle."""
    job = get(project)
    if job and job.thread:
        job.thread.join(timeout)
