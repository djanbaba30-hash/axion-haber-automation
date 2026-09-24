// Tasarım Stüdyosu canlı önizleme + blur/yazı editörü (Streamlit components v2).
// Efekt formülleri apps/design_studio/effects.py ile aynıdır; son video Python'da üretilir.

const STATE = new WeakMap();
const W = 1080, H = 1920;
const clamp = (p) => Math.min(1, Math.max(0, p));
const easeOut = (p) => 1 - Math.pow(1 - clamp(p), 3);
const easeIn = (p) => Math.pow(clamp(p), 3);
const easeOutBack = (p) => { p = clamp(p); const c = 1.70158; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
const fmt = (t) => t.toFixed(1).replace('.', ',');
const r3 = (t) => Math.round(t * 1000) / 1000;
const COLORS = { h1: '#123249', s: '#2f8f5b', h2: '#1f6fb2', logo: '#7a8699', text: '#8a5cc7', blur: '#e08a1e', mozaik: '#c0612b' };

// ---------------------------------------------------------------- yazı efektleri (effects.py ile aynı)
const MERGE = { stagger: 0.045, gap: 0.1, fade: 0.12, slide: 24, move: 0.6, exitSeconds: 0.26, exitSlide: 13 };
const word = (a = 1, dx = 0, dy = 0) => ({ a, dx, dy });
function stagger(n, step, limit) { return Math.min(step, limit / Math.max(1, n)); }
function mergeDelays(lines) {
  const order = [];
  [...new Set(lines)].sort((a, b) => a - b).forEach((line) => {
    const idx = lines.map((v, i) => (v === line ? i : -1)).filter((i) => i >= 0);
    order.push(...(line === 0 ? idx.reverse() : idx));
  });
  const st = Math.min(MERGE.stagger, 0.55 / Math.max(1, order.length));
  const delays = new Array(lines.length).fill(0);
  let delay = 0, prev = order.length ? lines[order[0]] : 0;
  for (const i of order) {
    if (lines[i] !== prev) { delay += MERGE.gap; prev = lines[i]; }
    delays[i] = delay; delay += st;
  }
  return delays;
}
function enterSeconds(effect, lines) {
  const n = lines.length;
  if (effect === 'merge') return Math.max(0, ...mergeDelays(lines)) + MERGE.move;
  if (effect === 'fade') return 0.4;
  if (effect === 'slide') return stagger(n, 0.06, 0.5) * Math.max(0, n - 1) + 0.45;
  if (effect === 'typewriter') return stagger(n, 0.11, 1.2) * n;
  if (effect === 'pop') return 0.35;
  return 0;
}
function exitSeconds(effect, lines) {
  const n = lines.length;
  if (effect === 'merge') return MERGE.exitSeconds;
  if (effect === 'fade') return 0.35;
  if (effect === 'slide') return stagger(n, 0.03, 0.2) * Math.max(0, n - 1) + 0.35;
  if (effect === 'pop') return 0.25;
  return 0;
}
function enterState(effect, lines, t) {
  const n = lines.length;
  if (effect === 'merge') {
    const d = mergeDelays(lines);
    return { scale: 1, words: lines.map((line, i) => { const l = t - d[i]; return word(clamp(l / MERGE.fade), (line === 0 ? 1 : -1) * MERGE.slide * (1 - easeOut(l / MERGE.move))); }) };
  }
  if (effect === 'fade') return { scale: 1, words: lines.map(() => word(easeOut(t / 0.4))) };
  if (effect === 'slide') { const s = stagger(n, 0.06, 0.5); return { scale: 1, words: lines.map((_, i) => word(clamp((t - i * s) / 0.2), 0, 36 * (1 - easeOut((t - i * s) / 0.45)))) }; }
  if (effect === 'typewriter') { const s = stagger(n, 0.11, 1.2); return { scale: 1, words: lines.map((_, i) => word(t >= i * s ? 1 : 0)) }; }
  if (effect === 'pop') return { scale: 0.6 + 0.4 * easeOutBack(t / 0.35), words: lines.map(() => word(clamp(t / 0.15))) };
  return { scale: 1, words: lines.map(() => word()) };
}
function exitState(effect, lines, t) {
  const n = lines.length;
  if (effect === 'merge') {
    const p = t / MERGE.exitSeconds, dx = -MERGE.exitSlide * easeIn(p);
    return { scale: 1, words: lines.map((line) => word(line === 0 ? 1 - clamp((p - 0.35) / 0.2) : 1 - easeIn((p - 0.55) / 0.45), dx)) };
  }
  if (effect === 'fade') return { scale: 1, words: lines.map(() => word(1 - easeIn(t / 0.35))) };
  if (effect === 'slide') { const s = stagger(n, 0.03, 0.2); return { scale: 1, words: lines.map((_, i) => word(1 - clamp((t - i * s) / 0.35), 0, -30 * easeIn((t - i * s) / 0.35))) }; }
  if (effect === 'pop') { const p = t / 0.25; return { scale: 1 - 0.3 * easeIn(p), words: lines.map(() => word(1 - clamp(p))) }; }
  return { scale: 1, words: lines.map(() => word(0)) };
}
function textState(enter, exit, lines, start, end, t) {
  if (t < start || t >= end) return null;
  const exitLen = Math.min(exitSeconds(exit, lines), Math.max(0, end - start));
  if (t >= end - exitLen) return exitState(exit, lines, t - (end - exitLen));
  if (t - start < enterSeconds(enter, lines)) return enterState(enter, lines, t - start);
  return { scale: 1, words: lines.map(() => word()) };
}

// ---------------------------------------------------------------- slogan ve logo efektleri
const SLOGAN_IN = { old_tv: 0.56, fade: 0.3, pop: 0.35, yok: 0 };
const SLOGAN_OUT = { old_tv: 0.23, fade: 0.3, pop: 0.2, yok: 0 };
function oldTvScale(a) {
  a = clamp(a);
  let sx = clamp((a - 0.08) / 0.3); sx = sx * sx * (3 - 2 * sx);
  const sy = a < 0.38 ? 0.2 + 0.25 * a / 0.38 : 0.45 + 0.55 * easeOut((a - 0.38) / 0.3);
  return [Math.max(sx, a > 0 ? 0.02 : 0), sy];
}
function sloganState(effect, start, end, t, frame) {
  if (t < start || t >= end) return null;
  const rise = SLOGAN_IN[effect] || 0, fall = SLOGAN_OUT[effect] || 0;
  let p, entering;
  if (t < start + rise) { p = (t - start) / rise; entering = true; }
  else if (t >= end - fall) { p = 1 - (t - (end - fall)) / fall; entering = false; }
  else return { a: 1, sx: 1, sy: 1, dy: 0, split: 0, flicker: false };
  if (effect === 'old_tv') { const [sx, sy] = oldTvScale(p); return { a: 1, sx, sy, dy: 0, split: p < 0.97 ? Math.round(7 * (1 - p)) + 1 : 0, flicker: frame % 2 === 1 && p < 0.97 }; }
  if (effect === 'fade') return { a: entering ? easeOut(p) : easeIn(p), sx: 1, sy: 1, dy: 0, split: 0 };
  if (effect === 'pop') { const s = entering ? 0.5 + 0.5 * easeOutBack(p) : 0.7 + 0.3 * p; return { a: clamp(p / 0.4), sx: s, sy: s, dy: 0, split: 0 }; }
  return { a: 1, sx: 1, sy: 1, dy: 0, split: 0 };
}
function logoState(L, t) {
  if (t < L.start || t >= L.end) return null;
  const glint = t >= L.glint[0] && t < L.glint[1] ? (t - L.glint[0]) / (L.glint[1] - L.glint[0]) : null;
  const rise = H - L.rest_y;
  if (L.effect === 'slow_baseline') {
    let y;
    if (t < L.drop_start) y = H - rise * (1 - Math.exp(-(t - L.start) / L.tau));
    else { const top = H - rise * (1 - Math.exp(-(L.drop_start - L.start) / L.tau)); y = top + (H - top) * Math.pow(clamp((t - L.drop_start) / (L.end - L.drop_start)), 1.5); }
    return { a: 1, sx: 1, sy: 1, dy: y - L.rest_y, glint };
  }
  if (L.effect === 'fade') return { a: Math.min(easeOut((t - L.start) / 0.4), 1 - easeIn((t - (L.end - 0.3)) / 0.3)), sx: 1, sy: 1, dy: 0, glint };
  if (L.effect === 'pop') {
    const pin = (t - L.start) / 0.35, pout = (t - (L.end - 0.25)) / 0.25;
    const s = pin < 1 ? 0.3 + 0.7 * easeOutBack(pin) : (pout > 0 ? 1 - 0.7 * easeIn(pout) : 1);
    return { a: clamp(pin / 0.3) * (1 - clamp(pout)), sx: s, sy: s, dy: 0, glint };
  }
  return { a: 1, sx: 1, sy: 1, dy: 0, glint };
}

// ---------------------------------------------------------------- çerçeve (üst ortadan saat yönünde s: 0..1)
function frameGeom(F) {
  const half = F.border / 2;
  const g = { cx: F.slot.x + F.slot.w / 2, cy: F.slot.y + F.slot.h / 2, hx: F.slot.w / 2 - half, hy: F.slot.h / 2 - half, r: F.radius - half };
  g.top = 2 * (g.hx - g.r); g.side = 2 * (g.hy - g.r); g.arc = Math.PI * g.r / 2;
  g.per = 2 * g.top + 2 * g.side + 4 * g.arc;
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
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function drawFrame(ctx, F, t) {
  if (F.style === 'yok') return;
  const g = frameGeom(F), half = F.border / 2;
  const path = () => roundRectPath(ctx, F.slot.x + half, F.slot.y + half, F.slot.w - F.border, F.slot.h - F.border, g.r);
  const period = (F.periods[F.style] || 1) / Math.max(0.2, F.speed);
  ctx.save();
  ctx.lineCap = 'round';
  if (F.style === 'sabit') { path(); ctx.strokeStyle = F.color; ctx.lineWidth = F.border; ctx.stroke(); }
  else if (F.style === 'nefes') {
    const pulse = 0.5 + 0.5 * Math.sin(2 * Math.PI * t / period);
    path(); ctx.shadowColor = F.accent; ctx.shadowBlur = 6 + 16 * pulse; ctx.strokeStyle = F.color; ctx.lineWidth = 2.5 + 2.5 * pulse; ctx.stroke();
  } else if (F.style === 'akis') {
    const grad = ctx.createConicGradient(-Math.PI / 2 + 2 * Math.PI * (t / period), g.cx, g.cy);
    [[0, F.color], [0.33, F.accent], [0.66, '#D0E491'], [1, F.color]].forEach(([o, c]) => grad.addColorStop(o, c));
    path(); ctx.strokeStyle = grad; ctx.lineWidth = 5; ctx.stroke();
  } else if (F.style === 'kovalayan') {
    path(); ctx.globalAlpha = 0.35; ctx.strokeStyle = F.color; ctx.lineWidth = 1.5; ctx.stroke(); ctx.globalAlpha = 1;
    const steps = 70;
    for (const offset of [0, 0.5]) {
      const head = (t / period + offset) % 1;
      let prev = pointAt(g, head);
      for (let i = 1; i <= steps; i++) {
        const k = 1 - i / steps;
        const p = pointAt(g, head - (i / steps) * F.comet.tail);
        ctx.beginPath(); ctx.moveTo(prev[0], prev[1]); ctx.lineTo(p[0], p[1]);
        ctx.strokeStyle = k > 0.5 ? '#FFFFFF' : F.accent;
        ctx.globalAlpha = 0.35 + 0.65 * k;
        ctx.shadowColor = F.accent; ctx.shadowBlur = 12 * k * k;
        ctx.lineWidth = 0.6 + F.comet.head * Math.pow(k, 1.3);
        ctx.stroke(); prev = p;
      }
    }
  }
  ctx.restore();
}

// ---------------------------------------------------------------- blur kutuları
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
  const key = { t: r3(t), x: box.x, y: box.y, w: box.w, h: box.h, r: Math.round(box.r * 10) / 10 };
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

// ---------------------------------------------------------------- kurulum
function setup(root, S) {
  const $ = (s) => root.querySelector(s);
  const canvas = $('.stage'), ctx = canvas.getContext('2d'), video = $('.vid'), wrap = $('.stage-wrap');
  const D = () => S.data;
  const now = () => video.currentTime || 0;
  const tol = () => 1.5 / D().fps;
  const dur = () => D().duration;
  const selBlur = () => S.blurs.find((b) => b.id === S.sel) || null;
  const images = new Map();
  const off = { eff: document.createElement('canvas'), mask: document.createElement('canvas'), small: document.createElement('canvas'), tmp: document.createElement('canvas') };
  let dirty = true;
  const invalidate = () => { dirty = true; };

  function img(url) {
    if (!url) return null;
    let im = images.get(url);
    if (!im) { im = new Image(); im.onload = invalidate; im.src = url; images.set(url, im); }
    return im.complete && im.naturalWidth ? im : null;
  }
  function channels(url) {  // eski TV renk kayması için tek kanallı kopyalar
    const key = 'ch:' + url;
    if (images.has(key)) return images.get(key);
    const im = img(url); if (!im) return null;
    const make = (ch) => {
      const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
      const x = c.getContext('2d'); x.drawImage(im, 0, 0);
      const d = x.getImageData(0, 0, c.width, c.height);
      for (let i = 0; i < d.data.length; i += 4) for (let j = 0; j < 3; j++) if (j !== ch) d.data[i + j] = 0;
      x.putImageData(d, 0, 0); return c;
    };
    const out = [make(0), make(1), make(2)];
    images.set(key, out); return out;
  }

  function send() {
    const payload = { v: `${S.born}-${++S.version}`, blurs: S.blurs, texts: S.textPos, selected_text: S.selText };  // sayfaya her dönüşte benzersiz
    S.setStateValue('edits', JSON.parse(JSON.stringify(payload)));
  }
  function sendSoon() { clearTimeout(S.timer); S.timer = setTimeout(send, 450); }

  // --- çizim
  function drawBlock(block, state) {
    const atlas = img(block.atlas); if (!atlas) return;
    const [cx, cy] = block.center;
    const dx0 = S.drag && S.drag.kind === 'text' && S.drag.id === block.id ? S.drag.dx : 0;
    const dy0 = S.drag && S.drag.kind === 'text' && S.drag.id === block.id ? S.drag.dy : 0;
    block.words.forEach((w, i) => {
      const ws = state.words[i]; if (!ws || ws.a <= 0.004) return;
      let x = w.x + ws.dx + dx0, y = w.y + ws.dy + dy0, sw = w.sw, sh = w.sh;
      if (Math.abs(state.scale - 1) > 0.001) {
        const mx = x + sw / 2, my = y + sh / 2; sw *= state.scale; sh *= state.scale;
        x = cx + dx0 + (mx - cx - dx0) * state.scale - sw / 2; y = cy + dy0 + (my - cy - dy0) * state.scale - sh / 2;
      }
      ctx.globalAlpha = ws.a; ctx.drawImage(atlas, w.sx, w.sy, w.sw, w.sh, x, y, sw, sh);
    });
    ctx.globalAlpha = 1;
  }
  function drawSprite(url, center, st) {
    const im = img(url); if (!im || st.a <= 0.004 || st.sx <= 0 || st.sy <= 0) return;
    const w = im.naturalWidth * st.sx, h = im.naturalHeight * st.sy;
    const x = center[0] - w / 2, y = center[1] - h / 2 + (st.dy || 0);
    ctx.globalAlpha = st.a * (st.flicker ? 0.8 : 1);
    const ch = st.split ? channels(url) : null;
    if (ch) {
      const t = off.tmp; t.width = Math.ceil(w + 2 * st.split); t.height = Math.ceil(h);
      const tc = t.getContext('2d'); tc.globalCompositeOperation = 'lighter';
      ch.forEach((c, i) => tc.drawImage(c, i * st.split, 0, w, h));
      ctx.drawImage(t, x, y);
    } else ctx.drawImage(im, x, y, w, h);
    if (st.glint != null) {
      ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
      const c = x - 60 + (w + 120) * st.glint;
      ctx.beginPath(); ctx.moveTo(c - 18, y + h); ctx.lineTo(c + 18, y + h); ctx.lineTo(c + 18 + h * 0.55, y); ctx.lineTo(c - 18 + h * 0.55, y); ctx.closePath();
      ctx.fillStyle = 'rgba(205,205,205,0.43)'; ctx.fill(); ctx.restore();
    }
    ctx.globalAlpha = 1;
  }
  function drawEffects(k, t) {
    const d = D(), slot = d.slot;
    const sw = Math.max(1, Math.round(slot.w * k)), sh = Math.max(1, Math.round(slot.h * k));
    for (const blur of S.blurs) {
      if (!(t >= blur.start && t < blur.end)) continue;
      const b = S.drag && S.drag.kind === 'blur' && S.drag.id === blur.id ? S.drag.box : boxAt(blur, t);
      const eff = off.eff; eff.width = sw; eff.height = sh;
      const ec = eff.getContext('2d');
      if (blur.effect === 'mozaik') {
        const block = (6 + 4 * blur.strength) * k;
        const sm = off.small; sm.width = Math.max(2, Math.round(sw / block)); sm.height = Math.max(2, Math.round(sh / block));
        sm.getContext('2d').drawImage(video, 0, 0, sm.width, sm.height);
        ec.imageSmoothingEnabled = false; ec.drawImage(sm, 0, 0, sw, sh);
      } else {
        ec.filter = `blur(${4 * blur.strength * k}px)`; ec.drawImage(video, 0, 0, sw, sh); ec.filter = 'none';
      }
      const m = off.mask; m.width = sw; m.height = sh;
      const mc = m.getContext('2d');
      const bw = b.w * sw, bh = b.h * sh, feather = (blur.feather || 0) * Math.min(bw, bh) / 2;
      mc.translate((b.x + b.w / 2) * sw, (b.y + b.h / 2) * sh); mc.rotate((b.r || 0) * Math.PI / 180);
      if (feather > 0.5) mc.filter = `blur(${feather / 2}px)`;
      shapePath(mc, blur.shape, Math.max(1, bw - feather), Math.max(1, bh - feather));
      mc.fillStyle = `rgba(255,255,255,${blur.opacity})`; mc.fill();
      ec.globalCompositeOperation = 'destination-in'; ec.drawImage(m, 0, 0); ec.globalCompositeOperation = 'source-over';
      ctx.drawImage(eff, slot.x, slot.y, slot.w, slot.h);
    }
  }
  function draw() {
    const d = D();
    const cssW = wrap.clientWidth || 360, dpr = window.devicePixelRatio || 1;
    const bw = Math.round(cssW * dpr), bh = Math.round(cssW * dpr * H / W);
    if (canvas.width !== bw || canvas.height !== bh) { canvas.width = bw; canvas.height = bh; }
    const k = bw / W, t = now(), frame = Math.round(t * d.fps);
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const bg = img(d.images.bg); if (bg) ctx.drawImage(bg, 0, 0, W, H); else { ctx.fillStyle = '#0d1f24'; ctx.fillRect(0, 0, W, H); }
    const s = d.slot;
    ctx.save(); roundRectPath(ctx, s.x, s.y, s.w, s.h, d.frame.radius); ctx.clip();
    if (video.readyState >= 2) { ctx.drawImage(video, s.x, s.y, s.w, s.h); drawEffects(k, t); }
    else { ctx.fillStyle = '#111'; ctx.fillRect(s.x, s.y, s.w, s.h); }
    ctx.restore();
    drawFrame(ctx, d.frame, t);
    // grafikler (Python ile aynı sıra)
    const draws = [];
    const h1 = textState(d.blocks.h1.enter, d.blocks.h1.exit, d.blocks.h1.lines, 0, d.times.h1_end, t);
    if (h1) draws.push(() => drawBlock(d.blocks.h1, h1));
    if (d.slogans.enabled) d.slogans.items.forEach((it) => { const st = sloganState(d.slogans.effect, it.start, it.end, t, frame); if (st) draws.push(() => drawSprite(it.url, d.slogans.center, st)); });
    const h2 = textState(d.blocks.h2.enter, d.blocks.h2.exit, d.blocks.h2.lines, d.times.h2_start, d.duration + 1, t);
    if (h2) draws.push(() => drawBlock(d.blocks.h2, h2));
    if (d.logo.enabled) { const st = logoState(d.logo, t); if (st) draws.push(() => drawSprite(d.logo.url, d.logo.center, st)); }
    for (const block of d.blocks.texts) { const st = textState(block.enter, block.exit, block.lines, block.start, block.end, t); if (st) draws.push(() => drawBlock(block, st)); }
    draws.forEach((f) => f());
    drawSelection(t);
    updateBar(t);
  }
  function drawSelection(t) {
    const d = D();
    const blur = selBlur();
    if (blur) {
      const b = S.drag && S.drag.kind === 'blur' && S.drag.id === blur.id ? S.drag.box : boxAt(blur, t);
      const c = blurCenter(b);
      ctx.save(); ctx.translate(c[0], c[1]); ctx.rotate((b.r || 0) * Math.PI / 180);
      const w = b.w * d.slot.w, h = b.h * d.slot.h;
      const active = t >= blur.start && t < blur.end;
      shapePath(ctx, 'dikdortgen', w, h);
      ctx.lineWidth = 9; ctx.strokeStyle = 'rgba(18,50,73,0.55)'; ctx.stroke();           // koyu alt çizgi: her zeminde görünsün
      ctx.setLineDash([16, 10]); ctx.lineWidth = 5; ctx.strokeStyle = active ? '#7fd3ff' : 'rgba(127,211,255,0.55)'; ctx.stroke();
      ctx.setLineDash([]); ctx.lineWidth = 4; ctx.strokeStyle = '#7fd3ff';
      ctx.fillStyle = '#7fd3ff';
      ctx.beginPath(); ctx.arc(w / 2, h / 2, 22, 0, 2 * Math.PI); ctx.fill();            // boyut
      ctx.beginPath(); ctx.moveTo(0, -h / 2); ctx.lineTo(0, -h / 2 - 50); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, -h / 2 - 62, 20, 0, 2 * Math.PI); ctx.fill();           // döndür
      ctx.restore();
    }
    const tb = d.blocks.texts.find((x) => x.id === S.selText);
    if (tb) {
      const dx = S.drag && S.drag.kind === 'text' ? S.drag.dx : 0, dy = S.drag && S.drag.kind === 'text' ? S.drag.dy : 0;
      const rect = [tb.bbox[0] + dx - 8, tb.bbox[1] + dy - 8, tb.bbox[2] - tb.bbox[0] + 16, tb.bbox[3] - tb.bbox[1] + 16];
      ctx.save(); ctx.lineWidth = 9; ctx.strokeStyle = 'rgba(18,50,73,0.55)'; ctx.strokeRect(...rect);
      ctx.setLineDash([16, 10]); ctx.lineWidth = 5; ctx.strokeStyle = '#d7bcff'; ctx.strokeRect(...rect); ctx.restore();
    }
  }
  const blurCenter = (b) => { const s = D().slot; return [s.x + (b.x + b.w / 2) * s.w, s.y + (b.y + b.h / 2) * s.h]; };

  // --- alt çubuk, zaman çizelgesi, blur paneli
  function updateBar(t) {
    $('.time').textContent = `${fmt(t)} / ${fmt(dur())} sn`;
    $('.play').textContent = video.paused ? '▶' : '⏸';
    $('.head').style.left = `${(t / dur()) * 100}%`;
  }
  function renderTimeline() {
    const d = D(), rows = $('.rows'); rows.innerHTML = '';
    const pct = (v) => `${(Math.max(0, Math.min(v, dur())) / dur()) * 100}%`;
    const seg = (row, a, b, color, label) => {
      const el = document.createElement('div'); el.className = 'seg';
      Object.assign(el.style, { left: pct(a), width: `calc(${pct(b)} - ${pct(a)})`, background: color });
      el.textContent = label || ''; row.appendChild(el); return el;
    };
    const row = (cls = '') => { const r = document.createElement('div'); r.className = 'row ' + cls; rows.appendChild(r); return r; };
    const base = row();
    seg(base, 0, d.times.h1_end, COLORS.h1, 'Başlık 1');
    if (d.slogans.enabled) seg(base, d.slogans.items[0].start, d.slogans.items[1].end, COLORS.s, 'Slogan');
    seg(base, d.times.h2_start, dur(), COLORS.h2, 'Başlık 2');
    if (d.logo.enabled) seg(base, d.logo.start, d.logo.end, COLORS.logo, 'Logo');
    d.blocks.texts.forEach((b) => seg(row(b.id === S.selText ? 'sel' : ''), b.start, b.end, COLORS.text, b.label));
    S.blurs.forEach((blur, i) => {
      const r = row(blur.id === S.sel ? 'sel' : '');
      seg(r, blur.start, blur.end, COLORS[blur.effect] || COLORS.blur, `${blur.effect === 'mozaik' ? 'Mozaik' : 'Blur'} ${i + 1}`);
      blur.keys.forEach((k) => { const dia = document.createElement('div'); dia.className = 'key'; dia.style.left = pct(k.t); r.appendChild(dia); });
    });
  }
  function renderPanel() {
    const list = $('.chips'); list.innerHTML = '';
    S.blurs.forEach((blur, i) => {
      const c = document.createElement('button'); c.type = 'button'; c.className = 'chip' + (blur.id === S.sel ? ' sel' : '');
      c.textContent = `${blur.effect === 'mozaik' ? '▦' : '◍'} ${i + 1}`;
      c.title = `${fmt(blur.start)}–${fmt(blur.end)} sn`;
      c.onclick = () => { S.sel = blur.id; S.selText = null; seek(Math.min(Math.max(now(), blur.start), blur.end - 0.01)); renderAll(); };
      list.appendChild(c);
    });
    const blur = selBlur();
    $('.edit').style.display = blur ? '' : 'none';
    if (!blur) return;
    $('.effect').value = blur.effect; $('.shape').value = blur.shape;
    $('.strength').value = blur.strength; $('.opacity').value = Math.round(blur.opacity * 100);
    $('.feather').value = Math.round((blur.feather || 0) * 100);
    $('.angle').value = Math.round(boxAt(blur, now()).r || 0);
    $('.hint').textContent = `${fmt(blur.start)}–${fmt(blur.end)} sn · ${blur.keys.length} anahtar kare`;
  }
  function renderAll() { invalidate(); renderTimeline(); renderPanel(); }
  function seek(t) { video.currentTime = Math.max(0, Math.min(t, dur() - 0.001)); invalidate(); }

  // canlı takip: oynarken her 0,1 sn'de anahtar kare; geçilen aralıktaki eski anahtarlar silinir
  function recordStep(force) {
    if (!S.drag || S.drag.kind !== 'blur' || !S.drag.live || !S.rec) return;
    const blur = S.blurs.find((b) => b.id === S.drag.id); if (!blur) return;
    const t = now();
    if (!force && S.rec.last >= 0 && t - S.rec.last < 0.1) return;
    if (S.rec.last >= 0) blur.keys = blur.keys.filter((k) => k.t <= S.rec.last + 1e-6 || k.t > t + tol());
    setKey(blur, t, S.drag.box, tol()); S.rec.last = t;
  }

  const loop = () => {
    if (!video.paused) { recordStep(false); dirty = true; }
    if (dirty) { dirty = false; draw(); }
    S.raf = requestAnimationFrame(loop);
  };
  S.start = () => {
    if (!S.raf) S.raf = requestAnimationFrame(loop);
    if (!S.observing) { S.observer.observe(wrap); S.observing = true; }
  };
  S.observer = new ResizeObserver(invalidate);
  for (const e of ['loadeddata', 'seeked', 'pause', 'play', 'timeupdate']) video.addEventListener(e, () => { invalidate(); if (e === 'pause' || e === 'seeked') renderPanel(); });

  $('.play').onclick = () => { if (video.paused) video.play(); else video.pause(); };
  $('.speed').onchange = (e) => { video.playbackRate = parseFloat(e.target.value); };
  $('.back').onclick = () => seek(now() - 1 / D().fps);
  $('.fwd').onclick = () => seek(now() + 1 / D().fps);
  const timeline = $('.timeline');
  const seekEvt = (e) => { const r = timeline.getBoundingClientRect(); seek(((e.clientX - r.left) / r.width) * dur()); };
  timeline.addEventListener('pointerdown', (e) => {
    seekEvt(e); timeline.setPointerCapture(e.pointerId);
    timeline.onpointermove = seekEvt; timeline.onpointerup = () => { timeline.onpointermove = null; renderPanel(); };
  });

  const addBlur = (effect) => {
    const t = r3(now()), id = 'b' + Date.now().toString(36);
    S.blurs.push({ id, effect, shape: effect === 'mozaik' ? 'dikdortgen' : 'yuvarlak', strength: effect === 'mozaik' ? 4 : 6, opacity: 1,
                   feather: 0.3, start: t, end: Math.min(dur(), r3(t + 3)), keys: [{ t, x: 0.35, y: 0.44, w: 0.3, h: 0.12, r: 0 }] });
    S.sel = id; S.selText = null; renderAll(); send();
  };
  $('.add-blur').onclick = () => addBlur('blur');
  $('.add-mosaic').onclick = () => addBlur('mozaik');
  const edit = (fn, immediate) => { const b = selBlur(); if (!b) return; fn(b); renderAll(); if (immediate) send(); else sendSoon(); };
  $('.effect').onchange = (e) => edit((b) => { b.effect = e.target.value; }, true);
  $('.shape').onchange = (e) => edit((b) => { b.shape = e.target.value; }, true);
  $('.strength').oninput = (e) => edit((b) => { b.strength = parseInt(e.target.value, 10); });
  $('.opacity').oninput = (e) => edit((b) => { b.opacity = parseInt(e.target.value, 10) / 100; });
  $('.feather').oninput = (e) => edit((b) => { b.feather = parseInt(e.target.value, 10) / 100; });
  $('.angle').oninput = (e) => edit((b) => { const box = boxAt(b, now()); box.r = parseInt(e.target.value, 10); setKey(b, now(), box, tol()); });
  $('.square').onclick = () => edit((b) => { const box = boxAt(b, now()); const s = D().slot; box.h = box.w * s.w / s.h; setKey(b, now(), box, tol()); }, true);
  $('.set-start').onclick = () => edit((b) => { if (now() < b.end) b.start = r3(now()); }, true);
  $('.set-end').onclick = () => edit((b) => { if (now() > b.start) b.end = r3(now()); }, true);
  $('.prev-key').onclick = () => { const b = selBlur(); if (!b) return; const k = [...b.keys].reverse().find((k) => k.t < now() - tol()); seek(k ? k.t : b.start); };
  $('.next-key').onclick = () => { const b = selBlur(); if (!b) return; const k = b.keys.find((k) => k.t > now() + tol()); seek(k ? k.t : b.end - 0.01); };
  $('.del-key').onclick = () => edit((b) => { if (b.keys.length < 2) return; const i = b.keys.findIndex((k) => Math.abs(k.t - now()) <= tol()); if (i >= 0) b.keys.splice(i, 1); }, true);
  $('.del-blur').onclick = () => {
    const i = S.blurs.findIndex((b) => b.id === S.sel); if (i < 0) return;
    S.blurs.splice(i, 1); S.sel = S.blurs.length ? S.blurs[Math.max(0, i - 1)].id : null; renderAll(); send();
  };

  // --- tuval etkileşimi: blur taşı/boyutlandır/döndür, yazı taşı, canlı takip
  const toCanvas = (e) => { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height]; };
  const local = (b, p) => {  // kutu merkezine göre, dönüşü geri alınmış koordinat
    const c = blurCenter(b), a = -(b.r || 0) * Math.PI / 180, dx = p[0] - c[0], dy = p[1] - c[1];
    return [dx * Math.cos(a) - dy * Math.sin(a), dx * Math.sin(a) + dy * Math.cos(a)];
  };
  function hitBlur(p, t) {
    const s = D().slot, blur = selBlur();
    if (blur) {
      const b = boxAt(blur, t), [lx, ly] = local(b, p), w = b.w * s.w, h = b.h * s.h;
      if (Math.hypot(lx - w / 2, ly - h / 2) < 40) return { blur, mode: 'resize' };
      if (Math.hypot(lx, ly + h / 2 + 62) < 40) return { blur, mode: 'rotate' };
    }
    for (const b of [...S.blurs].reverse()) {
      if (!(t >= b.start && t < b.end) && b.id !== S.sel) continue;
      const box = boxAt(b, t), [lx, ly] = local(box, p);
      if (Math.abs(lx) <= box.w * s.w / 2 + 10 && Math.abs(ly) <= box.h * s.h / 2 + 10) return { blur: b, mode: 'move' };
    }
    return null;
  }
  function hitText(p, t) {
    for (const b of [...D().blocks.texts].reverse()) {
      if (t < b.start || t >= b.end) continue;
      if (p[0] >= b.bbox[0] - 10 && p[0] <= b.bbox[2] + 10 && p[1] >= b.bbox[1] - 10 && p[1] <= b.bbox[3] + 10) return b;
    }
    return null;
  }
  wrap.addEventListener('pointerdown', (e) => {
    const p = toCanvas(e), t = now(), live = $('.track').checked;
    const blurHit = hitBlur(p, t), textHit = blurHit ? null : hitText(p, t);
    if (!blurHit && !textHit && !(live && selBlur())) { const had = S.selText; S.sel = null; S.selText = null; renderAll(); if (had) send(); return; }
    e.preventDefault(); wrap.setPointerCapture(e.pointerId);
    if (textHit) { S.selText = textHit.id; S.sel = null; S.drag = { kind: 'text', id: textHit.id, start: p, dx: 0, dy: 0 }; renderAll(); return; }
    const blur = blurHit ? blurHit.blur : selBlur();
    S.sel = blur.id; S.selText = null;
    const box = boxAt(blur, t);
    S.drag = { kind: 'blur', id: blur.id, mode: blurHit ? blurHit.mode : 'move', start: p, from: { ...box }, box: { ...box }, live };
    if (live) {
      const s = D().slot;
      S.drag.box.x = (p[0] - s.x) / s.w - box.w / 2; S.drag.box.y = (p[1] - s.y) / s.h - box.h / 2;
      S.rec = { last: -1 };
      if (t < blur.start) blur.start = r3(t);
      const speed = parseFloat($('.speed').value);
      video.playbackRate = speed < 1 ? speed : 0.5; video.play();
    }
    renderAll();
  });
  wrap.addEventListener('pointermove', (e) => {
    if (!S.drag) return;
    const p = toCanvas(e), d = S.drag, s = D().slot;
    if (d.kind === 'text') { d.dx = p[0] - d.start[0]; d.dy = p[1] - d.start[1]; invalidate(); return; }
    const f = d.from;
    if (d.live) { d.box = { ...d.box, x: (p[0] - s.x) / s.w - d.box.w / 2, y: (p[1] - s.y) / s.h - d.box.h / 2 }; }
    else if (d.mode === 'resize') { const [lx, ly] = local(f, p); d.box = { ...f, w: Math.max(0.02, 2 * Math.abs(lx) / s.w), h: Math.max(0.02, 2 * Math.abs(ly) / s.h) }; d.box.x = f.x + f.w / 2 - d.box.w / 2; d.box.y = f.y + f.h / 2 - d.box.h / 2; }
    else if (d.mode === 'rotate') { const c = blurCenter(f); d.box = { ...f, r: Math.round(Math.atan2(p[1] - c[1], p[0] - c[0]) * 180 / Math.PI + 90) }; }
    else d.box = { ...f, x: f.x + (p[0] - d.start[0]) / s.w, y: f.y + (p[1] - d.start[1]) / s.h };
    invalidate();
  });
  const finish = () => {
    const d = S.drag; if (!d) return;
    if (d.kind === 'text') {
      const b = D().blocks.texts.find((x) => x.id === d.id);
      if (b && (Math.abs(d.dx) > 1 || Math.abs(d.dy) > 1)) {
        const x = clamp((b.center[0] + d.dx) / W), y = clamp((b.center[1] + d.dy) / H);
        S.textPos[d.id] = [Math.round(x * 10000) / 10000, Math.round(y * 10000) / 10000];
        // Python yeni konumla yeniden çizene kadar yerinde dursun
        b.center = [b.center[0] + d.dx, b.center[1] + d.dy];
        b.words.forEach((w) => { w.x += d.dx; w.y += d.dy; });
        b.bbox = [b.bbox[0] + d.dx, b.bbox[1] + d.dy, b.bbox[2] + d.dx, b.bbox[3] + d.dy];
      }
      S.drag = null; renderAll(); send(); return;
    }
    const blur = S.blurs.find((b) => b.id === d.id);
    if (d.live) { video.pause(); recordStep(true); video.playbackRate = parseFloat($('.speed').value); if (blur && now() > blur.end) blur.end = r3(now()); }
    else if (blur) setKey(blur, now(), d.box, tol());
    S.drag = null; S.rec = null; renderAll(); send();
  };
  wrap.addEventListener('pointerup', finish);
  wrap.addEventListener('pointercancel', finish);

  S.applyData = () => {
    const d = D();
    if (video.getAttribute('src') !== d.video) video.setAttribute('src', d.video);
    if (!S.shapesReady) {
      const add = (sel, obj) => { for (const [v, l] of Object.entries(obj)) { const o = document.createElement('option'); o.value = v; o.textContent = l; $(sel).appendChild(o); } };
      add('.shape', d.shapes); add('.effect', d.effects); S.shapesReady = true;
    }
    if (d.selected_text !== undefined && !S.drag && S.pySel !== d.selected_text) { S.pySel = d.selected_text; S.selText = d.selected_text; if (S.selText) S.sel = null; }
    renderAll();
  };
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  let S = STATE.get(parentElement);
  if (!S) {
    S = { project: null, blurs: [], sel: null, selText: null, textPos: {}, drag: null, rec: null, timer: null, version: 0, born: Date.now().toString(36) };
    STATE.set(parentElement, S);
    S.data = data; S.setStateValue = setStateValue;
    setup(parentElement, S);
  }
  S.data = data; S.setStateValue = setStateValue;
  if (S.project !== data.project) {
    S.project = data.project;
    S.blurs = JSON.parse(JSON.stringify(data.blurs || []));
    S.textPos = {}; S.sel = null; S.selText = null; S.pySel = undefined;
  }
  S.start();
  S.applyData();
  return () => { cancelAnimationFrame(S.raf); S.raf = null; S.observer.disconnect(); S.observing = false; };
}
