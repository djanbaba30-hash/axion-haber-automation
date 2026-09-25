// Uzak tarayıcının tabletteki görünümü. Python ekran görüntüsünü (JPEG) yollar; bu dosya dokunuşları tarayıcının
// koordinatlarına çevirip olay olarak geri yollar (`input`). Dokun = tıkla, sürükle / tekerlek = kaydır.

const STATE = new WeakMap();

function setup(root, S) {
  const $ = (s) => root.querySelector(s);
  const img = $('.screen'), wrap = $('.screen-wrap'), url = $('.url'), text = $('.text'), wait = $('.wait');
  S.queue = []; S.seq = 0; S.born = Date.now().toString(36); S.wheel = null;

  const flush = () => {
    if (!S.queue.length) return;
    S.setStateValue('input', { seq: `${S.born}-${++S.seq}`, events: S.queue.splice(0) });
    wait.classList.add('on');
  };
  const send = (event) => { S.queue.push(event); flush(); };
  const toView = (e) => {
    const r = img.getBoundingClientRect(), [w, h] = S.data.viewport;
    return [Math.round((e.clientX - r.left) * w / r.width), Math.round((e.clientY - r.top) * h / r.height)];
  };
  const ripple = (e) => {
    const r = wrap.getBoundingClientRect(), dot = document.createElement('span');
    dot.className = 'ripple'; dot.style.left = `${e.clientX - r.left}px`; dot.style.top = `${e.clientY - r.top}px`;
    wrap.appendChild(dot); setTimeout(() => dot.remove(), 500);
  };
  // Kaydırma: parmak hareketi birikir, en fazla ~7 kez/sn gönderilir (yavaş internette olay yağmuru olmasın).
  const addWheel = (point, delta) => {
    if (!S.wheel) { S.wheel = { point, delta: 0 }; setTimeout(() => { const w = S.wheel; S.wheel = null; if (w && Math.abs(w.delta) >= 1) send({ t: 'wheel', v: [...w.point, Math.round(w.delta)] }); }, 140); }
    S.wheel.delta += delta;
  };

  let press = null;
  img.addEventListener('pointerdown', (e) => {
    img.focus({ preventScroll: true });
    press = { x: e.clientX, y: e.clientY, lastY: e.clientY, moved: false, point: toView(e) };
    img.setPointerCapture(e.pointerId);
  });
  img.addEventListener('pointermove', (e) => {
    if (!press) return;
    if (!press.moved && Math.hypot(e.clientX - press.x, e.clientY - press.y) > 8) press.moved = true;
    if (press.moved) {
      const scale = S.data.viewport[1] / img.getBoundingClientRect().height;
      addWheel(press.point, (press.lastY - e.clientY) * scale);
      press.lastY = e.clientY;
    }
  });
  const release = (e) => {
    if (press && !press.moved && e.type === 'pointerup') { ripple(e); send({ t: 'click', v: press.point }); }
    press = null;
  };
  img.addEventListener('pointerup', release);
  img.addEventListener('pointercancel', release);
  img.addEventListener('wheel', (e) => { e.preventDefault(); addWheel(toView(e), e.deltaY); }, { passive: false });
  img.addEventListener('contextmenu', (e) => e.preventDefault());
  // Fiziksel klavye: ekran seçiliyken yazılanlar doğrudan tarayıcıya gider.
  const KEYS = ['Enter', 'Backspace', 'Tab', 'Escape', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Delete', 'Home', 'End', 'PageUp', 'PageDown'];
  img.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key.length === 1) { e.preventDefault(); send({ t: 'type', v: e.key }); }
    else if (KEYS.includes(e.key)) { e.preventDefault(); send({ t: 'key', v: e.key }); }
  });

  root.querySelector('.bar').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-t]'); if (b) send({ t: b.dataset.t });
  });
  $('.go').addEventListener('submit', (e) => { e.preventDefault(); if (url.value.trim()) { send({ t: 'goto', v: url.value.trim() }); url.blur(); } });
  $('.typebar').addEventListener('submit', (e) => { e.preventDefault(); if (text.value) { send({ t: 'type', v: text.value }); text.value = ''; } });
  $('.typebar').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-k], button[data-t]'); if (!b) return;
    send(b.dataset.k ? { t: 'key', v: b.dataset.k } : { t: b.dataset.t });
  });
  root.querySelector('.tabs').addEventListener('click', (e) => { if (e.target.closest('button')) send({ t: 'close_tab' }); });
  // Giriş kaydı / indirilen videoyu kullanma düğmeleri (içerikleri her güncellemede yeniden çizilir).
  for (const box of [$('.login'), $('.downloads')]) {
    box.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-t]'); if (b) send(b.dataset.v ? { t: b.dataset.t, v: b.dataset.v } : { t: b.dataset.t });
    });
  }
  const esc = (x) => String(x ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  S.apply = () => {
    const d = S.data;
    if (d.img && d.img !== S.shown) {  // yeni görüntü önce yüklenir: titreme olmasın
      const next = new Image();
      next.onload = () => { if (S.data.img === d.img) { img.src = d.img; S.shown = d.img; } };
      next.src = d.img;
    }
    if (document.activeElement !== url && S.root.getRootNode().activeElement !== url) url.value = d.url || '';
    const tabs = $('.tabs');
    tabs.innerHTML = d.tabs > 1 ? `${d.tabs} sekme <button type="button" title="Bu sekmeyi kapat">✕</button>` : '';
    $('.pw').style.display = d.password ? '' : 'none';
    const login = d.login || {}, box = $('.login');
    const loginHtml = login.offer
      ? `<span>🔑 <b>${esc(login.offer.site)}</b> girişi kaydedilsin mi? (${esc(login.offer.username) || 'kullanıcı adı yok'}) Sonraki girişlerde kutular kendiliğinden dolar.</span>
         <button type="button" data-t="save_login">Kaydet</button><button type="button" data-t="dismiss_login">Hayır</button>`
      : login.filled ? `<span>🔑 Giriş bilgileri dolduruldu. Sayfadaki <b>Giriş</b> düğmesine dokun.</span>` : '';
    if (box.dataset.html !== loginHtml) { box.innerHTML = loginHtml; box.dataset.html = loginHtml; }
    box.classList.toggle('filled', !login.offer && !!login.filled);
    const rows = (d.downloads || []).map((x) => {
      const label = x.state === 'bitti' ? `✅ ${x.name} — ${x.mb} MB, bilgisayara indi`
        : x.state === 'hata' ? `⚠️ ${x.name} — inmedi: ${x.error || ''}` : `⏳ ${x.name} — iniyor… ${x.seconds} sn`;
      const use = x.state === 'bitti' && x.video ? `<button type="button" data-t="use_download" data-v="${esc(x.name)}">🎬 Video Stüdyosu'nda kullan</button>` : '';
      return `<div class="${x.state}"><span>${esc(label)}</span>${use}</div>`;
    }).join('');
    const dl = $('.downloads');
    if (dl.dataset.html !== rows) { dl.innerHTML = rows; dl.dataset.html = rows; }
    if (d.applied === `${S.born}-${S.seq}` || !S.seq) wait.classList.remove('on');
  };
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  let S = STATE.get(parentElement);
  if (!S) {
    S = { root: parentElement };
    STATE.set(parentElement, S);
    S.data = data; S.setStateValue = setStateValue;
    setup(parentElement, S);
  }
  S.data = data; S.setStateValue = setStateValue;
  S.apply();
}
