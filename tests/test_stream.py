"""Tarayıcı'nın doğrudan akış kanalı (WebSocket) ve Windows başlatıcı zinciri."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.remote_browser import service, stream

ROOT = Path(__file__).resolve().parents[1]


class FakeBrowser:
    closed = False

    def __init__(self):
        self.frame_count = 1
        self.frame = b"\xff\xd8kare1"
        self.calls = []

    def latest_frame(self):
        return self.frame

    def run(self, action, value=None):
        self.calls.append((action, value))


@pytest.fixture
def client(monkeypatch):
    fake = FakeBrowser()
    monkeypatch.setattr(service, "current", lambda: fake)
    app = Starlette(routes=[WebSocketRoute(stream.PATH, stream.endpoint)])
    with TestClient(app) as test_client:
        yield test_client, fake


def test_stream_rejects_missing_token(client):
    test_client, _ = client
    with pytest.raises(WebSocketDisconnect) as closed:
        with test_client.websocket_connect(stream.PATH + "?t=yanlis") as ws:
            ws.receive_bytes()
    assert closed.value.code == 4403


def test_stream_pushes_frames_with_ack_and_applies_only_fast_events(client):
    test_client, fake = client
    with test_client.websocket_connect(f"{stream.PATH}?t={stream.ticket('tablet1')}") as ws:
        assert ws.receive_bytes() == b"\xff\xd8kare1"
        assert stream.streaming("tablet1")  # sayfa aynı kareyi Streamlit'ten ikinci kez yollamaz
        assert not stream.streaming("tablet2")  # öteki tabletin yedek görüntüsü kesilmez (GPT v3.2 bulgusu)
        fake.frame, fake.frame_count = b"\xff\xd8kare2", 2
        assert ws.receive_bytes() == b"\xff\xd8kare2"
        ws.send_text(json.dumps({"t": "ack"}))
        ws.send_text(json.dumps({"events": [{"t": "click", "v": [10, 20]}, {"t": "save_login"}, {"t": "goto", "v": "x"}]}))
        ws.send_text("bozuk")
        deadline = time.monotonic() + 3
        while not fake.calls and time.monotonic() < deadline:
            time.sleep(0.01)
    # Yalnız dokunuş/kaydırma/yazı akıştan; giriş kaydı ve adres gibi işler Streamlit yolundan (doğrulamalı) gider.
    assert fake.calls == [("click", (10.0, 20.0))]


def test_stream_ticket_is_bound_to_its_session():
    assert stream._client_of(stream.ticket("a1")) == "a1"
    forged = stream.ticket("a1").replace("a1.", "b2.")
    assert stream._client_of(forged) is None and stream._client_of("") is None


def test_stream_disconnect_is_a_clean_close(client, caplog):
    """Tablet kapanınca alıcı görevin istisnası tüketilir; oturumun akış durumu silinir."""
    test_client, _ = client
    with test_client.websocket_connect(f"{stream.PATH}?t={stream.ticket('t3')}") as ws:
        ws.receive_bytes()
    deadline = time.monotonic() + 3
    while "t3" in stream._seen and time.monotonic() < deadline:
        time.sleep(0.01)
    assert "t3" not in stream._seen
    assert "never retrieved" not in caplog.text


def test_watchdog_does_not_restart_during_update():
    """GPT v3.2 bulgusu: güncelleme sırasında bekçi Axion'u yeniden açmasın (guncelle.bat komut satırı)."""
    watchdog = (ROOT / "windows" / "axion_calistir.ps1").read_text()
    assert "guncelle\\.bat" in watchdog and watchdog.count("if (Test-Updating) { break }") == 2


def test_launcher_chain_uses_stream_app_and_watchdog():
    """Kural 8: Windows betikleri ASCII + CRLF. Başlatıcı → bekçi → axion_app.py (akış kanallı uygulama)."""
    for script in (ROOT / "windows").iterdir():
        if script.suffix in {".bat", ".vbs", ".ps1"}:
            data = script.read_bytes()
            assert data.isascii(), script.name
            assert b"\n" not in data.replace(b"\r\n", b""), script.name
    assert "axion_calistir.ps1" in (ROOT / "windows" / "axion_baslat.vbs").read_text()
    watchdog = (ROOT / "windows" / "axion_calistir.ps1").read_text()
    assert "streamlit run axion_app.py" in watchdog and "-Wait" not in watchdog.replace("# -Wait", "")
    assert "axion_app.py" in (ROOT / "windows" / "sorun_giderme.bat").read_text()
    import axion_app

    assert any(getattr(route, "path", None) == stream.PATH for route in axion_app.app._user_routes)
