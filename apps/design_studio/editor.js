// Tasarım Stüdyosu editörü (Streamlit components v2): Canva benzeri düzen.
// Üstte bağlama göre araç çubuğu, solda seçili öğenin paneli (animasyon / blur), ortada tuval, sağda arka plan ve
// çerçeve, altta katmanlı zaman çizelgesi. Efekt formülleri apps/design_studio/effects.py ile aynıdır; son video
// Python'da üretilir. Tasarım bu editörde tutulur ve her değişiklikte Python'a gönderilir (`edits`).

const STATE = new WeakMap();
const W = 1080, H = 1920;
const clamp = (p) => Math.min(1, Math.max(0, p));
const easeOut = (p) => 1 - Math.pow(1 - clamp(p), 3);
const easeIn = (p) => Math.pow(clamp(p), 3);
const easeOutBack = (p) => { p = clamp(p); const c = 1.70158; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
const fmt = (t) => t.toFixed(1).replace('.', ',');
const r3 = (t) => Math.round(t * 1000) / 1000;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const clone = (x) => JSON.parse(JSON.stringify(x));

// ================================================================ efektler (effects.py ile aynı)
const MERGE = { stagger: 0.045, gap: 0.1, fade: 0.12, slide: 24, move: 0.6, exitSeconds: 0.26, exitSlide: 13 };
const word = (a = 1, dx = 0, dy = 0) => ({ a, dx, dy });
const stagger = (n, step, limit) => Math.min(step, limit / Math.max(1, n));
function mergeDelays(lines) {
  const order = [];
  [...new Set(lines)].sort((a, b) => a - b).forEach((line) => {
    const idx = lines.map((v, i) => (v === line ? i : -1)).filter((i) => i >= 0);
    order.push(...(line === 0 ? idx.reverse() : idx));
  });
  const st = Math.min(MERGE.stagger, 0.55 / Math.max(1, order.length));
  const delays = new Array(lines.length).fill(0);
  let delay = 0, prev = order.length ? lines[order[0]] : 0;
  for (const i of order) { if (lines[i] !== prev) { delay += MERGE.gap; prev = lines[i]; } delays[i] = delay; delay += st; }
  return delays;
}
function enterSeconds(e, lines) {
  const n = lines.length;
  if (e === 'merge') return Math.max(0, ...mergeDelays(lines)) + MERGE.move;
  if (e === 'fade') return 0.4;
  if (e === 'slide') return stagger(n, 0.06, 0.5) * Math.max(0, n - 1) + 0.45;
  if (e === 'typewriter') return stagger(n, 0.11, 1.2) * n;
  if (e === 'pop') return 0.35;
  return 0;
}
function exitSeconds(e, lines) {
  const n = lines.length;
  if (e === 'merge') return MERGE.exitSeconds;
  if (e === 'fade') return 0.35;
  if (e === 'slide') return stagger(n, 0.03, 0.2) * Math.max(0, n - 1) + 0.35;
  if (e === 'pop') return 0.25;
  return 0;
}
function enterState(e, lines, t) {
  const n = lines.length;
  if (e === 'merge') { const d = mergeDelays(lines); return { scale: 1, words: lines.map((line, i) => { const l = t - d[i]; return word(clamp(l / MERGE.fade), (line === 0 ? 1 : -1) * MERGE.slide * (1 - easeOut(l / MERGE.move))); }) }; }
  if (e === 'fade') return { scale: 1, words: lines.map(() => word(easeOut(t / 0.4))) };
  if (e === 'slide') { const s = stagger(n, 0.06, 0.5); return { scale: 1, words: lines.map((_, i) => word(clamp((t - i * s) / 0.2), 0, 36 * (1 - easeOut((t - i * s) / 0.45)))) }; }
  if (e === 'typewriter') { const s = stagger(n, 0.11, 1.2); return { scale: 1, words: lines.map((_, i) => word(t >= i * s ? 1 : 0)) }; }
  if (e === 'pop') return { scale: 0.6 + 0.4 * easeOutBack(t / 0.35), words: lines.map(() => word(clamp(t / 0.15))) };
  return { scale: 1, words: lines.map(() => word()) };
}
function exitState(e, lines, t) {
  const n = lines.length;
  if (e === 'merge') { const p = t / MERGE.exitSeconds, dx = -MERGE.exitSlide * easeIn(p); return { scale: 1, words: lines.map((line) => word(line === 0 ? 1 - clamp((p - 0.35) / 0.2) : 1 - easeIn((p - 0.55) / 0.45), dx)) }; }
  if (e === 'fade') return { scale: 1, words: lines.map(() => word(1 - easeIn(t / 0.35))) };
  if (e === 'slide') { const s = stagger(n, 0.03, 0.2); return { scale: 1, words: lines.map((_, i) => word(1 - clamp((t - i * s) / 0.35), 0, -30 * easeIn((t - i * s) / 0.35))) }; }
  if (e === 'pop') { const p = t / 0.25; return { scale: 1 - 0.3 * easeIn(p), words: lines.map(() => word(1 - clamp(p))) }; }
  return { scale: 1, words: lines.map(() => word(0)) };
}
function textState(enter, exit, lines, start, end, t) {
  if (t < start || t >= end) return null;
  const exitLen = Math.min(exitSeconds(exit, lines), Math.max(0, end - start));
  if (t >= end - exitLen) return exitState(exit, lines, t - (end - exitLen));
  if (t - start < enterSeconds(enter, lines)) return enterState(enter, lines, t - start);
  return { scale: 1, words: lines.map(() => word()) };
}
const SLOGAN_IN = { old_tv: 0.56, fade: 0.3, pop: 0.35, yok: 0 };
const SLOGAN_OUT = { old_tv: 0.23, fade: 0.3, pop: 0.2, yok: 0 };
function oldTvScale(a) {
  a = clamp(a); let sx = clamp((a - 0.08) / 0.3); sx = sx * sx * (3 - 2 * sx);
  return [Math.max(sx, a > 0 ? 0.02 : 0), a < 0.38 ? 0.2 + 0.25 * a / 0.38 : 0.45 + 0.55 * easeOut((a - 0.38) / 0.3)];
}
function sloganState(e, start, end, t, frame) {
  if (t < start || t >= end) return null;
  const rise = SLOGAN_IN[e] || 0, fall = SLOGAN_OUT[e] || 0;
  let p, entering;
  if (t < start + rise) { p = (t - start) / rise; entering = true; } else if (t >= end - fall) { p = 1 - (t - (end - fall)) / fall; entering = false; }
  else return { a: 1, sx: 1, sy: 1, dy: 0, split: 0 };
  if (e === 'old_tv') { const [sx, sy] = oldTvScale(p); return { a: 1, sx, sy, dy: 0, split: p < 0.97 ? Math.round(7 * (1 - p)) + 1 : 0, flicker: frame % 2 === 1 && p < 0.97 }; }
  if (e === 'fade') return { a: entering ? easeOut(p) : easeIn(p), sx: 1, sy: 1, dy: 0, split: 0 };
  if (e === 'pop') { const s = entering ? 0.5 + 0.5 * easeOutBack(p) : 0.7 + 0.3 * p; return { a: clamp(p / 0.4), sx: s, sy: s, dy: 0, split: 0 }; }
  return { a: 1, sx: 1, sy: 1, dy: 0, split: 0 };
}
function logoState(L, effect, t) {
  if (t < L.start || t >= L.end) return null;
  const glint = t >= L.glint[0] && t < L.glint[1] ? (t - L.glint[0]) / (L.glint[1] - L.glint[0]) : null;
  const rise = H - L.rest_y;
  if (effect === 'slow_baseline') {
    let y;
    if (t < L.drop_start) y = H - rise * (1 - Math.exp(-(t - L.start) / L.tau));
    else { const top = H - rise * (1 - Math.exp(-(L.drop_start - L.start) / L.tau)); y = top + (H - top) * Math.pow(clamp((t - L.drop_start) / (L.end - L.drop_start)), 1.5); }
    return { a: 1, sx: 1, sy: 1, dy: y - L.rest_y, glint };
  }
  if (effect === 'fade') return { a: Math.min(easeOut((t - L.start) / 0.4), 1 - easeIn((t - (L.end - 0.3)) / 0.3)), sx: 1, sy: 1, dy: 0, glint };
  if (effect === 'pop') { const pin = (t - L.start) / 0.35, pout = (t - (L.end - 0.25)) / 0.25; const s = pin < 1 ? 0.3 + 0.7 * easeOutBack(pin) : (pout > 0 ? 1 - 0.7 * easeIn(pout) : 1); return { a: clamp(pin / 0.3) * (1 - clamp(pout)), sx: s, sy: s, dy: 0, glint }; }
  return { a: 1, sx: 1, sy: 1, dy: 0, glint };
}

// ================================================================ çerçeve (üst ortadan saat yönünde s: 0..1)
function frameGeom(G) {
  const half = G.border / 2;
  const g = { cx: G.slot.x + G.slot.w / 2, cy: G.slot.y + G.slot.h / 2, hx: G.slot.w / 2 - half, hy: G.slot.h / 2 - half, r: G.radius - half };
  g.top = 2 * (g.hx - g.r); g.side = 2 * (g.hy - g.r); g.arc = Math.PI * g.r / 2; g.per = 2 * g.top + 2 * g.side + 4 * g.arc;
  return g;
}
function pointAt(g, s) {
  let d = (((s % 1) + 1) % 1) * g.per;
  const { cx, cy, hx, hy, r, top, side, arc } = g;
  const seg = (len) => { if (d <= len) return true; d -= len; return false; };
  const corner = (ox, oy, a0) => { const a = (a0 + (d / arc) * 90) * Math.PI / 180; return [ox + r * Math.cos(a), oy + r * Math.sin(a)]; };
  if (seg(top / 2)) return [cx + d, cy - hy];
  if (seg(arc)) return corner(cx + hx - r, cy - hy + r, -90);
  if (seg(side)) return [cx + hx, cy - hy + r + d];
  if (seg(arc)) return corner(cx + hx - r, cy + hy - r, 0);
  if (seg(top)) return [cx + hx - r - d, cy + hy];
  if (seg(arc)) return corner(cx - hx + r, cy + hy - r, 90);
  if (seg(side)) return [cx - hx, cy + hy - r - d];
  if (seg(arc)) return corner(cx - hx + r, cy - hy + r, 180);
  return [cx - hx + r + d, cy - hy];
}
function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function drawFrame(ctx, G, F, t) {
  if (F.style === 'yok') return;
  const g = frameGeom(G), half = G.border / 2;
  const path = () => roundRectPath(ctx, G.slot.x + half, G.slot.y + half, G.slot.w - G.border, G.slot.h - G.border, g.r);
  const period = (G.periods[F.style] || 1) / Math.max(0.2, F.speed);
  ctx.save(); ctx.lineCap = 'round';
  if (F.style === 'sabit') { path(); ctx.strokeStyle = F.color; ctx.lineWidth = G.border; ctx.stroke(); }
  else if (F.style === 'nefes') { const p = 0.5 + 0.5 * Math.sin(2 * Math.PI * t / period); path(); ctx.shadowColor = F.accent; ctx.shadowBlur = 6 + 16 * p; ctx.strokeStyle = F.color; ctx.lineWidth = 2.5 + 2.5 * p; ctx.stroke(); }
  else if (F.style === 'akis') {
    const grad = ctx.createConicGradient(-Math.PI / 2 + 2 * Math.PI * (t / period), g.cx, g.cy);
    [[0, F.color], [0.33, F.accent], [0.66, '#D0E491'], [1, F.color]].forEach(([o, c]) => grad.addColorStop(o, c));
    path(); ctx.strokeStyle = grad; ctx.lineWidth = 5; ctx.stroke();
  } else if (F.style === 'kovalayan') {
    path(); ctx.globalAlpha = 0.35; ctx.strokeStyle = F.color; ctx.lineWidth = 1.5; ctx.stroke(); ctx.globalAlpha = 1;
    for (const offset of [0, 0.5]) {
      const head = (t / period + offset) % 1; let prev = pointAt(g, head);
      for (let i = 1; i <= 70; i++) {
        const k = 1 - i / 70, p = pointAt(g, head - (i / 70) * G.comet.tail);
        ctx.beginPath(); ctx.moveTo(prev[0], prev[1]); ctx.lineTo(p[0], p[1]);
        ctx.strokeStyle = k > 0.5 ? '#FFFFFF' : F.accent; ctx.globalAlpha = 0.35 + 0.65 * k;
        ctx.shadowColor = F.accent; ctx.shadowBlur = 12 * k * k; ctx.lineWidth = 0.6 + G.comet.head * Math.pow(k, 1.3); ctx.stroke(); prev = p;
      }
    }
  }
  ctx.restore();
}

// ================================================================ blur kutuları
function boxAt(blur, t) {
  const k = blur.keys, f = ['x', 'y', 'w', 'h', 'r'];
  const pick = (key) => Object.fromEntries(f.map((n) => [n, key[n] || 0]));
  if (t <= k[0].t) return pick(k[0]);
  for (let i = 0; i < k.length - 1; i++) {
    const a = k[i], b = k[i + 1];
    if (a.t <= t && t <= b.t) { const p = b.t > a.t ? (t - a.t) / (b.t - a.t) : 1; return Object.fromEntries(f.map((n) => [n, (a[n] || 0) + ((b[n] || 0) - (a[n] || 0)) * p])); }
  }
  return pick(k[k.length - 1]);
}
function setKey(blur, t, box, tol) {
  const key = { t: r3(t), x: box.x, y: box.y, w: box.w, h: box.h, r: Math.round((box.r || 0) * 10) / 10 };
  const i = blur.keys.findIndex((k) => Math.abs(k.t - t) <= tol);
  if (i >= 0) blur.keys[i] = key; else blur.keys.push(key);
  blur.keys.sort((a, b) => a.t - b.t);
}
function shapePath(ctx, shape, w, h) {
  ctx.beginPath();
  if (shape === 'elips') ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, 2 * Math.PI);
  else if (shape === 'yuvarlak') roundRectPath(ctx, -w / 2, -h / 2, w, h, Math.min(w, h) * 0.25);
  else ctx.rect(-w / 2, -h / 2, w, h);
}

// ================================================================ arayüz
const ICON = { play: '▶', pause: '⏸' };
const TRACK_COLORS = { headline: '#3fb6c6', slogan: '#9aa7b4', text: '#8a5cc7', logo: '#6c7a89', blur: '#e08a1e', mozaik: '#c0612b' };

function setup(root, S) {
  const $ = (s) => root.querySelector(s);
  const canvas = $('.stage'), ctx = canvas.getContext('2d'), video = $('.vid'), finalVideo = $('.finalvid');
  const wrap = $('.stage-wrap');
  const D = () => S.data, d = () => S.design;
  const now = () => video.currentTime || 0;
  const dur = () => D().duration;
  const tol = () => 1.5 / D().fps;
  const images = new Map();
  const off = { eff: document.createElement('canvas'), mask: document.createElement('canvas'), small: document.createElement('canvas'), tmp: document.createElement('canvas') };
  let dirty = true;
  const invalidate = () => { dirty = true; };

  const img = (url) => {
    if (!url) return null;
    let im = images.get(url);
    if (!im) { im = new Image(); im.onload = invalidate; im.src = url; images.set(url, im); }
    return im.complete && im.naturalWidth ? im : null;
  };
  function channels(url) {
    const key = 'ch:' + url; if (images.has(key)) return images.get(key);
    const im = img(url); if (!im) return null;
    const make = (ch) => {
      const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
      const x = c.getContext('2d'); x.drawImage(im, 0, 0);
      const px = x.getImageData(0, 0, c.width, c.height);
      for (let i = 0; i < px.data.length; i += 4) for (let j = 0; j < 3; j++) if (j !== ch) px.data[i + j] = 0;
      x.putImageData(px, 0, 0); return c;
    };
    const out = [make(0), make(1), make(2)]; images.set(key, out); return out;
  }

  // ---------------------------------------------------------------- seçim ve gönderme
  const sel = () => S.sel;  // {kind: 'h1'|'h2'|'text'|'blur'|'slogans'|'logo', id?}
  const selBlur = () => (S.sel && S.sel.kind === 'blur' ? d().blurs.find((b) => b.id === S.sel.id) : null);
  const selText = () => (S.sel && S.sel.kind === 'text' ? d().texts.find((x) => x.id === S.sel.id) : null);
  const styleOf = (s) => (s.kind === 'text' ? selText() : d().headline_style);
  const headlineOf = (s) => (s.kind === 'h1' ? d().headline_1 : d().headline_2);
  function select(next) { S.sel = next; S.strikeMode = false; renderAll(); }
  function send(immediate) {
    clearTimeout(S.timer);
    const go = () => {
      const patch = { headline_style: d().headline_style, headline_1: { enter: d().headline_1.enter, exit: d().headline_1.exit },
        headline_2: { enter: d().headline_2.enter, exit: d().headline_2.exit }, slogans: d().slogans, logo: d().logo,
        frame: d().frame, background: d().background, texts: d().texts, blurs: d().blurs };
      const payload = { v: `${S.born}-${++S.version}`, design: clone(patch), ops: S.ops.splice(0) };
      S.setStateValue('edits', payload);
    };
    if (immediate) go(); else S.timer = setTimeout(go, 400);
  }
  const change = (fn, immediate = true) => { fn(); renderAll(); send(immediate); };

  // ---------------------------------------------------------------- tuval
  function blockFor(kind, id) {
    const b = D().blocks;
    if (kind === 'h1') return b.h1;
    if (kind === 'h2') return b.h2;
    return b.texts[id] || null;
  }
  function blockOffset(kind, id) {  // editörde taşınan yazı, Python yeniden çizene kadar kaydırılarak gösterilir
    if (kind !== 'text') return [0, 0];
    const layer = d().texts.find((x) => x.id === id), block = blockFor(kind, id);
    if (!layer || !block) return [0, 0];
    let dx = layer.x * W - block.center[0], dy = layer.y * H - block.center[1];
    if (S.drag && S.drag.kind === 'text' && S.drag.id === id) { dx += S.drag.dx; dy += S.drag.dy; }
    return [dx, dy];
  }
  function drawBlock(block, state, off2) {
    const atlas = img(block.atlas); if (!atlas) return;
    const [ox, oy] = off2, cx = block.center[0] + ox, cy = block.center[1] + oy;
    block.words.forEach((w, i) => {
      const ws = state.words[i]; if (!ws || ws.a <= 0.004) return;
      let x = w.x + ws.dx + ox, y = w.y + ws.dy + oy, sw = w.sw, sh = w.sh;
      if (Math.abs(state.scale - 1) > 0.001) { const mx = x + sw / 2, my = y + sh / 2; sw *= state.scale; sh *= state.scale; x = cx + (mx - cx) * state.scale - sw / 2; y = cy + (my - cy) * state.scale - sh / 2; }
      ctx.globalAlpha = ws.a; ctx.drawImage(atlas, w.sx, w.sy, w.sw, w.sh, x, y, sw, sh);
    });
    ctx.globalAlpha = 1;
  }
  function drawSprite(url, center, st) {
    const im = img(url); if (!im || st.a <= 0.004 || st.sx <= 0 || st.sy <= 0) return;
    const w = im.naturalWidth * st.sx, h = im.naturalHeight * st.sy, x = center[0] - w / 2, y = center[1] - h / 2 + (st.dy || 0);
    ctx.globalAlpha = st.a * (st.flicker ? 0.8 : 1);
    const ch = st.split ? channels(url) : null;
    if (ch) { const t = off.tmp; t.width = Math.ceil(w + 2 * st.split); t.height = Math.ceil(h); const tc = t.getContext('2d'); tc.globalCompositeOperation = 'lighter'; ch.forEach((c, i) => tc.drawImage(c, i * st.split, 0, w, h)); ctx.drawImage(t, x, y); }
    else ctx.drawImage(im, x, y, w, h);
    if (st.glint != null) {
      ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
      const c = x - 60 + (w + 120) * st.glint;
      ctx.beginPath(); ctx.moveTo(c - 18, y + h); ctx.lineTo(c + 18, y + h); ctx.lineTo(c + 18 + h * 0.55, y); ctx.lineTo(c - 18 + h * 0.55, y); ctx.closePath();
      ctx.fillStyle = 'rgba(205,205,205,0.43)'; ctx.fill(); ctx.restore();
    }
    ctx.globalAlpha = 1;
  }
  function drawEffects(k, t) {
    const s = D().slot, sw = Math.max(1, Math.round(s.w * k)), sh = Math.max(1, Math.round(s.h * k));
    for (const blur of d().blurs) {
      if (!(t >= blur.start && t < blur.end)) continue;
      const b = S.drag && S.drag.kind === 'blur' && S.drag.id === blur.id ? S.drag.box : boxAt(blur, t);
      const eff = off.eff; eff.width = sw; eff.height = sh; const ec = eff.getContext('2d');
      if (blur.effect === 'mozaik') {
        const block = (6 + 4 * blur.strength) * k, sm = off.small;
        sm.width = Math.max(2, Math.round(sw / block)); sm.height = Math.max(2, Math.round(sh / block));
        sm.getContext('2d').drawImage(video, 0, 0, sm.width, sm.height); ec.imageSmoothingEnabled = false; ec.drawImage(sm, 0, 0, sw, sh);
      } else { ec.filter = `blur(${4 * blur.strength * k}px)`; ec.drawImage(video, 0, 0, sw, sh); ec.filter = 'none'; }
      const m = off.mask; m.width = sw; m.height = sh; const mc = m.getContext('2d');
      const bw = b.w * sw, bh = b.h * sh, feather = (blur.feather || 0) * Math.min(bw, bh) / 2;
      mc.translate((b.x + b.w / 2) * sw, (b.y + b.h / 2) * sh); mc.rotate((b.r || 0) * Math.PI / 180);
      if (feather > 0.5) mc.filter = `blur(${feather / 2}px)`;
      shapePath(mc, blur.shape, Math.max(1, bw - feather), Math.max(1, bh - feather)); mc.fillStyle = `rgba(255,255,255,${blur.opacity})`; mc.fill();
      ec.globalCompositeOperation = 'destination-in'; ec.drawImage(m, 0, 0); ec.globalCompositeOperation = 'source-over';
      ctx.drawImage(eff, s.x, s.y, s.w, s.h);
    }
  }
  const blurCenter = (b) => { const s = D().slot; return [s.x + (b.x + b.w / 2) * s.w, s.y + (b.y + b.h / 2) * s.h]; };
  function visibleItems(t, frame) {  // Python Scene.items ile aynı sıra
    const out = [], dd = d(), T = D().times;
    const h1 = textState(dd.headline_1.enter, dd.headline_1.exit, D().blocks.h1.lines, 0, T.h1_end, t);
    if (h1) out.push({ kind: 'h1', state: h1 });
    if (dd.slogans.enabled) D().slogans.forEach((it, i) => { const st = sloganState(dd.slogans.effect, it.start, it.end, t, frame); if (st) out.push({ kind: 'slogans', i, state: st }); });
    const h2 = textState(dd.headline_2.enter, dd.headline_2.exit, D().blocks.h2.lines, T.h2_start, dur() + 1, t);
    if (h2) out.push({ kind: 'h2', state: h2 });
    if (dd.logo.enabled) { const st = logoState(D().logo, dd.logo.effect, t); if (st) out.push({ kind: 'logo', state: st }); }
    for (const layer of dd.texts) { const block = D().blocks.texts[layer.id]; if (!block) continue; const st = textState(layer.enter, layer.exit, block.lines, layer.start, layer.end, t); if (st) out.push({ kind: 'text', id: layer.id, state: st }); }
    return out;
  }
  function draw() {
    const cssW = wrap.clientWidth || 340, dpr = window.devicePixelRatio || 1;
    const bw = Math.round(cssW * dpr), bh = Math.round(cssW * dpr * H / W);
    if (canvas.width !== bw || canvas.height !== bh) { canvas.width = bw; canvas.height = bh; }
    const k = bw / W, t = now(), frame = Math.round(t * D().fps);
    ctx.setTransform(k, 0, 0, k, 0, 0); ctx.clearRect(0, 0, W, H);
    const bg = img(currentBackgroundUrl()); if (bg) ctx.drawImage(bg, 0, 0, W, H); else { ctx.fillStyle = '#0d1f24'; ctx.fillRect(0, 0, W, H); }
    const s = D().slot;
    ctx.save(); roundRectPath(ctx, s.x, s.y, s.w, s.h, D().frame_geom.radius); ctx.clip();
    if (video.readyState >= 2) { ctx.drawImage(video, s.x, s.y, s.w, s.h); drawEffects(k, t); } else { ctx.fillStyle = '#111'; ctx.fillRect(s.x, s.y, s.w, s.h); }
    ctx.restore();
    drawFrame(ctx, D().frame_geom, d().frame, t);
    for (const it of visibleItems(t, frame)) {
      if (it.kind === 'h1' || it.kind === 'h2' || it.kind === 'text') { const block = blockFor(it.kind, it.id); if (block) drawBlock(block, it.state, blockOffset(it.kind, it.id)); }
      else if (it.kind === 'slogans') drawSprite(D().slogans[it.i].url, D().slogans[it.i].center, it.state);
      else if (it.kind === 'logo') drawSprite(D().logo.url, D().logo.center, it.state);
    }
    drawSelection(t);
    updateTransport(t);
  }
  function outline(drawPath) {
    ctx.save(); drawPath(); ctx.lineWidth = 9; ctx.strokeStyle = 'rgba(18,50,73,0.55)'; ctx.stroke();
    ctx.setLineDash([16, 10]); ctx.lineWidth = 5; ctx.strokeStyle = '#8ee0ff'; ctx.stroke(); ctx.restore();
  }
  function blockRect(kind, id) {
    const block = blockFor(kind, id); if (!block) return null;
    const [ox, oy] = blockOffset(kind, id);
    return [block.bbox[0] + ox - 10, block.bbox[1] + oy - 10, block.bbox[2] - block.bbox[0] + 20, block.bbox[3] - block.bbox[1] + 20];
  }
  function drawSelection(t) {
    const s = sel(); if (!s) return;
    const blur = selBlur();
    if (blur) {
      const b = S.drag && S.drag.kind === 'blur' ? S.drag.box : boxAt(blur, t), c = blurCenter(b);
      const w = b.w * D().slot.w, h = b.h * D().slot.h;
      ctx.save(); ctx.translate(c[0], c[1]); ctx.rotate((b.r || 0) * Math.PI / 180);
      outline(() => shapePath(ctx, 'dikdortgen', w, h));
      ctx.fillStyle = '#8ee0ff'; ctx.strokeStyle = '#123249'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(w / 2, h / 2, 24, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, -h / 2); ctx.lineTo(0, -h / 2 - 50); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, -h / 2 - 64, 22, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
      ctx.restore(); return;
    }
    if (['h1', 'h2', 'text'].includes(s.kind)) { const r = blockRect(s.kind, s.id); if (r) outline(() => { ctx.beginPath(); ctx.rect(...r); }); }
    if (S.strikeMode) { ctx.save(); ctx.fillStyle = 'rgba(229,72,77,0.9)'; ctx.font = 'bold 34px sans-serif'; ctx.fillText('Sansür: kelimeye dokun', 40, 60); ctx.restore(); }
  }
  function currentBackgroundUrl() {
    const name = d().background || D().daily;
    const found = D().backgrounds.find((b) => b.name === name);
    return name === (D().design.background || D().daily) ? D().images.bg : (found ? found.url : D().images.bg);
  }

  // ---------------------------------------------------------------- tuval etkileşimi
  const toCanvas = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height]; };
  const local = (b, p) => { const c = blurCenter(b), a = -(b.r || 0) * Math.PI / 180, dx = p[0] - c[0], dy = p[1] - c[1]; return [dx * Math.cos(a) - dy * Math.sin(a), dx * Math.sin(a) + dy * Math.cos(a)]; };
  function hitBlur(p, t) {
    const s = D().slot, blur = selBlur();
    if (blur) {
      const b = boxAt(blur, t), [lx, ly] = local(b, p), w = b.w * s.w, h = b.h * s.h;
      if (Math.hypot(lx - w / 2, ly - h / 2) < 45) return { blur, mode: 'resize' };
      if (Math.hypot(lx, ly + h / 2 + 64) < 45) return { blur, mode: 'rotate' };
    }
    for (const b of [...d().blurs].reverse()) {
      if (!(t >= b.start && t < b.end) && !(blur && b.id === blur.id)) continue;
      const box = boxAt(b, t), [lx, ly] = local(box, p);
      if (Math.abs(lx) <= box.w * s.w / 2 + 10 && Math.abs(ly) <= box.h * s.h / 2 + 10) return { blur: b, mode: 'move' };
    }
    return null;
  }
  function hitItem(p, t) {
    const items = visibleItems(t, 0).reverse();
    for (const it of items) {
      let r = null;
      if (['h1', 'h2', 'text'].includes(it.kind)) r = blockRect(it.kind, it.id);
      else if (it.kind === 'slogans') { const im = img(D().slogans[it.i].url); if (im) { const [cx, cy] = D().slogans[it.i].center; r = [cx - im.naturalWidth / 2, cy - im.naturalHeight / 2, im.naturalWidth, im.naturalHeight]; } }
      else if (it.kind === 'logo') { const [cx, cy] = D().logo.center; r = [cx - 100, cy - 100 + (it.state.dy || 0), 200, 200]; }
      if (r && p[0] >= r[0] && p[0] <= r[0] + r[2] && p[1] >= r[1] && p[1] <= r[1] + r[3]) return it;
    }
    return null;
  }
  function wordAt(kind, id, p) {
    const block = blockFor(kind, id); if (!block) return -1;
    const [ox, oy] = blockOffset(kind, id);
    return block.words.findIndex((w) => p[0] >= w.x + ox && p[0] <= w.x + ox + w.sw && p[1] >= w.y + oy && p[1] <= w.y + oy + w.sh);
  }
  wrap.addEventListener('pointerdown', (e) => {
    if (S.mode !== 'edit') return;
    const p = toCanvas(e), t = now(), live = S.live && selBlur();
    if (S.strikeMode && S.sel && ['h1', 'h2', 'text'].includes(S.sel.kind)) {
      const i = wordAt(S.sel.kind, S.sel.id, p);
      if (i >= 0) { S.ops.push({ op: 'strike', target: S.sel.kind === 'text' ? `text:${S.sel.id}` : S.sel.kind, index: i }); send(true); }
      return;
    }
    const blurHit = hitBlur(p, t);
    const item = blurHit ? null : hitItem(p, t);
    if (!blurHit && !item && !live) { select(null); return; }
    e.preventDefault(); wrap.setPointerCapture(e.pointerId);
    if (item) {
      S.sel = { kind: item.kind, id: item.id }; S.strikeMode = false;
      if (item.kind === 'text') S.drag = { kind: 'text', id: item.id, start: p, dx: 0, dy: 0 };
      renderAll(); return;
    }
    const blur = blurHit ? blurHit.blur : selBlur();
    S.sel = { kind: 'blur', id: blur.id };
    const box = boxAt(blur, t);
    S.drag = { kind: 'blur', id: blur.id, mode: blurHit ? blurHit.mode : 'move', start: p, from: { ...box }, box: { ...box }, live: !!live };
    if (live) {
      const s = D().slot; S.drag.box.x = (p[0] - s.x) / s.w - box.w / 2; S.drag.box.y = (p[1] - s.y) / s.h - box.h / 2;
      S.rec = { last: -1 }; if (t < blur.start) blur.start = r3(t);
      video.playbackRate = S.speed < 1 ? S.speed : 0.5; video.play();
    }
    renderAll();
  });
  wrap.addEventListener('pointermove', (e) => {
    const dr = S.drag; if (!dr) return;
    const p = toCanvas(e), s = D().slot;
    if (dr.kind === 'text') { dr.dx = p[0] - dr.start[0]; dr.dy = p[1] - dr.start[1]; invalidate(); return; }
    const f = dr.from;
    if (dr.live) dr.box = { ...dr.box, x: (p[0] - s.x) / s.w - dr.box.w / 2, y: (p[1] - s.y) / s.h - dr.box.h / 2 };
    else if (dr.mode === 'resize') { const [lx, ly] = local(f, p); dr.box = { ...f, w: Math.max(0.02, 2 * Math.abs(lx) / s.w), h: Math.max(0.02, 2 * Math.abs(ly) / s.h) }; dr.box.x = f.x + f.w / 2 - dr.box.w / 2; dr.box.y = f.y + f.h / 2 - dr.box.h / 2; }
    else if (dr.mode === 'rotate') { const c = blurCenter(f); dr.box = { ...f, r: Math.round(Math.atan2(p[1] - c[1], p[0] - c[0]) * 180 / Math.PI + 90) }; }
    else dr.box = { ...f, x: f.x + (p[0] - dr.start[0]) / s.w, y: f.y + (p[1] - dr.start[1]) / s.h };
    invalidate();
  });
  function recordStep(force) {
    const dr = S.drag; if (!dr || dr.kind !== 'blur' || !dr.live || !S.rec) return;
    const blur = d().blurs.find((b) => b.id === dr.id); if (!blur) return;
    const t = now(); if (!force && S.rec.last >= 0 && t - S.rec.last < 0.1) return;
    if (S.rec.last >= 0) blur.keys = blur.keys.filter((k) => k.t <= S.rec.last + 1e-6 || k.t > t + tol());
    setKey(blur, t, dr.box, tol()); S.rec.last = t;
  }
  const finish = () => {
    const dr = S.drag; if (!dr) return; S.drag = null;
    if (dr.kind === 'text') {
      const layer = d().texts.find((x) => x.id === dr.id);
      if (layer && (Math.abs(dr.dx) > 1 || Math.abs(dr.dy) > 1)) { layer.x = clamp(layer.x + dr.dx / W); layer.y = clamp(layer.y + dr.dy / H); send(true); }
      renderAll(); return;
    }
    const blur = d().blurs.find((b) => b.id === dr.id);
    if (dr.live) { video.pause(); S.drag = dr; recordStep(true); S.drag = null; video.playbackRate = S.speed; if (blur && now() > blur.end) blur.end = r3(now()); }
    else if (blur) setKey(blur, now(), dr.box, tol());
    S.rec = null; renderAll(); send(true);
  };
  wrap.addEventListener('pointerup', finish);
  wrap.addEventListener('pointercancel', finish);

  // ---------------------------------------------------------------- oynatma
  const seek = (t) => { video.currentTime = Math.max(0, Math.min(t, dur() - 0.001)); invalidate(); };
  function updateTransport(t) {
    $('.time').textContent = `${fmt(t)} / ${fmt(dur())} sn`;
    $('.play').textContent = video.paused ? ICON.play : ICON.pause;
    $('.playhead').style.left = `calc(var(--label) + (100% - var(--label)) * ${t / dur()})`;
  }
  const loop = () => {
    if (!video.paused) { recordStep(false); dirty = true; }
    if (dirty && S.mode === 'edit') { dirty = false; draw(); }
    S.raf = requestAnimationFrame(loop);
  };
  S.start = () => { if (!S.raf) S.raf = requestAnimationFrame(loop); if (!S.observing) { S.observer.observe(wrap); S.observing = true; } };
  S.observer = new ResizeObserver(invalidate);
  for (const ev of ['loadeddata', 'seeked', 'pause', 'play', 'timeupdate']) video.addEventListener(ev, () => { invalidate(); if (ev === 'pause' || ev === 'seeked') renderLeft(); });

  // ---------------------------------------------------------------- panel ve araç çubuğu şablonları
  const effectDemo = (effect) => `<span class="demo demo-${effect}"><i>A</i><i>B</i><i>C</i></span>`;
  function cards(map, current, action, demo = true) {
    return `<div class="cards">${Object.entries(map).map(([k, label]) => `<button class="card ${k === current ? 'on' : ''}" data-action="${action}" data-value="${k}">${demo ? effectDemo(k) : ''}<span>${esc(label)}</span></button>`).join('')}</div>`;
  }
  const L = () => D().labels;
  function toolbarHtml() {
    const s = sel();
    if (!s) return `<span class="muted">Videoda veya zaman çizelgesinde bir öğeye dokun.</span>`;
    if (['h1', 'h2', 'text'].includes(s.kind)) {
      const st = styleOf(s); if (!st) return '';
      const fonts = D().fonts, families = Object.keys(fonts), weights = fonts[st.family] || [st.style];
      return `<span class="tag">${s.kind === 'text' ? 'Yazı' : s.kind === 'h1' ? 'Başlık 1' : 'Başlık 2'}${s.kind === 'text' ? '' : ' · iki başlık ortak'}</span>
        <select data-action="family" title="Yazı tipi">${families.map((f) => `<option ${f === st.family ? 'selected' : ''}>${esc(f)}</option>`).join('')}</select>
        <select data-action="weight" title="Kalınlık">${weights.map((w) => `<option ${w === st.style ? 'selected' : ''}>${esc(w)}</option>`).join('')}</select>
        <span class="size"><button data-action="size" data-value="-2" title="Küçült">−</button><b>${st.size}</b><button data-action="size" data-value="2" title="Büyüt">+</button></span>
        <label class="color" title="Renk"><span style="border-bottom-color:${esc(st.color)}">A</span><input type="color" data-action="color" value="${esc(st.color)}"></label>
        <button class="tool ${S.strikeMode ? 'on' : ''}" data-action="strike" title="Sansür: sonra videoda kelimeye dokun"><s>S</s></button>
        <button class="tool ${st.upper ? 'on' : ''}" data-action="upper" title="BÜYÜK HARF">aA</button>
        <label class="glow" title="Parıltı">✨<input type="range" min="0" max="100" step="5" value="${Math.round(st.glow * 100)}" data-action="glow"></label>`;
    }
    const blur = selBlur();
    if (blur) {
      const shapes = [['dikdortgen', '▭', 'Dikdörtgen / kare'], ['yuvarlak', '▢', 'Yuvarlak köşeli'], ['elips', '◯', 'Elips / daire']];
      return `<span class="tag">${blur.effect === 'mozaik' ? 'Mozaik' : 'Blur'}</span>
        <span class="seg">${[['blur', 'Bulanık'], ['mozaik', 'Mozaik']].map(([k, l]) => `<button class="${blur.effect === k ? 'on' : ''}" data-action="beffect" data-value="${k}">${l}</button>`).join('')}</span>
        <span class="seg">${shapes.map(([k, i, l]) => `<button class="${blur.shape === k ? 'on' : ''}" data-action="bshape" data-value="${k}" title="${l}">${i}</button>`).join('')}</span>
        <button class="tool" data-action="square" title="Kare / daire yap">1:1</button>
        <button class="tool danger" data-action="bdelete" title="Sil">🗑</button>`;
    }
    if (s.kind === 'slogans' || s.kind === 'logo') {
      const item = d()[s.kind];
      return `<span class="tag">${s.kind === 'logo' ? 'Logo kutusu' : 'Sloganlar'}</span><label class="switch"><input type="checkbox" data-action="toggle" ${item.enabled ? 'checked' : ''}> Videoda göster</label>`;
    }
    return '';
  }
  function slider(label, action, value, min, max, step, unit = '') {
    return `<label class="slider"><span>${label}<b>${value}${unit}</b></span><input type="range" min="${min}" max="${max}" step="${step}" value="${value}" data-action="${action}"></label>`;
  }
  function leftHtml() {
    const s = sel();
    if (!s) {
      return `<h4>Başlarken</h4><p class="muted">Başlığa, yazıya, logoya veya blura dokun: araçlar burada ve üstte açılır.</p>
        <div class="stack"><button class="big" data-action="add-text">➕ Yazı ekle</button><button class="big" data-action="add-blur">◍ Blur ekle</button><button class="big" data-action="add-mosaic">▦ Mozaik ekle</button></div>
        <p class="muted small">Başlık metinleri solda kenar çubuğunda. Sansür için başlığı seç, üstteki <s>S</s>'ye bas, sonra kelimeye dokun.</p>`;
    }
    if (['h1', 'h2', 'text'].includes(s.kind)) {
      const target = s.kind === 'text' ? selText() : headlineOf(s); if (!target) return '';
      const tab = S.animTab || 'enter';
      let html = '';
      if (s.kind === 'text') {
        html += `<h4>Yazı</h4><textarea data-action="text" rows="2">${esc(target.text)}</textarea>
          <div class="row2"><label>Başla<input type="number" step="0.1" min="0" max="${dur()}" value="${target.start}" data-action="tstart"></label>
          <label>Bitir<input type="number" step="0.1" min="0" max="${dur()}" value="${target.end}" data-action="tend"></label>
          <button class="tool" data-action="tnow" title="Başlangıcı şu ana al">⇤ şimdi</button></div>
          <button class="tool danger wide" data-action="tdelete">🗑 Yazıyı sil</button>`;
      }
      html += `<h4>Animasyon</h4><div class="seg wide">${[['enter', 'Girişte'], ['exit', 'Çıkışta']].map(([k, l]) => `<button class="${tab === k ? 'on' : ''}" data-action="animtab" data-value="${k}">${l}</button>`).join('')}</div>
        ${cards(tab === 'enter' ? L().enter : L().exit, tab === 'enter' ? target.enter : target.exit, 'anim')}`;
      return html;
    }
    const blur = selBlur();
    if (blur) {
      const box = boxAt(blur, now());
      return `<h4>${blur.effect === 'mozaik' ? 'Mozaik' : 'Blur'} ayarları</h4>
        ${slider('Güç', 'bstrength', blur.strength, 1, 10, 1)}
        ${slider('Opaklık', 'bopacity', Math.round(blur.opacity * 100), 10, 100, 5, '%')}
        ${slider('Yumuşak kenar', 'bfeather', Math.round((blur.feather || 0) * 100), 0, 100, 5, '%')}
        ${slider('Açı', 'bangle', Math.round(box.r || 0), -180, 180, 1, '°')}
        <h4>Zaman · ${fmt(blur.start)}–${fmt(blur.end)} sn</h4>
        <div class="row2"><button class="tool" data-action="bstart">⇤ Başla: şimdi</button><button class="tool" data-action="bend">Bitir: şimdi ⇥</button></div>
        <h4>Takip · ${blur.keys.length} anahtar kare</h4>
        <div class="row3"><button class="tool" data-action="kprev">◆◀ Önceki</button><button class="tool" data-action="knext">Sonraki ▶◆</button><button class="tool" data-action="kdel">◆✕ Sil</button></div>
        <label class="switch big-switch"><input type="checkbox" data-action="live" ${S.live ? 'checked' : ''}> Canlı takip</label>
        <p class="muted small">Kutuyu sürükle, sağ alttaki yuvarlakla boyutlandır, üstteki yuvarlakla döndür: o anda anahtar kare olur,
        kutu aralarda kendiliğinden kayar. Canlı takipte kutuya basılı tut: video yavaş oynar, sen plakayı takip edersin.</p>`;
    }
    if (s.kind === 'slogans') return `<h4>Slogan animasyonu</h4>${cards(L().slogan, d().slogans.effect, 'seffect')}`;
    if (s.kind === 'logo') return `<h4>Logo animasyonu</h4>${cards(L().logo, d().logo.effect, 'leffect')}`;
    return '';
  }
  function rightHtml() {
    const f = d().frame, daily = D().backgrounds.find((b) => b.name === D().daily);
    const bgs = [{ name: null, label: 'Günün', url: daily ? daily.url : '' }, ...D().backgrounds];
    return `<h4>Arka plan</h4><div class="bgs">${bgs.map((b) => `<button class="bg ${(d().background || null) === b.name ? 'on' : ''}" data-action="bg" data-value="${b.name || ''}" style="background-image:url('${b.url}')"><span>${esc(b.label)}</span></button>`).join('')}</div>
      <h4>Video çerçevesi</h4><div class="cards frames">${Object.entries(L().frame).map(([k, l]) => `<button class="card ${f.style === k ? 'on' : ''}" data-action="frame" data-value="${k}"><span class="fdemo f-${k}"></span><span>${esc(l)}</span></button>`).join('')}</div>
      <div class="row2"><label class="color-row">Çizgi<input type="color" data-action="fcolor" value="${esc(f.color)}"></label><label class="color-row">Işık<input type="color" data-action="faccent" value="${esc(f.accent)}"></label></div>
      ${['sabit', 'yok'].includes(f.style) ? '' : slider('Hız', 'fspeed', f.speed, 0.25, 3, 0.25, 'x')}
      <h4>Şablon</h4><div class="stack"><button class="tool wide" data-action="pick" data-value="slogans">Sloganlar: ${d().slogans.enabled ? L().slogan[d().slogans.effect] : 'kapalı'}</button>
      <button class="tool wide" data-action="pick" data-value="logo">Logo: ${d().logo.enabled ? L().logo[d().logo.effect] : 'kapalı'}</button></div>`;
  }

  // ---------------------------------------------------------------- zaman çizelgesi
  function timelineHtml() {
    const T = D().times, pct = (v) => `${(Math.max(0, Math.min(v, dur())) / dur()) * 100}%`;
    const isSel = (kind, id) => S.sel && S.sel.kind === kind && (id === undefined || S.sel.id === id);
    const clip = (kind, id, a, b, color, label, opts = {}) => `<div class="clip ${isSel(kind, id) ? 'sel' : ''} ${opts.off ? 'off' : ''} ${opts.drag ? 'drag' : ''}"
      data-kind="${kind}" data-id="${id ?? ''}" style="left:${pct(a)};width:calc(${pct(b)} - ${pct(a)});--c:${color}">${opts.drag ? '<i class="edge l"></i>' : ''}<span>${label}</span>${opts.keys || ''}${opts.drag ? '<i class="edge r"></i>' : ''}</div>`;
    const firstLine = (text) => esc((text || '').replace(/~~/g, '').split('\n').join(' ').slice(0, 40));
    let rows = '';
    const ticks = []; const step = dur() > 40 ? 10 : 5;
    for (let s = 0; s <= dur(); s += 1) ticks.push(`<i class="tick ${s % step === 0 ? 'major' : ''}" style="left:${pct(s)}">${s % step === 0 ? s + 's' : ''}</i>`);
    rows += `<div class="trow ruler"><div class="tlabel"></div><div class="ttrack">${ticks.join('')}</div></div>`;
    const sl = D().slogans, dd = d();
    rows += `<div class="trow"><div class="tlabel">Başlık</div><div class="ttrack">
      ${clip('h1', undefined, 0, T.h1_end, TRACK_COLORS.headline, firstLine(D().headlines.h1))}
      ${clip('slogans', undefined, sl[0].start, sl[0].end, TRACK_COLORS.slogan, '···', { off: !dd.slogans.enabled })}
      ${clip('slogans', undefined, sl[1].start, sl[1].end, TRACK_COLORS.slogan, '···', { off: !dd.slogans.enabled })}
      ${clip('h2', undefined, T.h2_start, dur(), TRACK_COLORS.headline, firstLine(D().headlines.h2))}</div></div>`;
    dd.texts.forEach((layer) => {
      rows += `<div class="trow"><div class="tlabel">Yazı</div><div class="ttrack">${clip('text', layer.id, layer.start, layer.end, TRACK_COLORS.text, firstLine(layer.text), { drag: true })}</div></div>`;
    });
    rows += `<div class="trow"><div class="tlabel">Logo</div><div class="ttrack">${clip('logo', undefined, D().logo.start, D().logo.end, TRACK_COLORS.logo, `<img src="${D().logo.url}">`, { off: !dd.logo.enabled })}</div></div>`;
    dd.blurs.forEach((blur, i) => {
      const keys = blur.keys.map((k) => `<b class="key" style="left:${((k.t - blur.start) / Math.max(0.01, blur.end - blur.start)) * 100}%"></b>`).join('');
      rows += `<div class="trow"><div class="tlabel">${blur.effect === 'mozaik' ? 'Mozaik' : 'Blur'} ${i + 1}</div><div class="ttrack">${clip('blur', blur.id, blur.start, blur.end, TRACK_COLORS[blur.effect] || TRACK_COLORS.blur, '', { drag: true, keys })}</div></div>`;
    });
    const strip = D().filmstrip ? `background-image:url('${D().filmstrip}')` : '';
    rows += `<div class="trow tall"><div class="tlabel">Video</div><div class="ttrack"><div class="film" style="${strip}"></div></div></div>`;
    rows += `<div class="trow"><div class="tlabel">Arka plan</div><div class="ttrack"><div class="bgtrack" style="background-image:url('${currentBackgroundUrl()}')"></div></div></div>`;
    return rows;
  }

  // ---------------------------------------------------------------- çizimler
  // Python'dan gelen yenilemede, editörün o an kullandığı girdiyi (kaydırıcı, renk, metin) bozma.
  const busy = (selector) => {
    const active = root.activeElement || document.activeElement;
    return S.fromPython && active && ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName) && $(selector).contains(active);
  };
  function renderToolbar() { if (!busy('.ctx')) $('.ctx').innerHTML = toolbarHtml(); }
  function renderLeft() { if (S.editingText || busy('.left')) return; $('.left').innerHTML = leftHtml(); }
  function renderRight() { if (!busy('.right')) $('.right').innerHTML = rightHtml(); }
  function renderTimeline() { $('.tracks').innerHTML = timelineHtml(); }
  function renderAll() {
    invalidate(); renderToolbar(); renderLeft(); renderRight(); renderTimeline();
    root.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('on', b.dataset.mode === S.mode));
    const final = S.mode === 'final';
    canvas.style.display = final ? 'none' : 'block';
    finalVideo.style.display = final ? 'block' : 'none';
    $('.msg-final').style.display = final && !D().final ? 'flex' : 'none';
    $('.tl').classList.toggle('dim', final);
  }

  // ---------------------------------------------------------------- olaylar (tek dinleyici, data-action)
  function styleChange(fn) { const st = styleOf(S.sel); if (!st) return; change(() => fn(st)); }
  function blurChange(fn, immediate = true) { const b = selBlur(); if (!b) return; fn(b); invalidate(); renderTimeline(); renderToolbar(); send(immediate); }
  function addBlur(effect) {
    const t = r3(now()), id = 'b' + Date.now().toString(36);
    d().blurs.push({ id, effect, shape: effect === 'mozaik' ? 'dikdortgen' : 'yuvarlak', strength: effect === 'mozaik' ? 4 : 6, opacity: 1, feather: 0.3,
      start: t, end: Math.min(dur(), r3(t + 3)), keys: [{ t, x: 0.35, y: 0.44, w: 0.3, h: 0.12, r: 0 }] });
    S.sel = { kind: 'blur', id }; renderAll(); send(true);
  }
  function addText() {
    const t = r3(now()), id = 't' + Date.now().toString(36);
    const base = d().headline_style;
    d().texts.push({ id, text: 'YAZI', family: base.family, style: base.style, size: 48, color: '#FFFFFF', glow: 0.38, upper: false,
      x: 0.5, y: 0.88, start: t, end: Math.min(dur(), r3(t + 5)), enter: 'fade', exit: 'fade' });
    S.sel = { kind: 'text', id }; renderAll(); send(true);
  }
  const actions = {
    family: (el) => styleChange((st) => { st.family = el.value; const w = D().fonts[el.value] || []; if (!w.includes(st.style)) st.style = w.includes('Bold') ? 'Bold' : w[w.length - 1]; }),
    weight: (el) => styleChange((st) => { st.style = el.value; }),
    size: (el) => styleChange((st) => { st.size = Math.max(16, Math.min(160, st.size + parseInt(el.dataset.value, 10))); }),
    color: (el) => styleChange((st) => { st.color = el.value.toUpperCase(); }),
    glow: (el) => { const st = styleOf(S.sel); if (st) { st.glow = parseInt(el.value, 10) / 100; send(false); } },
    upper: () => styleChange((st) => { st.upper = !st.upper; }),
    strike: () => { S.strikeMode = !S.strikeMode; renderToolbar(); invalidate(); },
    animtab: (el) => { S.animTab = el.dataset.value; renderLeft(); },
    anim: (el) => { const s = S.sel, target = s.kind === 'text' ? selText() : headlineOf(s); change(() => { target[(S.animTab || 'enter') === 'enter' ? 'enter' : 'exit'] = el.dataset.value; }); },
    text: (el) => { const t = selText(); if (t) { t.text = el.value; renderTimeline(); send(false); } },
    tstart: (el) => { const t = selText(); if (t) change(() => { t.start = Math.max(0, Math.min(parseFloat(el.value) || 0, t.end - 0.2)); }); },
    tend: (el) => { const t = selText(); if (t) change(() => { t.end = Math.min(dur(), Math.max(parseFloat(el.value) || 0, t.start + 0.2)); }); },
    tnow: () => { const t = selText(); if (t) change(() => { const len = t.end - t.start; t.start = r3(now()); t.end = Math.min(dur(), r3(t.start + len)); }); },
    tdelete: () => { const id = S.sel.id; d().texts = d().texts.filter((x) => x.id !== id); S.sel = null; renderAll(); send(true); },
    'add-text': addText, 'add-blur': () => addBlur('blur'), 'add-mosaic': () => addBlur('mozaik'),
    beffect: (el) => blurChange((b) => { b.effect = el.dataset.value; renderLeft(); }),
    bshape: (el) => blurChange((b) => { b.shape = el.dataset.value; }),
    square: () => blurChange((b) => { const box = boxAt(b, now()), s = D().slot; box.h = box.w * s.w / s.h; setKey(b, now(), box, tol()); }),
    bdelete: () => { const id = S.sel.id; d().blurs = d().blurs.filter((b) => b.id !== id); S.sel = null; renderAll(); send(true); },
    bstrength: (el) => blurChange((b) => { b.strength = parseInt(el.value, 10); sliderValue(el); }, false),
    bopacity: (el) => blurChange((b) => { b.opacity = parseInt(el.value, 10) / 100; sliderValue(el, '%'); }, false),
    bfeather: (el) => blurChange((b) => { b.feather = parseInt(el.value, 10) / 100; sliderValue(el, '%'); }, false),
    bangle: (el) => blurChange((b) => { const box = boxAt(b, now()); box.r = parseInt(el.value, 10); setKey(b, now(), box, tol()); sliderValue(el, '°'); }, false),
    bstart: () => blurChange((b) => { if (now() < b.end) b.start = r3(now()); renderLeft(); }),
    bend: () => blurChange((b) => { if (now() > b.start) b.end = r3(now()); renderLeft(); }),
    kprev: () => { const b = selBlur(); if (!b) return; const k = [...b.keys].reverse().find((k) => k.t < now() - tol()); seek(k ? k.t : b.start); },
    knext: () => { const b = selBlur(); if (!b) return; const k = b.keys.find((k) => k.t > now() + tol()); seek(k ? k.t : b.end - 0.01); },
    kdel: () => blurChange((b) => { if (b.keys.length < 2) return; const i = b.keys.findIndex((k) => Math.abs(k.t - now()) <= tol()); if (i >= 0) b.keys.splice(i, 1); renderLeft(); }),
    live: (el) => { S.live = el.checked; },
    toggle: (el) => change(() => { d()[S.sel.kind].enabled = el.checked; }),
    seffect: (el) => change(() => { d().slogans.effect = el.dataset.value; d().slogans.enabled = true; }),
    leffect: (el) => change(() => { d().logo.effect = el.dataset.value; d().logo.enabled = true; }),
    pick: (el) => select({ kind: el.dataset.value }),
    bg: (el) => change(() => { d().background = el.dataset.value || null; }),
    frame: (el) => change(() => { d().frame.style = el.dataset.value; }),
    fcolor: (el) => change(() => { d().frame.color = el.value.toUpperCase(); }),
    faccent: (el) => change(() => { d().frame.accent = el.value.toUpperCase(); }),
    fspeed: (el) => { d().frame.speed = parseFloat(el.value); sliderValue(el, 'x'); invalidate(); send(false); },
  };
  function sliderValue(el, unit = '') { const b = el.closest('.slider'); if (b) b.querySelector('b').textContent = el.value + unit; }
  const onInput = new Set(['glow', 'text', 'bstrength', 'bopacity', 'bfeather', 'bangle', 'fspeed']);
  root.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]'); if (!el || el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') return;
    const fn = actions[el.dataset.action]; if (fn) fn(el);
  });
  root.addEventListener('input', (e) => { const el = e.target.closest('[data-action]'); if (el && onInput.has(el.dataset.action)) { if (el.dataset.action === 'text') S.editingText = true; actions[el.dataset.action](el); } });
  root.addEventListener('change', (e) => {
    const el = e.target.closest('[data-action]'); if (!el) return;
    if (el.dataset.action === 'text') { S.editingText = false; send(true); return; }
    if (!onInput.has(el.dataset.action)) { const fn = actions[el.dataset.action]; if (fn) fn(el); }
    else if (el.dataset.action !== 'glow') renderLeft();
  });
  root.querySelectorAll('[data-mode]').forEach((b) => { b.onclick = () => { S.mode = b.dataset.mode; if (S.mode === 'final') video.pause(); renderAll(); }; });
  $('.play').onclick = () => { if (video.paused) video.play(); else video.pause(); };
  $('.back').onclick = () => seek(now() - 1 / D().fps);
  $('.fwd').onclick = () => seek(now() + 1 / D().fps);
  $('.speed').onchange = (e) => { S.speed = parseFloat(e.target.value); video.playbackRate = S.speed; };
  $('.t-add-text').onclick = addText;
  $('.t-add-blur').onclick = () => addBlur('blur');
  $('.t-add-mosaic').onclick = () => addBlur('mozaik');

  // zaman çizelgesi: tıklayıp sar, klibe dokunup seç, yazı/blur kliplerini taşı veya kenarından uzat
  const tl = $('.tl');
  const timeAt = (e) => { const track = tl.querySelector('.ttrack'); const r = track.getBoundingClientRect(); return clamp((e.clientX - r.left) / r.width) * dur(); };
  tl.addEventListener('pointerdown', (e) => {
    if (S.mode !== 'edit') return;
    const clipEl = e.target.closest('.clip');
    tl.setPointerCapture(e.pointerId);
    if (clipEl) {
      const kind = clipEl.dataset.kind, id = clipEl.dataset.id || undefined;
      S.sel = { kind, id }; S.strikeMode = false;
      const item = kind === 'text' ? d().texts.find((x) => x.id === id) : kind === 'blur' ? d().blurs.find((b) => b.id === id) : null;
      if (item && clipEl.classList.contains('drag')) {
        const edge = e.target.classList.contains('edge') ? (e.target.classList.contains('l') ? 'start' : 'end') : 'move';
        S.tdrag = { item, edge, t0: timeAt(e), start: item.start, end: item.end, keys: item.keys ? clone(item.keys) : null, moved: false };
      }
      renderAll(); return;
    }
    S.tdrag = { seek: true }; seek(timeAt(e));
  });
  tl.addEventListener('pointermove', (e) => {
    const g = S.tdrag; if (!g) return;
    if (g.seek) { seek(timeAt(e)); return; }
    const delta = timeAt(e) - g.t0, it = g.item; g.moved = true;
    if (g.edge === 'start') it.start = r3(Math.max(0, Math.min(g.start + delta, it.end - 0.2)));
    else if (g.edge === 'end') it.end = r3(Math.min(dur(), Math.max(g.end + delta, it.start + 0.2)));
    else {
      const shift = Math.max(-g.start, Math.min(delta, dur() - g.end));
      it.start = r3(g.start + shift); it.end = r3(g.end + shift);
      if (g.keys) it.keys = g.keys.map((k) => ({ ...k, t: r3(k.t + shift) }));
    }
    renderTimeline(); invalidate();
  });
  const tlUp = () => { const g = S.tdrag; S.tdrag = null; if (g && g.moved) { renderAll(); send(true); } else if (g && g.seek) renderLeft(); };
  tl.addEventListener('pointerup', tlUp);
  tl.addEventListener('pointercancel', tlUp);

  S.applyData = () => {
    const data = D();
    if (video.getAttribute('src') !== data.video) video.setAttribute('src', data.video);
    if (data.final && finalVideo.getAttribute('src') !== data.final) finalVideo.setAttribute('src', data.final);
    if (S.sel && S.sel.kind === 'text' && !d().texts.some((x) => x.id === S.sel.id)) S.sel = null;
    if (S.sel && S.sel.kind === 'blur' && !d().blurs.some((x) => x.id === S.sel.id)) S.sel = null;
    S.fromPython = true; renderAll(); S.fromPython = false;
  };
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  let S = STATE.get(parentElement);
  if (!S) {
    S = { project: null, sel: null, drag: null, rec: null, timer: null, version: 0, born: Date.now().toString(36), ops: [], mode: 'edit', speed: 1, live: false };
    STATE.set(parentElement, S);
    S.data = data; S.setStateValue = setStateValue;
    setup(parentElement, S);
  }
  S.data = data; S.setStateValue = setStateValue;
  if (S.project !== data.project) {  // tasarım editörde tutulur; yalnızca haber değişince Python'dan yüklenir
    S.project = data.project; S.design = clone(data.design); S.sel = null; S.ops = []; S.mode = 'edit';
  }
  S.start();
  S.applyData();
  return () => { cancelAnimationFrame(S.raf); S.raf = null; S.observer.disconnect(); S.observing = false; };
}
