import hashlib
import hmac
import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.audio_ingestion import (
    probe_audio,
    save_uploaded_audio,
)

from modules.edit_plan import (
    build_edit_project,
    validate_edit_project,
)

from modules.news_package import (
    parse_news_package_bytes,
)

from modules.media_library import (
    build_image_asset,
    build_media_library,
    detect_media_type,
)

from modules.representative_sampling import (
    extract_representative_frames,
)

from modules.shot_detection import (
    detect_shots,
)

from modules.video_asset import (
    build_video_asset,
)

from modules.video_ingestion import (
    create_proxy,
    probe_video,
    save_uploaded_video,
)

from modules.visual_analysis import (
    analyze_media_with_luna,
)


def secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value).strip() if value else None


def require_secrets() -> None:
    missing = [name for name in ("APP_PASSWORD", "OPENAI_API_KEY") if not secret(name)]
    if missing:
        st.error("Eksik Streamlit secret: " + ", ".join(missing))
        st.code('APP_PASSWORD = "..."\nOPENAI_API_KEY = "..."')
        st.stop()


def check_password() -> bool:
    expected = secret("APP_PASSWORD")
    if not expected:
        st.error("APP_PASSWORD secret tanımlı değil.")
        return False
    if st.session_state.get("video_password_correct"):
        return True

    def entered() -> None:
        st.session_state.video_password_correct = hmac.compare_digest(
            str(st.session_state.get("video_password", "")).encode("utf-8"),
            expected.encode("utf-8"),
        )
        st.session_state.pop("video_password", None)

    st.text_input("Şifre", type="password", key="video_password", on_change=entered)
    if st.session_state.get("video_password_correct") is False:
        st.error("Şifre yanlış.")
    return False


# =================================================
# ANALİZ SEÇENEKLERİ
# =================================================

ANALYSIS_OPTIONS = {
    "Ekonomik — 1 frame / shot": 1,
    "Dengeli — 2 frame / shot": 2,
    "Ayrıntılı — 3 frame / shot": 3,
    "Maksimum — 4 frame / shot": 4,
}


# =================================================
# STREAMLIT
# =================================================

st.set_page_config(
    page_title="Axion Video Studio",
    page_icon="🎬",
    layout="wide",
)

require_secrets()
if not check_password():
    st.stop()


# =================================================
# BAŞLIK
# =================================================

st.title("Axion Video Studio")

st.caption(
    "Haber videon için video ve görselleri yükle."
)


# =================================================
# ANALİZ + MEDYA YÜKLEME
# =================================================

analysis_col, upload_col = st.columns(
    [1, 2]
)


# =================================================
# ANALİZ
# =================================================

with analysis_col:

    st.write("**Analiz**")

    analysis_mode = st.selectbox(
        "Analiz yoğunluğu",
        options=list(
            ANALYSIS_OPTIONS.keys()
        ),
        index=0,
        label_visibility="collapsed",
    )

    selected_frame_count = (
        ANALYSIS_OPTIONS[
            analysis_mode
        ]
    )

    st.caption(
        f"{selected_frame_count} frame / shot"
    )


# =================================================
# MEDYA YÜKLEME
# =================================================

with upload_col:

    st.write("**Video ve görseller**")

    uploaded_files = st.file_uploader(
        "Video ve görselleri seç",

        type=[
            "mp4",
            "mov",
            "mkv",
            "avi",
            "webm",
            "m4v",
            "jpg",
            "jpeg",
            "png",
            "webp",
        ],

        accept_multiple_files=True,

        label_visibility="collapsed",
    )


# =================================================
# SEÇİLEN DOSYA SAYISI
# =================================================

if uploaded_files:

    st.caption(
        f"{len(uploaded_files)} medya seçildi."
    )


# =================================================
# MEDYALARI HAZIRLA
# =================================================

if uploaded_files:

    if st.button(
        "Medyaları hazırla",
        type="primary",
        use_container_width=True,
    ):

        try:

            video_assets = []

            all_shots = []

            all_images = []

            video_counter = 0
            image_counter = 0


            # =========================================
            # DOSYALAR
            # =========================================

            for uploaded_file in uploaded_files:

                media_type = detect_media_type(
                    uploaded_file.name
                )


                # =====================================
                # VIDEO
                # =====================================

                if media_type == "video":

                    video_counter += 1

                    asset_id = (
                        f"video_{video_counter:03d}"
                    )


                    with st.spinner(
                        "Videolar hazırlanıyor..."
                    ):

                        video_path = (
                            save_uploaded_video(
                                uploaded_file
                            )
                        )


                        metadata = probe_video(
                            video_path
                        )


                        metadata[
                            "original_filename"
                        ] = uploaded_file.name


                        metadata[
                            "original_path"
                        ] = str(
                            video_path
                        )


                        proxy_path = (
                            create_proxy(
                                video_path,
                                duration_seconds=metadata.get(
                                    "duration_seconds"
                                ),
                            )
                        )


                        proxy_size_mb = round(
                            proxy_path.stat().st_size
                            / (1024 * 1024),
                            2,
                        )


                        metadata[
                            "proxy"
                        ] = {
                            "path": str(
                                proxy_path
                            ),

                            "size_mb": (
                                proxy_size_mb
                            ),

                            "width": 960,
                        }


                        shots = detect_shots(
                            proxy_path,

                            metadata[
                                "duration_seconds"
                            ],
                        )


                        shots = (
                            extract_representative_frames(
                                proxy_path,

                                shots,

                                frame_count=(
                                    selected_frame_count
                                ),
                            )
                        )


                    # -----------------------------
                    # Shot ID
                    # -----------------------------

                    for shot in shots:

                        shot[
                            "asset_id"
                        ] = asset_id


                        shot[
                            "shot_id"
                        ] = (
                            f"{asset_id}_shot_"
                            f"{int(shot['shot_number']):03d}"
                        )


                    video_asset = {
                        "asset_id": asset_id,

                        "asset_type": "video",

                        "source_metadata": metadata,

                        "shots": shots,

                        "sampling": {
                            "frame_count_per_shot": (
                                selected_frame_count
                            ),

                            "analysis_mode": (
                                analysis_mode
                            ),
                        },
                    }


                    video_assets.append(
                        video_asset
                    )


                    all_shots.extend(
                        shots
                    )


                # =====================================
                # IMAGE
                # =====================================

                elif media_type == "image":

                    image_counter += 1

                    extension = (
                        Path(
                            uploaded_file.name
                        )
                        .suffix
                        .lower()
                    )


                    temp_file = (
                        tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=extension,
                        )
                    )


                    try:

                        temp_file.write(
                            uploaded_file.getbuffer()
                        )

                        temp_file.flush()

                    finally:

                        temp_file.close()


                    image_path = Path(
                        temp_file.name
                    )


                    image_asset = (
                        build_image_asset(
                            uploaded_file,
                            image_counter,
                        )
                    )


                    image_asset[
                        "path"
                    ] = str(
                        image_path
                    )


                    all_images.append(
                        image_asset
                    )


            # =========================================
            # API KEY
            # =========================================

            if (
                "OPENAI_API_KEY"
                not in st.secrets
            ):

                raise RuntimeError(
                    "OPENAI_API_KEY bulunamadı."
                )


            # =========================================
            # LUNA
            # =========================================

            with st.spinner(
                "Medya analiz ediliyor..."
            ):

                (
                    analyzed_shots,
                    analyzed_images,
                    usage,
                ) = analyze_media_with_luna(

                    all_shots,

                    all_images,

                    st.secrets[
                        "OPENAI_API_KEY"
                    ],
                )


            # =========================================
            # SHOT EŞLEŞTİRME
            # =========================================

            analyzed_shots_by_id = {
                shot[
                    "shot_id"
                ]: shot

                for shot in analyzed_shots
            }


            # =========================================
            # VIDEO ASSET'LERİ
            # =========================================

            standardized_video_assets = []


            for video_asset in video_assets:

                final_shots = []


                for shot in video_asset[
                    "shots"
                ]:

                    shot_id = shot[
                        "shot_id"
                    ]


                    analyzed_shot = (
                        analyzed_shots_by_id.get(
                            shot_id
                        )
                    )


                    if analyzed_shot:

                        final_shots.append(
                            analyzed_shot
                        )

                    else:

                        final_shots.append(
                            shot
                        )


                standardized_asset = (
                    build_video_asset(

                        metadata=(
                            video_asset[
                                "source_metadata"
                            ]
                        ),

                        shots=final_shots,

                        usage=usage,

                        analysis_mode=(
                            video_asset[
                                "sampling"
                            ][
                                "analysis_mode"
                            ]
                        ),

                        frame_count_per_shot=(
                            selected_frame_count
                        ),

                        asset_id=(
                            video_asset[
                                "asset_id"
                            ]
                        ),
                    )
                )


                standardized_video_assets.append(
                    standardized_asset
                )


            # =========================================
            # IMAGE ASSET'LERİ
            # =========================================

            standardized_image_assets = []


            for image in analyzed_images:

                standardized_image_assets.append(
                    {
                        "asset_id": image[
                            "asset_id"
                        ],

                        "asset_type": "image",

                        "source": image[
                            "source"
                        ],

                        "analysis": {
                            "frame_count": 1,
                        },

                        "visual": image.get(
                            "visual_asset",
                            {},
                        ),

                        "path": image.get(
                            "path",
                            "",
                        ),
                    }
                )


            # =========================================
            # MEDIA LIBRARY
            # =========================================

            library_assets = (
                standardized_video_assets
                + standardized_image_assets
            )


            media_library = (
                build_media_library(

                    assets=library_assets,

                    usage=usage,
                )
            )


            # =========================================
            # SESSION STATE
            # =========================================

            st.session_state[
                "media_library"
            ] = media_library


            st.session_state[
                "analysis_usage"
            ] = usage


            st.session_state[
                "analysis_mode"
            ] = analysis_mode


            st.session_state[
                "selected_frame_count"
            ] = selected_frame_count


            # Yeni medya oluşturulduğunda
            # eski proje temizlenir.

            st.session_state.pop(
                "edit_project",
                None,
            )


            # Tek kullanıcı mesajı.

            video_count = len(
                standardized_video_assets
            )

            image_count = len(
                standardized_image_assets
            )

            st.session_state[
                "media_ready_message"
            ] = (
                f"{video_count} video, "
                f"{image_count} görsel hazır."
            )


        except Exception as error:

            st.error(
                "Medya hazırlanırken bir hata oluştu."
            )

            st.exception(
                error
            )


# =================================================
# MEDYA HAZIR DURUMU
# =================================================

if (
    "media_library"
    in st.session_state
):

    st.success(
        "Medya hazır."
    )


# =================================================
# HABER + TTS + NEWS PACKAGE
# =================================================

if "media_library" in st.session_state:

    st.divider()

    # -------------------------------------------------
    # İSTEĞE BAĞLI NEWS PACKAGE İÇE AKTARMA
    # -------------------------------------------------
    st.write("**Axion Haber bağlantısı**")
    package_file = st.file_uploader(
        "Axion Haber NewsPackage JSON",
        type=["json"],
        accept_multiple_files=False,
        key="news_package_uploader",
        help="Axion Haber'den alınan NewsPackage JSON'u yükleyebilirsin. İsteğe bağlıdır.",
    )

    if package_file:
        package_hash = hashlib.sha256(package_file.getvalue()).hexdigest()
        if st.session_state.get("loaded_news_package_hash") != package_hash:
            try:
                package = parse_news_package_bytes(package_file.getvalue())
                st.session_state["news_package"] = package
                st.session_state["loaded_news_package_hash"] = package_hash
                caption = package["news"].get("caption", "").strip()
                if caption:
                    st.session_state["project_news_text"] = caption
                st.session_state["project_package_message"] = "NewsPackage başarıyla içe aktarıldı."
            except Exception as error:
                st.error("NewsPackage okunamadı.")
                st.caption(str(error))

    if st.session_state.get("project_package_message"):
        st.success(st.session_state.pop("project_package_message"))

    news_col, audio_col = st.columns([2, 1])

    # -------------------------------------------------
    # HABER
    # -------------------------------------------------
    with news_col:
        st.write("**Haber metni**")
        news_text = st.text_area(
            "Haber metni",
            placeholder=(
                "Axion Haber'den oluşturduğun haber metnini buraya ekle."
            ),
            height=180,
            key="project_news_text",
            label_visibility="collapsed",
        )

        package = st.session_state.get("news_package")
        if package:
            package_news = package.get("news", {})
            package_info = []
            if package_news.get("headline_1"):
                package_info.append("2 başlık")
            if package_news.get("tts_text"):
                package_info.append("TTS metni")
            if package_news.get("source_text"):
                package_info.append("kaynak metni")
            if package_info:
                st.caption("NewsPackage: " + " · ".join(package_info) + " hazır.")

    # -------------------------------------------------
    # TTS
    # -------------------------------------------------
    with audio_col:
        st.write("**TTS ses dosyası**")
        uploaded_audio = st.file_uploader(
            "TTS ses dosyasını seç",
            type=["mp3", "wav", "m4a", "aac", "ogg", "flac"],
            accept_multiple_files=False,
            key="project_audio_uploader",
            label_visibility="collapsed",
        )

        audio_path = st.session_state.get("project_audio_path")
        audio_metadata = st.session_state.get("project_audio_metadata")

        if uploaded_audio:
            audio_hash = hashlib.sha256(uploaded_audio.getvalue()).hexdigest()
            if st.session_state.get("project_audio_hash") != audio_hash:
                try:
                    audio_path = save_uploaded_audio(uploaded_audio)
                    audio_metadata = probe_audio(audio_path)
                    audio_metadata = {
                        **audio_metadata,
                        "filename": uploaded_audio.name,
                        "mime_type": uploaded_audio.type or "audio/mpeg",
                        "size_bytes": len(uploaded_audio.getvalue()),
                    }
                    st.session_state["project_audio_hash"] = audio_hash
                    st.session_state["project_audio_path"] = str(audio_path)
                    st.session_state["project_audio_metadata"] = audio_metadata
                    st.session_state.pop("edit_project", None)
                except Exception as error:
                    st.error("TTS dosyası okunamadı.")
                    st.caption(str(error))
                    audio_path = None
                    audio_metadata = None

        if audio_metadata:
            st.caption(
                f"{audio_metadata.get('filename', 'TTS')} · "
                f"Süre: {audio_metadata.get('duration_formatted', '—')}"
            )

# =================================================
# PROJEYİ HAZIRLA
# =================================================

if "media_library" in st.session_state:

    st.divider()
    st.write("**Proje**")

    project_col, info_col = st.columns([2, 1])

    with project_col:
        prepare_project = st.button(
            "Projeyi hazırla",
            type="primary",
            use_container_width=True,
            key="prepare_edit_project",
        )

    with info_col:
        if st.session_state.get("edit_project"):
            st.success("EditProject hazır.")
        else:
            st.caption("Haber + TTS + Media Library hazır olduğunda proje oluşturulur.")

    if prepare_project:
        current_news_text = str(st.session_state.get("project_news_text", "")).strip()
        current_audio_path = st.session_state.get("project_audio_path")
        current_audio_metadata = st.session_state.get("project_audio_metadata")
        current_package = st.session_state.get("news_package")

        if not current_news_text:
            st.warning("Önce haber metnini ekle veya NewsPackage yükle.")
        elif not current_audio_path or not current_audio_metadata:
            st.warning("Önce TTS ses dosyasını ekle.")
        else:
            try:
                edit_project = build_edit_project(
                    media_library=st.session_state["media_library"],
                    news_text=current_news_text,
                    audio_path=str(current_audio_path),
                    audio_duration_seconds=float(
                        current_audio_metadata.get("duration_seconds", 0) or 0
                    ),
                    news_package=current_package,
                    audio_metadata=current_audio_metadata,
                )

                validation_errors = validate_edit_project(edit_project)
                if validation_errors:
                    st.error("EditProject doğrulaması başarısız.")
                    for validation_error in validation_errors:
                        st.write(f"- {validation_error}")
                else:
                    st.session_state["edit_project"] = edit_project
                    st.session_state["project_ready_message"] = True
                    st.rerun()
            except Exception as error:
                st.error("EditProject oluşturulamadı.")
                st.exception(error)

    if st.session_state.pop("project_ready_message", False):
        project = st.session_state.get("edit_project", {})
        audio = project.get("audio", {})
        media = project.get("media", {})
        plan = project.get("edit_plan", {})
        assets = media.get("assets", []) if isinstance(media, dict) else []
        video_count = sum(1 for asset in assets if asset.get("asset_type") == "video")
        image_count = sum(1 for asset in assets if asset.get("asset_type") == "image")

        st.success("EditProject hazır. Edit Plan aşamasına geçilebilir.")
        summary_cols = st.columns(5)
        summary_cols[0].metric("Haber", f"{len(project.get('news', {}).get('text', '')):,} karakter")
        summary_cols[1].metric("TTS", f"{float(audio.get('duration_seconds', 0)):.1f} sn")
        summary_cols[2].metric("Video", str(video_count))
        summary_cols[3].metric("Görsel", str(image_count))
        summary_cols[4].metric("Shot", str(sum(len(a.get('shots', [])) for a in assets if isinstance(a, dict))))
        st.caption(
            f"Timeline başlangıcı: {float(plan.get('timeline_duration_seconds', 0)):.3f} sn · "
            "Henüz otomatik medya seçimi yapılmadı."
        )

        project_json = json.dumps(project, ensure_ascii=False, indent=2)
        st.download_button(
            "EditProject JSON indir",
            data=project_json.encode("utf-8"),
            file_name="edit_project.json",
            mime="application/json",
            use_container_width=True,
            key="download_edit_project_json",
        )

# =================================================
# GELİŞTİRİCİ BİLGİLERİ
# =================================================

if (
    "media_library"
    in st.session_state
):

    usage = (
        st.session_state.get(
            "analysis_usage",
            {},
        )
    )


    with st.expander(
        "Geliştirici bilgileri"
    ):

        st.subheader(
            "Luna Kullanımı"
        )


        usage_col1, usage_col2, usage_col3, usage_col4 = (
            st.columns(4)
        )


        with usage_col1:

            st.metric(
                "Input Tokens",
                f'{usage.get("input_tokens", 0):,}',
            )


        with usage_col2:

            st.metric(
                "Output Tokens",
                f'{usage.get("output_tokens", 0):,}',
            )


        with usage_col3:

            st.metric(
                "Reasoning Tokens",
                f'{usage.get("reasoning_tokens", 0):,}',
            )


        with usage_col4:

            st.metric(
                "Toplam Tokens",
                f'{usage.get("total_tokens", 0):,}',
            )


        st.caption(
            f'Model: {usage.get("model", "—")} · '
            f'API Calls: {usage.get("api_calls", 0)} · '
            f'Görüntü: {usage.get("frame_count", 0)} · '
            f'Tahmini maliyet: '
            f'${usage.get("estimated_cost_usd", 0):.8f}'
        )


        st.divider()


        st.subheader(
            "Seçilen analiz"
        )


        st.write(
            st.session_state.get(
                "analysis_mode",
                "—",
            )
        )


        st.caption(
            (
                f'Video: '
                f'{st.session_state.get("selected_frame_count", 0)} '
                f'frame / shot · '
                f'Görsel: 1 frame'
            )
        )


        st.divider()


        st.subheader(
            "Media Library"
        )


        st.json(
            st.session_state[
                "media_library"
            ]
        )


        # =============================================
        # EDIT PROJECT
        # =============================================

        if (
            "edit_project"
            in st.session_state
        ):

            st.divider()

            st.subheader(
                "Edit Project"
            )

            st.json(
                st.session_state[
                    "edit_project"
                ]
            )
