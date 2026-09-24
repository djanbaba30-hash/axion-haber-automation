"""Tasarım Stüdyosu (Faz 5): kurgu → Axion şablonu (1080x1920), sade bir Canva.

Editör geldiğinde son video standart şablonla hazırdır (Video Stüdyosu kurguyla birlikte üretir). İsterse başlıkları,
yazı tipini, efektleri, çerçeveyi, arka planı değiştirir; yazı ekler; blur/mozaik koyar; videoyu yeniden oluşturur.
Canlı önizleme son videonun aynısını tarayıcıda gösterir. API yok.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from apps.axion_local.project_picker import project_selector, selected_project
from apps.axion_local.settings import secret
from apps.axion_local.store import FINAL_VIDEO_FILENAME, ROUGH_CUT_FILENAME, load_news_project
from apps.design_studio import assets, template
from apps.design_studio.blur import clean_blurs
from apps.design_studio.design import Design, TextLayer, TextStyle
from apps.design_studio.editor import (
    block_data,
    design_editor,
    frame_data,
    image_bytes,
    media_url,
    share_button,
)
from apps.design_studio.effects import FRAME_STYLES, LOGO_EFFECTS, SLOGAN_EFFECTS, TEXT_ENTER, TEXT_EXIT
from apps.design_studio.pipeline import (
    background_path,
    final_is_current,
    load_project_design,
    project_timing,
    render_project_final,
    save_project_design,
)
from apps.design_studio.render import preview_video
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
from shared.text_layout import STRIKE, parse_lines

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


def init(name: str, value) -> str:
    """Widget'ın ilk değeri tasarımdan; sonrası Streamlit'te (value= ile çakışma uyarısı olmasın diye)."""
    if key(name) not in ss:
        ss[key(name)] = value
    return key(name)


def save() -> None:
    save_project_design(project, design)


def options_index(options: list, value) -> int:
    return options.index(value) if value in options else 0


# ---------------------------------------------------------------- tuvaldeki değişiklikler (blur, yazı konumu, seçim)
editor_key = key("editor")
editor_state = ss.get(editor_key)
edits = editor_state.get("edits") if hasattr(editor_state, "get") else None  # bileşen durumu (önceki çalıştırmadan)
if isinstance(edits, dict) and edits.get("v") != ss.get(key("edits_v")):
    ss[key("edits_v")] = edits.get("v")
    design.blurs = clean_blurs(edits.get("blurs"), seconds)
    for layer in design.texts:
        position = (edits.get("texts") or {}).get(layer.id)
        if isinstance(position, list) and len(position) == 2:
            layer.x, layer.y = (min(1.0, max(0.0, float(v))) for v in position)
    selected = edits.get("selected_text")
    if selected and any(layer.id == selected for layer in design.texts):
        ss[key("text_select")] = selected
    save()

left, right = st.columns([5, 7], gap="large")  # önce sağ doldurulur (tuval, düzenlemelerden sonra çizilsin)


# ---------------------------------------------------------------- sağ: durum + düğmeler + düzenleme sekmeleri
def style_editor(style: TextStyle, name: str, sizes: tuple[int, int]) -> bool:
    """Yazı tipi, kalınlık, boyut, renk, parıltı, büyük harf (başlıklar ve yazılar için ortak)."""
    fonts = families()
    names = list(fonts) or [style.family]
    c1, c2, c3 = st.columns([3, 2, 2])
    family = c1.selectbox("Yazı tipi", names, key=init(f"{name}_family", style.family if style.family in names else names[0]))
    weights = fonts.get(family, [style.style])
    if ss.get(key(f"{name}_style")) not in weights:
        ss[key(f"{name}_style")] = style.style if style.style in weights else weights[-1]
    weight = c2.selectbox("Kalınlık", weights, key=key(f"{name}_style"))
    size = c3.number_input("Boyut", sizes[0], sizes[1], step=2, key=init(f"{name}_size", style.size))
    c4, c5, c6 = st.columns([2, 3, 2], vertical_alignment="bottom")
    color = c4.color_picker("Renk", key=init(f"{name}_color", style.color))
    glow = c5.slider("Parıltı", 0.0, 1.0, step=0.05, key=init(f"{name}_glow", float(style.glow)))
    upper = c6.toggle("BÜYÜK HARF", key=init(f"{name}_upper", style.upper))
    new = (family, weight, int(size), color.upper(), float(glow), bool(upper))
    old = (style.family, style.style, style.size, style.color.upper(), style.glow, style.upper)
    style.family, style.style, style.size, style.color, style.glow, style.upper = new
    return new != old


def strike_editor(text_key: str, name: str) -> None:
    """Sansür: seçilen kelimelerin üstü videoda çizilir (metinde ~~kelime~~ olarak saklanır)."""
    lines = parse_lines(ss.get(text_key, ""), upper=False)
    words = [t for line in lines for t in line]
    labels = [f"{i + 1}. {t.text}" for i, t in enumerate(words)]
    ss[key(f"{name}_strike")] = [label for label, t in zip(labels, words) if t.strike]

    def apply() -> None:
        chosen = set(ss[key(f"{name}_strike")])
        index, out = 0, []
        for line in parse_lines(ss.get(text_key, ""), upper=False):
            parts = []
            for token in line:
                label = f"{index + 1}. {token.text}"
                parts.append(f"{STRIKE}{token.text}{STRIKE}" if label in chosen else token.text)
                index += 1
            out.append(" ".join(parts))
        ss[text_key] = "\n".join(out)

    st.multiselect("Üstünü çiz (sansür)", labels, key=key(f"{name}_strike"), on_change=apply,
                   placeholder="✂️ Sansür: üstü çizilecek kelimeyi seç", label_visibility="collapsed")


def fit_note(text: str, style: TextStyle) -> None:
    block = template.headline_block(text, style)
    lines = len({w.line for w in block.words})
    if block.fits:
        st.caption(f"✅ {lines} satır, {block.size} px")
    else:
        st.caption(f"⚠️ {style.size} px'te 2 satıra sığmadı; {block.size} px'e küçüldü ({lines} satır). Başlığı kısaltmak daha iyi.")


with right:
    top = st.container()  # durum ve düğmeler: düzenlemeler uygulandıktan sonra doldurulur
    tab_headlines, tab_texts, tab_effects, tab_background, tab_assets = st.tabs(
        ["✏️ Başlıklar", "🔤 Yazılar", "✨ Efektler", "🖼️ Arka plan", "📦 Varlıklar"]
    )
    changed = False

    with tab_headlines:
        for number, (headline, start_label) in enumerate(((design.headline_1, "0–9 sn"), (design.headline_2, "13 sn → son")), 1):
            text_key = init(f"h{number}_text", headline.text)
            head_col, enter_col, exit_col = st.columns([4, 2, 2], vertical_alignment="bottom")
            head_col.markdown(f"**Başlık {number}** · {start_label}")
            enter = enter_col.selectbox("Giriş", list(TEXT_ENTER), format_func=TEXT_ENTER.get, key=init(f"h{number}_enter", headline.enter))
            exit_ = exit_col.selectbox("Çıkış", list(TEXT_EXIT), format_func=TEXT_EXIT.get, key=init(f"h{number}_exit", headline.exit))
            text = st.text_area(f"Başlık {number}", key=text_key, height=68, label_visibility="collapsed",
                                help="Satırı istediğin yerden bölmek için Enter. Sansür için aşağıdan kelime seç.")
            strike_editor(text_key, f"h{number}")
            fit_note(text, design.headline_style)
            if (text, enter, exit_) != (headline.text, headline.enter, headline.exit):
                headline.text, headline.enter, headline.exit = text, enter, exit_
                changed = True
        with st.container(border=True):
            st.caption("Başlık yazısı (iki başlık için)")
            changed |= style_editor(design.headline_style, "hs", (30, 90))

    with tab_texts:
        ids = [layer.id for layer in design.texts]
        pick_col, add_col, del_col = st.columns([5, 2, 1], vertical_alignment="bottom")
        if add_col.button("➕ Yazı ekle", width="stretch"):
            new_id = f"yazi{max([int(i[4:]) for i in ids if i[4:].isdigit()] + [0]) + 1}"
            design.texts.append(TextLayer(id=new_id, text="YAZI", start=0.0, end=min(5.0, seconds)))
            ss[key("text_select")] = new_id
            save()
            st.rerun()
        if not design.texts:
            st.caption("Videoya kalıcı yazı ekle (ör. yer, tarih, kaynak). Konumunu önizlemede sürükleyerek ayarla.")
        else:
            if ss.get(key("text_select")) not in ids:
                ss[key("text_select")] = ids[0]
            labels = {layer.id: f"{i + 1}. {layer.text.splitlines()[0][:28] if layer.text.strip() else '(boş)'}" for i, layer in enumerate(design.texts)}
            chosen = pick_col.selectbox("Yazı", ids, format_func=labels.get, key=key("text_select"))
            layer = next(l for l in design.texts if l.id == chosen)
            if del_col.button("🗑", help="Bu yazıyı sil", width="stretch"):
                design.texts = [l for l in design.texts if l.id != chosen]
                for name in [k for k in ss.keys() if str(k).startswith(key(f"t_{chosen}_"))]:
                    del ss[name]  # aynı adla eklenecek yeni yazı eski değerleri almasın
                save()
                st.rerun()
            name = f"t_{chosen}"
            text = st.text_area("Metin", key=init(f"{name}_text", layer.text), height=68, label_visibility="collapsed")
            strike_editor(key(f"{name}_text"), name)
            c1, c2 = st.columns(2)
            enter = c1.selectbox("Giriş", list(TEXT_ENTER), format_func=TEXT_ENTER.get, key=init(f"{name}_enter", layer.enter))
            exit_ = c2.selectbox("Çıkış", list(TEXT_EXIT), format_func=TEXT_EXIT.get, key=init(f"{name}_exit", layer.exit))
            start, end = st.slider("Görünme aralığı (sn)", 0.0, float(seconds), step=0.1,
                                   key=init(f"{name}_range", (float(layer.start), float(min(layer.end, seconds)))))
            changed |= style_editor(layer, name, (16, 160))
            if (text, enter, exit_, start, end) != (layer.text, layer.enter, layer.exit, layer.start, layer.end):
                layer.text, layer.enter, layer.exit, layer.start, layer.end = text, enter, exit_, start, max(end, start + 0.2)
                changed = True
            st.caption("Konum: önizlemede yazıyı sürükle.")

    with tab_effects:
        frame = design.frame
        c1, c2, c3 = st.columns([3, 2, 2], vertical_alignment="bottom")
        style = c1.selectbox("Video çerçevesi", list(FRAME_STYLES), format_func=FRAME_STYLES.get, key=init("frame_style", frame.style))
        color = c2.color_picker("Çizgi rengi", key=init("frame_color", frame.color))
        accent = c3.color_picker("Işık rengi", key=init("frame_accent", frame.accent))
        speed = st.slider("Animasyon hızı", 0.25, 3.0, step=0.25, key=init("frame_speed", float(frame.speed)),
                          disabled=style in ("sabit", "yok"))
        if (style, color.upper(), accent.upper(), speed) != (frame.style, frame.color.upper(), frame.accent.upper(), frame.speed):
            frame.style, frame.color, frame.accent, frame.speed = style, color.upper(), accent.upper(), speed
            changed = True
        st.divider()
        for label, item, effects_map in (("Sloganlar (9–13 sn)", design.slogans, SLOGAN_EFFECTS), ("Logo kutusu (15–18 sn)", design.logo, LOGO_EFFECTS)):
            c1, c2 = st.columns([2, 3], vertical_alignment="bottom")
            name = "slogans" if item is design.slogans else "logo"
            enabled = c1.toggle(label, key=init(f"{name}_on", item.enabled))
            effect = c2.selectbox("Efekt", list(effects_map), format_func=effects_map.get, key=init(f"{name}_effect", item.effect),
                                  disabled=not enabled, label_visibility="collapsed")
            if (enabled, effect) != (item.enabled, item.effect):
                item.enabled, item.effect = enabled, effect
                changed = True

    with tab_background:
        items = assets.backgrounds()
        daily = assets.background_for_day(project.work_day)
        st.caption(f"Günün arka planı: **{daily.stem.replace('_', ' ')}** (her gün 02:00'de sıradakine geçer).")
        columns = st.columns(5)
        for index, path in enumerate([None, *items]):
            column = columns[index % 5]
            shown = daily if path is None else path
            column.image(image_bytes(template.background_image(shown).resize((108, 192)), "JPEG", quality=80), width="stretch")
            selected = (design.background is None) if path is None else (design.background == path.name)
            label = ("✓ " if selected else "") + ("Günün" if path is None else path.stem.split("_")[-1])
            if column.button(label, key=key(f"bg_{index}"), width="stretch", type="primary" if selected else "secondary"):
                design.background = None if path is None else path.name
                save()
                st.rerun()

    with tab_assets:
        token = secret("GITHUB_TOKEN")
        st.caption(
            "Yeni yazı tipi (.ttf, .otf) veya arka plan (1080×1920 PNG/JPG) ekle. Bu bilgisayarda hemen kullanılır; "
            + ("GitHub'a da yüklenir." if token else "GitHub'a da yüklensin istersen `windows\\anahtarlar.bat` ile GITHUB_TOKEN ekle.")
        )
        uploads = st.file_uploader("Varlık", type=["ttf", "otf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   key=key("uploads"), label_visibility="collapsed")
        if uploads and st.button("Ekle", type="primary"):
            for upload in uploads:
                kind = "font" if upload.name.lower().endswith((".ttf", ".otf")) else "arka_plan"
                try:
                    path, repo_path = assets.save_asset(kind, upload.name, upload.getvalue())
                    note = f"✅ {path.name} eklendi."
                    if token:
                        assets.upload_to_github(repo_path, upload.getvalue(), token)
                        note += " GitHub'a da yüklendi."
                    st.success(note)
                except (ValueError, RuntimeError, OSError) as error:
                    st.error(f"{upload.name}: {error}")
        fonts = families()
        st.caption("Yazı tipleri: " + " · ".join(f"{name} ({len(styles)})" for name, styles in fonts.items()))
        st.caption(f"Arka planlar: {len(items)}")

    if changed:
        save()

    with top:
        current = final_is_current(project, design)
        status_col, render_col = st.columns([3, 2], vertical_alignment="center")
        if not final.exists():
            status_col.info("Son video yok.")
        elif current:
            status_col.success("Son video hazır ve güncel.")
        else:
            status_col.warning("Değişiklikler son videoya işlenmedi.")
        label = "🎬 Yeniden oluştur" if final.exists() else "🎬 Oluştur"
        if render_col.button(label, type="secondary" if current else "primary", width="stretch"):
            try:
                with st.spinner("Son video oluşturuluyor..."):
                    render_project_final(project, design)
            except (RuntimeError, ValueError, FileNotFoundError) as error:
                st.error("Son video oluşturulamadı.")
                st.code(str(error))
            else:
                st.rerun()
        if final.exists():
            download_col, share_col = st.columns(2)
            download_col.download_button("⬇️ İndir", final.read_bytes(), file_name=f"{pid}.mp4", mime="video/mp4",
                                         width="stretch", help=None if current else "Son oluşturulan hâl (değişiklikler hariç).")
            with share_col:
                share_button(final, f"{pid}.mp4", package.caption, key=key("share"))

    st.caption("Paylaşım metni")
    st.code(package.caption, language=None, wrap_lines=True, height=120)


# ---------------------------------------------------------------- sol: canlı önizleme ve son video
@st.cache_data(show_spinner=False, max_entries=24)
def _background_jpeg(path: str, mtime: float) -> bytes:
    return image_bytes(template.background_image(Path(path)).resize((540, 960)), "JPEG", quality=85)


with left:
    preview_tab, final_tab = st.tabs(["🎨 Canlı önizleme", "🎬 Son video"])
    with preview_tab:
        with st.spinner("Önizleme hazırlanıyor..."):
            preview = preview_video(rough_cut, project.folder / "onizleme")
        background = background_path(project, design)
        scene = template.build_scene(design, seconds)
        slot = {"x": VIDEO_SLOT["x"], "y": VIDEO_SLOT["y"], "w": VIDEO_SLOT["width"], "h": VIDEO_SLOT["height"]}
        logo_image = template.logo_box()
        data = {
            "project": pid,
            "video": media_url(preview, "video/mp4", "video"),
            "duration": seconds,
            "fps": fps,
            "slot": slot,
            "images": {"bg": media_url(_background_jpeg(str(background), background.stat().st_mtime), "image/jpeg", "bg")},
            "frame": frame_data(design.frame, slot, FRAME_BORDER, FRAME_RADIUS),
            "times": {"h1_end": template.HEADLINE_1_END, "h2_start": HEADLINE_2_ENTER_START},
            "blocks": {
                "h1": block_data(scene.headline_1, "h1", enter=design.headline_1.enter, exit=design.headline_1.exit),
                "h2": block_data(scene.headline_2, "h2", enter=design.headline_2.enter, exit=design.headline_2.exit),
                "texts": [
                    block_data(block, f"t_{layer.id}", id=layer.id, label=layer.text.splitlines()[0][:16],
                               enter=layer.enter, exit=layer.exit, start=layer.start, end=layer.end)
                    for layer, block in scene.layers
                ],
            },
            "slogans": {
                "enabled": design.slogans.enabled, "effect": design.slogans.effect, "center": list(template.slogan_center()),
                "items": [
                    {"url": media_url(image_bytes(template.slogan_image(s["file"])), "image/png", f"s{i}"),
                     "start": s["enter"][0], "end": s["exit"][1]}
                    for i, s in enumerate(SLOGANS)
                ],
            },
            "logo": {
                "enabled": design.logo.enabled, "effect": design.logo.effect, "url": media_url(image_bytes(logo_image), "image/png", "logo"),
                "center": list(template.logo_center()), "start": LOGO_RISE_START, "end": template.LOGO_END,
                "rest_y": LOGO_BOX["rest_y"], "tau": LOGO_RISE_TAU, "drop_start": LOGO_DROP_START, "glint": list(LOGO_GLINT),
            },
            "blurs": design.blurs,
            "selected_text": ss.get(key("text_select")),
        }
        design_editor(data, key=editor_key)
    with final_tab:
        if final.exists():
            st.video(str(final))
        else:
            st.info("Son video henüz yok.")
