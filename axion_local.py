"""Axion Local: Haber Stüdyosu ve Video Studio'yu tek arayüzde açar.

Çalıştırma: masaüstündeki "Axion Local" kısayolu (windows/axion_baslat.vbs)
veya: streamlit run axion_local.py
"""

import hmac
import os
import sys
import threading
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("AXION_LOCAL", "1")

# Sayfa değişince Streamlit, görünmeyen sayfanın widget değerlerini siler; bunlar korunur.
PERSISTENT_WIDGET_KEYS = ("project_news_text",)

LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]")

st.set_page_config(page_title="Axion Local", page_icon="🗞️", layout="wide")


def _secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value).strip() if value else None


def _authenticated() -> bool:
    expected = _secret("APP_PASSWORD")
    if not expected or st.session_state.get("axion_authenticated"):
        return True

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


def _opened_on_this_computer() -> bool:
    host = str(st.context.headers.get("Host") or "")
    return host.split(":")[0] in LOCAL_HOSTS or host.startswith("[::1]")


def _shutdown_controls() -> None:
    with st.sidebar:
        st.divider()
        if st.session_state.get("axion_confirm_shutdown"):
            st.warning("Axion kapatılsın mı? Tabletten erişim de kapanır.")
            yes, no = st.columns(2)
            if yes.button("Evet, kapat", type="primary", use_container_width=True):
                st.info("Axion kapatıldı. Bu sekmeyi kapatabilirsin.")
                threading.Timer(1.0, os._exit, args=(0,)).start()
            if no.button("Vazgeç", use_container_width=True):
                st.session_state.axion_confirm_shutdown = False
                st.rerun()
        elif st.button("Axion'u kapat", use_container_width=True):
            st.session_state.axion_confirm_shutdown = True
            st.rerun()


if not _authenticated():
    st.stop()

# Sayfalar kendi şifre ekranlarını göstermesin.
st.session_state["password_correct"] = True
st.session_state["video_password_correct"] = True

for _key in PERSISTENT_WIDGET_KEYS:
    if _key in st.session_state:
        st.session_state[_key] = st.session_state[_key]

page = st.navigation(
    [
        st.Page(ROOT / "apps" / "news_studio" / "app.py", title="Haber Stüdyosu", icon="📰", url_path="haber"),
        st.Page(ROOT / "apps" / "video_studio" / "app.py", title="Video Studio", icon="🎬", url_path="video"),
    ]
)

if _opened_on_this_computer():
    _shutdown_controls()

page.run()
