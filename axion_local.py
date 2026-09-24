"""Axion Local: Haber Stüdyosu ve Video Studio'yu tek uygulamada açan ana giriş.

Windows: masaüstündeki "Axion Local" ikonu (windows/axion_baslat.vbs).
Geliştirme: `make run` (streamlit run axion_local.py). Ayarlar: .streamlit/config.toml
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

from apps.axion_local.settings import secret  # noqa: E402
from apps.axion_local.store import get_news_project  # noqa: E402

# Sayfa değişince Streamlit, görünmeyen sayfanın widget değerlerini siler; bunlar korunur.
PERSISTENT_WIDGET_KEYS = ("project_news_text",)
LOCAL_HOSTS = ("localhost", "127.0.0.1")

st.set_page_config(page_title="Axion Local", page_icon="🗞️", layout="wide")
st.markdown(
    """<style>
    [data-testid="stMainBlockContainer"], .block-container {padding-top: 2rem; max-width: 1100px;}
    </style>""",
    unsafe_allow_html=True,
)


def authenticated() -> bool:
    """APP_PASSWORD boşsa şifre sorulmaz."""
    expected = secret("APP_PASSWORD")
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


def opened_on_this_computer() -> bool:
    host = str(st.context.headers.get("Host") or "")
    return host.startswith("[::1]") or host.split(":")[0] in LOCAL_HOSTS


def sidebar_footer() -> None:
    with st.sidebar:
        active_id = st.session_state.get("active_news_project")
        project = get_news_project(active_id) if active_id else None
        if project:
            st.caption(f"Aktif proje: **{project.headline}**")
        if not opened_on_this_computer():
            return
        st.divider()
        if st.session_state.get("axion_confirm_shutdown"):
            st.warning("Axion kapatılsın mı? Telefon/tabletten erişim de kapanır.")
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


if not authenticated():
    st.stop()

for key in PERSISTENT_WIDGET_KEYS:
    if key in st.session_state:
        st.session_state[key] = st.session_state[key]

page = st.navigation(
    [
        st.Page(ROOT / "apps" / "news_studio" / "page.py", title="Haber Stüdyosu", icon="📰", url_path="haber", default=True),
        st.Page(ROOT / "apps" / "video_studio" / "page.py", title="Video Studio", icon="🎬", url_path="video"),
    ]
)
page.run()
sidebar_footer()
