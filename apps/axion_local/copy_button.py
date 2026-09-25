"""Tek dokunuşla metin kopyalama düğmesi (paylaşım metni). Streamlit components v2; Python'a veri dönmez.

Tablet Axion'u Tailscale üzerinden `http://` ile açtığında tarayıcı `navigator.clipboard`'ı vermez (güvenli bağlam
değil); o zaman gizli bir metin kutusu seçilip `execCommand("copy")` ile kopyalanır.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

HTML = '<button class="copy" type="button"></button>'

CSS = """
.copy { width: 100%; min-height: 40px; border: 1px solid #d5dee6; border-radius: 8px; background: #fff; color: #123249;
  font: 500 15px "Source Sans Pro", system-ui, sans-serif; cursor: pointer; padding: 0 12px; }
.copy:active { background: #e7f1fb; }
.copy.ok { background: #e6f4ec; border-color: #9fd3b4; }
.copy.err { background: #fdecea; }
"""

JS = """
function fallback(text) {
  const area = document.createElement('textarea');
  area.value = text; area.setAttribute('readonly', '');
  area.style.position = 'fixed'; area.style.opacity = '0'; area.style.top = '0';
  document.body.appendChild(area); area.select(); area.setSelectionRange(0, text.length);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
  area.remove();
  return ok;
}

export default function ({ data, parentElement }) {
  const button = parentElement.querySelector('.copy');
  button.textContent = data.label;
  button.onclick = async () => {
    let ok = false;
    try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(data.text); ok = true; } }
    catch (e) { ok = false; }
    if (!ok) ok = fallback(data.text);
    button.classList.toggle('ok', ok); button.classList.toggle('err', !ok);
    button.textContent = ok ? '✅ Kopyalandı' : 'Kopyalanamadı: aşağıdaki metni seç';
    setTimeout(() => { button.textContent = data.label; button.classList.remove('ok', 'err'); }, 2500);
  };
}
"""

_MOUNTS: dict[str, Any] = {}


def _component():
    from streamlit.components.v2 import get_bidi_component_manager

    name = "axion_kopyala"
    if name not in _MOUNTS or get_bidi_component_manager().get(name) is None:
        _MOUNTS[name] = st.components.v2.component(name, html=HTML, css=CSS, js=JS)
    return _MOUNTS[name]


def copy_button(text: str, label: str, key: str) -> None:
    _component()(data={"text": text, "label": label}, key=key)


def caption_copy(caption: str, key: str) -> None:
    """Paylaşım metnini kopyala düğmesi + (kopyalanamazsa elle seçmek için) kapalı metin."""
    caption = (caption or "").strip()
    if not caption:
        return
    copy_button(caption, "📋 Paylaşım metnini kopyala", key=key)
    with st.expander("Paylaşım metni"):
        st.code(caption, language=None, wrap_lines=True)
