"""Seslendirmeyi okuyarak dinleme (kalite kontrolü): çalan kelime vurgulanır, kelimeye dokununca oradan çalar.

ElevenLabs'in karakter zamanları (`convert_with_timestamps`) zaten var; ek çağrı yok. Streamlit components v2.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from apps.axion_local.media import media_url

HTML = '<div class="ra"><audio class="player" controls preload="auto"></audio><p class="words"></p></div>'

CSS = """
.ra { font-family: "Source Sans Pro", system-ui, sans-serif; color: #1B2B3A; display: flex; flex-direction: column; gap: 8px; }
.player { width: 100%; height: 40px; }
.words { margin: 0; padding: 12px 14px; border: 1px solid #DCE5EC; border-radius: 10px; background: #F8FBFD;
  font-size: 17px; line-height: 1.7; }
.words span { cursor: pointer; border-radius: 4px; padding: 1px 0; transition: background .08s; }
.words span:hover { background: #E7F1FB; }
.words span.on { background: #D0E491; box-shadow: 0 0 0 2px #D0E491; }
.words span.done { color: #6B7C8C; }
"""

JS = """
const STATE = new WeakMap();
export default function ({ data, parentElement }) {
  let S = STATE.get(parentElement);
  const audio = parentElement.querySelector('.player'), box = parentElement.querySelector('.words');
  if (!S) {
    S = {}; STATE.set(parentElement, S);
    box.addEventListener('click', (e) => {
      const w = e.target.closest('span[data-i]'); if (!w) return;
      audio.currentTime = S.words[+w.dataset.i][1] + 0.001; audio.play();
    });
    const tick = () => {
      const t = audio.currentTime, spans = box.children;
      let current = -1;
      for (let i = 0; i < S.words.length; i++) if (S.words[i][1] <= t) current = i;
      if (current !== S.current) {
        for (let i = 0; i < spans.length; i++) { spans[i].classList.toggle('on', i === current); spans[i].classList.toggle('done', i < current); }
        S.current = current;
      }
      if (!audio.paused) requestAnimationFrame(tick);
    };
    audio.addEventListener('play', () => requestAnimationFrame(tick));
    audio.addEventListener('seeked', tick);
    S.tick = tick;
  }
  if (S.src !== data.src) {  // yeni ses
    S.src = data.src; S.words = data.words; S.current = null;
    audio.src = data.src;
    box.innerHTML = '';
    data.words.forEach(([text], i) => {
      const span = document.createElement('span'); span.dataset.i = i; span.textContent = text;
      box.append(span, document.createTextNode(' '));
    });
  }
}
"""

_MOUNTS: dict[str, Any] = {}


def word_times(characters: list[str], starts: list[float], ends: list[float]) -> list[list[Any]]:
    """Karakter zamanlarından kelime zamanları: [[kelime, başlangıç, bitiş], ...]."""
    words: list[list[Any]] = []
    current: list[Any] | None = None
    for char, start, end in zip(characters, starts, ends):
        if char.isspace():
            current = None
            continue
        if current is None:
            current = [char, start, end]
            words.append(current)
        else:
            current[0] += char
            current[2] = end
    return words


def read_along(audio: bytes, alignment: dict[str, Any], key: str) -> None:
    from streamlit.components.v2 import get_bidi_component_manager

    name = "axion_okuyarak_dinle"
    if name not in _MOUNTS or get_bidi_component_manager().get(name) is None:
        _MOUNTS[name] = st.components.v2.component(name, html=HTML, css=CSS, js=JS)
    words = word_times(alignment.get("characters", []), alignment.get("start_seconds", []), alignment.get("end_seconds", []))
    _MOUNTS[name](data={"src": media_url(audio, "audio/mpeg", "ses"), "words": words}, key=key)
