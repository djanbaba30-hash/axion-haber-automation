"""Tasarım Stüdyosu canlı önizleme + elle blur editörü (Streamlit components v2, tarayıcıda çalışır; API yok).

Önizleme: arka plan, video alanında kurgu videosu, çerçeve, o anki başlık/slogan ve logo kutusu (animasyonlar son
videoda). Blur: kutu ekle, şekil/güç/opaklık ayarla, videoyu bir ana getirip kutuyu sürükle → o anda anahtar kare.
"Canlı takip" açıkken video yavaş oynar; basılı tutup sürükledikçe her 0,1 sn'de anahtar kare yazılır.
Blur listesi her değişiklikte Python'a gönderilir (`blurs` durumu) ve projeye kaydedilir.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image

HTML = """
<div class="ax">
  <div class="stage-wrap"><div class="stage">
    <img class="bg" alt="">
    <div class="slot"><video class="vid" playsinline preload="auto"></video><div class="blurs"></div></div>
    <img class="frame" alt="">
    <img class="strip" alt="">
    <img class="logo" alt="">
  </div></div>
  <div class="controls">
    <button class="play" type="button">▶</button>
    <span class="time">0,0 / 0,0 sn</span>
    <select class="speed" title="Oynatma hızı">
      <option value="1">1x</option><option value="0.5">0,5x</option><option value="0.25">0,25x</option>
    </select>
  </div>
  <div class="timeline"><div class="rows"></div><div class="head"></div></div>
  <div class="panel">
    <div class="list"></div>
    <button class="add" type="button">+ Blur ekle</button>
    <div class="edit">
      <label>Şekil <select class="shape"></select></label>
      <label>Güç <input class="strength" type="range" min="1" max="10" step="1"></label>
      <label>Opaklık <input class="opacity" type="range" min="10" max="100" step="5"></label>
      <div class="btns">
        <button class="set-start" type="button">Başlangıç: şu an</button>
        <button class="set-end" type="button">Bitiş: şu an</button>
        <button class="prev-key" type="button">◀ Anahtar</button>
        <button class="next-key" type="button">Anahtar ▶</button>
        <button class="del-key" type="button">Bu anahtarı sil</button>
        <button class="del-blur" type="button">Blur'u sil</button>
      </div>
      <label class="live"><input class="track" type="checkbox"> Canlı takip: video yavaş oynarken kutuyu basılı tutup sürükle</label>
      <div class="hint"></div>
    </div>
  </div>
</div>
"""

CSS = """
.ax { font-family: var(--st-font, sans-serif); color: var(--st-text-color, #123249); font-size: 14px; }
.stage-wrap { position: relative; width: 100%; max-width: 405px; aspect-ratio: 9 / 16; overflow: hidden;
  border-radius: 8px; background: #000; touch-action: none; user-select: none; }
.stage { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform-origin: 0 0; }
.stage img { position: absolute; pointer-events: none; }
.bg, .frame { left: 0; top: 0; width: 1080px; height: 1920px; }
.slot { position: absolute; overflow: hidden; background: #111; }
.vid { width: 100%; height: 100%; object-fit: fill; display: block; }
.blurs { position: absolute; inset: 0; }
.bl { position: absolute; box-sizing: border-box; cursor: move; }
.bl.sel { outline: 3px dashed #7fd3ff; }
.bl .handle { display: none; position: absolute; right: -14px; bottom: -14px; width: 28px; height: 28px;
  background: #7fd3ff; border-radius: 50%; cursor: nwse-resize; }
.bl.sel .handle { display: block; }
.controls { display: flex; gap: 8px; align-items: center; margin: 8px 0 4px; max-width: 405px; }
.controls button, .panel button { border: 1px solid #c9d3df; background: #fff; color: #123249; border-radius: 6px;
  padding: 4px 10px; cursor: pointer; }
.controls .play { min-width: 44px; font-size: 16px; }
.panel button.add { background: #123249; color: #fff; border-color: #123249; margin: 6px 0; }
.timeline { position: relative; max-width: 405px; background: #f1f4f8; border-radius: 6px; padding: 4px 0; cursor: pointer; touch-action: none; }
.row { position: relative; height: 16px; margin: 3px 0; }
.seg { position: absolute; top: 2px; height: 12px; border-radius: 3px; opacity: 0.85; font-size: 9px; color: #fff;
  overflow: hidden; white-space: nowrap; padding-left: 3px; box-sizing: border-box; line-height: 12px; }
.key { position: absolute; top: 3px; width: 9px; height: 9px; margin-left: -5px; transform: rotate(45deg);
  background: #fff; border: 1px solid #123249; }
.row.sel .seg { outline: 2px solid #123249; }
.head { position: absolute; top: 0; bottom: 0; width: 2px; background: #e5484d; pointer-events: none; }
.panel { max-width: 405px; margin-top: 8px; }
.list { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { border: 1px solid #c9d3df; border-radius: 14px; padding: 2px 10px; cursor: pointer; background: #fff; }
.chip.sel { background: #123249; color: #fff; border-color: #123249; }
.edit label { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
.edit input[type=range] { flex: 1; }
.btns { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
.live { font-size: 13px; }
.hint { font-size: 12px; opacity: 0.75; }
"""

JS = """
const STATE = new WeakMap();
const COLORS = { h1: '#123249', s: '#2f8f5b', h2: '#1f6fb2', logo: '#7a8699', blur: '#e08a1e' };
const fmt = (t) => t.toFixed(1).replace('.', ',');
const r3 = (t) => Math.round(t * 1000) / 1000;

function boxAt(blur, t) {
  const k = blur.keys;
  if (t <= k[0].t) return { ...k[0] };
  for (let i = 0; i < k.length - 1; i++) {
    const a = k[i], b = k[i + 1];
    if (a.t <= t && t <= b.t) {
      const p = b.t > a.t ? (t - a.t) / (b.t - a.t) : 1;
      return { t, x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, w: a.w + (b.w - a.w) * p, h: a.h + (b.h - a.h) * p };
    }
  }
  return { ...k[k.length - 1] };
}

function setKey(blur, t, box, tolerance) {
  const key = { t: r3(t), x: box.x, y: box.y, w: box.w, h: box.h };
  const i = blur.keys.findIndex((k) => Math.abs(k.t - t) <= tolerance);
  if (i >= 0) blur.keys[i] = key; else blur.keys.push(key);
  blur.keys.sort((a, b) => a.t - b.t);
}

// Tek seferlik kurulum: olaylar S (paylaşılan durum) üzerinden çalışır; her yeniden çizimde S.data güncellenir.
function setup(root, S) {
  const $ = (s) => root.querySelector(s);
  const video = $('.vid'), stage = $('.stage'), wrap = $('.stage-wrap'), slot = $('.slot');
  const strip = $('.strip'), logo = $('.logo'), shapeSel = $('.shape');
  const D = () => S.data;
  const T = () => S.data.times;
  const tol = () => 1.5 / S.data.fps;
  const duration = () => S.data.duration;
  const now = () => video.currentTime || 0;
  const selected = () => S.blurs.find((b) => b.id === S.sel) || null;
  const setSrc = (el, url) => { if (url && el.getAttribute('src') !== url) el.setAttribute('src', url); };

  function send(immediate) {
    clearTimeout(S.timer);
    const go = () => {
      const text = JSON.stringify(S.blurs);
      if (text === S.lastSent) return;
      S.lastSent = text;
      S.setStateValue('blurs', JSON.parse(text));
    };
    if (immediate) go(); else S.timer = setTimeout(go, 500);
  }

  function stripFor(t) {
    const tm = T(), im = D().images;
    if (t < tm.h1_end) return im.h1;
    if (t >= tm.s1[0] && t < tm.s1[1]) return im.s1;
    if (t >= tm.s2[0] && t < tm.s2[1]) return im.s2;
    if (t >= tm.h2_start) return im.h2;
    return null;
  }

  function applyData() {
    const d = D();
    setSrc($('.bg'), d.images.bg);
    setSrc($('.frame'), d.images.frame);
    setSrc(logo, d.images.logo);
    if (video.getAttribute('src') !== d.video) video.setAttribute('src', d.video);
    Object.assign(slot.style, { left: d.slot.x + 'px', top: d.slot.y + 'px', width: d.slot.w + 'px', height: d.slot.h + 'px' });
    Object.assign(strip.style, { left: '0px', top: d.strip_y + 'px', width: '1080px', height: d.strip_h + 'px' });
    Object.assign(logo.style, { left: d.logo.x + 'px', top: d.logo.y + 'px', width: d.logo.w + 'px', height: d.logo.h + 'px' });
    if (!shapeSel.options.length) {
      for (const [value, label] of Object.entries(d.shapes)) {
        const o = document.createElement('option'); o.value = value; o.textContent = label; shapeSel.appendChild(o);
      }
    }
  }

  function renderStage() {
    stage.style.transform = `scale(${wrap.clientWidth / 1080})`;
    const t = now(), d = D();
    const src = stripFor(t);
    if (src) { setSrc(strip, src); strip.style.display = ''; } else { strip.style.display = 'none'; }
    logo.style.display = t >= T().logo[0] && t < T().logo[1] ? '' : 'none';
    const layer = $('.blurs');
    const W = d.slot.w, H = d.slot.h;
    const seen = new Set();
    for (const blur of S.blurs) {
      let el = layer.querySelector(`[data-id="${blur.id}"]`);
      const active = t >= blur.start && t < blur.end;
      if (!el) {
        el = document.createElement('div'); el.className = 'bl'; el.dataset.id = blur.id;
        const h = document.createElement('div'); h.className = 'handle'; el.appendChild(h);
        layer.appendChild(el);
      }
      seen.add(blur.id);
      const box = S.drag && S.drag.id === blur.id ? S.drag.box : boxAt(blur, t);
      el.style.display = active || blur.id === S.sel ? '' : 'none';
      el.classList.toggle('sel', blur.id === S.sel);
      Object.assign(el.style, { left: box.x * W + 'px', top: box.y * H + 'px', width: box.w * W + 'px', height: box.h * H + 'px' });
      el.style.borderRadius = blur.shape === 'elips' ? '50%'
        : blur.shape === 'yuvarlak' ? `${Math.round(Math.min(box.w * W, box.h * H) * 0.25)}px` : '0';
      const filter = active ? `blur(${4 * blur.strength}px)` : 'none';
      el.style.backdropFilter = filter;
      el.style.webkitBackdropFilter = filter;
      el.style.opacity = active ? blur.opacity : 0.35;
      el.style.background = active ? 'transparent' : 'rgba(127,211,255,0.25)';
    }
    for (const el of [...layer.children]) if (!seen.has(el.dataset.id)) el.remove();
    $('.time').textContent = `${fmt(t)} / ${fmt(duration())} sn`;
    $('.play').textContent = video.paused ? '▶' : '⏸';
    $('.head').style.left = `${(t / duration()) * 100}%`;
  }

  function renderTimeline() {
    const rows = $('.rows');
    rows.innerHTML = '';
    const tm = T();
    const pct = (v) => `${(Math.max(0, Math.min(v, duration())) / duration()) * 100}%`;
    const seg = (row, a, b, color, label) => {
      const s = document.createElement('div'); s.className = 'seg';
      Object.assign(s.style, { left: pct(a), width: `calc(${pct(b)} - ${pct(a)})`, background: color });
      s.textContent = label || ''; row.appendChild(s);
    };
    const base = document.createElement('div'); base.className = 'row';
    seg(base, 0, tm.h1_end, COLORS.h1, 'Başlık 1');
    seg(base, tm.s1[0], tm.s2[1], COLORS.s, 'Slogan');
    seg(base, tm.h2_start, duration(), COLORS.h2, 'Başlık 2');
    rows.appendChild(base);
    const logoRow = document.createElement('div'); logoRow.className = 'row';
    seg(logoRow, tm.logo[0], tm.logo[1], COLORS.logo, 'Logo');
    rows.appendChild(logoRow);
    S.blurs.forEach((blur, i) => {
      const row = document.createElement('div'); row.className = 'row' + (blur.id === S.sel ? ' sel' : '');
      seg(row, blur.start, blur.end, COLORS.blur, `Blur ${i + 1}`);
      for (const k of blur.keys) {
        const dia = document.createElement('div'); dia.className = 'key'; dia.style.left = pct(k.t); row.appendChild(dia);
      }
      rows.appendChild(row);
    });
  }

  function renderPanel() {
    const list = $('.list');
    list.innerHTML = '';
    S.blurs.forEach((blur, i) => {
      const c = document.createElement('span'); c.className = 'chip' + (blur.id === S.sel ? ' sel' : '');
      c.textContent = `Blur ${i + 1} · ${fmt(blur.start)}–${fmt(blur.end)} sn`;
      c.onclick = () => { S.sel = blur.id; seek(Math.min(Math.max(now(), blur.start), blur.end - 0.01)); renderAll(); };
      list.appendChild(c);
    });
    const blur = selected();
    $('.edit').style.display = blur ? '' : 'none';
    if (blur) {
      shapeSel.value = blur.shape;
      $('.strength').value = blur.strength;
      $('.opacity').value = Math.round(blur.opacity * 100);
      $('.hint').textContent = `${blur.keys.length} anahtar kare. Videoyu bir ana getir, kutuyu sürükle; köşedeki yuvarlakla boyutlandır.`;
    }
  }

  function renderAll() { applyData(); renderStage(); renderTimeline(); renderPanel(); }
  function seek(t) { video.currentTime = Math.max(0, Math.min(t, duration() - 0.001)); renderStage(); }

  // Canlı takip: oynarken her 0,1 sn'de bir anahtar kare; geçilen aralıktaki eski anahtarlar silinir.
  function recordStep(force) {
    if (!S.drag || !S.drag.live || !S.rec) return;
    const blur = S.blurs.find((b) => b.id === S.drag.id);
    if (!blur) return;
    const t = now();
    if (!force && S.rec.last >= 0 && t - S.rec.last < 0.1) return;
    if (S.rec.last >= 0) blur.keys = blur.keys.filter((k) => k.t <= S.rec.last + 1e-6 || k.t > t + tol());
    setKey(blur, t, S.drag.box, tol());
    S.rec.last = t;
  }

  for (const name of ['timeupdate', 'seeked', 'play', 'pause', 'loadedmetadata']) video.addEventListener(name, renderStage);
  const tick = () => { if (!video.paused) { recordStep(false); renderStage(); } S.raf = requestAnimationFrame(tick); };
  S.observer = new ResizeObserver(() => renderStage());
  // Streamlit bileşeni kaldırıp geri takabilir: döngü ve gözlemci her çizimde gerekiyorsa yeniden başlar.
  S.start = () => {
    if (!S.raf) S.raf = requestAnimationFrame(tick);
    if (!S.observing) { S.observer.observe(wrap); S.observing = true; }
  };

  $('.play').onclick = () => { if (video.paused) video.play(); else video.pause(); };
  $('.speed').onchange = (e) => { video.playbackRate = parseFloat(e.target.value); };

  const timeline = $('.timeline');
  const seekFromEvent = (e) => {
    const r = timeline.getBoundingClientRect();
    seek(((e.clientX - r.left) / r.width) * duration());
  };
  timeline.addEventListener('pointerdown', (e) => {
    seekFromEvent(e);
    timeline.setPointerCapture(e.pointerId);
    timeline.onpointermove = seekFromEvent;
    timeline.onpointerup = () => { timeline.onpointermove = null; };
  });

  $('.add').onclick = () => {
    const t = r3(now());
    const id = 'b' + Date.now().toString(36);
    S.blurs.push({ id, shape: 'yuvarlak', strength: 6, opacity: 1, start: t, end: Math.min(duration(), r3(t + 3)),
                   keys: [{ t, x: 0.35, y: 0.44, w: 0.3, h: 0.12 }] });
    S.sel = id; renderAll(); send(true);
  };
  shapeSel.onchange = (e) => { const b = selected(); if (b) { b.shape = e.target.value; renderAll(); send(false); } };
  $('.strength').oninput = (e) => { const b = selected(); if (b) { b.strength = parseInt(e.target.value, 10); renderStage(); send(false); } };
  $('.opacity').oninput = (e) => { const b = selected(); if (b) { b.opacity = parseInt(e.target.value, 10) / 100; renderStage(); send(false); } };
  $('.set-start').onclick = () => { const b = selected(); if (b && now() < b.end) { b.start = r3(now()); renderAll(); send(true); } };
  $('.set-end').onclick = () => { const b = selected(); if (b && now() > b.start) { b.end = r3(now()); renderAll(); send(true); } };
  $('.prev-key').onclick = () => { const b = selected(); if (!b) return; const k = [...b.keys].reverse().find((k) => k.t < now() - tol()); seek(k ? k.t : b.start); };
  $('.next-key').onclick = () => { const b = selected(); if (!b) return; const k = b.keys.find((k) => k.t > now() + tol()); seek(k ? k.t : b.end - 0.01); };
  $('.del-key').onclick = () => {
    const b = selected(); if (!b || b.keys.length < 2) return;
    const i = b.keys.findIndex((k) => Math.abs(k.t - now()) <= tol());
    if (i >= 0) { b.keys.splice(i, 1); renderAll(); send(true); }
  };
  $('.del-blur').onclick = () => {
    const i = S.blurs.findIndex((b) => b.id === S.sel); if (i < 0) return;
    S.blurs.splice(i, 1); S.sel = S.blurs.length ? S.blurs[Math.max(0, i - 1)].id : null; renderAll(); send(true);
  };

  // Sürükleme: kutuyu taşı / köşeden boyutlandır. Canlı takipte basılı tutarken video yavaş oynar ve yol kaydedilir.
  const point = (e) => {
    const r = slot.getBoundingClientRect();
    return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
  };
  wrap.addEventListener('pointerdown', (e) => {
    const target = e.target.closest('.bl');
    const live = $('.track').checked;
    if (target) S.sel = target.dataset.id;
    const blur = selected();
    if (!blur || (!target && !live)) { renderAll(); return; }
    e.preventDefault();
    wrap.setPointerCapture(e.pointerId);
    const box = boxAt(blur, now());
    const p = point(e);
    S.drag = { id: blur.id, box, start: p, from: { ...box }, resize: e.target.classList.contains('handle'), live };
    if (live) {
      S.drag.box = { ...box, x: p.x - box.w / 2, y: p.y - box.h / 2 };
      S.rec = { last: -1 };
      if (now() < blur.start) blur.start = r3(now());
      video.playbackRate = parseFloat($('.speed').value) < 1 ? parseFloat($('.speed').value) : 0.5;
      video.play();
    }
    renderAll();
  });
  wrap.addEventListener('pointermove', (e) => {
    if (!S.drag) return;
    const p = point(e);
    const d = S.drag, f = d.from;
    if (d.live) d.box = { ...d.box, x: p.x - d.box.w / 2, y: p.y - d.box.h / 2 };
    else if (d.resize) d.box = { ...f, w: Math.max(0.02, f.w + p.x - d.start.x), h: Math.max(0.02, f.h + p.y - d.start.y) };
    else d.box = { ...f, x: f.x + p.x - d.start.x, y: f.y + p.y - d.start.y };
    renderStage();
  });
  const finish = () => {
    if (!S.drag) return;
    const blur = S.blurs.find((b) => b.id === S.drag.id);
    if (S.drag.live) {
      video.pause();
      recordStep(true);
      video.playbackRate = parseFloat($('.speed').value);
      if (blur && now() > blur.end) blur.end = r3(now());
    } else if (blur) {
      setKey(blur, now(), S.drag.box, tol());
    }
    S.drag = null; S.rec = null;
    renderAll(); send(true);
  };
  wrap.addEventListener('pointerup', finish);
  wrap.addEventListener('pointercancel', finish);

  S.renderAll = renderAll;
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  let S = STATE.get(parentElement);
  if (!S) {
    S = { project: null, blurs: [], sel: null, drag: null, rec: null, timer: null, lastSent: '' };
    STATE.set(parentElement, S);
    S.data = data;
    S.setStateValue = setStateValue;
    setup(parentElement, S);
  }
  S.data = data;
  S.setStateValue = setStateValue;
  if (S.project !== data.project) {
    S.project = data.project;
    S.blurs = JSON.parse(JSON.stringify(data.blurs || []));
    S.lastSent = JSON.stringify(S.blurs);
    S.sel = S.blurs.length ? S.blurs[0].id : null;
  }
  S.start();
  S.renderAll();
  return () => {
    cancelAnimationFrame(S.raf);
    S.raf = null;
    S.observer.disconnect();
    S.observing = false;
  };
}
"""

_EDITOR = st.components.v2.component("axion_tasarim_editoru", html=HTML, css=CSS, js=JS)


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


def design_editor(data: dict[str, Any], key: str) -> list[dict[str, Any]] | None:
    """Editörü gösterir; editör blur listesini değiştirdiyse yeni listeyi döndürür."""
    result = _EDITOR(data=data, key=key, default={"blurs": None}, on_blurs_change=lambda: None)
    return result.blurs
