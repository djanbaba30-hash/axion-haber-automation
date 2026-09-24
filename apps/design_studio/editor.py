"""Tasarım Stüdyosu canlı önizleme + blur/yazı editörü (Streamlit components v2; JS: `editor.js`). API yok.

Tuval son videonun aynısını gösterir: arka plan, video, blur/mozaik, çerçeve animasyonu, başlık/slogan/logo/yazı
efektleri. Yazılar Python'da (Pillow) kelime kelime çizilip tek bir "atlas" PNG olarak gönderilir; tarayıcı yalnızca
yerleştirir ve canlandırır. Editörün tuvaldeki değişiklikleri (blurlar, yazı konumları, seçili yazı) `edits` durumuyla
Python'a döner ve projeye kaydedilir.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image

from . import effects as fx
from .blur import EFFECTS, SHAPES
from .template import TextBlock

HTML = """
<div class="ax">
  <div class="stage-wrap"><canvas class="stage"></canvas><video class="vid" playsinline preload="auto"></video></div>
  <div class="bar">
    <button class="back" type="button" title="1 kare geri">⏮</button>
    <button class="play" type="button">▶</button>
    <button class="fwd" type="button" title="1 kare ileri">⏭</button>
    <span class="time">0,0 / 0,0 sn</span>
    <select class="speed" title="Oynatma hızı"><option value="1">1x</option><option value="0.5">0,5x</option><option value="0.25">0,25x</option></select>
  </div>
  <div class="timeline"><div class="rows"></div><div class="head"></div></div>
  <div class="tools">
    <button class="add-blur" type="button" title="Bulanıklaştırma kutusu ekle">+ Blur</button>
    <button class="add-mosaic" type="button" title="Mozaik kutusu ekle">+ Mozaik</button>
    <span class="chips"></span>
  </div>
  <div class="edit">
    <div class="grid">
      <label>Efekt<select class="effect"></select></label>
      <label>Şekil<select class="shape"></select></label>
      <label>Güç<input class="strength" type="range" min="1" max="10" step="1"></label>
      <label>Opaklık<input class="opacity" type="range" min="10" max="100" step="5"></label>
      <label>Yumuşak kenar<input class="feather" type="range" min="0" max="100" step="5"></label>
      <label>Açı<input class="angle" type="range" min="-180" max="180" step="1"></label>
    </div>
    <div class="btns">
      <button class="square" type="button" title="Genişliğe göre kare yap">▢ Kare</button>
      <button class="set-start" type="button">⇤ Başla: şimdi</button>
      <button class="set-end" type="button">Bitir: şimdi ⇥</button>
      <button class="prev-key" type="button" title="Önceki anahtar kare">◆◀</button>
      <button class="next-key" type="button" title="Sonraki anahtar kare">▶◆</button>
      <button class="del-key" type="button" title="Bu andaki anahtar kareyi sil">◆✕</button>
      <button class="del-blur" type="button" title="Kutuyu sil">🗑</button>
    </div>
    <label class="live"><input class="track" type="checkbox"> Canlı takip: kutuya basılı tut, video yavaş oynarken sürükle</label>
    <div class="hint"></div>
  </div>
</div>
"""

CSS = """
.ax { font-family: var(--st-font, sans-serif); color: var(--st-text-color, #1B2B3A); font-size: 13px; max-width: 400px; }
.stage-wrap { position: relative; width: 100%; aspect-ratio: 9 / 16; border-radius: 10px; overflow: hidden;
  background: #0d1f24; touch-action: none; user-select: none; box-shadow: 0 6px 18px rgba(18,50,73,.18); }
.stage { width: 100%; height: 100%; display: block; cursor: crosshair; }
.vid { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; left: 0; top: 0; }
.bar { display: flex; gap: 6px; align-items: center; margin: 8px 0 6px; }
button, select { border: 1px solid #c9d3df; background: #fff; color: #123249; border-radius: 7px; padding: 3px 8px;
  cursor: pointer; font-size: 13px; }
button:hover { border-color: #123249; }
.play { min-width: 40px; font-size: 15px; background: #123249; color: #fff; border-color: #123249; }
.time { font-variant-numeric: tabular-nums; margin-left: 2px; flex: 1; }
.timeline { position: relative; background: #f1f4f8; border-radius: 7px; padding: 3px 0; cursor: pointer; touch-action: none; }
.row { position: relative; height: 14px; margin: 2px 0; }
.seg { position: absolute; top: 1px; height: 12px; border-radius: 3px; opacity: .9; font-size: 9px; color: #fff; overflow: hidden;
  white-space: nowrap; padding-left: 3px; box-sizing: border-box; line-height: 12px; }
.row.sel .seg { outline: 2px solid #123249; }
.key { position: absolute; top: 3px; width: 8px; height: 8px; margin-left: -4px; transform: rotate(45deg); background: #fff; border: 1px solid #123249; }
.head { position: absolute; top: 0; bottom: 0; width: 2px; background: #e5484d; pointer-events: none; }
.tools { display: flex; gap: 6px; align-items: center; margin: 8px 0 4px; flex-wrap: wrap; }
.add-blur, .add-mosaic { background: #123249; color: #fff; border-color: #123249; }
.chips { display: inline-flex; gap: 4px; flex-wrap: wrap; }
.chip { border-radius: 12px; padding: 2px 9px; }
.chip.sel { background: #BEE1E8; border-color: #123249; }
.edit { background: #f7f9fb; border: 1px solid #e3e9ef; border-radius: 8px; padding: 6px 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 10px; }
.grid label { display: flex; flex-direction: column; font-size: 11px; color: #4b5d6e; gap: 2px; }
.grid input[type=range] { width: 100%; accent-color: #123249; }
.btns { display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0 4px; }
.btns button { padding: 2px 7px; }
.live { display: flex; gap: 6px; align-items: center; font-size: 12px; }
.hint { font-size: 11px; color: #6b7c8c; margin-top: 2px; }
"""

JS = Path(__file__).with_name("editor.js").read_text(encoding="utf-8")

_MOUNTS: dict[str, Any] = {}


def _component(name: str, **parts: str):
    """Bileşen bu Streamlit çalışma ortamında kayıtlı değilse kaydeder (testlerde her uygulama yeni ortamdır)."""
    from streamlit.components.v2 import get_bidi_component_manager

    if name not in _MOUNTS or get_bidi_component_manager().get(name) is None:
        _MOUNTS[name] = st.components.v2.component(name, **parts)
    return _MOUNTS[name]


def media_url(content: bytes | Path, mimetype: str, name: str) -> str:
    """Tarayıcının indireceği adres: Streamlit'in medya sunucusu (video ileri/geri sarılabilir); olmazsa data URL."""
    try:
        from streamlit import runtime

        if runtime.exists():
            source = str(content) if isinstance(content, Path) else content
            return runtime.get_instance().media_file_mgr.add(source, mimetype, f"axion_tasarim.{name}")
    except Exception:  # noqa: BLE001 — medya sunucusu yoksa (ör. test) gömülü veriye düş
        pass
    raw = content.read_bytes() if isinstance(content, Path) else content
    return f"data:{mimetype};base64,{base64.b64encode(raw).decode('ascii')}"


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
        "comet": {"tail": fx.COMET_TAIL, "head": fx.COMET_HEAD},
    }


def design_editor(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Editörü gösterir. Tuvalde değişiklik olduysa {v, blurs, texts: {id: [x, y]}, selected_text} döner."""
    data = {**data, "shapes": SHAPES, "effects": EFFECTS}
    mount = _component("axion_tasarim_editoru", html=HTML, css=CSS, js=JS)
    result = mount(data=data, key=key, default={"edits": None}, on_edits_change=lambda: None)
    return result.edits


SHARE_HTML = """<button class="share" type="button">📤 Paylaş</button><div class="msg"></div>"""
SHARE_CSS = """
.share { width: 100%; border: 1px solid #c9d3df; background: #fff; color: #123249; border-radius: 8px; padding: 7px 10px;
  font-size: 14px; cursor: pointer; font-family: var(--st-font, sans-serif); }
.share:hover { border-color: #123249; }
.msg { font-size: 11px; color: #6b7c8c; margin-top: 3px; font-family: var(--st-font, sans-serif); }
"""
SHARE_JS = """
export default function (component) {
  const { data, parentElement } = component;
  const button = parentElement.querySelector('.share');
  const msg = parentElement.querySelector('.msg');
  button.onclick = async () => {
    if (!navigator.share || !window.isSecureContext) {
      msg.textContent = 'Paylaşım için Axion https adresiyle açılmalı (Tailscale serve). Şimdilik İndir ile al.';
      return;
    }
    try {
      button.disabled = true; msg.textContent = 'Hazırlanıyor...';
      const blob = await (await fetch(data.url)).blob();
      const file = new File([blob], data.filename, { type: 'video/mp4' });
      if (navigator.canShare && !navigator.canShare({ files: [file] })) { msg.textContent = 'Bu cihaz video paylaşımını desteklemiyor.'; return; }
      await navigator.share({ files: [file], text: data.text || '' });
      msg.textContent = '';
    } catch (e) {
      msg.textContent = e && e.name === 'AbortError' ? '' : 'Paylaşılamadı: ' + e;
    } finally { button.disabled = false; }
  };
}
"""



def share_button(video: Path, filename: str, text: str, key: str) -> None:
    """Telefon/tablette Android paylaşım menüsünü açar (Instagram, TikTok, YouTube...). HTTPS gerektirir."""
    mount = _component("axion_paylas", html=SHARE_HTML, css=SHARE_CSS, js=SHARE_JS)
    mount(data={"url": media_url(video, "video/mp4", "paylas"), "filename": filename, "text": text}, key=key)
