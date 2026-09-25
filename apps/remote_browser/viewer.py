"""Uzak tarayıcının tabletteki görünümü (Streamlit components v2; JS: `viewer.js`).

Ekran görüntüsünü gösterir; dokunma → tıklama, parmakla sürükleme / fare tekerleği → kaydırma, yazı kutusu → klavye.
Olaylar `input` durumuyla Python'a döner, `apply_events` tarayıcıya uygular.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from .service import KEYS, VIEWPORT, RemoteBrowser

HTML = """
<div class="rb">
  <div class="bar">
    <button data-t="back" title="Geri">◀</button><button data-t="forward" title="İleri">▶</button>
    <button data-t="reload" title="Yenile">⟳</button><button data-t="home" title="Ana sayfa">⌂</button>
    <form class="go"><input class="url" type="text" inputmode="url" autocomplete="off" spellcheck="false"
      placeholder="Adres veya arama"><button type="submit">Git</button></form>
    <span class="tabs"></span>
  </div>
  <div class="screen-wrap"><img class="screen" alt="Tarayıcı" tabindex="0" draggable="false"><span class="wait"></span>
    <div class="login"></div></div>
  <form class="typebar">
    <input class="text" type="text" autocomplete="off" placeholder="Seçili kutuya yazılacak metin (önce ekranda kutuya dokun)">
    <button type="submit">Yaz</button><button type="button" data-k="Enter" title="Enter">↵</button>
    <button type="button" data-k="Backspace" title="Sil">⌫</button><button type="button" data-k="Tab" title="Sonraki kutu">⇥</button>
    <button type="button" class="pw" data-t="password" title="Bu sitenin kayıtlı kullanıcı adı ve şifresini giriş kutularına yazar">🔑 Girişi doldur</button>
  </form>
  <div class="downloads"></div>
</div>
"""

CSS = """
.rb { font-family: "Source Sans Pro", system-ui, sans-serif; color: #1b2b3a; display: flex; flex-direction: column; gap: 8px; }
.rb button { border: 1px solid #d5dee6; background: #fff; border-radius: 8px; min-width: 40px; min-height: 40px;
  padding: 0 10px; font-size: 16px; cursor: pointer; color: #123249; }
.rb button:active { background: #e7f1fb; }
.bar, .typebar { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.go { display: flex; gap: 6px; flex: 1; min-width: 220px; }
.rb input { flex: 1; min-height: 40px; border: 1px solid #d5dee6; border-radius: 8px; padding: 0 10px; font-size: 16px; min-width: 0; }
.tabs { font-size: 13px; color: #6b7c8c; white-space: nowrap; }
.tabs button { min-height: 32px; font-size: 13px; margin-left: 4px; }
.screen-wrap { position: relative; width: 100%; max-width: calc((100vh - 230px) * 1.6); min-width: 280px; }
.screen { display: block; width: 100%; aspect-ratio: 1024 / 640; background: #f3f7fa; border: 1px solid #d5dee6;
  border-radius: 8px; touch-action: none; user-select: none; -webkit-user-select: none; outline: none; }
.screen:focus-visible { border-color: #123249; }
.wait { position: absolute; right: 10px; top: 10px; width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid #bee1e8; border-top-color: #123249; animation: spin .8s linear infinite; display: none; }
.wait.on { display: block; }
@keyframes spin { to { transform: rotate(360deg); } }
.ripple { position: absolute; width: 26px; height: 26px; margin: -13px 0 0 -13px; border-radius: 50%;
  background: rgba(18, 50, 73, .25); pointer-events: none; animation: rip .45s ease-out forwards; }
@keyframes rip { to { transform: scale(1.8); opacity: 0; } }
.downloads { display: flex; flex-direction: column; gap: 4px; font-size: 14px; }
.downloads div { padding: 6px 10px; border-radius: 8px; background: #f3f7fa; display: flex; align-items: center; gap: 8px; }
.downloads div span { flex: 1; }
.downloads button, .login button { min-height: 34px; font-size: 14px; }
.login:empty { display: none; }
/* Görüntünün üstüne biner (alt kenar): belirince tarayıcı görüntüsü kaymaz, dokunuşlar yanlış yere gitmez. */
.login { position: absolute; left: 8px; right: 8px; bottom: 8px; display: flex; gap: 8px; align-items: center;
  flex-wrap: wrap; padding: 8px 12px; border-radius: 8px; background: #fdf1dc; font-size: 15px;
  box-shadow: 0 2px 10px rgba(18, 50, 73, .25); }
.login.filled { background: #e6f4ec; }
.login span { flex: 1; min-width: 200px; }
.downloads .bitti { background: #e6f4ec; } .downloads .hata { background: #fdecea; }
"""

JS = Path(__file__).with_name("viewer.js").read_text(encoding="utf-8")
_MOUNTS: dict[str, Any] = {}
MAX_EVENTS = 60


def _component(name: str, **parts: str):
    """Bileşen bu Streamlit çalışma ortamında kayıtlı değilse kaydeder (testlerde her uygulama yeni ortamdır)."""
    from streamlit.components.v2 import get_bidi_component_manager

    if name not in _MOUNTS or get_bidi_component_manager().get(name) is None:
        _MOUNTS[name] = st.components.v2.component(name, **parts)
    return _MOUNTS[name]


def _number(value: Any, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return min(high, max(low, number)) if number == number else None


def apply_events(browser: RemoteBrowser, events: Any, password: str | None, home: str) -> int:
    """Tabletten gelen olayları doğrulayıp tarayıcıya uygular; uygulananların sayısını döndürür."""
    applied = 0
    width, height = VIEWPORT
    for event in (events if isinstance(events, list) else [])[:MAX_EVENTS]:
        if not isinstance(event, dict):
            continue
        kind, value = event.get("t"), event.get("v")
        if kind in ("click", "wheel") and isinstance(value, list) and len(value) >= 2:
            x, y = _number(value[0], 0, width - 1), _number(value[1], 0, height - 1)
            if x is None or y is None:
                continue
            if kind == "click":
                browser.run("click", (x, y))
            else:
                delta = _number(value[2] if len(value) > 2 else 0, -6000, 6000)
                if not delta:
                    continue
                browser.run("wheel", (x, y, delta))
        elif kind == "goto" and isinstance(value, str) and value.strip():
            browser.run("goto", value[:2000])
        elif kind == "home":
            browser.run("goto", home)
        elif kind == "type" and isinstance(value, str) and value:
            browser.run("type", value[:2000])
        elif kind == "key" and value in KEYS:
            browser.run("key", value)
        elif kind in ("back", "forward", "reload", "close_tab"):
            browser.run(kind)
        elif kind == "password":
            # Kayıtlı giriş varsa kutular doldurulur; yoksa (eski ayar) DHA_SIFRE seçili kutuya yazılır.
            if not browser.fill_login() and password:
                browser.run("type", password)
        elif kind in ("save_login", "dismiss_login"):
            browser.answer_login_offer(kind == "save_login")
        else:
            continue
        applied += 1
    return applied


def browser_view(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    mount = _component("axion_uzak_tarayici", html=HTML, css=CSS, js=JS)
    result = mount(data={**data, "viewport": list(VIEWPORT)}, key=key, default={"input": None}, on_input_change=lambda: None)
    return result.input
