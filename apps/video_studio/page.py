"""Video Stüdyosu: haber projesi + görüntüler → Luna analizi → kaynak sesli kesitler → kaba kurgu MP4.

Adımlar sırayla açılır; tamamlanan adım tek satırlık özete daralır.
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from apps.axion_local.project_picker import project_selector, selected_project
from apps.axion_local.settings import require_secrets, secret
from apps.axion_local.store import (
    EDIT_PROJECT_FILENAME,
    FINAL_VIDEO_FILENAME,
    MEDIA_LIBRARY_FILENAME,
    ROUGH_CUT_FILENAME,
    NewsProject,
    inbox_dir,
    list_inbox_media,
    load_news_project,
    load_project_json,
    save_project_json,
)
from apps.video_studio import jobs as video_jobs
from apps.video_studio.modules.audio_ingestion import probe_audio
from apps.video_studio.modules.edit_plan import build_edit_project
from apps.video_studio.modules.local_media import LocalMediaFile
from apps.video_studio.modules.media_library import detect_media_type
from apps.video_studio.modules.media_pipeline import is_current_media_library, prepare_media_library, shot_rows
from apps.video_studio.modules.news_package import news_package_to_state
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
page_started = time.monotonic()

st.set_page_config(page_title="Video Stüdyosu · Axion", page_icon="🎬", layout="wide")
require_secrets("OPENAI_API_KEY")
st.title("Video Stüdyosu")


@st.cache_data(show_spinner=False, max_entries=32)
def video_duration(path: str, mtime: float) -> float:
    """Kesit kaydırıcısının uzunluğu; FFprobe her etkileşimde değil, dosya başına bir kez çalışır."""
    return float(probe_video(Path(path)).get("duration_seconds") or 0)


def render_status(project: NewsProject) -> None:
    """Arka planda süren video üretimi: saniyede bir yenilenen durum; bitince sayfa videoyu göstermek için yenilenir."""
    job = video_jobs.get(project)

    @st.fragment(run_every=1.0 if job and job.running else None)
    def status() -> None:
        job = video_jobs.get(project)
        if job and job.running:
            st.info(f"⏳ {video_jobs.STAGES[job.stage]} oluşturuluyor… {job.elapsed:.0f} sn. Bu bilgisayarda sürer: "
                    "sayfadan ayrılabilir ya da tableti kapatabilirsin, bitince burada görünür.")
        elif job and job.finished and not job.seen:
            job.seen = True
            if job.finished > page_started:
                st.rerun(scope="app")  # iş bu sayfa açıkken bitti: video ve İndir görünsün

    status()


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
    (project.folder / FINAL_VIDEO_FILENAME).unlink(missing_ok=True)


def save_soundbites(project: NewsProject, soundbites: list[Soundbite]) -> None:
    ss.soundbites = soundbites
    save_project_json(project, SOUNDBITES_FILENAME, [bite.model_dump() for bite in soundbites])
    invalidate_cut(project)


# =================================================
# 1. HABER
# =================================================

project: NewsProject | None = selected_project("video_project_id")
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
    project_selector("video_project_id")
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
            help="Kare sayısı arttıkça analiz daha ayrıntılı ama daha pahalı olur. Ekonomik çoğu haber için yeterli. "
            "Uzun videolarda maliyet sınırı için kare sayısı otomatik azaltılır.",
        )
    frame_count = ANALYSIS_OPTIONS[analysis_mode]

    if upload_mode:
        media_files = st.file_uploader("Video ve görseller", type=UPLOAD_TYPES, accept_multiple_files=True, label_visibility="collapsed") or []
    else:
        local_files = list_inbox_media(Path(folder))
        # Tarayıcı sayfasından "Video Stüdyosu'nda kullan" ile gelen seçim: listede olmayan (silinmiş, başka klasör) atlanır.
        if ss.get("selected_media"):
            ss["selected_media"] = [path for path in ss["selected_media"] if path in local_files]
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
        if st.button(label, type="primary", width="stretch"):
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
            if st.button("▶️ Videoyu izle ve kesit seç", width="stretch"):
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
            duration = video_duration(str(source), source.stat().st_mtime)
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
            if add_col.button("➕ Kesiti ekle", type="primary", width="stretch", disabled=end_s - start_s < 0.5):
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
        if remove_col.button("Kaldır", key=f"kesit_kaldir_{index}", width="stretch"):
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
        (project.folder / FINAL_VIDEO_FILENAME).unlink(missing_ok=True)

edit_project = ss.get("edit_project")
with st.expander("4. Video", expanded=True):
    if plan_error:
        st.error(f"Kurgu planı oluşturulamadı: {plan_error}")
    if not (edit_project and project):
        checks = [("Haber", bool(project and news_text)), ("Ses", bool(audio_metadata)), ("Görüntüler", bool(media_library))]
        st.caption("Hazırlık: " + "  ·  ".join(f"{'✅' if ok else '⬜'} {label}" for label, ok in checks))
    else:
        output = project.folder / ROUGH_CUT_FILENAME
        render_status(project)
        job = video_jobs.get(project)
        busy = bool(job and job.running)
        label = "Videoyu yeniden oluştur" if output.exists() else "🎬 Videoyu oluştur"
        if st.button("⏳ Video oluşturuluyor…" if busy else label, type="primary", width="stretch", disabled=busy):
            try:
                # Plan güncel kurallarla yeniden kurulur (API yok): kural güncellemeleri eski projelere de uygulanır.
                edit_project = plan_rough_cut(edit_project, media_library, soundbites=soundbites)
            except ValueError as error:
                st.error(f"Kurgu planı oluşturulamadı: {error}")
            else:
                ss.edit_project = edit_project
                save_project_json(project, EDIT_PROJECT_FILENAME, edit_project)
                # Kurgu ve ardından son video (1080x1920, Axion şablonu; varsa editörün tasarımıyla) arka planda üretilir.
                video_jobs.start(project, edit_project, media_library)
                st.rerun()
        final = project.folder / FINAL_VIDEO_FILENAME
        if job and job.finished and job.error:
            st.error("Video oluşturulamadı.")
            st.code(job.error[-1500:])
        elif job and job.finished and job.final_error:
            st.warning("Kurgu hazır ama şablon uygulanamadı; Tasarım Stüdyosu'nda yeniden dene.")
        if not busy and (final.exists() or output.exists()):
            shown = final if final.exists() else output
            st.video(str(shown))
            download_col, design_col = st.columns(2)
            download_col.download_button(  # dosya yalnızca tıklanınca okunur (her etkileşimde 10–25 MB değil)
                "⬇️ Son videoyu indir" if final.exists() else "MP4'ü indir", lambda: shown.read_bytes(),
                file_name=f"{project.id}.mp4", mime="video/mp4", width="stretch", on_click="ignore",
            )
            if design_col.button("🎨 Tasarım Stüdyosu'nda düzenle →", width="stretch"):
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
            st.dataframe(rows, width="stretch", hide_index=True)
        st.json(media_library, expanded=False)
        if edit_project:
            job = video_jobs.get(project) if project else None
            if job and job.encoder:
                st.caption(f"Kurgu kodlayıcısı: {job.encoder} · {job.elapsed:.0f} sn")
            st.dataframe(clip_rows(edit_project), width="stretch", hide_index=True)
            st.json(edit_project, expanded=False)
