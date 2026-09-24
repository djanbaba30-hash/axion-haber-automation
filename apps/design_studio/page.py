"""Tasarım Stüdyosu (Faz 5): kurgu → Axion şablonu (1080x1920), sade bir Canva.

Editör geldiğinde son video standart şablonla hazırdır (Video Stüdyosu kurguyla birlikte üretir). Kenar çubuğunda
durum, Yeniden oluştur/İndir ve başlık metinleri; ana alanda Canva benzeri editör (ortada video, üstte yazı araç
çubuğu, solda seçili öğenin animasyon/blur paneli, sağda arka plan ve çerçeve, altta katmanlı zaman çizelgesi). API yok.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from apps.axion_local.project_picker import project_selector, selected_project
from apps.axion_local.settings import secret
from apps.axion_local.store import FINAL_VIDEO_FILENAME, ROUGH_CUT_FILENAME
from apps.design_studio import assets, template
from apps.design_studio.design import apply_editor_patch, dump_design
from apps.design_studio.editor import block_data, design_editor, frame_data, image_bytes, media_url
from apps.design_studio.effects import FRAME_STYLES, LOGO_EFFECTS, SLOGAN_EFFECTS, TEXT_ENTER, TEXT_EXIT
from apps.design_studio.pipeline import (
    background_path,
    final_is_current,
    load_project_design,
    project_timing,
    render_project_final,
    save_project_design,
)
from apps.design_studio.render import filmstrip, preview_video
from shared.axion_template import (
    FRAME_BORDER,
    FRAME_RADIUS,
    HEADLINE_2_ENTER_START,
    LOGO_BOX,
    LOGO_DROP_START,
    LOGO_GLINT,
    LOGO_RISE_START,
    LOGO_RISE_TAU,
    SLOGANS,
    VIDEO_SLOT,
)
from shared.fonts import families
from shared.text_layout import toggle_strike

ss = st.session_state

st.set_page_config(page_title="Tasarım Stüdyosu · Axion", page_icon="🎨", layout="wide")
# Editör tüm genişliği ve ekran yüksekliğini kullansın (genel stil ana alanı 1080 px ile sınırlıyor).
st.html('<style>[data-testid="stMainBlockContainer"], .block-container '
        '{padding-top: 1rem !important; max-width: 1640px !important;}</style>')

project = selected_project("design_project_id")
project_selector("design_project_id")
if not project:
    st.stop()
rough_cut = project.folder / ROUGH_CUT_FILENAME
if not rough_cut.exists():
    st.info("Bu haberin videosu henüz yok. Video Stüdyosu'nda **Videoyu oluştur**.")
    if st.button("Video Stüdyosu'na geç"):
        st.switch_page("apps/video_studio/page.py")
    st.stop()

pid = project.id
fps, seconds = project_timing(project)
design = load_project_design(project, seconds)
final = project.folder / FINAL_VIDEO_FILENAME

# Editör geldiğinde video hazır olsun: eski projelerde (Video Stüdyosu'nun otomatik üretiminden önce) burada üretilir.
if not final.exists() and not ss.get(f"ds_{pid}_auto_failed"):
    with st.spinner("Son video standart şablonla hazırlanıyor..."):
        try:
            render_project_final(project, design)
        except (RuntimeError, ValueError, FileNotFoundError) as error:
            ss[f"ds_{pid}_auto_failed"] = True
            st.error(f"Son video hazırlanamadı: {error}")
    design = load_project_design(project, seconds)


def key(name: str) -> str:
    return f"ds_{pid}_{name}"


def save() -> None:
    save_project_design(project, design)


# ---------------------------------------------------------------- editörden gelen değişiklikler (önceki çalıştırma)
editor_key = key("editor")
editor_state = ss.get(editor_key)
edits = editor_state.get("edits") if hasattr(editor_state, "get") else None
h1_key, h2_key = key("h1_text"), key("h2_text")
ss.setdefault(h1_key, design.headline_1.text)
ss.setdefault(h2_key, design.headline_2.text)
if isinstance(edits, dict) and edits.get("v") != ss.get(key("edits_v")):
    ss[key("edits_v")] = edits.get("v")
    design = apply_editor_patch(design, edits.get("design"), seconds)
    for op in edits.get("ops") or []:  # tuvalde kelimeye tıklayıp sansür çizgisi
        if not isinstance(op, dict) or op.get("op") != "strike" or not isinstance(op.get("index"), int):
            continue
        target = op.get("target")
        if target in ("h1", "h2"):
            text_key = h1_key if target == "h1" else h2_key
            ss[text_key] = toggle_strike(ss[text_key], op["index"])
        else:
            for layer in design.texts:
                if f"text:{layer.id}" == target:
                    layer.text = toggle_strike(layer.text, op["index"])
    save()


# ---------------------------------------------------------------- kenar çubuğu: durum, düğmeler, başlıklar, varlıklar
def fit_caption(text: str) -> None:
    block = template.headline_block(text, design.headline_style)
    lines = len({w.line for w in block.words})
    if block.fits:
        st.caption(f"✅ {lines} satır · {block.size} px")
    else:
        st.caption(f"⚠️ 2 satıra sığmadı, {block.size} px'e küçüldü. Kısaltmak daha iyi.")


with st.sidebar:
    status_box = st.container()
    st.markdown("**Başlıklar**")
    headline_1 = st.text_area("Başlık 1 · 0–9 sn", key=h1_key, height=80,
                              help="Enter ile satırı böl. Sansür: araç çubuğunda S̶, sonra videoda kelimeye tıkla.")
    fit_caption(headline_1)
    headline_2 = st.text_area("Başlık 2 · 13 sn → son", key=h2_key, height=80)
    fit_caption(headline_2)
    if (headline_1, headline_2) != (design.headline_1.text, design.headline_2.text):
        design.headline_1.text, design.headline_2.text = headline_1, headline_2
        save()

    with st.expander("📦 Yazı tipi / arka plan ekle"):
        token = secret("GITHUB_TOKEN")
        st.caption("Bu bilgisayarda hemen kullanılır; " + ("GitHub'a da yüklenir." if token else "GitHub için GITHUB_TOKEN gerekir."))
        uploads = st.file_uploader("Varlık", type=["ttf", "otf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   key=key("uploads"), label_visibility="collapsed")
        if uploads and st.button("Ekle", type="primary", width="stretch"):
            for upload in uploads:
                kind = "font" if upload.name.lower().endswith((".ttf", ".otf")) else "arka_plan"
                try:
                    path, repo_path = assets.save_asset(kind, upload.name, upload.getvalue())
                    if token:
                        assets.upload_to_github(repo_path, upload.getvalue(), token)
                    st.success(f"{path.name} eklendi" + (" (GitHub'a da)." if token else "."))
                except (ValueError, RuntimeError, OSError) as error:
                    st.error(f"{upload.name}: {error}")

    with status_box:
        current = final_is_current(project, design)
        if not final.exists():
            st.info("Son video yok.")
        elif current:
            st.success("Son video hazır ve güncel.")
        else:
            st.warning("Değişiklikler son videoya işlenmedi.")
        if st.button("🎬 Yeniden oluştur" if final.exists() else "🎬 Oluştur", type="secondary" if current else "primary",
                     width="stretch"):
            try:
                with st.spinner("Son video oluşturuluyor..."):
                    render_project_final(project, design)
            except (RuntimeError, ValueError, FileNotFoundError) as error:
                st.error("Son video oluşturulamadı.")
                st.code(str(error))
            else:
                st.rerun()
        if final.exists():
            st.download_button("⬇️ İndir", final.read_bytes(), file_name=f"{pid}.mp4", mime="video/mp4", width="stretch",
                               help=None if current else "Son oluşturulan hâl (değişiklikler hariç).")
        st.divider()


# ---------------------------------------------------------------- ana alan: editör
@st.cache_data(show_spinner=False, max_entries=24)
def _background_jpeg(path: str, mtime: float, width: int) -> bytes:
    return image_bytes(template.background_image(Path(path)).resize((width, width * 16 // 9)), "JPEG", quality=85)


with st.spinner("Önizleme hazırlanıyor..."):
    preview = preview_video(rough_cut, project.folder / "onizleme")
    strip = filmstrip(preview, project.folder / "onizleme", seconds)
background = background_path(project, design)
daily = assets.background_for_day(project.work_day)
scene = template.build_scene(design, seconds)
slot = {"x": VIDEO_SLOT["x"], "y": VIDEO_SLOT["y"], "w": VIDEO_SLOT["width"], "h": VIDEO_SLOT["height"]}
data = {
    "project": pid,
    "video": media_url(preview, "video/mp4", "video"),
    "final": media_url(final, "video/mp4", "final") if final.exists() else None,
    "filmstrip": media_url(strip, "image/jpeg", "strip") if strip else None,
    "duration": seconds,
    "fps": fps,
    "slot": slot,
    "images": {"bg": media_url(_background_jpeg(str(background), background.stat().st_mtime, 540), "image/jpeg", "bg")},
    "frame_geom": frame_data(design.frame, slot, FRAME_BORDER, FRAME_RADIUS),
    "times": {"h1_end": template.HEADLINE_1_END, "h2_start": HEADLINE_2_ENTER_START},
    "design": dump_design(design),
    "headlines": {"h1": design.headline_1.text, "h2": design.headline_2.text},
    "blocks": {
        "h1": block_data(scene.headline_1, "h1"),
        "h2": block_data(scene.headline_2, "h2"),
        "texts": {layer.id: block_data(block, f"t_{layer.id}") for layer, block in scene.layers},
    },
    "slogans": [
        {"url": media_url(image_bytes(template.slogan_image(s["file"])), "image/png", f"s{i}"), "start": s["enter"][0],
         "end": s["exit"][1], "center": list(template.slogan_center())}
        for i, s in enumerate(SLOGANS)
    ],
    "logo": {
        "url": media_url(image_bytes(template.logo_box()), "image/png", "logo"), "center": list(template.logo_center()),
        "start": LOGO_RISE_START, "end": template.LOGO_END, "rest_y": LOGO_BOX["rest_y"], "tau": LOGO_RISE_TAU,
        "drop_start": LOGO_DROP_START, "glint": list(LOGO_GLINT),
    },
    "fonts": families(),
    "backgrounds": [
        {"name": path.name, "label": path.stem.split("_")[-1],
         "url": media_url(_background_jpeg(str(path), path.stat().st_mtime, 90), "image/jpeg", f"bg_{path.stem}")}
        for path in assets.backgrounds()
    ],
    "daily": daily.name,
    "labels": {"enter": TEXT_ENTER, "exit": TEXT_EXIT, "slogan": SLOGAN_EFFECTS, "logo": LOGO_EFFECTS, "frame": FRAME_STYLES},
}
design_editor(data, key=editor_key)
