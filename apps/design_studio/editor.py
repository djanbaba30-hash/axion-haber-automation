"""Tasarım Stüdyosu canlı önizleme + blur/yazı editörü (Streamlit components v2; JS: `editor.js`). API yok.

Tuval son videonun aynısını gösterir: arka plan, video, blur/mozaik, çerçeve animasyonu, başlık/slogan/logo/yazı
efektleri. Yazılar Python'da (Pillow) kelime kelime çizilip tek bir "atlas" PNG olarak gönderilir; tarayıcı yalnızca
yerleştirir ve canlandırır. Editörün tuvaldeki değişiklikleri (blurlar, yazı konumları, seçili yazı) `edits` durumuyla
Python'a döner ve projeye kaydedilir.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image

from apps.axion_local.media import media_url  # noqa: F401 — page.py buradan alır

from . import effects as fx
from .blur import EFFECTS, SHAPES
from .template import TextBlock

HTML = """
<div class="ax">
  <div class="topbar">
    <div class="modes"><button data-mode="edit" class="on">🎨 Düzenle</button><button data-mode="final">🎬 Son video</button></div>
    <div class="hist"><button class="undo" type="button" title="Geri al (Ctrl+Z)" disabled>↶</button><button class="redo" type="button" title="Yinele (Ctrl+Y)" disabled>↷</button></div>
    <div class="ctx"></div>
    <span class="saved" data-state=""></span>
    <span class="final-state" data-state="" title="Son video (kenar çubuğunda oluştur / indir)"></span>
    <button class="help" type="button" title="Klavye kısayolları (?)">⌨</button>
    <div class="keys"><b>Kısayollar</b>
      <span><kbd>Boşluk</kbd> oynat / durdur</span><span><kbd>←</kbd> <kbd>→</kbd> 1 kare · <kbd>Shift</kbd> ile 1 sn</span>
      <span><kbd>Ctrl</kbd>+<kbd>Z</kbd> geri al · <kbd>Ctrl</kbd>+<kbd>Y</kbd> yinele</span><span><kbd>Ctrl</kbd>+<kbd>D</kbd> seçiliyi çoğalt</span>
      <span><kbd>Delete</kbd> seçiliyi sil · <kbd>Esc</kbd> seçimi bırak</span><span><kbd>S</kbd> sansür modu · <kbd>K</kbd> blura anahtar kare</span>
      <span><kbd>L</kbd> döngü · <kbd>Home</kbd>/<kbd>End</kbd> başa/sona</span><span>Zaman çizelgesinde klibe çift tıkla: başına git</span></div>
  </div>
  <div class="main">
    <aside class="left panel"></aside>
    <div class="center">
      <div class="stage-wrap">
        <canvas class="stage"></canvas>
        <video class="finalvid" controls playsinline></video>
        <div class="msg-final">Son video henüz yok. Kenar çubuğundan <b>Oluştur</b>.</div>
        <video class="vid" playsinline preload="auto"></video>
      </div>
    </div>
    <aside class="right panel"></aside>
  </div>
  <div class="transport">
    <button class="back" type="button" title="1 kare geri">⏮</button>
    <button class="play" type="button">▶</button>
    <button class="fwd" type="button" title="1 kare ileri">⏭</button>
    <span class="time">0,0 / 0,0 sn</span>
    <select class="speed" title="Oynatma hızı"><option value="1">1x</option><option value="0.5">0,5x</option><option value="0.25">0,25x</option></select>
    <button class="loop" type="button" title="Döngüde oynat (L)">🔁</button>
    <span class="grow"></span>
    <button class="t-add-text" type="button">➕ Yazı</button>
    <button class="t-add-blur" type="button">◍ Blur</button>
    <button class="t-add-mosaic" type="button">▦ Mozaik</button>
  </div>
  <div class="tl"><div class="tracks"></div><div class="playhead"></div></div>
</div>
"""

CSS = """
.ax { --navy: #123249; --sky: #BEE1E8; --lime: #D0E491; --line: #e1e7ee; --soft: #f5f8fb; --label: 74px;
  font-family: var(--st-font, sans-serif); color: #1B2B3A; font-size: 13px; container-type: inline-size; }
button, select, input, textarea { font-family: inherit; font-size: 13px; }
button, select { border: 1px solid #cfd8e2; background: #fff; color: var(--navy); border-radius: 8px; padding: 5px 9px; cursor: pointer; }
button:hover { border-color: var(--navy); }
button.on { background: var(--sky); border-color: var(--navy); }
.muted { color: #6b7c8c; } .small { font-size: 12px; }
/* üst çubuk (Canva araç çubuğu) */
.topbar { display: flex; gap: 10px; align-items: center; background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 6px 8px; box-shadow: 0 2px 8px rgba(18,50,73,.06); min-height: 42px; flex-wrap: wrap; }
.modes { display: inline-flex; gap: 2px; background: var(--soft); border-radius: 9px; padding: 2px; }
.modes button { border: 0; background: transparent; }
.modes button.on { background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.ctx { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; flex: 1; }
.ctx .tag { font-weight: 600; color: var(--navy); margin-right: 4px; }
.ctx select { max-width: 160px; }
.size { display: inline-flex; align-items: center; border: 1px solid #cfd8e2; border-radius: 8px; }
.size button { border: 0; padding: 5px 9px; } .size b { min-width: 28px; text-align: center; }
.color { position: relative; display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 30px;
  border: 1px solid #cfd8e2; border-radius: 8px; cursor: pointer; font-weight: 700; }
.color span { border-bottom: 4px solid; line-height: 16px; }
.color input { position: absolute; opacity: 0; inset: 0; width: 100%; height: 100%; cursor: pointer; }
.tool { min-width: 34px; } .tool.danger:hover { border-color: #e5484d; color: #e5484d; }
.glow { display: inline-flex; gap: 4px; align-items: center; } .glow input { width: 80px; accent-color: var(--navy); }
.seg { display: inline-flex; border: 1px solid #cfd8e2; border-radius: 8px; overflow: hidden; }
.seg button { border: 0; border-radius: 0; } .seg.wide { display: flex; margin: 6px 0; } .seg.wide button { flex: 1; }
.topbar { position: relative; }
.hist { display: inline-flex; gap: 2px; } .hist button { min-width: 32px; } .hist button:disabled { opacity: .35; cursor: default; }
.saved { font-size: 12px; color: #6b7c8c; min-width: 90px; text-align: right; }
.saved[data-state=saved] { color: #2f8f5b; }
.final-state { font-size: 12px; padding: 3px 9px; border-radius: 999px; white-space: nowrap; background: #eef2f5; color: #6b7c8c; }
.final-state:empty { display: none; }
.final-state[data-state=current] { background: #e6f4ec; color: #2f8f5b; }
.final-state[data-state=stale] { background: #fdf1dc; color: #9a6212; }
.final-state[data-state=rendering] { background: #e7f1fb; color: #2b6cb0; }
.help { min-width: 32px; }
.keys { display: none; position: absolute; right: 8px; top: 46px; z-index: 20; background: #fff; border: 1px solid var(--line);
  border-radius: 10px; padding: 10px 12px; box-shadow: 0 8px 24px rgba(18,50,73,.18); flex-direction: column; gap: 5px; font-size: 12px; }
.keys.show { display: flex; }
kbd { background: var(--soft); border: 1px solid #cfd8e2; border-bottom-width: 2px; border-radius: 5px; padding: 0 5px; font-size: 11px; font-family: inherit; }
/* üç sütun */
.main { display: grid; grid-template-columns: minmax(210px, 1fr) auto minmax(210px, 1fr); gap: 14px; margin: 12px 0; align-items: start; }
.panel { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; max-height: 660px; overflow: auto; }
.panel h4 { margin: 10px 0 6px; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #4b5d6e; }
.panel h4:first-child { margin-top: 0; }
.center { display: flex; justify-content: center; }
.stage-wrap { position: relative; height: clamp(360px, calc(100vh - 400px), 640px); aspect-ratio: 9 / 16; border-radius: 14px; overflow: hidden;
  background: #0d1f24; touch-action: none; user-select: none; box-shadow: 0 10px 28px rgba(18,50,73,.22); }
.stage, .finalvid { width: 100%; height: 100%; display: block; } .stage { cursor: crosshair; }
.finalvid { display: none; background: #000; }
.msg-final { position: absolute; inset: 0; display: none; align-items: center; justify-content: center; color: #fff; padding: 20px; text-align: center; }
.vid { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; left: 0; top: 0; }
/* panel öğeleri */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(86px, 1fr)); gap: 6px; }
.card { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 8px 4px; border-radius: 10px; font-size: 12px; }
.card.on { background: #e9f6f9; border: 2px solid var(--navy); }
.demo { font-weight: 800; font-size: 20px; color: #7a3ff2; display: inline-flex; height: 26px; }
.demo i { font-style: normal; display: inline-block; }
.demo-merge i:nth-child(odd) { animation: mergeL 1.6s infinite; } .demo-merge i:nth-child(even) { animation: mergeR 1.6s infinite; }
@keyframes mergeL { 0%,15% { transform: translateX(-10px); opacity: 0 } 50%,100% { transform: none; opacity: 1 } }
@keyframes mergeR { 0%,15% { transform: translateX(10px); opacity: 0 } 50%,100% { transform: none; opacity: 1 } }
.demo-fade i { animation: fadeA 1.6s infinite; } @keyframes fadeA { 0%,10% { opacity: 0 } 50%,100% { opacity: 1 } }
.demo-slide i { animation: slideA 1.6s infinite; } .demo-slide i:nth-child(2) { animation-delay: .12s } .demo-slide i:nth-child(3) { animation-delay: .24s }
@keyframes slideA { 0%,10% { transform: translateY(12px); opacity: 0 } 45%,100% { transform: none; opacity: 1 } }
.demo-typewriter i { animation: typeA 1.6s infinite steps(1); } .demo-typewriter i:nth-child(2) { animation-delay: .25s } .demo-typewriter i:nth-child(3) { animation-delay: .5s }
@keyframes typeA { 0% { opacity: 0 } 20%,100% { opacity: 1 } }
.demo-pop { animation: popA 1.6s infinite; } @keyframes popA { 0%,10% { transform: scale(.5); opacity: 0 } 40% { transform: scale(1.1); opacity: 1 } 55%,100% { transform: scale(1) } }
.demo-old_tv { animation: tvA 1.6s infinite; } @keyframes tvA { 0%,10% { transform: scale(.05,.08) } 25% { transform: scale(1,.12) } 50%,100% { transform: none } }
.demo-slow_baseline { animation: baseA 1.6s infinite; } @keyframes baseA { 0%,10% { transform: translateY(16px); opacity: 0 } 60%,100% { transform: none; opacity: 1 } }
.demo-yok { color: #9aa7b4; }
.fdemo { width: 24px; height: 32px; border-radius: 5px; background: #0d1f24; display: block; }
.frames { grid-template-columns: repeat(auto-fill, minmax(72px, 1fr)); } .frames .card { padding: 6px 2px; font-size: 11px; }
.f-sabit { box-shadow: inset 0 0 0 3px #f6f6f6; } .f-yok { box-shadow: inset 0 0 0 1px #33444f; }
.f-nefes { animation: breathe 2.4s infinite; } @keyframes breathe { 0%,100% { box-shadow: inset 0 0 0 2px #f6f6f6, 0 0 2px #BEE1E8 } 50% { box-shadow: inset 0 0 0 4px #fff, 0 0 12px #BEE1E8 } }
.f-kovalayan { background: conic-gradient(from 0deg, #fff 0 8%, #0d1f24 8% 50%, #fff 50% 58%, #0d1f24 58%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; padding: 3px; }
.f-akis { background: conic-gradient(#f6f6f6, #BEE1E8, #D0E491, #f6f6f6);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; padding: 3px; }
.bgs { display: grid; grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 6px; }
.bg { aspect-ratio: 9 / 16; padding: 0; background-size: cover; background-position: center; position: relative; border-radius: 8px; border: 2px solid transparent; }
.bg.on { border-color: var(--navy); box-shadow: 0 0 0 2px var(--sky); }
.bg span { position: absolute; bottom: 2px; left: 2px; right: 2px; font-size: 10px; background: rgba(18,50,73,.75); color: #fff; border-radius: 4px; }
.slider { display: block; margin: 6px 0 10px; } .slider span { display: flex; justify-content: space-between; font-size: 12px; color: #4b5d6e; }
.slider input { width: 100%; accent-color: var(--navy); height: 24px; }
.row2, .row3 { display: grid; gap: 6px; align-items: end; margin: 4px 0; } .row2 { grid-template-columns: 1fr 1fr auto; } .row3 { grid-template-columns: 1fr 1fr 1fr; }
.row2 label { display: flex; flex-direction: column; font-size: 11px; color: #4b5d6e; } .row2 input[type=number] { width: 100%; box-sizing: border-box; padding: 5px; border: 1px solid #cfd8e2; border-radius: 8px; }
.color-row { display: flex !important; flex-direction: row !important; align-items: center; gap: 6px; } .color-row input { width: 40px; height: 28px; border: 0; background: none; }
.stack { display: flex; flex-direction: column; gap: 6px; } .big { padding: 10px; font-size: 14px; text-align: left; } .wide { width: 100%; text-align: left; }
textarea { width: 100%; box-sizing: border-box; border: 1px solid #cfd8e2; border-radius: 8px; padding: 6px; resize: vertical; }
.switch { display: flex; gap: 8px; align-items: center; } .switch input { width: 18px; height: 18px; accent-color: var(--navy); }
.big-switch { margin: 10px 0 4px; padding: 8px; background: var(--soft); border-radius: 8px; font-weight: 600; }
/* oynatma ve zaman çizelgesi (Canva düzeni) */
.transport { display: flex; gap: 6px; align-items: center; background: #fff; border: 1px solid var(--line); border-bottom: 0;
  border-radius: 12px 12px 0 0; padding: 6px 10px; }
.transport .play { min-width: 42px; background: var(--navy); color: #fff; border-color: var(--navy); font-size: 15px; }
.transport .time { font-variant-numeric: tabular-nums; min-width: 100px; } .transport .grow { flex: 1; }
.tl { position: relative; background: #fff; border: 1px solid var(--line); border-radius: 0 0 12px 12px; padding: 4px 10px 10px; touch-action: none; user-select: none; }
.tl.dim { opacity: .45; pointer-events: none; }
.trow { display: flex; align-items: stretch; height: 30px; margin: 4px 0; } .trow.tall { height: 44px; } .trow.ruler { height: 18px; margin: 0; }
.tlabel { width: var(--label); flex: none; font-size: 11px; color: #6b7c8c; display: flex; align-items: center; }
.ttrack { position: relative; flex: 1; background: var(--soft); border-radius: 7px; cursor: pointer; }
.ruler .ttrack { background: transparent; }
.tick { position: absolute; top: 10px; width: 1px; height: 6px; background: #c5cfd9; font-style: normal; }
.tick.major { top: 0; height: 16px; }
.tick { font-size: 10px; color: #6b7c8c; text-indent: 3px; line-height: 10px; white-space: nowrap; }
.clip { position: absolute; top: 0; bottom: 0; border-radius: 7px; background: var(--c); color: #fff; overflow: hidden; box-sizing: border-box;
  display: flex; align-items: center; padding: 0 8px; font-size: 11px; font-weight: 700; white-space: nowrap; cursor: pointer; }
.clip span { overflow: hidden; text-overflow: ellipsis; pointer-events: none; }
.clip img { height: 22px; border-radius: 4px; }
.clip.off { opacity: .35; background-image: repeating-linear-gradient(45deg, rgba(255,255,255,.35) 0 4px, transparent 4px 9px); }
.clip.sel { box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--navy); z-index: 2; }
.clip.drag { cursor: grab; }
.clip .edge { position: absolute; top: 0; bottom: 0; width: 10px; cursor: ew-resize; background: rgba(255,255,255,.35); }
.clip .edge.l { left: 0; } .clip .edge.r { right: 0; }
.clip .key { position: absolute; top: 50%; width: 9px; height: 9px; margin: -5px 0 0 -5px; transform: rotate(45deg); background: #fff; border: 1px solid var(--navy); }
.film { position: absolute; inset: 0; border-radius: 7px; background-size: 100% 100%; background-color: #26343f; }
.bgtrack { position: absolute; inset: 0; border-radius: 7px; background-size: auto 100%; background-repeat: repeat-x; opacity: .9; }
.playhead { position: absolute; top: 2px; bottom: 6px; width: 2px; background: #e5484d; pointer-events: none; z-index: 5; }
.playhead::before { content: ""; position: absolute; top: -2px; left: -5px; width: 12px; height: 12px; border-radius: 50%; background: #e5484d; }
/* dar ekran (tablet dikey): sütunlar alt alta */
@container (max-width: 860px) { .main { grid-template-columns: 1fr; } .center { order: -1; } .panel { max-height: none; } }
"""

# Efekt süre/mesafeleri effects.py ile aynı kaynaktan (effects.json) gelir; tek JSON satırı olarak gömülür.
JS = Path(__file__).with_name("editor.js").read_text(encoding="utf-8").replace("/*FX*/null", json.dumps(fx.FX, ensure_ascii=False), 1)

_MOUNTS: dict[str, Any] = {}


def _component(name: str, **parts: str):
    """Bileşen bu Streamlit çalışma ortamında kayıtlı değilse kaydeder (testlerde her uygulama yeni ortamdır)."""
    from streamlit.components.v2 import get_bidi_component_manager

    if name not in _MOUNTS or get_bidi_component_manager().get(name) is None:
        _MOUNTS[name] = st.components.v2.component(name, **parts)
    return _MOUNTS[name]


def image_bytes(image: Image.Image, fmt: str = "PNG", **options: Any) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt, **options)
    return buffer.getvalue()


def block_atlas(block: TextBlock) -> tuple[bytes, list[dict[str, int]]]:
    """Kelime sprite'larını yan yana tek PNG'ye dizer; her kelimenin atlas içindeki yeri ve kanvastaki konumu."""
    gap = 2
    width = sum(w.image.width + gap for w in block.words) or 1
    height = max((w.image.height for w in block.words), default=1)
    atlas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    words, x = [], 0
    for word in block.words:
        atlas.paste(word.image, (x, 0))
        words.append({"sx": x, "sy": 0, "sw": word.image.width, "sh": word.image.height, "x": word.x, "y": word.y, "line": word.line})
        x += word.image.width + gap
    return image_bytes(atlas), words


def block_data(block: TextBlock, key: str, **extra: Any) -> dict[str, Any]:
    atlas, words = block_atlas(block)
    return {
        "atlas": media_url(atlas, "image/png", key), "words": words, "lines": block.lines,
        "center": list(block.center), "bbox": list(block.bbox()), **extra,
    }


def frame_data(frame: Any, slot: dict[str, int], border: int, radius: int) -> dict[str, Any]:
    return {
        "style": frame.style, "color": frame.color, "accent": frame.accent, "speed": frame.speed,
        "slot": slot, "border": border, "radius": radius, "periods": fx.FRAME_PERIOD,
        "comet": {"tail": fx.COMET_TAIL, "head": fx.COMET_HEAD, "base": fx.COMET_BASE, "base_alpha": fx.COMET_BASE_ALPHA},
        "breath": {"width": fx.BREATH_WIDTH, "glow": fx.BREATH_GLOW}, "flow_width": fx.FLOW_WIDTH,
    }


def design_editor(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Editörü gösterir. Tuvalde değişiklik olduysa {v, blurs, texts: {id: [x, y]}, selected_text} döner."""
    data = {**data, "shapes": SHAPES, "effects": EFFECTS}
    mount = _component("axion_tasarim_editoru", html=HTML, css=CSS, js=JS)
    result = mount(data=data, key=key, default={"edits": None}, on_edits_change=lambda: None)
    return result.edits

