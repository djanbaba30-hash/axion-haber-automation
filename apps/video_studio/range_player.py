"""Kesit oynatıcısı (v4.0, editör: "kesit seçtiğimde ne olursa olsun videoda yalnız o kesit oynasın").

Yalnız seçili aralık oynar: her oynatma kesitin başından başlar (durdurunca aralık içinde elle sarılan yerden sürer),
sonunda durup başa döner, aralığın dışına sarılamaz. Aralık (kaydırıcı ya da cümleye dokunma) değişince video durur ve
yeni aralığın başına gider. `st.video(start_time, end_time)` bunu yapmıyordu (ilk oynatmadan sonra devam ediyor, yeni
aralığa gitmiyordu). Streamlit components v2; video Streamlit'in medya sunucusundan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from apps.axion_local.media import media_url

HTML = '<div class="kp"><video class="v" controls playsinline preload="auto"></video><div class="bar"></div></div>'

CSS = """
.kp { display: flex; flex-direction: column; gap: 6px; font-family: "Source Sans Pro", system-ui, sans-serif; }
.v { width: 100%; max-height: 62vh; background: #000; border-radius: 10px; }
.bar { font-size: 14px; color: #3B4B5A; }
"""

JS = """
const STATE = new WeakMap();
const mmss = (t) => `${String(Math.floor(t / 60)).padStart(2, '0')}:${(t % 60).toFixed(1).padStart(4, '0')}`;
export default function ({ data, parentElement }) {
  let S = STATE.get(parentElement);
  const v = parentElement.querySelector('.v'), bar = parentElement.querySelector('.bar');
  if (!S) {
    S = { manual: false }; STATE.set(parentElement, S);
    const inside = () => v.currentTime >= S.start - 0.05 && v.currentTime < S.end - 0.05;
    v.addEventListener('play', () => {  // her oynatma kesitin başından (durdurup aralık içinde sarıldıysa oradan)
      if (!S.manual || !inside()) v.currentTime = S.start;
      S.manual = false; watch();
    });
    v.addEventListener('seeking', () => {
      if (v.currentTime < S.start - 0.05) v.currentTime = S.start;
      else if (v.currentTime > S.end) v.currentTime = Math.max(S.start, S.end - 0.1);
      if (v.paused) S.manual = true;
    });
    const watch = () => {
      if (v.currentTime >= S.end - 0.03) { v.pause(); v.currentTime = S.start; S.manual = false; return; }
      if (!v.paused) requestAnimationFrame(watch);
    };
  }
  const changed = S.src !== data.src || S.start !== data.start || S.end !== data.end;
  if (S.src !== data.src) { S.src = data.src; v.src = data.src; }
  S.start = data.start; S.end = data.end;
  bar.textContent = `Kesit: ${mmss(data.start)} – ${mmss(data.end)} (${(data.end - data.start).toFixed(1)} sn) · yalnız bu aralık oynar`;
  if (changed) {  // yeni aralık: dur, başına git
    v.pause(); S.manual = false;
    const go = () => { v.currentTime = S.start; };
    if (v.readyState >= 1) go(); else v.addEventListener('loadedmetadata', go, { once: true });
  }
}
"""

_MOUNTS: dict[str, Any] = {}


def range_player(video: Path, start: float, end: float, key: str) -> None:
    from streamlit.components.v2 import get_bidi_component_manager

    name = "axion_kesit_oynatici"
    if name not in _MOUNTS or get_bidi_component_manager().get(name) is None:
        _MOUNTS[name] = st.components.v2.component(name, html=HTML, css=CSS, js=JS)
    _MOUNTS[name](data={"src": media_url(video, "video/mp4", "kesit"), "start": round(start, 2),
                        "end": round(max(end, start + 0.1), 2)}, key=key)
