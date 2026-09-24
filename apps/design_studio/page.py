"""Tasarım Stüdyosu: kaba kurguyu Axion şablonuna (1080x1920) yerleştirme — Canva'nın yerini alacak bölüm (Faz 5).

Şimdilik: aktif haberin videosu, başlıkları ve paylaşım metni Canva'ya aktarmaya hazır hâlde.
"""

from __future__ import annotations

import streamlit as st

from apps.axion_local.project_picker import project_selector, selected_project
from apps.axion_local.store import ROUGH_CUT_FILENAME, load_news_project

ss = st.session_state

st.set_page_config(page_title="Tasarım Stüdyosu · Axion", page_icon="🎨", layout="wide")
st.title("Tasarım Stüdyosu")

project = selected_project("design_project_id")
project_selector("design_project_id")
if not project:
    st.stop()
package, _ = load_news_project(project)

video_col, text_col = st.columns([2, 3])
with video_col:
    video = project.folder / ROUGH_CUT_FILENAME
    if video.exists():
        st.video(str(video))
        st.download_button("MP4'ü indir", video.read_bytes(), file_name=f"{project.id}.mp4", mime="video/mp4", use_container_width=True)
    else:
        st.info("Bu haberin videosu henüz yok. Video Stüdyosu'nda **Videoyu oluştur**.")
        if st.button("Video Stüdyosu'na geç", use_container_width=True):
            st.switch_page("apps/video_studio/page.py")
with text_col:
    st.caption("Başlık 1 (0–9 sn)")
    st.code(package.headline_1, language=None, wrap_lines=True)
    st.caption("Başlık 2 (13. sn’den sona kadar)")
    st.code(package.headline_2, language=None, wrap_lines=True)
    st.caption("Paylaşım metni")
    st.code(package.caption, language=None, wrap_lines=True)

st.info(
    "Şimdilik videoyu ve metinleri Canva şablonuna aktar (kopyalamak için kutuların sağ üstündeki simgeye bas). "
    "Bu sayfa ileride arka plan, başlık animasyonları, sloganlar ve logoyla 1080×1920 videoyu kendisi hazırlayacak."
)
