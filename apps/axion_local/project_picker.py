"""Video ve Tasarım stüdyolarının ortak haber seçicisi.

- Uygulama taze açıldığında hiçbir haber seçili gelmez (editör kararı); Haber Stüdyosu'ndan "Kaydet ve …'na geç"
  ile gelince o haber seçilidir.
- Liste her gün 02:00'de sıfırlanır: yalnızca bugünün haberleri; "Önceki günler" ile eskiler de görünür.

Kullanım: sayfa başında `selected_project(key)` (arayüz çizmez, başlıklar için), uygun yerde `project_selector(key)`.
"""

from __future__ import annotations

import streamlit as st

from .presence import open_elsewhere
from .store import NewsProject, list_news_projects, work_day_start


def _choices(key: str) -> dict[str, NewsProject]:
    ss = st.session_state
    show_old = bool(ss.get(f"{key}_old"))
    projects = list_news_projects(since=None if show_old else work_day_start())
    active = ss.get("active_news_project")
    if active and active not in {p.id for p in projects}:
        # Oturumda üzerinde çalışılan haber (ör. gece 02:00'den önce kaydedilmiş) listede kalsın.
        projects = [p for p in list_news_projects() if p.id == active] + projects
    return {p.id: p for p in projects}


def selected_project(key: str) -> NewsProject | None:
    """Seçili haber (yoksa None). Seçim yoksa oturumdaki aktif haber seçilir; taze açılışta hiçbiri."""
    ss = st.session_state
    choices = _choices(key)
    if ss.get(key) not in choices:
        active = ss.get("active_news_project")
        ss[key] = active if active in choices else None
    project = choices.get(ss.get(key))
    if project:
        ss.active_news_project = project.id
    return project


def project_selector(key: str) -> None:
    choices = _choices(key)
    select_col, old_col = st.columns([5, 1], vertical_alignment="center")
    old_col.checkbox("Önceki günler", key=f"{key}_old", help="Önceki 2 günün haberleri. Haberler 3 gün saklanır, daha eskileri otomatik silinir.")
    if not choices:
        select_col.info("Bugün kaydedilmiş haber yok. Haber Stüdyosu'nda haberi hazırlayıp kaydet.")
        return
    select_col.selectbox(
        "Haber",
        list(choices),
        key=key,
        format_func=lambda i: choices[i].label,
        placeholder="Haber seç",
        label_visibility="collapsed",
    )
    if open_elsewhere(st.session_state.get(key)):  # editör: bilgisayar + tablet
        st.warning("Bu haber başka bir cihazda da açık. İkisinden aynı anda değişiklik yapma: son kaydeden geçerli olur.",
                   icon="📱")
