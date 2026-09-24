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

st.set_page_config(page_title="Video Studio · Axion", page_icon="🎬", layout="wide")
require_secrets("OPENAI_API_KEY")
st.title("Video Studio")


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
    if edit_project and edit_project.get("project_version") == "2.1":
        ss.edit_project = edit_project
    else:
        # 1.1 veya bozuk eski projeyi sessizce kullanma; 2.1 yeniden üretilsin.
        ss.pop("edit_project", None)


# =================================================
# 1. HABER
# =================================================

st.subheader("1. Haber")
projects = list_news_projects()
project: NewsProject | None = None

if not projects:
    st.info("Henüz kayıtlı haber yok. Haber Stüdyosu'nda haberi hazırlayıp **Kaydet ve Video Studio'ya geç**'e bas.")
else:
    ids = [p.id for p in projects]
    active = ss.get("active_news_project")
    project = st.selectbox(
        "Haber",
        projects,
        index=ids.index(active) if active in ids else 0,
        format_func=lambda p: p.label,
        label_visibility="collapsed",
    )
    if ss.get("loaded_news_project") != project.id:
        try:
            load_project(project)
        except Exception as error:
            st.error(f"Haber yüklenemedi: {error}")
            project = None

if project and ss.get("loaded_news_project") == project.id:
    audio_path = ss.get("project_audio_path")
    if audio_path:
        st.audio(audio_path)
    else:
        st.warning("Bu haberin sesi yok. Haber Stüdyosu'nda seslendirip yeniden kaydet.")


# =================================================
# 2. MEDYA
# =================================================

st.subheader("2. Görüntüler")
with st.expander("Gelişmiş"):
    folder = st.text_input("Video klasörü", value=str(inbox_dir()), help="DHA'dan indirdiğin videoların bulunduğu klasör.")
    upload_mode = st.toggle("Dosyayı tarayıcıdan yükle", help="Telefondan veya tabletten dosya göndermek için.")
    analysis_mode = st.selectbox(
        "Analiz yoğunluğu",
        list(ANALYSIS_OPTIONS),
        help="Kare sayısı arttıkça analiz daha ayrıntılı ama daha pahalı olur. Ekonomik çoğu haber için yeterli.",
    )
    frame_count = ANALYSIS_OPTIONS[analysis_mode]

if upload_mode:
    media_files = st.file_uploader("Video ve görseller", type=UPLOAD_TYPES, accept_multiple_files=True, label_visibility="collapsed") or []
else:
    local_files = list_inbox_media(Path(folder))
    selected = st.multiselect(
        "Dosyalar",
        local_files,
        placeholder="İndirilenler'den video veya görsel seç" if local_files else "Klasörde video bulunamadı",
        format_func=lambda path: f"{path.name} · {path.stat().st_size / (1024 * 1024):.0f} MB",
        label_visibility="collapsed",
    )
    media_files = [LocalMediaFile(path) for path in selected]

if media_files and st.button("Görüntüleri analiz et", type="primary", use_container_width=True):
    try:
        with st.status("Görüntüler analiz ediliyor...", expanded=True) as status:
            media_library, usage = prepare_media_library(
                media_files,
                frame_count,
                analysis_mode,
                secret("OPENAI_API_KEY"),
                progress=status.write,
                storage_dir=(project.folder / "media") if project else None,
            )
            status.update(label="Analiz tamamlandı.", state="complete", expanded=False)
        ss.media_library = media_library
        ss.analysis_usage = usage
        ss.pop("edit_project", None)
        if project:
            save_project_json(project, MEDIA_LIBRARY_FILENAME, media_library)
            (project.folder / EDIT_PROJECT_FILENAME).unlink(missing_ok=True)
    except Exception as error:
        st.error("Görüntüler analiz edilemedi.")
        with st.expander("Hata ayrıntısı"):
            st.exception(error)

media_library = ss.get("media_library")
if media_library:
    assets = media_library.get("assets", [])
    video_count = sum(1 for asset in assets if asset.get("asset_type") == "video")
    image_count = sum(1 for asset in assets if asset.get("asset_type") == "image")
    names = [a.get("source", {}).get("filename", "") for a in assets if a.get("asset_type") == "video"]
    summary = ", ".join(names) if names else f"{image_count} görsel"
    st.caption(f"Analiz edildi: {summary} · {video_count} video · {image_count} görsel")


# =================================================
# PROJE (otomatik; kullanıcı düğmesi yok)
# =================================================

news_text = str(ss.get("project_news_text", "")).strip()
audio_metadata = ss.get("project_audio_metadata")
ready = bool(project and news_text and audio_metadata and media_library)

if ready and not ss.get("edit_project"):
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
        st.error("Proje oluşturulamadı:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        ss.edit_project = edit_project
        save_project_json(project, EDIT_PROJECT_FILENAME, edit_project)

st.divider()
if ss.get("edit_project"):
    st.success("Proje hazır. Otomatik kurgu (MP4) bir sonraki sürümde bu adımdan devam edecek.")
else:
    checks = [("Haber", bool(project and news_text)), ("Ses", bool(audio_metadata)), ("Görüntüler", bool(media_library))]
    st.caption("Hazırlık: " + "  ·  ".join(f"{'✅' if ok else '⬜'} {label}" for label, ok in checks))


# =================================================
# GELİŞTİRİCİ BİLGİLERİ
# =================================================

if media_library:
    usage = ss.get("analysis_usage") or {}
    edit_project = ss.get("edit_project")
    with st.expander("Geliştirici bilgileri"):
        cols = st.columns(4)
        cols[0].metric("Input", f"{usage.get('input_tokens', 0):,}")
        cols[1].metric("Output", f"{usage.get('output_tokens', 0):,}")
        cols[2].metric("Reasoning", f"{usage.get('reasoning_tokens', 0):,}")
        cols[3].metric("Maliyet", f"${float(usage.get('estimated_cost_usd', 0) or 0):.4f}")
        st.caption(
            f"Model: {usage.get('model', '—')} · API çağrısı: {usage.get('api_calls', 0)} · "
            f"Görüntü: {usage.get('frame_count', 0)} · Analiz: {analysis_mode}"
        )
        if project:
            st.caption(f"Proje klasörü: {project.folder}")
        rows = shot_rows(media_library)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.json(media_library, expanded=False)
        if edit_project:
            st.json(edit_project, expanded=False)
