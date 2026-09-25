"""Tarayıcıya dosya/görsel verme: Streamlit'in medya sunucusu (iç API; streamlit sürümü sabit), olmazsa data URL."""

from __future__ import annotations

import base64
from pathlib import Path


def media_url(content: bytes | Path, mimetype: str, name: str) -> str:
    """Tarayıcının indireceği adres: Streamlit'in medya sunucusu (video ileri/geri sarılabilir); olmazsa data URL."""
    try:
        from streamlit import runtime

        if runtime.exists():
            source = str(content) if isinstance(content, Path) else content
            return runtime.get_instance().media_file_mgr.add(source, mimetype, f"axion.{name}")
    except Exception:  # noqa: BLE001 — medya sunucusu yoksa (ör. test) gömülü veriye düş
        pass
    raw = content.read_bytes() if isinstance(content, Path) else content
    return f"data:{mimetype};base64,{base64.b64encode(raw).decode('ascii')}"
