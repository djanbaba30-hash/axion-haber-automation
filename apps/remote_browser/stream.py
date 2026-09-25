"""Tarayıcı ekranının doğrudan akışı (WebSocket): kareler Chrome ürettiği anda tablete gider, dokunuşlar doğrudan gelir.

Streamlit'in yeniden çalıştırma turunu beklemez (v3.1'de kare başına bir tur, ~4 kare/sn). `axion_app.py` bu uç noktayı
`st.App`'e ekler. Yetki: jeton yalnızca Axion'a girmiş (APP_PASSWORD'u geçmiş) sayfaya verilir. Jeton oturuma bağlıdır
(`ticket(client)`): "akış açık mı" her tablet için ayrı bilinir; bir tabletin akışı ötekinin yedek görüntüsünü kesmez.
Akış kurulamazsa (eski başlatıcı, ağ sorunu) sayfa Streamlit üzerinden yenilenmeye devam eder.

Akış denetimi: tablet her kareyi gösterince "ack" yollar; en fazla 2 kare yolda olur, arada gelenler atlanır. Yavaş
internette gecikme birikmez, yalnız kare sayısı düşer.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from starlette.websockets import WebSocketDisconnect

from . import service
from .viewer import apply_events

PATH = "/axion/tarayici/akis"
_SECRET = secrets.token_bytes(32)  # süreç başına; jetonlar bununla imzalanır
FAST_EVENTS = {"click", "wheel", "type", "key"}  # uygulamayı ilgilendirenler (giriş kaydı, indirme) Streamlit'ten gider
IN_FLIGHT = 2
POLL_SECONDS = 0.012
_seen: dict[str, float] = {}  # oturum → son kare zamanı


def _sign(client: str) -> str:
    return hmac.new(_SECRET, client.encode(), hashlib.sha256).hexdigest()[:32]


def ticket(client: str) -> str:
    """Bu oturumun akış jetonu (sayfa bileşene verir)."""
    return f"{client}.{_sign(client)}"


def _client_of(token: str) -> str | None:
    client, _, signature = token.rpartition(".")
    return client if client and hmac.compare_digest(signature, _sign(client)) else None


def streaming(client: str) -> bool:
    """Bu oturumun tableti şu an akıştan kare alıyor mu (sayfa o zaman aynı kareyi Streamlit'ten yollamaz)."""
    return time.monotonic() - _seen.get(client, 0.0) < 2.0


def _events(message: Any) -> list[dict[str, Any]]:
    events = message.get("events") if isinstance(message, dict) else None
    return [e for e in events if isinstance(e, dict) and e.get("t") in FAST_EVENTS] if isinstance(events, list) else []


async def endpoint(websocket) -> None:
    client = _client_of(websocket.query_params.get("t", ""))
    if client is None:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    credit = IN_FLIGHT

    async def receive() -> None:
        nonlocal credit
        while True:
            try:
                message = json.loads(await websocket.receive_text())
            except WebSocketDisconnect:
                return  # tablet kapandı: normal kapanış
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("t") == "ack":
                credit = min(IN_FLIGHT, credit + 1)
                continue
            browser = service.current()
            events = _events(message)
            if browser is not None and events:
                await asyncio.to_thread(apply_events, browser, events, None, "")

    reader = asyncio.create_task(receive())
    sent = -1
    try:
        while not reader.done():
            browser = service.current()
            frame = browser.latest_frame() if browser is not None else None
            if frame is not None:
                _seen[client] = time.monotonic()
                if credit > 0 and browser.frame_count != sent:
                    sent = browser.frame_count
                    credit -= 1
                    await websocket.send_bytes(frame)
            await asyncio.sleep(POLL_SECONDS)
    except Exception:  # noqa: BLE001 — bağlantı koptu: tablet yeniden bağlanır
        pass
    finally:
        reader.cancel()
        # Görevin sonucunu/istisnasını tüket ("Task exception was never retrieved" günlüğe düşmesin).
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await reader
        _seen.pop(client, None)
