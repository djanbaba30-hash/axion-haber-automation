"""Tasarım Stüdyosu (Faz 5): kaba kurgu → Axion şablonu (1080x1920), Canva'nın yerine.

Şablon kendiliğinden dolar: günün arka planı, başlıklar (düzeltilebilir), sloganlar, logo kutusu. Editör isterse
elle blur ekler (canlı önizlemede sürükleyerek). "Son videoyu oluştur" tek FFmpeg komutuyla MP4'ü üretir. API yok.
"""

from __future__ import annotations

import hashlib
import json

import streamlit as st

from apps.axion_local.project_picker import project_selector, selected_project
from apps.axion_local.store import (
    DESIGN_FILENAME,
    EDIT_PROJECT_FILENAME,
    FINAL_VIDEO_FILENAME,
    ROUGH_CUT_FILENAME,
    load_news_project,
    load_project_json,
    save_project_json,
)
from apps.design_studio import template
from apps.design_studio.blur import SHAPES, clean_blurs
from apps.design_studio.editor import design_editor, image_bytes, media_url
from apps.design_studio.render import preview_video, render_final, timeline_seconds
from shared.axion_template import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    HEADLINE_1_EXIT,
    HEADLINE_2_ENTER_START,
    LOGO_BOX,
    LOGO_DROP_SECONDS,
    LOGO_DROP_START,
    LOGO_RISE_START,
    SLOGANS,
    VIDEO_SLOT,
)

ss = st.session_state

st.set_page_config(page_title="Tasarım Stüdyosu · Axion", page_icon="🎨", layout="wide")
st.title("Tasarım Stüdyosu")

project = selected_project("design_project_id")
project_selector("design_project_id")
if not project:
    st.stop()
package, _ = load_news_project(project)
rough_cut = project.folder / ROUGH_CUT_FILENAME
if not rough_cut.exists():
    st.info("Bu haberin videosu henüz yok. Video Stüdyosu'nda **Videoyu oluştur**.")
    if st.button("Video Stüdyosu'na geç"):
        st.switch_page("apps/video_studio/page.py")
    st.stop()

design = load_project_json(project, DESIGN_FILENAME) or {}
timing = timeline_seconds(load_project_json(project, EDIT_PROJECT_FILENAME)) or (30, 20.0)
fps, seconds = timing


def save_design(**changes) -> None:
    design.update(changes)
    save_project_json(project, DESIGN_FILENAME, design)


@st.cache_data(show_spinner=False, max_entries=16)
def _background_jpeg(index: int) -> bytes:
    return image_bytes(template.background_image(index).resize((540, 960)), "JPEG", quality=85)


@st.cache_data(show_spinner=False, max_entries=16)
def _frame_png(index: int) -> bytes:
    return image_bytes(template.frame_overlay(index).resize((540, 960)))


@st.cache_data(show_spinner=False, max_entries=32)
def _headline_png(text: str) -> bytes:
    return image_bytes(template.render_headline(template.layout_headline(text)))


@st.cache_data(show_spinner=False, max_entries=4)
def _static_png(kind: str) -> bytes:
    if kind == "logo":
        return image_bytes(template.render_logo_box())
    return image_bytes(template.render_slogan(kind, 1.0))


daily_background = template.background_index(project.work_day)
settings_col, editor_col = st.columns([4, 5], gap="large")

with settings_col:
    headline_1 = st.text_area(
        "Başlık 1 (0–9 sn)", design.get("headline_1") or package.headline_1, height=80, key=f"tasarim_b1_{project.id}",
        help="Satırı istediğin yerden bölmek için Enter'a bas; yoksa iki satıra kendiliğinden bölünür.",
    )
    headline_2 = st.text_area(
        "Başlık 2 (13. sn'den sona kadar)", design.get("headline_2") or package.headline_2, height=80,
        key=f"tasarim_b2_{project.id}",
    )
    options = [0, *range(1, template.BACKGROUND_COUNT + 1)]
    background_choice = st.selectbox(
        "Arka plan",
        options,
        index=options.index(design.get("background") or 0) if (design.get("background") or 0) in options else 0,
        format_func=lambda i: f"Günün arka planı ({daily_background})" if i == 0 else f"Arka plan {i}",
        key=f"tasarim_arka_plan_{project.id}",
    )
    background = background_choice or daily_background
    changes = {}
    if headline_1 != (design.get("headline_1") or package.headline_1):
        changes["headline_1"] = headline_1
    if headline_2 != (design.get("headline_2") or package.headline_2):
        changes["headline_2"] = headline_2
    if (background_choice or None) != design.get("background"):
        changes["background"] = background_choice or None
    if changes:
        save_design(**changes)

with editor_col:
    with st.spinner("Önizleme hazırlanıyor..."):
        preview = preview_video(rough_cut, project.folder / "onizleme")
    blurs = clean_blurs(design.get("blurs"), seconds)
    edited = design_editor(
        {
            "project": project.id,
            "video": media_url(preview, "video/mp4", "video"),
            "duration": seconds,
            "fps": fps,
            "images": {
                "bg": media_url(_background_jpeg(background), "image/jpeg", "bg"),
                "frame": media_url(_frame_png(background), "image/png", "frame"),
                "h1": media_url(_headline_png(headline_1), "image/png", "h1"),
                "h2": media_url(_headline_png(headline_2), "image/png", "h2"),
                "s1": media_url(_static_png(SLOGANS[0]["file"]), "image/png", "s1"),
                "s2": media_url(_static_png(SLOGANS[1]["file"]), "image/png", "s2"),
                "logo": media_url(_static_png("logo"), "image/png", "logo"),
            },
            "slot": {"x": VIDEO_SLOT["x"], "y": VIDEO_SLOT["y"], "w": VIDEO_SLOT["width"], "h": VIDEO_SLOT["height"]},
            "strip_y": template.STRIP_Y,
            "strip_h": template.STRIP_HEIGHT,
            "logo": {"x": LOGO_BOX["x"], "y": LOGO_BOX["rest_y"], "w": LOGO_BOX["width"], "h": LOGO_BOX["height"]},
            "times": {
                "h1_end": HEADLINE_1_EXIT[1],
                "s1": [SLOGANS[0]["enter"][0], SLOGANS[0]["exit"][1]],
                "s2": [SLOGANS[1]["enter"][0], SLOGANS[1]["exit"][1]],
                "h2_start": HEADLINE_2_ENTER_START,
                "logo": [LOGO_RISE_START, LOGO_DROP_START + LOGO_DROP_SECONDS],
            },
            "shapes": SHAPES,
            "blurs": blurs,
            "canvas": [CANVAS_WIDTH, CANVAS_HEIGHT],
        },
        key=f"tasarim_editoru_{project.id}",
    )
    if edited is not None:
        cleaned = clean_blurs(edited, seconds)
        if cleaned != blurs:
            blurs = cleaned
            save_design(blurs=blurs)
    st.caption(
        "Önizlemede başlık ve sloganlar sabit görünür; animasyonlar son videoda. Blur için **+ Blur ekle**, videoyu "
        "istediğin ana getir ve kutuyu sürükle: her sürükleme o anda bir anahtar kare olur, kutu aralarda kendiliğinden kayar."
    )

with settings_col:
    final = project.folder / FINAL_VIDEO_FILENAME
    signature = hashlib.sha256(
        json.dumps([headline_1, headline_2, background, blurs, rough_cut.stat().st_mtime], ensure_ascii=False).encode()
    ).hexdigest()
    outdated = final.exists() and design.get("rendered") != signature
    label = "🎬 Son videoyu yeniden oluştur" if final.exists() else "🎬 Son videoyu oluştur"
    if st.button(label, type="primary", use_container_width=True):
        try:
            with st.spinner("Son video oluşturuluyor... (birkaç dakika sürebilir)"):
                render_final(rough_cut, headline_1, headline_2, background, fps, seconds, final, blurs)
        except (RuntimeError, ValueError, FileNotFoundError) as error:
            st.error("Son video oluşturulamadı.")
            st.code(str(error))
        else:
            save_design(rendered=signature)
            outdated = False
    if final.exists():
        if outdated:
            st.warning("Başlık, arka plan veya blurda değişiklik var; son videoya işlenmesi için yeniden oluştur.")
        st.video(str(final))
        st.download_button(
            "Son videoyu indir", final.read_bytes(), file_name=f"{project.id}.mp4", mime="video/mp4",
            use_container_width=True,
        )
    st.caption("Paylaşım metni")
    st.code(package.caption, language=None, wrap_lines=True)
