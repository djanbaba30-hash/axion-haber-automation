"""Tarayıcı: evdeki bilgisayarın görünmez tarayıcısını (Brave) tabletten kullanma. DHA'dan haber bulunur, video
bilgisayara, evin internetiyle iner (İndirilenler → "Video Stüdyosu'nda kullan"). Giriş bilgileri bir kez kaydedilir,
sonra kutular kendiliğinden dolar. API yok.

Düzen (editör, v3.1–3.2): kenar çubuğunda gezinme, adres ve sekmeler; ortada ekran; sağda yazı ve indirilenler.
Ekran önce doğrudan akış kanalıyla (stream.py) taşınır; yoksa bu sayfanın fragment'ı kareleri yollar.
"""

from __future__ import annotations

import secrets
from typing import Any

import streamlit as st

from apps.axion_local.media import media_url
from apps.axion_local.settings import secret
from apps.axion_local.store import NEWS_IMPORT_KEY, data_dir, inbox_dir, read_text_file
from apps.remote_browser import service, stream
from apps.remote_browser.logins import FILENAME as LOGINS_FILENAME
from apps.remote_browser.logins import Logins, site_of
from apps.remote_browser.viewer import apply_events, browser_view, panel_view

ss = st.session_state
HOME = "https://dhaabone.dha.com.tr/news"  # editörün işi yalnız DHA abone paneli
VIEW_KEY = "tarayici_gorunum"
PANEL_KEY = "tarayici_panel"
SCREEN_SECONDS = 0.25  # ekran yenileme (canlı akış: yalnız değişen kare gelir)
PANEL_SECONDS = 1.0
VIDEO_PAGE = "apps/video_studio/page.py"
NEWS_PAGE = "apps/news_studio/page.py"
logins = Logins(data_dir() / LOGINS_FILENAME)

st.set_page_config(page_title="Tarayıcı · Axion", page_icon="🌐", layout="wide")
# Tablette ekranın her pikseli tarayıcıya: Streamlit'in yan/üst boşlukları bu sayfada daraltılır.
st.html('<style>[data-testid="stMainBlockContainer"], .block-container '
        '{padding: .75rem 1rem 1rem !important; max-width: 1640px !important;}</style>')

executable = service.find_browser(secret("TARAYICI_YOLU"))
if executable is None:
    st.error("Bilgisayarda Brave (ya da Chrome) bulunamadı. Brave'i kur ya da `windows\\anahtarlar.bat` ile "
             "TARAYICI_YOLU'na brave.exe'nin yolunu yaz, sonra Axion'u yeniden başlat.")
    st.stop()

try:
    with st.spinner("Tarayıcı açılıyor..."):
        browser = service.shared(executable, data_dir() / "tarayici", inbox_dir(), logins)
except Exception as error:  # noqa: BLE001 — Playwright/tarayıcı başlatılamadı
    st.error(f"Tarayıcı açılamadı: {str(error).splitlines()[0][:300]}")
    st.stop()


def take_events(key: str) -> list[Any]:
    """Bileşenin yeni olayları (aynı paket iki kez uygulanmaz)."""
    state = ss.get(key)
    payload = state.get("input") if hasattr(state, "get") else None
    if not isinstance(payload, dict) or payload.get("seq") == ss.get(key + "_seq"):
        return []
    ss[key + "_seq"] = payload.get("seq")
    return payload.get("events") if isinstance(payload.get("events"), list) else []


def handle(events: list[Any]) -> None:
    apply_events(browser, events, secret("DHA_SIFRE"), HOME)
    first = {e.get("t"): e.get("v") for e in reversed(events) if isinstance(e, dict)}
    path = browser.downloaded(str(first["use_download"])) if first.get("use_download") else None
    if path:  # Video Stüdyosu'nun 2. adımında seçili gelsin (önceki seçimler korunur)
        ss["selected_media"] = [*[p for p in ss.get("selected_media") or [] if p != path], path]
        st.switch_page(VIDEO_PAGE)
    text_path = browser.downloaded(str(first["use_text"])) if first.get("use_text") else None
    if text_path:  # DHA'nın "TXT indir"i: "metni kopyala" evdeki tarayıcıda kalır, tablete gelmez
        ss[NEWS_IMPORT_KEY] = read_text_file(text_path)
        st.switch_page(NEWS_PAGE)
    if "save_login" in first:
        st.rerun(scope="app")  # kenar çubuğundaki "Kayıtlı girişler" listesi yenilensin


def current_screen(after_frame: int | None = None):
    try:
        return browser.screen(after_frame)
    except Exception:  # noqa: BLE001 — tarayıcı kapandı/çöktü: bir sonraki çalıştırmada yeniden açılır
        browser.closed = True
        return None


@st.fragment(run_every=PANEL_SECONDS)
def side_panel() -> None:
    handle(take_events(PANEL_KEY))
    screen = current_screen()
    if screen is None:
        return
    panel_view({"url": screen.url, "tabs": screen.tabs, "applied": ss.get(PANEL_KEY + "_seq")}, key=PANEL_KEY)


@st.fragment(run_every=SCREEN_SECONDS)
def live() -> None:
    frame = browser.frame_count
    events = take_events(VIEW_KEY)
    handle(events)
    screen = current_screen(frame if events else None)
    if screen is None:
        st.warning("Tarayıcı yeniden başlatılıyor…")
        return
    if screen.url in ("", "about:blank") and not ss.get("tarayici_acildi"):
        ss["tarayici_acildi"] = True
        browser.run("goto", HOME)
    client = ss.setdefault("tarayici_akis_id", secrets.token_hex(8))  # bu oturumun akışı
    browser_view({
        # Akış kanalı açıksa kareler oradan gider; aynı kare Streamlit'ten ikinci kez yollanmaz.
        "img": None if stream.streaming(client) else media_url(screen.image, "image/jpeg", "tarayici"),
        "stream": {"path": stream.PATH, "token": stream.ticket(client)},
        "downloads": browser.download_rows(),
        "password": bool(secret("DHA_SIFRE")) or site_of(screen.url) in dict(logins.sites()),
        "login": browser.login_state(),
        "applied": ss.get(VIEW_KEY + "_seq"),
    }, key=VIEW_KEY)


with st.sidebar:
    side_panel()
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

live()
