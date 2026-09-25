"""Uzak tarayıcının tabletteki görünümü (Streamlit components v2; JS: `viewer.js`).

İki bileşen: ortada ekran + sağda yazı paneli (dokunma → tıklama, sürükleme / tekerlek → kaydırma, yazı → klavye) ve
kenar çubuğunda gezinme, adres, sekmeler, indirilenler. Olaylar `input` durumuyla Python'a döner, `apply_events`
tarayıcıya uygular.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from .service import KEYS, VIEWPORT, RemoteBrowser

ICON = '<svg viewBox="0 0 24 24" aria-hidden="true">{}</svg>'
ICONS = {
    "back": ICON.format('<path d="M15 18l-6-6 6-6"/>'),
    "forward": ICON.format('<path d="M9 18l6-6-6-6"/>'),
    "reload": ICON.format('<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>'),
    "home": ICON.format('<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>'),
}

# Ortada ekran (4:3), sağda yazı paneli; tablet dik tutulursa panel ekranın altına iner.
SCREEN_HTML = """
<div class="rb">
  <div class="screen-wrap"><img class="screen" alt="Tarayıcı" tabindex="0" draggable="false"><span class="wait"></span>
    <div class="login"></div></div>
  <aside class="side">
    <div class="h">Yazı</div>
    <form class="typebar">
      <input class="text" type="text" autocomplete="off" placeholder="Önce ekranda kutuya dokun">
      <button type="submit" class="primary">Yaz</button>
    </form>
    <div class="keys">
      <button type="button" data-k="Enter" title="Enter">↵</button><button type="button" data-k="Backspace" title="Sil">⌫</button>
      <button type="button" data-k="Tab" title="Sonraki kutu">⇥</button>
    </div>
    <button type="button" class="pw" data-t="password" title="Bu sitenin kayıtlı kullanıcı adı ve şifresini giriş kutularına yazar">🔑 Girişi doldur</button>
  </aside>
</div>
"""

PANEL_HTML = f"""
<div class="pn">
  <div class="nav">
    <button type="button" data-t="back" title="Geri">{ICONS["back"]}</button>
    <button type="button" data-t="forward" title="İleri">{ICONS["forward"]}</button>
    <button type="button" data-t="reload" title="Yenile">{ICONS["reload"]}</button>
    <button type="button" data-t="home" title="DHA haberleri">{ICONS["home"]}</button>
  </div>
  <form class="go"><input class="url" type="text" inputmode="url" autocomplete="off" spellcheck="false"
    placeholder="Adres veya arama"><button type="submit" class="primary">Git</button></form>
  <div class="h">Sekmeler</div><div class="tabs"></div>
  <div class="h">İndirilenler</div><div class="downloads"></div>
</div>
"""

BASE_CSS = """
:host, .rb, .pn { --navy: #123249; --sky: #BEE1E8; --lime: #D0E491; --soft: #F3F7FA; --line: #DCE5EC; --ink: #1B2B3A;
  font-family: "Source Sans Pro", system-ui, sans-serif; color: var(--ink); }
button { font: inherit; border: 1px solid var(--line); background: #fff; color: var(--navy); border-radius: 10px;
  min-height: 40px; padding: 0 12px; font-size: 15px; font-weight: 600; cursor: pointer; transition: background .12s, transform .06s; }
button:active { background: #E7F1FB; transform: scale(.97); }
button.primary { background: var(--navy); border-color: var(--navy); color: #fff; }
button.primary:active { background: #0B2233; }
input { font: inherit; min-height: 40px; border: 1px solid var(--line); border-radius: 10px; padding: 0 10px; font-size: 16px;
  min-width: 0; background: #fff; color: var(--ink); outline: none; }
input:focus { border-color: var(--navy); box-shadow: 0 0 0 3px rgba(190, 225, 232, .7); }
.h { font-size: 12px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #6B7C8C; margin: 4px 2px -2px; }
"""

SCREEN_CSS = BASE_CSS + """
.rb { display: grid; grid-template-columns: minmax(0, 1fr) 156px; gap: 12px; align-items: start; }
.screen-wrap { position: relative; width: 100%; max-width: calc((100vh - 36px) * 4 / 3); justify-self: center;
  border-radius: 12px; overflow: hidden; box-shadow: 0 1px 2px rgba(18, 50, 73, .08), 0 6px 20px rgba(18, 50, 73, .10);
  background: var(--soft); }
.screen { display: block; width: 100%; aspect-ratio: var(--ar, 4 / 3); touch-action: none; user-select: none;
  -webkit-user-select: none; outline: none; will-change: transform; }
.screen-wrap:has(.screen:focus-visible) { box-shadow: 0 0 0 3px var(--sky); }
.wait { position: absolute; right: 10px; top: 10px; width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid var(--sky); border-top-color: var(--navy); animation: spin .8s linear infinite; display: none; }
.wait.on { display: block; }
@keyframes spin { to { transform: rotate(360deg); } }
.ripple { position: absolute; width: 28px; height: 28px; margin: -14px 0 0 -14px; border-radius: 50%;
  background: rgba(18, 50, 73, .28); pointer-events: none; animation: rip .45s ease-out forwards; }
@keyframes rip { to { transform: scale(1.8); opacity: 0; } }
.side { display: flex; flex-direction: column; gap: 8px; position: sticky; top: 8px; }
.typebar { display: flex; flex-direction: column; gap: 8px; }
.keys { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.keys button { padding: 0; font-size: 18px; }
/* Giriş çubuğu görüntünün üstüne biner (alt kenar): belirince görüntü kaymaz, dokunuşlar yanlış yere gitmez. */
.login:empty { display: none; }
.login { position: absolute; left: 10px; right: 10px; bottom: 10px; display: flex; gap: 8px; align-items: center;
  flex-wrap: wrap; padding: 10px 12px; border-radius: 12px; background: #FDF1DC; font-size: 15px;
  box-shadow: 0 4px 16px rgba(18, 50, 73, .25); }
.login.filled { background: #E6F4EC; }
.login span { flex: 1; min-width: 200px; }
.login button { min-height: 36px; }
@media (orientation: portrait) {
  .rb { grid-template-columns: 1fr; }
  .screen-wrap { max-width: 100%; }
  .side { position: static; display: grid; grid-template-columns: 1fr auto auto; align-items: end; }
  .side .h { display: none; }
  .typebar { flex-direction: row; }
}
"""

PANEL_CSS = BASE_CSS + """
.pn { display: flex; flex-direction: column; gap: 8px; }
.nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.nav button { padding: 0; display: grid; place-items: center; }
.nav svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
.go { display: flex; gap: 6px; }
.go input { flex: 1; width: 0; }
.go button { padding: 0 10px; }
.tabs { display: flex; flex-direction: column; gap: 4px; }
.tab { display: flex; align-items: stretch; border: 1px solid var(--line); border-radius: 10px; background: #fff; overflow: hidden; }
.tab.on { border-color: var(--navy); background: #EAF3F8; box-shadow: inset 3px 0 0 var(--navy); }
.tab button { border: 0; border-radius: 0; background: transparent; min-height: 38px; }
.tab .pick { flex: 1; min-width: 0; text-align: left; font-weight: 500; font-size: 14px; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; padding: 0 10px; }
.tab.on .pick { font-weight: 700; }
.tab .x { width: 36px; padding: 0; color: #6B7C8C; font-size: 14px; }
.downloads { display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
.dl { padding: 8px 10px; border-radius: 10px; background: var(--soft); border: 1px solid var(--line); display: flex;
  flex-direction: column; gap: 4px; }
.dl .name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dl .info { font-size: 12px; color: #6B7C8C; }
.dl.bitti { background: #EEF7F1; border-color: #CBE7D5; } .dl.hata { background: #FDECEA; border-color: #F4C7C1; }
.dl button { min-height: 34px; font-size: 13px; padding: 0 8px; }
.empty { font-size: 13px; color: #6B7C8C; padding: 2px; }
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
        elif kind in ("back", "forward", "reload"):
            browser.run(kind)
        elif kind in ("tab", "close_tab"):
            index = _number(value, 0, 50) if value is not None else None
            if kind == "tab" and index is None:
                continue
            browser.run(kind, None if index is None else int(index))
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
    """Ekran + yazı paneli (ana alan)."""
    mount = _component("axion_uzak_tarayici_ekran", html=SCREEN_HTML, css=SCREEN_CSS, js=JS)
    result = mount(data={**data, "viewport": list(VIEWPORT)}, key=key, default={"input": None}, on_input_change=lambda: None)
    return result.input


def panel_view(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Gezinme, adres, sekmeler, indirilenler (kenar çubuğu)."""
    mount = _component("axion_uzak_tarayici_panel", html=PANEL_HTML, css=PANEL_CSS, js=JS)
    result = mount(data=data, key=key, default={"input": None}, on_input_change=lambda: None)
    return result.input
