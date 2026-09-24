"""Axion Local: Haber Stüdyosu ve Video Studio'yu tek şifreyle tek arayüzde açar.

Çalıştırma: windows/axion_baslat.bat  (veya: streamlit run axion_local.py)
"""

import hmac
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("AXION_LOCAL", "1")

st.set_page_config(page_title="Axion Local", page_icon="🗞️", layout="wide")


def _secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value).strip() if value else None


def _authenticated() -> bool:
    if st.session_state.get("axion_authenticated"):
        return True
    expected = _secret("APP_PASSWORD")
    if not expected:
        st.error("APP_PASSWORD tanımlı değil. `.streamlit/secrets.toml` dosyasını kontrol et.")
        return False

    def entered() -> None:
        ok = hmac.compare_digest(
            str(st.session_state.get("axion_password", "")).encode("utf-8"),
            expected.encode("utf-8"),
        )
        st.session_state.axion_authenticated = ok
        st.session_state.axion_password_failed = not ok
        st.session_state.pop("axion_password", None)

    st.title("Axion Local")
    st.text_input("Şifre", type="password", key="axion_password", on_change=entered)
    if st.session_state.get("axion_password_failed"):
        st.error("Şifre yanlış.")
    return False


if not _authenticated():
    st.stop()

# Sayfalar kendi şifre ekranlarını göstermesin.
st.session_state["password_correct"] = True
st.session_state["video_password_correct"] = True

page = st.navigation(
    [
        st.Page(ROOT / "apps" / "news_studio" / "app.py", title="Haber Stüdyosu", icon="📰", url_path="haber"),
        st.Page(ROOT / "apps" / "video_studio" / "app.py", title="Video Studio", icon="🎬", url_path="video"),
    ]
)
page.run()
