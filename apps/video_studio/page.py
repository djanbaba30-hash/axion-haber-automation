"""Video Studio: haber projesi + medya → Media Library (Luna) → EditProject."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from apps.axion_local.settings import require_secrets, secret
from apps.axion_local.store import (
    EDIT_PROJECT_FILENAME,
    MEDIA_LIBRARY_FILENAME,
    NewsProject,
    get_news_project,
    inbox_dir,
    list_inbox_media,
    list_news_projects,
    load_news_project,
    load_project_json,
    save_project_json,
)
from apps.video_studio.modules.audio_ingestion import probe_audio
from apps.video_studio.modules.edit_plan import build_edit_project, validate_edit_project
from apps.video_studio.modules.local_media import LocalMediaFile
from apps.video_studio.modules.media_pipeline import prepare_media_library, shot_rows
from apps.video_studio.modules.news_package import news_package_to_state

ANALYSIS_OPTIONS = {
    "Ekonomik — 1 kare / shot": 1,
    "Dengeli — 2 kare / shot": 2,
    "Ayrıntılı — 3 kare / shot": 3,
    "Maksimum — 4 kare / shot": 4,
}
UPLOAD_TYPES = ["mp4", "mov", "mkv", "avi", "webm", "m4v", "jpg", "jpeg", "png", "webp"]

ss = st.session_state

st.set_page_config(page_title="Axion Video Studio", page_icon="🎬", layout="wide")
require_secrets("OPENAI_API_KEY")
st.title("Axion Video Studio")


def load_project(project: NewsProject) -> None:
    """Projenin haberini, sesini ve (varsa) kayıtlı medya analizini oturuma alır."""
    package, audio_path = load_news_project(project)
    ss.news_package = news_package_to_state(package)
    ss.project_news_text = package.caption
    ss.project_audio_path = str(audio_path) if audio_path else None
    ss.project_audio_metadata = probe_audio(audio_path) if audio_path else None
    ss.loaded_news_project = project.id
    ss.active_news_project = project.id

    media_library = load_project_json(project, MEDIA_LIBRARY_FILENAME)
    if media_library:
        ss.media_library = media_library
        ss.analysis_usage = media_library.get("analysis", {})
    else:
        ss.pop("media_library", None)
        ss.pop("analysis_usage", None)
    edit_project = load_project_json(project, EDIT_PROJECT_FILENAME)
    if edit_project:
        ss.edit_project = edit_project
    else:
        ss.pop("edit_project", None)


# =================================================
# 1. HABER PROJESİ
# =================================================

st.subheader("1. Haber projesi")
projects = list_news_projects()
project: NewsProject | None = None

if not projects:
    st.info("Henüz proje yok. Haber Stüdyosu'nda haberi işle, seslendir ve **Projeye kaydet**'e bas.")
else:
    ids = [p.id for p in projects]
    active = ss.get("active_news_project")
    project = st.selectbox(
        "Haber projesi",
        projects,
        index=ids.index(active) if active in ids else 0,
        format_func=lambda p: p.label,
        label_visibility="collapsed",
    )
    if ss.get("loaded_news_project") != project.id:
        try:
            load_project(project)
        except Exception as error:
            st.error(f"Proje yüklenemedi: {error}")
            project = None

if project and ss.get("loaded_news_project") == project.id:
    news_col, audio_col = st.columns([2, 1])
    with news_col:
        st.text_area("Haber metni", height=160, key="project_news_text")
    with audio_col:
        audio_path = ss.get("project_audio_path")
        audio_metadata = ss.get("project_audio_metadata") or {}
        if audio_path:
            st.audio(audio_path)
            st.caption(f"TTS süresi: {audio_metadata.get('duration_formatted', '—')}")
        else:
            st.warning("Bu projede ses yok. Haber Stüdyosu'nda seslendirip yeniden kaydet.")


# =================================================
# 2. MEDYA
# =================================================

st.divider()
st.subheader("2. Medya")
source_col, analysis_col = st.columns([2, 1])

with analysis_col:
    analysis_mode = st.selectbox("Analiz yoğunluğu", list(ANALYSIS_OPTIONS))
    frame_count = ANALYSIS_OPTIONS[analysis_mode]

with source_col:
    source_mode = st.radio(
        "Medya kaynağı",
        ["Bilgisayardaki klasör", "Tarayıcıdan yükle"],
        horizontal=True,
        label_visibility="collapsed",
        help="Tarayıcıdan yükleme, telefondan/tabletten dosya göndermek için.",
    )
    if source_mode == "Bilgisayardaki klasör":
        folder = st.text_input("Klasör", value=str(inbox_dir()), help="DHA'dan indirdiğin videoların bulunduğu klasör.")
        local_files = list_inbox_media(Path(folder))
        if not local_files:
            st.caption("Bu klasörde video veya görsel bulunamadı.")
        selected = st.multiselect(
            "Dosyalar (en yeniden eskiye)",
            local_files,
            placeholder="Video veya görsel seç",
            format_func=lambda path: f"{path.name} · {path.stat().st_size / (1024 * 1024):.0f} MB",
        )
        media_files = [LocalMediaFile(path) for path in selected]
    else:
        media_files = st.file_uploader("Video ve görseller", type=UPLOAD_TYPES, accept_multiple_files=True) or []

if media_files and st.button("Medyayı analiz et", type="primary", use_container_width=True):
    try:
        with st.status("Medya hazırlanıyor...", expanded=True) as status:
            media_library, usage = prepare_media_library(
                media_files, frame_count, analysis_mode, secret("OPENAI_API_KEY"), progress=status.write
            )
            status.update(label="Medya hazır.", state="complete", expanded=False)
        ss.media_library = media_library
        ss.analysis_usage = usage
        ss.pop("edit_project", None)
        if project:
            save_project_json(project, MEDIA_LIBRARY_FILENAME, media_library)
            (project.folder / EDIT_PROJECT_FILENAME).unlink(missing_ok=True)
    except Exception as error:
        st.error("Medya hazırlanırken bir hata oluştu.")
        st.exception(error)

media_library = ss.get("media_library")
if media_library:
    rows = shot_rows(media_library)
    st.success(
        f"{media_library.get('video_count', 0)} video, {media_library.get('image_count', 0)} görsel · "
        f"{len(rows)} shot. Luna maliyeti: ${float((ss.get('analysis_usage') or {}).get('estimated_cost_usd', 0)):.4f}"
    )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)


# =================================================
# 3. PROJE
# =================================================

st.divider()
st.subheader("3. Proje")

news_text = str(ss.get("project_news_text", "")).strip()
audio_metadata = ss.get("project_audio_metadata")
missing = [
    label for label, ok in (
        ("haber projesi", bool(project and news_text)),
        ("TTS sesi", bool(audio_metadata)),
        ("medya analizi", bool(media_library)),
    ) if not ok
]
if missing:
    st.caption("Proje için eksik: " + ", ".join(missing) + ".")
elif st.button("Projeyi hazırla", type="primary", use_container_width=True):
    edit_project = build_edit_project(
        media_library=media_library,
        news_text=news_text,
        audio_path=ss.project_audio_path,
        audio_duration_seconds=float(audio_metadata.get("duration_seconds", 0) or 0),
        news_package=ss.get("news_package"),
        audio_metadata={**audio_metadata, "mime_type": "audio/mpeg", "size_bytes": audio_metadata.get("file_size_bytes")},
    )
    errors = validate_edit_project(edit_project)
    if errors:
        st.error("EditProject doğrulaması başarısız:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        ss.edit_project = edit_project
        save_project_json(project, EDIT_PROJECT_FILENAME, edit_project)

edit_project = ss.get("edit_project")
if edit_project:
    audio = edit_project.get("audio", {})
    assets = (edit_project.get("media") or {}).get("assets", [])
    st.success("EditProject hazır ve proje klasörüne kaydedildi. Sıradaki aşama: otomatik kurgu (Edit Planner).")
    cols = st.columns(4)
    cols[0].metric("TTS", f"{float(audio.get('duration_seconds', 0)):.1f} sn")
    cols[1].metric("Video", sum(1 for a in assets if a.get("asset_type") == "video"))
    cols[2].metric("Görsel", sum(1 for a in assets if a.get("asset_type") == "image"))
    cols[3].metric("Shot", sum(len(a.get("shots", [])) for a in assets))
    if project:
        st.caption(f"Proje klasörü: `{project.folder}`")


# =================================================
# GELİŞTİRİCİ BİLGİLERİ
# =================================================

if media_library:
    usage = ss.get("analysis_usage") or {}
    with st.expander("Geliştirici bilgileri"):
        cols = st.columns(4)
        cols[0].metric("Input", f"{usage.get('input_tokens', 0):,}")
        cols[1].metric("Output", f"{usage.get('output_tokens', 0):,}")
        cols[2].metric("Reasoning", f"{usage.get('reasoning_tokens', 0):,}")
        cols[3].metric("Toplam", f"{usage.get('total_tokens', 0):,}")
        st.caption(
            f"Model: {usage.get('model', '—')} · API çağrısı: {usage.get('api_calls', 0)} · "
            f"Görüntü: {usage.get('frame_count', 0)} · Tahmini maliyet: ${usage.get('estimated_cost_usd', 0):.6f}"
        )
        st.json(media_library, expanded=False)
        if edit_project:
            st.json(edit_project, expanded=False)
