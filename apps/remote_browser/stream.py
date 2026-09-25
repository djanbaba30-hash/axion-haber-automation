"""Tarayıcı ekranının doğrudan akışı (WebSocket): kareler Chrome ürettiği anda tablete gider, dokunuşlar doğrudan gelir.

Streamlit'in yeniden çalıştırma turunu beklemez (v3.1'de kare başına bir tur, ~4 kare/sn). `axion_app.py` bu uç noktayı
`st.App`'e ekler. Yetki: jeton yalnızca Axion'a girmiş (APP_PASSWORD'u geçmiş) sayfaya verilir. Akış kurulamazsa
(eski başlatıcı, ağ sorunu) sayfa Streamlit üzerinden yenilenmeye devam eder.

Akış denetimi: tablet her kareyi gösterince "ack" yollar; en fazla 2 kare yolda olur, arada gelenler atlanır. Yavaş
internette gecikme birikmez, yalnız kare sayısı düşer.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from typing import Any

from . import service
from .viewer import apply_events

PATH = "/axion/tarayici/akis"
TOKEN = secrets.token_urlsafe(24)  # süreç başına; sayfa bileşene verir
FAST_EVENTS = {"click", "wheel", "type", "key"}  # uygulamayı ilgilendirenler (giriş kaydı, indirme) Streamlit'ten gider
IN_FLIGHT = 2
POLL_SECONDS = 0.012
_last_stream = 0.0


def streaming() -> bool:
    """Bir tablet şu an akıştan kare alıyor mu (sayfa o zaman aynı kareyi Streamlit'ten yollamaz)."""
    return time.monotonic() - _last_stream < 2.0


def _events(message: Any) -> list[dict[str, Any]]:
    events = message.get("events") if isinstance(message, dict) else None
    return [e for e in events if isinstance(e, dict) and e.get("t") in FAST_EVENTS] if isinstance(events, list) else []


async def endpoint(websocket) -> None:
    global _last_stream
    if not secrets.compare_digest(websocket.query_params.get("t", ""), TOKEN):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    credit = IN_FLIGHT

    async def receive() -> None:
        nonlocal credit
        while True:
            try:
                message = json.loads(await websocket.receive_text())
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
                _last_stream = time.monotonic()
                if credit > 0 and browser.frame_count != sent:
                    sent = browser.frame_count
                    credit -= 1
                    await websocket.send_bytes(frame)
            await asyncio.sleep(POLL_SECONDS)
    except Exception:  # noqa: BLE001 — bağlantı koptu: tablet yeniden bağlanır
        pass
    finally:
        reader.cancel()
