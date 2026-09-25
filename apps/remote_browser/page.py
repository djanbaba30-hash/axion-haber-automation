"""Tarayıcı: evdeki bilgisayarın görünmez tarayıcısını (Brave) tabletten kullanma. DHA'dan haber bulunur, video
bilgisayara, evin internetiyle iner (İndirilenler → Video Stüdyosu'nda listede). API yok.
"""

from __future__ import annotations

import streamlit as st

from apps.axion_local.media import media_url
from apps.axion_local.preferences import load_preferences, save_preferences
from apps.axion_local.settings import secret
from apps.axion_local.store import data_dir, inbox_dir
from apps.remote_browser import service
from apps.remote_browser.viewer import apply_events, browser_view

ss = st.session_state
DEFAULT_HOME = "https://www.dha.com.tr"
HOME_KEY = "tarayici_ana_sayfa"
VIEW_KEY = "tarayici_gorunum"
REFRESH_SECONDS = 0.5

st.set_page_config(page_title="Tarayıcı · Axion", page_icon="🌐", layout="wide")
# Tablette ekranın her pikseli tarayıcıya: Streamlit'in geniş yan boşlukları bu sayfada daraltılır.
st.html('<style>[data-testid="stMainBlockContainer"], .block-container '
        '{padding: 1rem 1rem 2rem !important; max-width: 1640px !important;}</style>')

executable = service.find_browser(secret("TARAYICI_YOLU"))
if executable is None:
    st.error("Bilgisayarda Brave (ya da Chrome) bulunamadı. Brave'i kur ya da `windows\\anahtarlar.bat` ile "
             "TARAYICI_YOLU'na brave.exe'nin yolunu yaz, sonra Axion'u yeniden başlat.")
    st.stop()

if HOME_KEY not in ss:
    ss[HOME_KEY] = load_preferences().get(HOME_KEY) or DEFAULT_HOME

with st.sidebar:
    home = st.text_input("Ana sayfa (⌂)", key=HOME_KEY, help="Örn. DHA panelinin adresi. Hatırlanır.")
    if home != load_preferences().get(HOME_KEY, DEFAULT_HOME):
        save_preferences({**load_preferences(), HOME_KEY: home})
    st.caption("Bu tarayıcı evdeki bilgisayarda çalışır; indirdiğin videolar bilgisayarın **İndirilenler** klasörüne "
               "iner ve Video Stüdyosu'nda listede görünür. DHA'ya bu tarayıcıda bir kez giriş yapman yeterli.")
    if st.button("🎬 Video Stüdyosu'na geç", width="stretch"):
        st.switch_page("apps/video_studio/page.py")
    st.divider()

try:
    with st.spinner("Tarayıcı açılıyor..."):
        browser = service.shared(executable, data_dir() / "tarayici", inbox_dir())
except Exception as error:  # noqa: BLE001 — Playwright/tarayıcı başlatılamadı
    st.error(f"Tarayıcı açılamadı: {str(error).splitlines()[0][:300]}")
    st.stop()


@st.fragment(run_every=REFRESH_SECONDS)
def live() -> None:
    state = ss.get(VIEW_KEY)
    payload = state.get("input") if hasattr(state, "get") else None
    if isinstance(payload, dict) and payload.get("seq") != ss.get("tarayici_seq"):
        ss["tarayici_seq"] = payload.get("seq")
        apply_events(browser, payload.get("events"), secret("DHA_SIFRE"), ss[HOME_KEY] or DEFAULT_HOME)
    try:
        screen = browser.screen()
    except Exception:  # noqa: BLE001 — tarayıcı kapandı/çöktü: bir sonraki çalıştırmada yeniden açılır
        browser.closed = True
        st.warning("Tarayıcı yeniden başlatılıyor…")
        return
    if screen.url in ("", "about:blank") and not ss.get("tarayici_acildi"):
        ss["tarayici_acildi"] = True
        browser.run("goto", ss[HOME_KEY] or DEFAULT_HOME)
    browser_view({
        "img": media_url(screen.image, "image/jpeg", "tarayici"),
        "url": screen.url, "title": screen.title, "tabs": screen.tabs,
        "downloads": browser.download_rows(),
        "password": bool(secret("DHA_SIFRE")),
        "applied": ss.get("tarayici_seq"),
    }, key=VIEW_KEY)


live()
