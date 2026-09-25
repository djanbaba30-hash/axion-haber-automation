"""Projenin son videosu: tasarım belgesini okur, arka planı seçer, `son_video.mp4`'ü üretir ve imzasını kaydeder.

Video Stüdyosu kurguyu oluşturunca bunu varsayılan tasarımla çağırır (editör Tasarım Stüdyosu'na geldiğinde video
indirmeye hazırdır); Tasarım Stüdyosu değişikliklerden sonra aynı yolla yeniden üretir.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from apps.axion_local.store import (
    DESIGN_FILENAME,
    EDIT_PROJECT_FILENAME,
    FINAL_VIDEO_FILENAME,
    ROUGH_CUT_FILENAME,
    NewsProject,
    load_news_project,
    load_project_json,
    save_project_json,
)

from .assets import background_by_name
from .design import Design, dump_design, load_design, signature_payload
from .render import render_final, timeline_seconds

DEFAULT_TIMING = (30, 20.0)
# tasarim.json'u sayfa (editörün değişiklikleri) ve arka plandaki üretim (imza) aynı süreçte, farklı iş parçacıklarında
# yazar: oku-değiştir-yaz birbirinin arasına girmesin.
_DESIGN_LOCK = threading.Lock()


def project_timing(project: NewsProject) -> tuple[int, float]:
    return timeline_seconds(load_project_json(project, EDIT_PROJECT_FILENAME)) or DEFAULT_TIMING


def load_project_design(project: NewsProject, seconds: float | None = None) -> Design:
    package, _ = load_news_project(project)
    seconds = seconds if seconds is not None else project_timing(project)[1]
    return load_design(load_project_json(project, DESIGN_FILENAME), package.headline_1, package.headline_2, seconds)


def save_project_design(project: NewsProject, design: Design) -> None:
    """Editörün değişikliklerini yazar. `rendered` imzasına dokunmaz (onu yalnızca üretim yazar, `mark_rendered`):
    sayfanın elindeki kopya, arka planda biten bir üretimin imzasını ezmesin."""
    with _DESIGN_LOCK:
        stored = load_project_json(project, DESIGN_FILENAME)
        data = dump_design(design)
        if isinstance(stored, dict) and stored.get("version") == 2:
            data["rendered"] = stored.get("rendered")
        save_project_json(project, DESIGN_FILENAME, data)


def mark_rendered(project: NewsProject, design: Design) -> None:
    """Üretilen tasarımın imzasını yazar; bu sırada yapılmış düzenlemeler korunur (imza tutmazsa "işlenmedi" görünür)."""
    rendered = signature(project, design)
    with _DESIGN_LOCK:
        stored = load_project_json(project, DESIGN_FILENAME)
        if not isinstance(stored, dict) or stored.get("version") != 2:  # henüz kaydedilmemiş/eski belge: bu tasarım yazılır
            stored = dump_design(design)
        stored["rendered"] = rendered
        save_project_json(project, DESIGN_FILENAME, stored)


def background_path(project: NewsProject, design: Design) -> Path:
    return background_by_name(design.background, project.work_day)


def signature(project: NewsProject, design: Design) -> str:
    """Son videoyu etkileyen her şeyin özeti: tasarım + arka plan dosyası + kurgu videosu."""
    rough_cut = project.folder / ROUGH_CUT_FILENAME
    payload = [signature_payload(design), background_path(project, design).name,
               rough_cut.stat().st_mtime if rough_cut.exists() else None]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def final_is_current(project: NewsProject, design: Design) -> bool:
    return (project.folder / FINAL_VIDEO_FILENAME).exists() and design.rendered == signature(project, design)


def render_project_final(project: NewsProject, design: Design | None = None) -> str:
    """Son videoyu üretir, imzayı tasarım belgesine yazar. Kullanılan kodlayıcının adını döndürür."""
    fps, seconds = project_timing(project)
    design = design or load_project_design(project, seconds)
    encoder = render_final(project.folder / ROUGH_CUT_FILENAME, design, background_path(project, design), fps, seconds,
                           project.folder / FINAL_VIDEO_FILENAME)
    mark_rendered(project, design)
    return encoder
