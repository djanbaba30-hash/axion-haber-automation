"""Axion'un başlatma noktası (v3.2): Streamlit uygulaması (`axion_local.py`) + Tarayıcı'nın doğrudan akış kanalı.

`streamlit run axion_app.py` bu dosyadaki `app`'i bulup çalıştırır (Streamlit'in resmi `st.App` yolu). Akış kanalı
(WebSocket) Tarayıcı ekranını Streamlit turlarını beklemeden taşır; bkz. apps/remote_browser/stream.py.
"""

from pathlib import Path

import streamlit as st
from starlette.routing import WebSocketRoute

from apps.remote_browser import stream

app = st.App(Path(__file__).with_name("axion_local.py"), routes=[WebSocketRoute(stream.PATH, stream.endpoint)])
