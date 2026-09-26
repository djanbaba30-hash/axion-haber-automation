// Uzak tarayıcının tabletteki görünümü. Python ekran görüntüsünü (JPEG) yollar; bu dosya dokunuşları tarayıcının
// koordinatlarına çevirip olay olarak geri yollar (`input`). Dokun = tıkla, sürükle / tekerlek = kaydır.
// İki parça: "screen" (ortada ekran + sağda yazı ve indirilenler) ve "panel" (kenar çubuğunda gezinme, adres, sekmeler).
// Ekran önce doğrudan akış kanalını (WebSocket, stream.py) dener: kareler anında gelir, dokunuşlar anında gider.
// Kanal yoksa kareler ve olaylar Streamlit üzerinden gider (daha yavaş ama her zaman çalışır).

const STATE = new WeakMap();
const KEYS = ['Enter', 'Backspace', 'Tab', 'Escape', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Delete', 'Home', 'End', 'PageUp', 'PageDown'];
const esc = (x) => String(x ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function channel(S) {
  S.queue = []; S.seq = 0; S.born = Date.now().toString(36);
  S.send = (event) => {
    S.queue.push(event);
    S.setStateValue('input', { seq: `${S.born}-${++S.seq}`, events: S.queue.splice(0) });
    if (S.onSend) S.onSend();
  };
  S.pending = () => S.seq && S.data.applied !== `${S.born}-${S.seq}`;
}

// Düğmeler: data-t = olay türü, data-v = değer (sekme sırası, dosya adı), data-k = tuş.
function buttons(box, S) {
  box.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-t], button[data-k]'); if (!b) return;
    e.preventDefault();
    if (b.dataset.k) S.send({ t: 'key', v: b.dataset.k });
    else S.send(b.dataset.v !== undefined ? { t: b.dataset.t, v: b.dataset.v } : { t: b.dataset.t });
  });
}

const FAST = new Set(['click', 'wheel', 'type', 'key']);

function downloadRows(list) {
  const rows = (list || []).map((x) => {
    const icon = x.state === 'bitti' ? '✅' : x.state === 'hata' ? '⚠️' : '⏳';
    const info = x.state === 'bitti' ? `${x.mb} MB · bilgisayarda` : x.state === 'hata' ? `inmedi: ${esc(x.error || '')}` : `iniyor… ${x.seconds} sn`;
    const use = x.state !== 'bitti' ? ''
      : x.video ? `<button type="button" class="primary" data-t="use_download" data-v="${esc(x.name)}" title="Video Stüdyosu'nda seçili açılır">🎬 Videoda kullan</button>`
      : x.text ? `<button type="button" class="primary" data-t="use_text" data-v="${esc(x.name)}" title="Haber Stüdyosu'nda ham haber olarak açılır">📰 Habere aktar</button>` : '';
    return `<div class="dl ${x.state}"><div class="name">${icon} <b title="${esc(x.name)}">${esc(x.name)}</b></div><div class="info">${info}</div>${use}</div>`;
  }).join('');
  return rows || '<div class="empty">Henüz indirme yok. İndirilenler bilgisayarın <b>İndirilenler</b> klasörüne iner.</div>';
}

function setupScreen(root, S) {
  const $ = (s) => root.querySelector(s);
  const img = $('.screen'), wrap = $('.screen-wrap'), text = $('.text'), wait = $('.wait');
  channel(S);
  S.wheel = null;
  S.onSend = () => wait.classList.add('on');
  // Doğrudan akış: gelen her kare gösterilince "ack" (en fazla 2 kare yolda; yavaş internette gecikme birikmez).
  const show = (url, done) => {
    const next = new Image();
    next.onload = () => {
      img.src = url; done();
      if (!press) { S.shift = 0; img.style.transform = ''; }
    };
    next.onerror = done;
    next.src = url;
  };
  const connect = () => {
    const info = S.data.stream;
    if (!info || S.ws || S.gone) return;
    let ws;
    try { ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${info.path}?t=${encodeURIComponent(info.token)}`); }
    catch (e) { return; }
    ws.binaryType = 'blob'; S.ws = ws;
    ws.onmessage = (m) => {
      if (!img.isConnected) { S.gone = true; ws.close(); return; }  // sayfadan çıkıldı: akış dursun
      S.live = true;
      const url = URL.createObjectURL(m.data);
      show(url, () => { if (S.blob) URL.revokeObjectURL(S.blob); S.blob = url; if (ws.readyState === 1) ws.send('{"t":"ack"}'); });
    };
    ws.onclose = () => { S.ws = null; S.live = false; if (!S.gone) setTimeout(connect, 3000); };
  };
  S.connect = connect;
  const streamlitSend = S.send;
  S.send = (event) => {  // dokunuş/kaydırma/yazı akıştan; giriş kaydı, indirme gibi uygulama işleri Streamlit'ten
    if (S.live && S.ws && S.ws.readyState === 1 && FAST.has(event.t)) S.ws.send(JSON.stringify({ events: [event] }));
    else streamlitSend(event);
  };
  const toView = (e) => {
    const r = img.getBoundingClientRect(), [w, h] = S.data.viewport;
    return [Math.round((e.clientX - r.left) * w / r.width), Math.round((e.clientY - r.top) * h / r.height)];
  };
  const ripple = (e) => {
    const r = wrap.getBoundingClientRect(), dot = document.createElement('span');
    dot.className = 'ripple'; dot.style.left = `${e.clientX - r.left}px`; dot.style.top = `${e.clientY - r.top}px`;
    wrap.appendChild(dot); setTimeout(() => dot.remove(), 500);
  };
  // Kaydırma: parmak hareketi birikir; akış kanalında ~30 kez/sn, Streamlit yolunda ~10 kez/sn gönderilir. Görüntü o sırada parmakla birlikte kayar
  // (yeni kare gelene kadar): uzaktaki tarayıcıyı beklemeden anında tepki hissi.
  const nudge = (px) => { S.shift = Math.max(-240, Math.min(240, (S.shift || 0) + px)); img.style.transform = `translateY(${S.shift}px)`; };
  // Sayfanın başı/sonu gibi kaymayan yerde yeni kare gelmez: kaydırılan görüntü (üstte/altta boşluk) geri yerine oturur.
  const settle = () => {
    clearTimeout(S.settle);
    S.settle = setTimeout(() => {
      if (press || !S.shift) return;
      S.shift = 0; img.style.transition = 'transform .15s ease-out'; img.style.transform = '';
      setTimeout(() => { img.style.transition = ''; }, 200);
    }, 800);
  };
  const addWheel = (point, delta) => {
    if (!S.wheel) {
      S.wheel = { point, delta: 0 };
      setTimeout(() => { const w = S.wheel; S.wheel = null; if (w && Math.abs(w.delta) >= 1) S.send({ t: 'wheel', v: [...w.point, Math.round(w.delta)] }); }, S.live ? 30 : 90);
    }
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
      nudge(e.clientY - press.lastY);
      press.lastY = e.clientY;
    }
  });
  const release = (e) => {
    if (press && !press.moved && e.type === 'pointerup') { ripple(e); S.send({ t: 'click', v: press.point }); }
    press = null;
    settle();
  };
  img.addEventListener('pointerup', release);
  img.addEventListener('pointercancel', release);
  img.addEventListener('wheel', (e) => {
    e.preventDefault(); addWheel(toView(e), e.deltaY);
    nudge(-e.deltaY * img.getBoundingClientRect().height / S.data.viewport[1]);
    settle();
  }, { passive: false });
  img.addEventListener('contextmenu', (e) => e.preventDefault());
  // Fiziksel klavye: ekran seçiliyken yazılanlar doğrudan tarayıcıya gider.
  img.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key.length === 1) { e.preventDefault(); S.send({ t: 'type', v: e.key }); }
    else if (KEYS.includes(e.key)) { e.preventDefault(); S.send({ t: 'key', v: e.key }); }
  });
  $('.typebar').addEventListener('submit', (e) => { e.preventDefault(); if (text.value) { S.send({ t: 'type', v: text.value }); text.value = ''; } });
  buttons($('.side'), S);
  buttons($('.login'), S);
  const downloads = $('.downloads');

  S.apply = () => {
    const d = S.data;
    wrap.style.setProperty('--ar', `${d.viewport[0]} / ${d.viewport[1]}`);
    if (!S.ws) S.connect();
    if (!S.live && d.img && d.img !== S.shown) {  // akış yoksa: Streamlit'in yolladığı kare (önce yüklenir, titreme olmasın)
      const url = d.img;
      show(url, () => { S.shown = url; });
    }
    const rows = downloadRows(d.downloads);
    if (downloads.dataset.html !== rows) { downloads.innerHTML = rows; downloads.dataset.html = rows; }
    $('.pw').style.display = d.password ? '' : 'none';
    const login = d.login || {}, box = $('.login');
    const loginHtml = login.offer
      ? `<span>🔑 <b>${esc(login.offer.site)}</b> girişi kaydedilsin mi? (${esc(login.offer.username) || 'kullanıcı adı yok'}) Sonraki girişlerde kutular kendiliğinden dolar.</span>
         <button type="button" class="primary" data-t="save_login">Kaydet</button><button type="button" data-t="dismiss_login">Hayır</button>`
      : login.filled ? `<span>🔑 Giriş bilgileri dolduruldu. Sayfadaki <b>Giriş</b> düğmesine dokun.</span>` : '';
    if (box.dataset.html !== loginHtml) { box.innerHTML = loginHtml; box.dataset.html = loginHtml; }
    box.classList.toggle('filled', !login.offer && !!login.filled);
    if (!S.pending()) wait.classList.remove('on');
  };
}

function setupPanel(root, S) {
  const $ = (s) => root.querySelector(s);
  const url = $('.url');
  channel(S);
  buttons($('.nav'), S);
  buttons($('.tabs'), S);
  $('.go').addEventListener('submit', (e) => { e.preventDefault(); if (url.value.trim()) { S.send({ t: 'goto', v: url.value.trim() }); url.blur(); } });
  const html = (box, markup) => { if (box.dataset.html !== markup) { box.innerHTML = markup; box.dataset.html = markup; } };

  S.apply = () => {
    const d = S.data;
    if (document.activeElement !== url && S.root.getRootNode().activeElement !== url) url.value = d.url || '';
    const tabs = d.tabs || [];
    html($('.tabs'), tabs.map((tab, i) => `<div class="tab${tab.active ? ' on' : ''}">
        <button type="button" class="pick" data-t="tab" data-v="${i}" title="${esc(tab.url)}">${esc(tab.title || tab.url || 'Yeni sekme')}</button>
        ${tabs.length > 1 ? `<button type="button" class="x" data-t="close_tab" data-v="${i}" title="Sekmeyi kapat">✕</button>` : ''}</div>`).join(''));
  };
}

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  let S = STATE.get(parentElement);
  if (!S) {
    S = { root: parentElement, data, setStateValue };
    STATE.set(parentElement, S);
    (parentElement.querySelector('.screen') ? setupScreen : setupPanel)(parentElement, S);
  }
  S.data = data; S.setStateValue = setStateValue;
  S.apply();
}
