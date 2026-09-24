import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.news_package import NewsPackage

from modules.audio_ingestion import (
    probe_audio,
    save_uploaded_audio,
)

from modules.edit_plan import (
    build_edit_project,
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
                                video_path
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

            try:
                openai_api_key = st.secrets.get("OPENAI_API_KEY")
            except Exception:
                openai_api_key = None

            if not openai_api_key:
                raise RuntimeError("OPENAI_API_KEY Streamlit secrets içinde tanımlı değil.")


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

                    openai_api_key,
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
# HABER + TTS
# =================================================

if (
    "media_library"
    in st.session_state
):

    st.divider()

    news_col, audio_col = st.columns(
        [2, 1]
    )


    # =============================================
    # HABER
    # =============================================

    with news_col:

        st.write("**Haber metni / NewsPackage**")

        package_upload = st.file_uploader(
            "Axion Haber NewsPackage JSON",
            type=["json"],
            label_visibility="collapsed",
            key="news_package_upload",
        )

        imported_package = None
        if package_upload:
            try:
                imported_package = NewsPackage.model_validate_json(package_upload.getvalue())
                st.success("NewsPackage okundu.")
            except Exception as error:
                st.error(f"NewsPackage okunamadı: {error}")

        default_news = imported_package.caption if imported_package else ""
        news_text = st.text_area(
            "Haber metni",
            value=default_news,
            placeholder="Axion Haber'den oluşturduğun haber metnini buraya ekle.",
            height=180,
            label_visibility="collapsed",
        )


    # =============================================
    # TTS
    # =============================================

    with audio_col:

        st.write("**TTS ses dosyası**")

        uploaded_audio = st.file_uploader(
            "TTS ses dosyasını seç",

            type=None,

            accept_multiple_files=False,

            label_visibility="collapsed",
        )


        audio_path = None

        audio_metadata = None


        if uploaded_audio:

            try:

                audio_path = (
                    save_uploaded_audio(
                        uploaded_audio
                    )
                )


                audio_metadata = (
                    probe_audio(
                        audio_path
                    )
                )


                st.caption(
                    (
                        f"{uploaded_audio.name}\n\n"
                        f"Süre: "
                        f"{audio_metadata['duration_formatted']}"
                    )
                )


            except Exception as error:

                st.error(
                    "TTS dosyası okunamadı."
                )

                st.exception(
                    error
                )


# =================================================
# PROJEYİ HAZIRLA
# =================================================

if (
    "media_library"
    in st.session_state
):

    if st.button(
        "Projeyi hazırla",
        type="primary",
        use_container_width=True,
    ):

        if (
            "news_text"
            not in locals()
            or not news_text.strip()
        ):

            st.warning(
                "Önce haber metnini ekle."
            )

        elif (
            "audio_path"
            not in locals()
            or audio_path is None
            or audio_metadata is None
        ):

            st.warning(
                "Önce TTS ses dosyasını ekle."
            )

        else:

            edit_project = (
                build_edit_project(

                    media_library=(
                        st.session_state[
                            "media_library"
                        ]
                    ),

                    news_text=(
                        news_text.strip()
                    ),

                    audio_path=str(
                        audio_path
                    ),

                    audio_duration_seconds=(
                        audio_metadata[
                            "duration_seconds"
                        ]
                    ),
                )
            )


            st.session_state[
                "edit_project"
            ] = edit_project


            # Kullanıcıya ekstra başarı
            # mesajı göstermiyoruz.
            #
            # Bir sonraki aşamada burası
            # doğrudan Edit Plan ekranına
            # dönüşecek.


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
