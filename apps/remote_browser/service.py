"""Uzak tarayıcı: evdeki bilgisayarda görünmez bir Brave/Chrome açar (Playwright), tabletteki Axion sayfası onun ekran
görüntüsünü gösterir ve dokunuşları/yazıyı iletir. İndirilen dosyalar gelen kutusuna (İndirilenler) iner; video
tablete ya da dükkân internetine hiç uğramaz. API yok.

Tarayıcı Axion'un kendi profilini kullanır (`data/tarayici`): editörün normal Brave'ine ve kayıtlı şifrelerine
dokunulmaz; DHA'ya bu profilde bir kez giriş yapılır, oturum orada kalır. Tüm oturumlar tek tarayıcıyı paylaşır
(tek editör). Uzun süre kullanılmazsa kapanır, sayfa yeniden açılınca kendiliğinden başlar.

Playwright'ın async API'si kendi iş parçacığındaki olay döngüsünde çalışır: indirmeler sürerken ekran akmaya devam eder.

Girişler (logins.py): editör bir giriş formunu gönderirken (Giriş düğmesi / Enter) kullanıcı adı ve şifre okunur,
"kaydedilsin mi?" sorulur; kayıtlı sitenin giriş sayfası açılınca kutular kendiliğinden doldurulur.
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apps.axion_local.store import MEDIA_EXTENSIONS

from .logins import Logins, site_of

VIEWPORT = (1024, 768)  # 4:3: yatay tabletin dikey alanını doldurur; DHA paneli masaüstü düzeninde kalır
JPEG_QUALITY = 60
IDLE_SECONDS = 20 * 60
COMMAND_TIMEOUT = 30.0

BROWSER_ENV = "AXION_BROWSER"
_WINDOWS_BROWSERS = [
    (root, Path(*parts))
    for parts in (("BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                  ("Google", "Chrome", "Application", "chrome.exe"))
    for root in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
]
_UNIX_BROWSERS = ("brave-browser", "brave", "google-chrome", "chromium", "chromium-browser")
KEYS = {"Enter", "Backspace", "Tab", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Delete", "Home", "End",
        "PageUp", "PageDown"}

# Giriş formu: görünür şifre kutusu ve ondan önceki son yazı kutusu (kullanıcı adı). `point` verilirse (tıklama)
# yalnızca bir gönder düğmesine/bağlantıya tıklanıyorsa okunur (şifre yazılıyken başka yere dokunmak kaydı açmasın).
_LOGIN_FIELDS = """
const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
  && getComputedStyle(el).visibility !== 'hidden' && !el.disabled && !el.readOnly;
const loginFields = () => {
  const pw = [...document.querySelectorAll('input[type=password]')].find(visible);
  if (!pw) return null;
  const scope = pw.form || document;
  let user = null;
  for (const el of scope.querySelectorAll('input')) {
    const type = (el.getAttribute('type') || 'text').toLowerCase();
    if (el === pw) break;
    if (['text', 'email', 'tel'].includes(type) && visible(el)) user = el;
  }
  return { pw, user };
};
"""
READ_LOGIN = "(point) => {" + _LOGIN_FIELDS + """
  const f = loginFields();
  if (!f || !f.pw.value) return null;
  if (point) {
    const target = document.elementFromPoint(point[0], point[1]);
    if (!target || !target.closest('button, input[type=submit], input[type=image], a, [role=button]')) return null;
  }
  return { username: f.user ? f.user.value : '', password: f.pw.value };
}"""
FILL_LOGIN = "([username, password]) => {" + _LOGIN_FIELDS + """
  const f = loginFields();
  if (!f || f.pw.value) return false;
  const set = (el, value) => {  // React/Vue gibi sayfalar da görsün: gerçek yazma olayları
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  if (f.user && !f.user.value && username) set(f.user, username);
  set(f.pw, password);
  return true;
}"""


def find_browser(configured: str | None = None) -> Path | None:
    """Sürülecek tarayıcı: ayar (TARAYICI_YOLU) → AXION_BROWSER → Brave → Chrome. Edge kasıtlı yok (editör kararı)."""
    for candidate in (configured, os.environ.get(BROWSER_ENV)):
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    for root, relative in _WINDOWS_BROWSERS:
        base = os.environ.get(root)
        if base and (Path(base) / relative).is_file():
            return Path(base) / relative
    for name in _UNIX_BROWSERS:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def kill_orphans(profile: Path) -> None:
    """Axion'un profiliyle çalışan artık tarayıcı süreçlerini kapatır (normal Brave'e dokunmaz: profil yolu ayırt eder)."""
    import subprocess

    marker = str(profile.resolve())
    if sys.platform == "win32":
        escaped = marker.replace("'", "''")
        script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('"
                  + escaped + "') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
        command = ["powershell", "-NoProfile", "-Command", script]
    else:
        command = ["pkill", "-f", "--", f"--user-data-dir={marker}"]
    try:
        subprocess.run(command, capture_output=True, timeout=20, check=False,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        pass
    time.sleep(1.0)


def normalize_url(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if re.match(r"^[a-z][a-z0-9+.-]*://", text, re.I) or text.startswith("about:"):
        return text
    if re.match(r"^(localhost|\d{1,3}(\.\d{1,3}){3})(:\d+)?(/|$)", text):
        return "http://" + text
    if " " in text or "." not in text:
        return "https://duckduckgo.com/?q=" + text.replace(" ", "+")
    return "https://" + text


def unique_path(folder: Path, name: str) -> Path:
    """İndirilenler'de aynı adlı dosya varsa üzerine yazmaz: "video (2).mp4"."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "indirilen"
    path = folder / name
    stem, suffix, number = path.stem, path.suffix, 2
    while path.exists():
        path = folder / f"{stem} ({number}){suffix}"
        number += 1
    return path


@dataclass
class Download:
    name: str
    path: Path
    started: float = field(default_factory=time.monotonic)
    finished: float | None = None
    error: str | None = None

    @property
    def state(self) -> str:
        return "hata" if self.error else ("bitti" if self.finished else "iniyor")

    def summary(self) -> dict[str, Any]:
        size = self.path.stat().st_size if self.finished and self.path.exists() else 0
        return {"name": self.path.name, "state": self.state, "mb": round(size / 1e6, 1), "error": self.error,
                "seconds": round((self.finished or time.monotonic()) - self.started),
                "video": self.path.suffix.lower() in MEDIA_EXTENSIONS, "text": self.path.suffix.lower() == ".txt"}


@dataclass
class Screen:
    image: bytes
    url: str
    title: str
    tabs: list[dict[str, Any]]  # [{title, url, active}]


class RemoteBrowser:
    def __init__(self, executable: Path, profile: Path, inbox: Path, logins: Logins | None = None) -> None:
        self.executable, self.profile, self.inbox = executable, profile, inbox
        self.logins = logins
        self.login_offer: dict[str, str] | None = None  # {site, username, password}: "kaydedilsin mi?"
        self.filled_site: str | None = None              # az önce kutuları doldurulan site (ekranda not)
        self._declined: set[tuple[str, str, str]] = set()
        self.downloads: list[Download] = []
        self.last_used = time.monotonic()
        self.closed = False
        self._screen: Screen | None = None
        # Canlı görüntü (CDP screencast): Chrome yalnız değişen kareyi yollar; ekran görüntüsü beklemekten hızlı.
        self._cast: Any = None
        self._cast_page: Any = None
        self._frame: bytes | None = None
        self.frame_count = 0  # gelen kare sayacı: bir işlemden sonra taze kare beklemek için
        self._page: Any = None
        self._context: Any = None
        self._playwright: Any = None
        # Windows'ta tarayıcıyı alt süreç olarak başlatmak Proactor döngüsü ister (Streamlit başka ilke kurmuş olabilir).
        self._loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="axion-tarayici")
        self._thread.start()
        try:
            self._call(self._start(), 60)
        except BaseException:
            self.close()
            raise

    # ------------------------------------------------------------------ iş parçacığı köprüsü
    def _call(self, coroutine, timeout: float = COMMAND_TIMEOUT):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(timeout)

    async def _start(self) -> None:
        from playwright.async_api import async_playwright

        self.profile.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        options = dict(executable_path=str(self.executable), headless=True, accept_downloads=True, locale="tr-TR",
                       viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]},
                       args=["--no-first-run", "--no-default-browser-check"])
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(str(self.profile), **options)
        except Exception:  # noqa: BLE001 — çoğunlukla: Axion zorla kapatılmış, eski Brave profili kilitli tutuyor
            await asyncio.to_thread(kill_orphans, self.profile)
            self._context = await self._playwright.chromium.launch_persistent_context(str(self.profile), **options)
        self._context.on("page", self._on_new_page)
        for page in self._context.pages:
            self._watch(page)
        self._page = self._context.pages[-1] if self._context.pages else await self._context.new_page()
        self._watchdog = self._loop.create_task(self._idle_watch())

    def _watch(self, page) -> None:
        page.on("download", lambda download: self._loop.create_task(self._save(download)))
        page.on("close", self._on_close)
        page.on("load", lambda loaded: self._loop.create_task(self._autofill(loaded)))
        page.on("framenavigated", lambda frame: self._on_navigated(page, frame))

    def _on_navigated(self, page, frame) -> None:
        if frame is page.main_frame and page is self._page:
            self.filled_site = None  # yeni sayfa: "dolduruldu" notu yalnız dolduran sayfada görünür

    def _on_new_page(self, page) -> None:  # yeni sekme / açılır pencere öne gelir
        self._watch(page)
        self._page = page

    def _on_close(self, page) -> None:
        if page is self._page and self._context is not None:
            pages = [p for p in self._context.pages if p is not page]
            self._page = pages[-1] if pages else None

    async def _save(self, download) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        item = Download(download.suggested_filename, unique_path(self.inbox, download.suggested_filename))
        self.downloads.append(item)
        partial = item.path.with_name(item.path.name + ".iniyor")
        try:
            await download.save_as(partial)
            partial.replace(item.path)  # yarım dosya Video Stüdyosu'nun listesinde görünmesin
            item.finished = time.monotonic()
        except Exception as error:  # noqa: BLE001 — ekranda gösterilir
            item.error = str(error).splitlines()[0][:200] or error.__class__.__name__
            partial.unlink(missing_ok=True)

    async def _idle_watch(self) -> None:
        while not self.closed:
            await asyncio.sleep(30)
            busy = any(d.state == "iniyor" for d in self.downloads)
            if not busy and time.monotonic() - self.last_used > IDLE_SECONDS:
                await self._shutdown()

    async def _shutdown(self) -> None:
        self.closed = True
        watchdog = getattr(self, "_watchdog", None)
        if watchdog is not None and watchdog is not asyncio.current_task():
            watchdog.cancel()
        for closer in (self._context, self._playwright):
            try:
                if closer is self._playwright and closer is not None:
                    await closer.stop()
                elif closer is not None:
                    await closer.close()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ girişler
    async def _autofill(self, page) -> bool:
        """Kayıtlı sitenin giriş kutularını doldurur (şifre kutusu boşsa). Doldurduysa True."""
        site = site_of(page.url)
        saved = self.logins.get(site) if self.logins and site else None
        if not saved:
            return False
        for frame in page.frames:
            try:
                if await frame.evaluate(FILL_LOGIN, list(saved)):
                    self.filled_site = site
                    return True
            except Exception:  # noqa: BLE001 — çerçeve kapandı / gezinme sürüyor
                continue
        return False

    async def _read_login(self, page, point: tuple[float, float] | None) -> None:
        """Form gönderilirken kullanıcı adı + şifreyi okur; kayıtlıdan farklıysa "kaydedilsin mi?" sorulacak."""
        site = site_of(page.url)
        if not self.logins or not site:
            return
        try:
            found = await page.evaluate(READ_LOGIN, list(point) if point else None)
        except Exception:  # noqa: BLE001
            return
        if not found or not found.get("password"):
            return
        entry = (site, str(found.get("username", "")), str(found["password"]))
        if self.logins.get(site) == entry[1:] or entry in self._declined:
            return
        self.login_offer = {"site": entry[0], "username": entry[1], "password": entry[2]}

    def login_state(self) -> dict[str, Any]:
        """Tablete giden giriş bilgisi (şifre asla): kayıt teklifi ve az önce doldurulan site."""
        offer = self.login_offer
        return {"offer": {"site": offer["site"], "username": offer["username"]} if offer else None,
                "filled": self.filled_site}

    def answer_login_offer(self, save: bool) -> None:
        offer, self.login_offer = self.login_offer, None
        if not offer:
            return
        if save and self.logins:
            self.logins.save(offer["site"], offer["username"], offer["password"])
        else:
            self._declined.add((offer["site"], offer["username"], offer["password"]))

    def fill_login(self) -> bool:
        """"🔑 Girişi doldur" düğmesi: kayıtlı girişi şimdi yazar (sayfa kendiliğinden doldurmadıysa)."""
        self.last_used = time.monotonic()

        async def fill() -> bool:
            return await self._autofill(await self._active())

        return bool(self._call(fill()))

    async def _start_cast(self, page) -> None:
        if self._cast_page is page:
            return
        old, self._cast, self._cast_page, self._frame = self._cast, None, None, None
        if old is not None:
            try:
                await old.detach()
            except Exception:  # noqa: BLE001 — sekme kapanmış olabilir
                pass
        try:
            session = await self._context.new_cdp_session(page)
            session.on("Page.screencastFrame", lambda frame: self._loop.create_task(self._on_frame(session, frame)))
            await session.send("Page.startScreencast", {"format": "jpeg", "quality": JPEG_QUALITY,
                                                        "maxWidth": VIEWPORT[0], "maxHeight": VIEWPORT[1]})
            self._cast, self._cast_page = session, page
        except Exception:  # noqa: BLE001 — akış yoksa ekran görüntüsüne düşülür
            self._cast = self._cast_page = None

    async def _on_frame(self, session, frame: dict[str, Any]) -> None:
        if session is self._cast:
            self._frame = base64.b64decode(frame["data"])
            self.frame_count += 1
        try:
            await session.send("Page.screencastFrameAck", {"sessionId": frame["sessionId"]})
        except Exception:  # noqa: BLE001
            pass

    async def _active(self):
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
        return self._page

    # ------------------------------------------------------------------ komutlar (tabletten)
    async def _run(self, action: str, value: Any = None) -> None:
        page = await self._active()
        try:
            if action == "goto" and value:
                await page.goto(normalize_url(str(value)), wait_until="commit", timeout=20000)
            elif action == "click":
                await self._read_login(page, (float(value[0]), float(value[1])))
                await page.mouse.click(float(value[0]), float(value[1]))
            elif action == "wheel":
                await page.mouse.move(float(value[0]), float(value[1]))
                await page.mouse.wheel(0, float(value[2]))
            elif action == "type" and value:
                await page.keyboard.type(str(value))
            elif action == "key" and value in KEYS:
                if value == "Enter":
                    await self._read_login(page, None)
                await page.keyboard.press(str(value))
            elif action == "back":
                await page.go_back(wait_until="commit", timeout=10000)
            elif action == "forward":
                await page.go_forward(wait_until="commit", timeout=10000)
            elif action == "reload":
                await page.reload(wait_until="commit", timeout=20000)
            elif action == "tab" and 0 <= int(value) < len(self._context.pages):
                self._page = self._context.pages[int(value)]
                await self._page.bring_to_front()
            elif action == "close_tab" and len(self._context.pages) > 1:
                pages = self._context.pages
                target = pages[int(value)] if value is not None and 0 <= int(value) < len(pages) else page
                if target is page:  # açık sekme kapanıyorsa bir öncekine geçilir
                    self._page = pages[max(0, pages.index(page) - 1)]
                await target.close()
        except Exception:  # noqa: BLE001 — zaman aşımı/gezinme hatası: ekran olduğu gibi kalır, editör yeniden dener
            pass

    def run(self, action: str, value: Any = None) -> None:
        self.last_used = time.monotonic()
        self._call(self._run(action, value))

    async def _capture(self) -> Screen:
        page = await self._active()
        await self._start_cast(page)
        image = self._frame if self._cast_page is page else None
        if image is None:  # akışın ilk karesi gelmedi (ya da akış yok): ekran görüntüsü
            try:
                image = await page.screenshot(type="jpeg", quality=JPEG_QUALITY, timeout=5000)
            except Exception:  # noqa: BLE001 — sayfa yüklenirken: son görüntü kalır
                if self._screen:
                    return self._screen
                raise
        tabs = []
        for tab in self._context.pages:
            try:
                title = await tab.title()
            except Exception:  # noqa: BLE001
                title = ""
            tabs.append({"title": title or tab.url, "url": tab.url, "active": tab is page})
        self._screen = Screen(image, page.url, next((t["title"] for t in tabs if t["active"]), ""), tabs)
        return self._screen

    def screen(self, after_frame: int | None = None, wait: float = 0.15) -> Screen:
        """Son kare. `after_frame` verilirse (tıklama/kaydırma sonrası) en fazla `wait` sn daha yeni kare beklenir:
        tablet işlemin sonucunu bir sonraki yenilemeyi beklemeden görür."""
        self.last_used = time.monotonic()
        deadline = time.monotonic() + wait
        while after_frame is not None and self.frame_count <= after_frame and time.monotonic() < deadline:
            time.sleep(0.01)
        return self._call(self._capture(), 15)

    def download_rows(self, limit: int = 6) -> list[dict[str, Any]]:
        return [d.summary() for d in self.downloads[-limit:]][::-1]

    def downloaded(self, name: str) -> Path | None:
        """Bitmiş bir indirmenin yolu (ekrandaki adıyla)."""
        for item in reversed(self.downloads):
            if item.path.name == name and item.state == "bitti" and item.path.exists():
                return item.path
        return None

    def close(self) -> None:
        if not self.closed and self._loop.is_running():
            try:
                self._call(self._shutdown(), 15)
            except Exception:  # noqa: BLE001
                pass
        self.closed = True
        self._loop.call_soon_threadsafe(self._loop.stop)


_SHARED: RemoteBrowser | None = None
_LOCK = threading.Lock()


def shared(executable: Path, profile: Path, inbox: Path, logins: Logins | None = None) -> RemoteBrowser:
    """Uygulamadaki tek tarayıcı; kapanmışsa (boşta kaldı, çöktü) yeniden başlatılır."""
    global _SHARED
    with _LOCK:
        if _SHARED is None or _SHARED.closed or _SHARED.executable != executable:
            if _SHARED is not None:
                _SHARED.close()
            _SHARED = RemoteBrowser(executable, profile, inbox, logins)
        return _SHARED


def close_shared() -> None:
    """Axion kapanırken (os._exit öncesi): tarayıcıyı düzgün kapat, arkada Brave süreci kalmasın."""
    global _SHARED
    with _LOCK:
        if _SHARED is not None:
            _SHARED.close()
            _SHARED = None
