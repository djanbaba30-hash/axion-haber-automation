"""Durum paneli (v4.0.0-alpha.6, Geliştirici bilgileri): disk, ElevenLabs kalan karakter, FFmpeg ve kodlayıcı,
bugünün ve bu ayın yapay zekâ maliyeti. ElevenLabs sorgusu ücretsizdir (abonelik bilgisi; karakter harcamaz) ve
10 dakikada bir yapılır; okunamazsa panel yine açılır, nedeni açıkça yazar (v4.1: ör. anahtarda "User → Read" izni
yok) ve Axion'un bugün/bu ay harcadığı karakter (maliyet defteri) her durumda görünür.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from apps.axion_local import ledger
from apps.axion_local.store import data_dir

ELEVENLABS_TTL = 600
_ELEVENLABS: dict[str, tuple[float, dict[str, Any]]] = {}  # anahtar → (zaman, sonuç)
_ELEVENLABS_RUNNING: dict[str, threading.Thread] = {}
_ELEVENLABS_LOCK = threading.Lock()
LOW_DISK_GB = 10


def _folder_size(folder: Path) -> int:
    total = 0
    for path in folder.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def disk() -> dict[str, float]:
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(folder)
    projects = folder / "projects"
    return {"bos_gb": usage.free / 1e9, "toplam_gb": usage.total / 1e9,
            "projeler_gb": _folder_size(projects) / 1e9 if projects.is_dir() else 0.0}


@lru_cache(maxsize=1)
def ffmpeg() -> dict[str, Any]:
    """FFmpeg sürümü ve AMD donanım kodlayıcısı (Axion açıkken değişmez: bir kez sorulur)."""
    from apps.video_studio.modules.render import amd_encoder_available

    try:
        first = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=15).stdout.splitlines()[0]
        version = first.split(" Copyright")[0].replace("ffmpeg version ", "")
    except (OSError, subprocess.SubprocessError, IndexError):
        version = None
    return {"surum": version, "ffprobe": shutil.which("ffprobe") is not None,
            "amd": amd_encoder_available() if version else False}


def _query(api_key: str, client: Any = None) -> dict[str, Any]:
    try:
        if client is None:
            from elevenlabs.client import ElevenLabs

            client = ElevenLabs(api_key=api_key, timeout=10)
        subscription = client.user.subscription.get()
        reset = subscription.next_character_count_reset_unix
        return {"kullanilan": subscription.character_count, "sinir": subscription.character_limit,
                "kalan": max(0, subscription.character_limit - subscription.character_count),
                "yenilenme": datetime.fromtimestamp(reset).strftime("%d.%m.%Y") if reset else None}
    except Exception as error:  # noqa: BLE001 — ağ, yetkisiz anahtar: panel yine açılsın
        from apps.news_studio.tts.service import error_message

        return {"hata": error_message(error)}


def elevenlabs(api_key: str | None, client: Any = None, now: float | None = None, wait: bool = False) -> dict[str, Any]:
    """Kalan karakter ve yenilenme günü; hata olursa {"hata": ...}. 10 dk önbellekli; eskiyse arka planda yenilenir
    (sayfa beklemez, yeni sonuç bir sonraki çizimde). `wait`: sonucu bekle (testler)."""
    if not api_key:
        return {"hata": "ELEVENLABS_API_KEY yok"}
    now = time.time() if now is None else now
    with _ELEVENLABS_LOCK:
        cached = _ELEVENLABS.get(api_key)
        fresh = cached is not None and now - cached[0] < ELEVENLABS_TTL
        running = _ELEVENLABS_RUNNING.get(api_key)
        if not fresh and not (running and running.is_alive()):
            def refresh() -> None:
                result = _query(api_key, client)
                with _ELEVENLABS_LOCK:
                    _ELEVENLABS[api_key] = (now, result)

            running = threading.Thread(target=refresh, daemon=True, name="axion-elevenlabs")
            _ELEVENLABS_RUNNING[api_key] = running
            running.start()
    if wait and running is not None:
        running.join(timeout=15)
    with _ELEVENLABS_LOCK:
        cached = _ELEVENLABS.get(api_key)
    return cached[1] if cached else {"hata": "sorgulanıyor, birazdan görünür"}


def lines(api_key: str | None) -> list[str]:
    """Panelin satırları (Markdown)."""
    rows = []
    space = disk()
    warn = "⚠️ " if space["bos_gb"] < LOW_DISK_GB else ""
    rows.append(f"{warn}**Disk:** {space['bos_gb']:.0f} GB boş / {space['toplam_gb']:.0f} GB · projeler "
                f"{space['projeler_gb']:.2f} GB (3 günde silinir)")
    spent = ledger.totals()
    today, month = (f"{spent[period]['karakter']:,}".replace(",", ".") for period in ("gun", "ay"))
    used = f"Axion bugün {today}, bu ay {month} karakter harcadı"
    voice = elevenlabs(api_key)
    if "hata" in voice:
        rows.append(f"**ElevenLabs:** kalan karakter okunamadı: {voice['hata']} · {used}")
    else:
        warn = "⚠️ " if voice["kalan"] < 0.1 * max(1, voice["sinir"]) else ""
        renewal = f" · yenilenme {voice['yenilenme']}" if voice["yenilenme"] else ""
        rows.append(f"{warn}**ElevenLabs:** {voice['kalan']:,} karakter kaldı / {voice['sinir']:,}".replace(",", ".")
                    + f"{renewal} · {used}")
    tools = ffmpeg()
    if tools["surum"]:
        encoder = "AMD donanım (h264_amf)" if tools["amd"] else "işlemci (x264)"
        rows.append(f"**FFmpeg:** {tools['surum']} · kodlayıcı {encoder}" + ("" if tools["ffprobe"] else " · ⚠️ FFprobe yok"))
    else:
        rows.append("⚠️ **FFmpeg:** bulunamadı (video üretilemez)")
    rows.append(f"**Bugün:** {ledger.describe(spent['gun'])}")
    rows.append(f"**Bu ay:** {ledger.describe(spent['ay'])}")
    return rows


def render(api_key: str | None) -> None:
    """Geliştirici bilgileri'nin başında (çağıranın bölümüne) çizilir."""
    import streamlit as st

    with st.container(border=True):
        st.markdown("**🩺 Durum ve maliyet**")
        st.markdown("  \n".join(lines(api_key)))
        st.caption("Maliyet tahmindir (kullanım sayıları × fiyat tablosu). ElevenLabs aboneliğe dahil: karakter sayılır.")
