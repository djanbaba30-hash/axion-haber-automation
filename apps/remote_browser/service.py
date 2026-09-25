"""Uzak tarayıcı: evdeki bilgisayarda görünmez bir Brave/Chrome açar (Playwright), tabletteki Axion sayfası onun ekran
görüntüsünü gösterir ve dokunuşları/yazıyı iletir. İndirilen dosyalar gelen kutusuna (İndirilenler) iner; video
tablete ya da dükkân internetine hiç uğramaz. API yok.

Tarayıcı Axion'un kendi profilini kullanır (`data/tarayici`): editörün normal Brave'ine ve kayıtlı şifrelerine
dokunulmaz; DHA'ya bu profilde bir kez giriş yapılır, oturum orada kalır. Tüm oturumlar tek tarayıcıyı paylaşır
(tek editör). Uzun süre kullanılmazsa kapanır, sayfa yeniden açılınca kendiliğinden başlar.

Playwright'ın async API'si kendi iş parçacığındaki olay döngüsünde çalışır: indirmeler sürerken ekran akmaya devam eder.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VIEWPORT = (1024, 640)  # tablet ekranına yakın oran; DHA paneli masaüstü düzeninde kalır
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
                "seconds": round((self.finished or time.monotonic()) - self.started)}


@dataclass
class Screen:
    image: bytes
    url: str
    title: str
    tabs: int


class RemoteBrowser:
    def __init__(self, executable: Path, profile: Path, inbox: Path) -> None:
        self.executable, self.profile, self.inbox = executable, profile, inbox
        self.downloads: list[Download] = []
        self.last_used = time.monotonic()
        self.closed = False
        self._screen: Screen | None = None
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
        self._context = await self._playwright.chromium.launch_persistent_context(
            str(self.profile), executable_path=str(self.executable), headless=True,
            viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]}, accept_downloads=True, locale="tr-TR",
            args=["--no-first-run", "--no-default-browser-check"],
        )
        self._context.on("page", self._on_new_page)
        for page in self._context.pages:
            self._watch(page)
        self._page = self._context.pages[-1] if self._context.pages else await self._context.new_page()
        self._watchdog = self._loop.create_task(self._idle_watch())

    def _watch(self, page) -> None:
        page.on("download", lambda download: self._loop.create_task(self._save(download)))
        page.on("close", lambda closed: self._on_close(closed))

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
                await page.mouse.click(float(value[0]), float(value[1]))
            elif action == "wheel":
                await page.mouse.move(float(value[0]), float(value[1]))
                await page.mouse.wheel(0, float(value[2]))
            elif action == "type" and value:
                await page.keyboard.type(str(value))
            elif action == "key" and value in KEYS:
                await page.keyboard.press(str(value))
            elif action == "back":
                await page.go_back(wait_until="commit", timeout=10000)
            elif action == "forward":
                await page.go_forward(wait_until="commit", timeout=10000)
            elif action == "reload":
                await page.reload(wait_until="commit", timeout=20000)
            elif action == "close_tab" and len(self._context.pages) > 1:
                await page.close()
        except Exception:  # noqa: BLE001 — zaman aşımı/gezinme hatası: ekran olduğu gibi kalır, editör yeniden dener
            pass

    def run(self, action: str, value: Any = None) -> None:
        self.last_used = time.monotonic()
        self._call(self._run(action, value))

    async def _capture(self) -> Screen:
        page = await self._active()
        try:
            image = await page.screenshot(type="jpeg", quality=JPEG_QUALITY, timeout=5000)
        except Exception:  # noqa: BLE001 — sayfa yüklenirken: son görüntü kalır
            if self._screen:
                return self._screen
            raise
        try:
            title = await page.title()
        except Exception:  # noqa: BLE001
            title = ""
        self._screen = Screen(image, page.url, title, len(self._context.pages))
        return self._screen

    def screen(self) -> Screen:
        self.last_used = time.monotonic()
        return self._call(self._capture(), 15)

    def download_rows(self, limit: int = 6) -> list[dict[str, Any]]:
        return [d.summary() for d in self.downloads[-limit:]][::-1]

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


def shared(executable: Path, profile: Path, inbox: Path) -> RemoteBrowser:
    """Uygulamadaki tek tarayıcı; kapanmışsa (boşta kaldı, çöktü) yeniden başlatılır."""
    global _SHARED
    with _LOCK:
        if _SHARED is None or _SHARED.closed or _SHARED.executable != executable:
            if _SHARED is not None:
                _SHARED.close()
            _SHARED = RemoteBrowser(executable, profile, inbox)
        return _SHARED
