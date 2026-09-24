"""Video Stüdyosu: haber projesi + görüntüler → Luna analizi → kaynak sesli kesitler → kaba kurgu MP4.

Adımlar sırayla açılır; tamamlanan adım tek satırlık özete daralır.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from apps.axion_local.settings import require_secrets, secret
from apps.axion_local.store import (
    EDIT_PROJECT_FILENAME,
    MEDIA_LIBRARY_FILENAME,
    NewsProject,
    inbox_dir,
    list_inbox_media,
    list_news_projects,
    load_news_project,
    load_project_json,
    save_project_json,
)
from apps.video_studio.modules.audio_ingestion import probe_audio
from apps.video_studio.modules.edit_plan import build_edit_project
from apps.video_studio.modules.local_media import LocalMediaFile
from apps.video_studio.modules.media_library import detect_media_type
from apps.video_studio.modules.media_pipeline import is_current_media_library, prepare_media_library, shot_rows
from apps.video_studio.modules.news_package import news_package_to_state
from apps.video_studio.modules.render import ROUGH_CUT_FILENAME, render_rough_cut
from apps.video_studio.modules.rough_cut import clip_rows, has_rough_cut, matches_template, plan_rough_cut
from apps.video_studio.modules.soundbites import (
    PLACEMENT_LABELS,
    SOUNDBITES_FILENAME,
    Soundbite,
    make_preview,
    parse_soundbites,
    preview_path,
    total_seconds,
)
from apps.video_studio.modules.video_ingestion import probe_video

ANALYSIS_OPTIONS = {
    "Ekonomik — sahne başına 1 kare": 1,
    "Dengeli — sahne başına 2 kare": 2,
    "Ayrıntılı — sahne başına 3 kare": 3,
    "En ayrıntılı — sahne başına 4 kare": 4,
}
UPLOAD_TYPES = ["mp4", "mov", "mkv", "avi", "webm", "m4v", "jpg", "jpeg", "png", "webp"]
DESIGN_PAGE = "apps/design_studio/page.py"

ss = st.session_state

st.set_page_config(page_title="Video Stüdyosu · Axion", page_icon="🎬", layout="wide")
require_secrets("OPENAI_API_KEY")
st.title("Video Stüdyosu")


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


def load_project(project: NewsProject) -> None:
    """Projenin haberini, sesini, kayıtlı analizini ve kesitlerini oturuma alır."""
    package, audio_path = load_news_project(project)
    ss.news_package = news_package_to_state(package)
    ss.project_news_text = package.caption
    ss.project_audio_path = str(audio_path) if audio_path else None
    ss.project_audio_metadata = probe_audio(audio_path) if audio_path else None
    ss.loaded_news_project = project.id
    ss.active_news_project = project.id
    ss.soundbites = parse_soundbites(load_project_json(project, SOUNDBITES_FILENAME))

    media_library = load_project_json(project, MEDIA_LIBRARY_FILENAME)
    ss.media_library_outdated = bool(media_library) and not is_current_media_library(media_library)
    if media_library and not ss.media_library_outdated:
        ss.media_library = media_library
        ss.analysis_usage = media_library.get("analysis", {})
    else:
        ss.pop("media_library", None)
        ss.pop("analysis_usage", None)
    edit_project = load_project_json(project, EDIT_PROJECT_FILENAME)
    if edit_project and edit_project.get("project_version") == "2.1" and has_rough_cut(edit_project) and matches_template(edit_project):
        ss.edit_project = edit_project
    else:
        # 1.1, bozuk, kurgusuz veya eski ölçüdeki (1080x1440) projeyi kullanma; yeniden üretilsin.
        ss.pop("edit_project", None)


def invalidate_cut(project: NewsProject) -> None:
    """Görüntüler veya kesitler değişti: kurgu planı ve video yeniden oluşturulacak."""
    ss.pop("edit_project", None)
    (project.folder / EDIT_PROJECT_FILENAME).unlink(missing_ok=True)
    (project.folder / ROUGH_CUT_FILENAME).unlink(missing_ok=True)


def save_soundbites(project: NewsProject, soundbites: list[Soundbite]) -> None:
    ss.soundbites = soundbites
    save_project_json(project, SOUNDBITES_FILENAME, [bite.model_dump() for bite in soundbites])
    invalidate_cut(project)


# =================================================
# 1. HABER
# =================================================

projects = list_news_projects()
by_id = {p.id: p for p in projects}
if ss.get("video_project_id") not in by_id:
    active = ss.get("active_news_project")
    ss.video_project_id = active if active in by_id else (projects[0].id if projects else None)
project: NewsProject | None = by_id.get(ss.video_project_id)
if project and ss.get("loaded_news_project") != project.id:
    try:
        load_project(project)
    except Exception as error:
        st.error(f"Haber yüklenemedi: {error}")
        project = None

audio_path = ss.get("project_audio_path") if project else None
step1_done = bool(project and audio_path)
with st.expander(
    f"✅ 1. Haber — {project.headline}" if step1_done else "1. Haber",
    expanded=not step1_done,
):
    if not projects:
        st.info("Henüz kayıtlı haber yok. Haber Stüdyosu'nda haberi hazırlayıp **Kaydet ve Video Stüdyosu'na geç**'e bas.")
    else:
        st.selectbox("Haber", list(by_id), key="video_project_id", format_func=lambda i: by_id[i].label, label_visibility="collapsed")
        if audio_path:
            st.audio(audio_path)
        elif project:
            st.warning("Bu haberin sesi yok. Haber Stüdyosu'nda seslendirip yeniden kaydet.")


# =================================================
# 2. GÖRÜNTÜLER
# =================================================

media_library = ss.get("media_library")
analysed_names = [a.get("source", {}).get("filename", "") for a in (media_library or {}).get("assets", [])]
with st.expander(
    f"✅ 2. Görüntüler — {', '.join(analysed_names)}" if media_library else "2. Görüntüler",
    expanded=step1_done and not media_library,
):
    if ss.get("media_library_outdated") and not media_library:
        st.info("Bu haberin görüntüleri eski bir sürümle analiz edilmiş. Daha iyi sahne tanıma için yeniden analiz et.")
    with st.popover("⚙️ Ayarlar"):
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
            key="selected_media",
            placeholder="İndirilenler'den video veya görsel seç" if local_files else "Klasörde video bulunamadı",
            format_func=lambda path: f"{path.name} · {path.stat().st_size / (1024 * 1024):.0f} MB",
            label_visibility="collapsed",
        )
        media_files = [LocalMediaFile(path) for path in selected]

    if media_files:
        label = "Görüntüleri yeniden analiz et" if media_library else "Görüntüleri analiz et"
        if st.button(label, type="primary", use_container_width=True):
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
            except Exception as error:
                st.error(f"Görüntüler analiz edilemedi: {error}")
            else:
                ss.media_library = media_library
                ss.analysis_usage = usage
                ss.media_library_outdated = False
                if project:
                    save_project_json(project, MEDIA_LIBRARY_FILENAME, media_library)
                    invalidate_cut(project)
                st.rerun()


# =================================================
# 3. KAYNAK SESLİ KESİTLER (isteğe bağlı)
# =================================================

soundbites: list[Soundbite] = ss.get("soundbites", []) if project else []
# Kesit seçilebilecek videolar: 2. adımda seçilenler + analiz edilmiş olanlar (analizden önce de seçilebilir).
kesit_sources: dict[str, Path] = {}
for path in ss.get("selected_media") or []:
    if detect_media_type(path.name) == "video":
        kesit_sources.setdefault(str(path), path)
for asset in (media_library or {}).get("assets", []):
    original = asset.get("source", {}).get("original_path")
    if asset.get("asset_type") == "video" and original and Path(original).exists():
        kesit_sources.setdefault(original, Path(original))

summary = f" — {len(soundbites)} kesit, {total_seconds(soundbites):.0f} sn" if soundbites else ""
with st.expander(f"3. Kaynak sesli kesitler (isteğe bağlı){summary}", expanded=bool(ss.get("kesit_open"))):
    st.caption(
        "Videodan bir bölümü kendi sesiyle seslendirmenin önüne (dikkat çekici an) veya arkasına (röportaj) ekle."
    )
    if not project:
        st.caption("Önce bir haber seç.")
    elif not kesit_sources:
        st.caption("Önce 2. adımda video seç.")
    else:
        source_key = st.selectbox("Video", list(kesit_sources), format_func=lambda key: kesit_sources[key].name)
        source = kesit_sources[source_key]
        preview = preview_path(source, project.folder)
        if not preview.exists():
            if st.button("▶️ Videoyu izle ve kesit seç", use_container_width=True):
                ss.kesit_open = True
                try:
                    with st.spinner("Önizleme hazırlanıyor (bir kez)..."):
                        make_preview(source, project.folder)
                except Exception as error:
                    st.error(f"Önizleme hazırlanamadı: {error}")
                else:
                    st.rerun()
        else:
            ss.kesit_open = True
            duration = float(probe_video(source).get("duration_seconds") or 0)
            if ss.get("kesit_source") != source_key or ss.get("kesit_range", (0, 0))[1] > duration:
                ss.kesit_source = source_key
                ss.kesit_range = (0.0, min(5.0, duration))
            start_s, end_s = st.slider(
                "Kesit aralığı (saniye)", 0.0, duration, key="kesit_range", step=0.1, format="%.1f",
            )
            st.video(str(preview), start_time=int(start_s), end_time=max(int(start_s) + 1, int(end_s + 0.999)))
            placement_col, add_col = st.columns([2, 1], vertical_alignment="bottom")
            placement = placement_col.segmented_control(
                "Nereye", list(PLACEMENT_LABELS), key="kesit_placement", default="before",
                format_func=PLACEMENT_LABELS.get,
            )
            if add_col.button("➕ Kesiti ekle", type="primary", use_container_width=True, disabled=end_s - start_s < 0.5):
                bite = Soundbite(
                    path=str(source), filename=source.name, start_s=round(start_s, 2), end_s=round(end_s, 2),
                    placement=placement or "before",
                )
                save_soundbites(project, [*soundbites, bite])
                st.rerun()

    for index, bite in enumerate(soundbites):
        text_col, remove_col = st.columns([5, 1], vertical_alignment="center")
        text_col.markdown(
            f"**{PLACEMENT_LABELS[bite.placement]}:** {bite.filename} · {mmss(bite.start_s)}–{mmss(bite.end_s)} "
            f"({bite.duration_s:.1f} sn)"
        )
        if remove_col.button("Kaldır", key=f"kesit_kaldir_{index}", use_container_width=True):
            save_soundbites(project, [b for i, b in enumerate(soundbites) if i != index])
            st.rerun()


# =================================================
# 4. VİDEO
# =================================================

news_text = str(ss.get("project_news_text", "")).strip()
audio_metadata = ss.get("project_audio_metadata")
ready = bool(project and news_text and audio_metadata and media_library)
plan_error = None

if ready and not ss.get("edit_project"):
    try:
        edit_project = plan_rough_cut(
            build_edit_project(
                media_library=media_library,
                news_text=news_text,
                audio_path=ss.project_audio_path,
                audio_duration_seconds=float(audio_metadata.get("duration_seconds", 0) or 0),
                news_package=ss.get("news_package"),
                audio_metadata={**audio_metadata, "mime_type": "audio/mpeg", "size_bytes": audio_metadata.get("file_size_bytes")},
            ),
            media_library,
            soundbites=soundbites,
        )
    except ValueError as error:
        plan_error = str(error)
    else:
        ss.edit_project = edit_project
        save_project_json(project, EDIT_PROJECT_FILENAME, edit_project)
        (project.folder / ROUGH_CUT_FILENAME).unlink(missing_ok=True)

edit_project = ss.get("edit_project")
with st.expander("4. Video", expanded=True):
    if plan_error:
        st.error(f"Kurgu planı oluşturulamadı: {plan_error}")
    if not (edit_project and project):
        checks = [("Haber", bool(project and news_text)), ("Ses", bool(audio_metadata)), ("Görüntüler", bool(media_library))]
        st.caption("Hazırlık: " + "  ·  ".join(f"{'✅' if ok else '⬜'} {label}" for label, ok in checks))
    else:
        output = project.folder / ROUGH_CUT_FILENAME
        label = "Videoyu yeniden oluştur" if output.exists() else "🎬 Videoyu oluştur"
        if st.button(label, type="primary", use_container_width=True):
            try:
                # Plan güncel kurallarla yeniden kurulur (API yok): kural güncellemeleri eski projelere de uygulanır.
                edit_project = plan_rough_cut(edit_project, media_library, soundbites=soundbites)
                with st.spinner("Video oluşturuluyor... (birkaç dakika sürebilir)"):
                    encoder = render_rough_cut(edit_project, media_library, output)
            except (RuntimeError, ValueError, FileNotFoundError) as error:
                st.error("Video oluşturulamadı.")
                st.code(str(error))
            else:
                ss.edit_project = edit_project
                ss.render_encoder = encoder
                save_project_json(project, EDIT_PROJECT_FILENAME, edit_project)
                st.rerun()
        if output.exists():
            st.video(str(output))
            download_col, design_col = st.columns(2)
            download_col.download_button(
                "MP4'ü indir", output.read_bytes(), file_name=f"{project.id}.mp4", mime="video/mp4", use_container_width=True,
            )
            if design_col.button("Tasarım Stüdyosu'na geç →", use_container_width=True):
                st.switch_page(DESIGN_PAGE)
        else:
            st.caption(
                "Sahneler seslendirmeye göre seçildi. Kadraj her sahnede haberin ana öznesine göre ayarlanır, "
                "video alanı hep tam dolu kalır."
            )


# =================================================
# GELİŞTİRİCİ BİLGİLERİ
# =================================================

if media_library:
    usage = ss.get("analysis_usage") or {}
    with st.expander("Geliştirici bilgileri"):
        cols = st.columns(4)
        cols[0].metric("Girdi token", f"{usage.get('input_tokens', 0):,}")
        cols[1].metric("Çıktı token", f"{usage.get('output_tokens', 0):,}")
        cols[2].metric("Düşünme token", f"{usage.get('reasoning_tokens', 0):,}")
        cols[3].metric("Maliyet", f"${float(usage.get('estimated_cost_usd', 0) or 0):.4f}")
        st.caption(
            f"Model: {usage.get('model', '—')} · API çağrısı: {usage.get('api_calls', 0)} · "
            f"Kare: {usage.get('frame_count', 0)} · Analiz: {analysis_mode}"
        )
        if project:
            st.caption(f"Proje klasörü: {project.folder}")
        rows = shot_rows(media_library)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.json(media_library, expanded=False)
        if edit_project:
            if ss.get("render_encoder"):
                st.caption(f"Son video kodlayıcısı: {ss.render_encoder}")
            st.dataframe(clip_rows(edit_project), use_container_width=True, hide_index=True)
            st.json(edit_project, expanded=False)
