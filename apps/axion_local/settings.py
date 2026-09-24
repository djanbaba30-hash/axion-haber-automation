"""API anahtarları: `.streamlit/secrets.toml` (Windows'ta `windows/anahtarlar.bat` ile düzenlenir)."""

from __future__ import annotations

import streamlit as st


def secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value).strip() if value else None


def require_secrets(*names: str) -> None:
    """Eksik anahtar varsa açıklayıcı bir mesajla sayfayı durdurur."""
    missing = [name for name in names if not secret(name)]
    if missing:
        st.error(
            "Eksik API anahtarı: " + ", ".join(missing)
            + ". `windows\\anahtarlar.bat` ile ekleyip Axion'u yeniden başlat."
        )
        st.stop()
