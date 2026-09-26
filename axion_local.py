"""Axion Local: Haber, Video ve Tasarım stüdyolarını (ve uzak Tarayıcı'yı) tek uygulamada açan ana giriş.

Windows: masaüstündeki "Axion Local" ikonu (windows/axion_baslat.vbs).
Geliştirme: `make run` (streamlit run axion_local.py). Ayarlar ve tema: .streamlit/config.toml
"""

import hmac
import logging
import os
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.axion_local import update_check  # noqa: E402
from apps.axion_local.settings import secret  # noqa: E402
from apps.axion_local.store import KEEP_DAYS, delete_old_projects, get_news_project, work_day_start  # noqa: E402
from apps.news_studio.config import HISTORY_DB_PATH  # noqa: E402
from apps.news_studio.integration.history import delete_runs_before  # noqa: E402

ASSETS = ROOT / "assets"
LOCAL_HOSTS = ("localhost", "127.0.0.1")

# Logo renkleri: lacivert #123249, açık mavi #BEE1E8, yeşil #D0E491 (tema: .streamlit/config.toml)
STYLE = """<style>
[data-testid="stMainBlockContainer"], .block-container {padding: 2rem 1.5rem 3rem; max-width: 1240px;}
h1 {color: #123249; font-weight: 800; letter-spacing: -0.02em;}
h3 {color: #123249;}
h1::after {content: ""; display: block; width: 56px; height: 4px; margin-top: .35rem;
           border-radius: 2px; background: linear-gradient(90deg, #D0E491, #BEE1E8);}
[data-testid="stSidebar"] {border-right: 1px solid #E3EAF0;}
/* Kenar çubuğu sabit 250 px (Streamlit: en dar 200, varsayılan 300; editör ortasını istedi), boyutlandırılamaz. */
[data-testid="stSidebar"][aria-expanded="true"] {width: 250px !important; min-width: 250px !important; max-width: 250px !important;}
[data-testid="stSidebarResizeHandle"] {display: none !important;}
div[data-testid="stExpander"] details {border-radius: 10px;}
</style>"""

st.set_page_config(page_title="Axion", page_icon=str(ASSETS / "axion_mark.png"), layout="wide")
st.markdown(STYLE, unsafe_allow_html=True)


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

    st.title("Axion")
    st.text_input("Şifre", type="password", key="axion_password", on_change=entered)
    if st.session_state.get("axion_password_failed"):
        st.error("Şifre yanlış.")
    return False


def opened_on_this_computer() -> bool:
    host = str(st.context.headers.get("Host") or "")
    return host.startswith("[::1]") or host.split(":")[0] in LOCAL_HOSTS


def shut_down() -> None:
    """Tarayıcı sayfasının görünmez Brave'ini düzgün kapatır (arkada süreç kalmasın), sonra Axion'u sonlandırır."""
    def stop() -> None:
        try:
            from apps.remote_browser.service import close_shared

            close_shared()
        finally:
            os._exit(0)

    threading.Timer(1.0, stop).start()


def restart_after_update() -> None:
    """Güncellemeden sonra: Brave'i kapat, bekçiye "yeniden başlat" koduyla çık (paketleri o kurar)."""
    def stop() -> None:
        try:
            from apps.remote_browser.service import close_shared

            close_shared()
        finally:
            os._exit(update_check.RESTART_CODE)

    threading.Timer(1.5, stop).start()


@st.fragment(run_every=update_check.REFRESH_SECONDS)
def update_controls() -> None:
    """🟢/🔴 satırı; 🔴 ise uygulamadan güncelle ve yeniden başlat (editör: dükkândayken bilgisayara erişim yok).
    Kendi başına yenilenir: yeni sürüm yayımlanınca sayfaya dokunmadan birkaç dakikada 🔴 görünür."""
    value = update_check.status()
    text = update_check.label(value, update_check.version())
    if not text:
        return
    st.caption(text, help="Bilgisayardaki Axion repodaki son sürümle karşılaştırılır (2 dakikada bir).")
    notice = update_check.rollback_notice()
    if value == "var" and update_check.blocked_by_rollback(notice):
        st.caption("⚠️ Son güncelleme açılamadı; Axion önceki sürüme döndü. Düzeltilmiş sürüm gelince yeniden "
                   "güncelleyebilirsin (Claude'a/GPT'ye `data\\axion.log`'u gönder).")
        return
    if value != "var":
        return
    if not update_check.supervised():
        st.caption("Uygulamadan güncellemek için Axion'u masaüstündeki simgeyle aç.")
        return
    if not st.session_state.get("axion_confirm_update"):
        if st.button("⬇️ Güncelle ve yeniden başlat", width="stretch"):
            st.session_state.axion_confirm_update = True
            st.rerun()
        return
    st.warning("Axion güncellenip yeniden başlatılsın mı? Yaklaşık yarım dakika erişilemez; sayfa kendiliğinden yenilenir.")
    if rendering():
        st.error("⏳ Şu an bir video oluşturuluyor; güncellersen yarıda kalır (bitmesini beklemen iyi olur).")
    yes, no = st.columns(2)
    if yes.button("Evet, güncelle", type="primary", width="stretch"):
        with st.spinner("Yeni sürüm indiriliyor..."):
            error = update_check.apply_update()
        st.session_state.axion_confirm_update = False
        if error:
            st.error(f"Güncelleme olmadı: {error}")
        else:
            st.success("Güncellendi. Axion yeniden başlıyor; yarım dakika içinde sayfa kendiliğinden yenilenir.")
            update_check.reload_when_back()
            restart_after_update()
    if no.button("Vazgeç", width="stretch", key="axion_update_cancel"):
        st.session_state.axion_confirm_update = False
        st.rerun()


def rendering() -> bool:
    """Arka planda video üretimi sürüyor mu (Video ya da Tasarım Stüdyosu)."""
    from apps.design_studio import jobs as design_jobs
    from apps.video_studio import jobs as video_jobs

    return video_jobs.busy() or design_jobs.busy()


def notify_finished_jobs() -> None:
    """Arka plandaki video biterse editör hangi sayfadaysa kısa bildirim (editör: "✅ … videosu hazır")."""
    from apps.design_studio import jobs as design_jobs
    from apps.video_studio import jobs as video_jobs

    ss = st.session_state
    since = ss.setdefault("axion_oturum_basi", time.monotonic())
    seen = ss.setdefault("axion_bildirilen_isler", set())

    @st.fragment(run_every=2.0 if rendering() else None)
    def watch() -> None:
        for kind, module in (("video", video_jobs), ("tasarim", design_jobs)):
            for folder, job in module.finished_since(since):
                if (kind, folder, job.finished) in seen or getattr(job, "cancelled", False):
                    continue
                seen.add((kind, folder, job.finished))
                project = get_news_project(Path(folder).name)
                name = f"«{project.headline}»" if project else "Haber"
                if job.error or getattr(job, "final_error", None):
                    st.toast(f"{name} videosu oluşturulamadı; ayrıntı Video/Tasarım Stüdyosu'nda.", icon="⚠️")
                else:
                    st.toast(f"{name} videosu hazır ({job.elapsed:.0f} sn).", icon="✅")

    watch()


def sidebar_footer() -> None:
    with st.sidebar:
        update_controls()
        active_id = st.session_state.get("active_news_project")
        project = get_news_project(active_id) if active_id else None
        local = opened_on_this_computer()
        if not project and not local:
            return
        if project:
            st.caption(f"Aktif haber: **{project.headline}**")
        if not local:
            return
        if st.session_state.get("axion_confirm_shutdown"):
            st.warning("Axion kapatılsın mı? Telefon/tabletten erişim de kapanır.")
            if rendering():
                st.error("⏳ Şu an bir video oluşturuluyor; kapatırsan yarıda kalır (bitmesini beklemen iyi olur).")
            yes, no = st.columns(2)
            if yes.button("Evet, kapat", type="primary", width="stretch"):
                st.info("Axion kapatıldı. Bu sekmeyi kapatabilirsin.")
                shut_down()
            if no.button("Vazgeç", width="stretch"):
                st.session_state.axion_confirm_shutdown = False
                st.rerun()
        elif st.button("Axion'u kapat", width="stretch"):
            st.session_state.axion_confirm_shutdown = True
            st.rerun()


if not authenticated():
    st.stop()


@st.cache_resource(show_spinner=False)
def clean_up_for_day(day: str) -> list[str]:
    """Her iş günü bir kez: 3 günden eski haber projelerini ve üretim kayıtlarını sil (editör kararı).

    Temizlik hatası uygulamanın açılmasını engellemez; ayrıntı data/axion.log'a yazılır.
    """
    try:
        delete_runs_before(HISTORY_DB_PATH, work_day_start() - timedelta(days=KEEP_DAYS - 1))
        return delete_old_projects()
    except Exception:
        logging.getLogger("axion").exception("Günlük temizlik başarısız")
        return []


clean_up_for_day(work_day_start().date().isoformat())

pages = [
    st.Page(ROOT / "apps" / "news_studio" / "page.py", title="Haber Stüdyosu", icon="📰", url_path="haber", default=True),
    st.Page(ROOT / "apps" / "video_studio" / "page.py", title="Video Stüdyosu", icon="🎬", url_path="video"),
    st.Page(ROOT / "apps" / "design_studio" / "page.py", title="Tasarım Stüdyosu", icon="🎨", url_path="tasarim"),
    st.Page(ROOT / "apps" / "remote_browser" / "page.py", title="Tarayıcı", icon="🌐", url_path="tarayici"),
]
page = st.navigation(pages, position="hidden")
with st.sidebar:
    for item in pages:
        st.page_link(item)
    st.divider()
page.run()
sidebar_footer()
notify_finished_jobs()
