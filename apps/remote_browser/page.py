"""Tarayıcı: evdeki bilgisayarın görünmez tarayıcısını (Brave) tabletten kullanma. DHA'dan haber bulunur, video
bilgisayara, evin internetiyle iner (İndirilenler → "Video Stüdyosu'nda kullan"). Giriş bilgileri bir kez kaydedilir,
sonra kutular kendiliğinden dolar. API yok.
"""

from __future__ import annotations

import streamlit as st

from apps.axion_local.media import media_url
from apps.axion_local.preferences import load_preferences, save_preferences
from apps.axion_local.settings import secret
from apps.axion_local.store import NEWS_IMPORT_KEY, data_dir, inbox_dir, read_text_file
from apps.remote_browser import service
from apps.remote_browser.logins import FILENAME as LOGINS_FILENAME
from apps.remote_browser.logins import Logins, site_of
from apps.remote_browser.viewer import apply_events, browser_view

ss = st.session_state
DEFAULT_HOME = "https://www.dha.com.tr"
HOME_KEY = "tarayici_ana_sayfa"
VIEW_KEY = "tarayici_gorunum"
REFRESH_SECONDS = 0.5
VIDEO_PAGE = "apps/video_studio/page.py"
NEWS_PAGE = "apps/news_studio/page.py"
logins = Logins(data_dir() / LOGINS_FILENAME)

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
               "iner. İlk girişte bilgilerini kaydedersen sonraki girişlerde kutular kendiliğinden dolar.")
    if st.button("🎬 Video Stüdyosu'na geç", width="stretch"):
        st.switch_page(VIDEO_PAGE)
    saved_sites = logins.sites()
    if saved_sites:
        with st.expander(f"🔑 Kayıtlı girişler ({len(saved_sites)})"):
            st.caption("Şifreler bu bilgisayarda, Windows hesabına bağlı şifrelenmiş olarak durur; tablete gönderilmez.")
            for site, username in saved_sites:
                name_col, delete_col = st.columns([3, 1], vertical_alignment="center")
                name_col.markdown(f"**{site}**  \n{username or '—'}")
                if delete_col.button("Sil", key=f"giris_sil_{site}"):
                    logins.delete(site)
                    st.rerun()
    st.divider()

try:
    with st.spinner("Tarayıcı açılıyor..."):
        browser = service.shared(executable, data_dir() / "tarayici", inbox_dir(), logins)
except Exception as error:  # noqa: BLE001 — Playwright/tarayıcı başlatılamadı
    st.error(f"Tarayıcı açılamadı: {str(error).splitlines()[0][:300]}")
    st.stop()


@st.fragment(run_every=REFRESH_SECONDS)
def live() -> None:
    state = ss.get(VIEW_KEY)
    payload = state.get("input") if hasattr(state, "get") else None
    if isinstance(payload, dict) and payload.get("seq") != ss.get("tarayici_seq"):
        ss["tarayici_seq"] = payload.get("seq")
        events = payload.get("events") if isinstance(payload.get("events"), list) else []
        apply_events(browser, events, secret("DHA_SIFRE"), ss[HOME_KEY] or DEFAULT_HOME)
        use = next((e.get("v") for e in events if isinstance(e, dict) and e.get("t") == "use_download"), None)
        path = browser.downloaded(str(use)) if use else None
        if path:  # Video Stüdyosu'nun 2. adımında seçili gelsin (önceki seçimler korunur)
            ss["selected_media"] = [*[p for p in ss.get("selected_media") or [] if p != path], path]
            st.switch_page(VIDEO_PAGE)
        text = next((e.get("v") for e in events if isinstance(e, dict) and e.get("t") == "use_text"), None)
        text_path = browser.downloaded(str(text)) if text else None
        if text_path:  # DHA'nın "TXT indir"i: "metni kopyala" evdeki tarayıcıda kalır, tablete gelmez
            ss[NEWS_IMPORT_KEY] = read_text_file(text_path)
            st.switch_page(NEWS_PAGE)
        if any(isinstance(e, dict) and e.get("t") == "save_login" for e in events):
            st.rerun(scope="app")  # kenar çubuğundaki "Kayıtlı girişler" listesi yenilensin
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
        "password": bool(secret("DHA_SIFRE")) or site_of(screen.url) in dict(logins.sites()),
        "login": browser.login_state(),
        "applied": ss.get("tarayici_seq"),
    }, key=VIEW_KEY)


live()
