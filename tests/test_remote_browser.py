"""Uzak tarayıcı (Tasarım/Video'dan ayrı modül): gerçek Chromium ile uçtan uca. Tarayıcı yoksa atlanır."""

from __future__ import annotations

import http.server
import threading
import time
from pathlib import Path

import pytest

from apps.remote_browser import service
from apps.remote_browser.service import RemoteBrowser, find_browser, normalize_url, unique_path

PAGE = b"""<!doctype html><html><body style="margin:0">
<input id="kutu" style="position:absolute;left:100px;top:100px;width:200px;height:30px">
<a id="indir" href="/video.mp4" download style="position:absolute;left:100px;top:200px">indir</a>
<a id="sekme" href="/ikinci" target="_blank" style="position:absolute;left:100px;top:300px">yeni sekme</a>
<div style="height:3000px"></div></body></html>"""
VIDEO = b"\x00\x00\x00\x18ftypmp42" + b"x" * 200_000


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/video.mp4":
            body, kind = VIDEO, "video/mp4"
        elif self.path == "/ikinci":
            body, kind = b"<title>Ikinci</title><h1>ikinci</h1>", "text/html"
        else:
            body, kind = PAGE, "text/html"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _chromium() -> Path | None:
    found = find_browser()
    if found:
        return found
    candidates = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    return candidates[-1] if candidates else None


@pytest.fixture()
def site():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_port}"
    server.shutdown()


def _wait(condition, seconds=10.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.1)
    return False


def test_normalize_url_and_unique_path(tmp_path):
    assert normalize_url("dha.com.tr/panel") == "https://dha.com.tr/panel"
    assert normalize_url("http://x.y") == "http://x.y"
    assert normalize_url("localhost:8501/a") == "http://localhost:8501/a"
    assert normalize_url("kars kaza") == "https://duckduckgo.com/?q=kars+kaza"
    (tmp_path / "video.mp4").write_bytes(b"1")
    assert unique_path(tmp_path, "video.mp4").name == "video (2).mp4"
    assert unique_path(tmp_path, 'a/b:c?.mp4').name == "a_b_c_.mp4"


def test_find_browser_prefers_setting_and_skips_edge(tmp_path, monkeypatch):
    brave = tmp_path / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe"
    brave.parent.mkdir(parents=True)
    brave.write_bytes(b"")
    edge = tmp_path / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.write_bytes(b"")
    monkeypatch.delenv(service.BROWSER_ENV, raising=False)
    for root in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        monkeypatch.setenv(root, str(tmp_path))
    monkeypatch.setattr(service.shutil, "which", lambda name: None)
    assert find_browser() == brave
    assert find_browser(str(edge)) == edge  # editör isterse elle verebilir
    brave.unlink()
    assert find_browser() is None  # Edge kendiliğinden seçilmez


@pytest.mark.skipif(_chromium() is None, reason="Chromium/Brave yok")
def test_remote_browser_types_scrolls_downloads_and_follows_new_tab(tmp_path, site):
    browser = RemoteBrowser(_chromium(), tmp_path / "profil", tmp_path / "indirilenler")
    try:
        browser.run("goto", site)
        assert _wait(lambda: browser.screen().url.endswith("/"))
        screen = browser.screen()
        assert screen.image[:2] == b"\xff\xd8" and screen.tabs == 1  # JPEG

        browser.run("click", (150, 115))
        browser.run("type", "şifre")
        browser.run("key", "Backspace")
        assert browser._call(browser._page.evaluate("document.getElementById('kutu').value")) == "şifr"
        browser.run("key", "rm -rf")  # bilinmeyen tuş yok sayılır
        browser.run("wheel", (400, 400, 500))
        assert _wait(lambda: browser._call(browser._page.evaluate("window.scrollY")) > 0)
        browser.run("wheel", (400, 400, -5000))
        assert _wait(lambda: browser._call(browser._page.evaluate("window.scrollY")) == 0)

        browser.run("click", (110, 205))
        assert _wait(lambda: browser.download_rows() and browser.download_rows()[0]["state"] == "bitti")
        saved = tmp_path / "indirilenler" / "video.mp4"
        assert saved.read_bytes() == VIDEO and not list(saved.parent.glob("*.iniyor"))
        assert browser.download_rows()[0]["name"] == "video.mp4"

        browser.run("click", (110, 305))
        assert _wait(lambda: browser.screen().tabs == 2 and browser.screen().url.endswith("/ikinci"))
        browser.run("close_tab")
        assert _wait(lambda: browser.screen().tabs == 1 and browser.screen().url.endswith("/"))
    finally:
        browser.close()
    assert browser.closed


@pytest.mark.skipif(_chromium() is None, reason="Chromium/Brave yok")
def test_shared_browser_restarts_after_close(tmp_path):
    first = service.shared(_chromium(), tmp_path / "p", tmp_path / "i")
    try:
        assert service.shared(_chromium(), tmp_path / "p", tmp_path / "i") is first
        first.close()
        second = service.shared(_chromium(), tmp_path / "p", tmp_path / "i")
        assert second is not first and not second.closed
    finally:
        service.shared(_chromium(), tmp_path / "p", tmp_path / "i").close()
