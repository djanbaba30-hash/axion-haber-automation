"""Maliyet defteri (v4.0.0-alpha.6): her yapay zekâ çağrısının tahmini maliyeti ve ElevenLabs karakteri.

Projeler 3 günde silinir; günlük/aylık toplam için ayrı, silinmeyen küçük bir defter tutulur (`data/maliyet.jsonl`,
çağrı başına bir satır, ~100 bayt). Maliyetler kullanım sayılarından tahmindir (fiyat tablosu `news_studio/ai/cost.py`
ve `video_studio/modules/visual_analysis.calculate_cost`); faturanın yerini tutmaz.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import date, datetime
from typing import Any

from apps.axion_local.store import data_dir

FILENAME = "maliyet.jsonl"
KINDS = {"haber": "haber metni", "baslik": "başlık yenileme", "seslendirme_metni": "seslendirme metni yenileme",
         "goruntu": "görüntü analizi", "sahne": "sahne seçimi", "ses": "ses (ElevenLabs)"}
_LOCK = threading.Lock()


def add(kind: str, usd: float | None, characters: int = 0, when: datetime | None = None) -> None:
    """Bir çağrıyı deftere yazar; yazılamazsa editörün işi durmaz."""
    line = {"tarih": (when or datetime.now()).isoformat(timespec="seconds"), "tur": kind,
            "usd": round(float(usd or 0.0), 6), **({"karakter": characters} if characters else {})}
    with _LOCK:
        try:
            path = data_dir() / FILENAME
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        except OSError:
            logging.getLogger(__name__).exception("Maliyet defteri yazılamadı")


def _lines() -> list[dict[str, Any]]:
    try:
        text = (data_dir() / FILENAME).read_text(encoding="utf-8")
    except OSError:
        return []
    result = []
    for raw in text.splitlines():
        try:
            result.append(json.loads(raw))
        except ValueError:
            continue
    return result


def totals(today: date | None = None) -> dict[str, dict[str, Any]]:
    """{"gun": {...}, "ay": {...}}: toplam $, tür başına $, çağrı sayısı, ElevenLabs karakteri."""
    today = today or date.today()
    result = {period: {"usd": 0.0, "turler": {}, "cagri": 0, "karakter": 0} for period in ("gun", "ay")}
    for line in _lines():
        try:
            day = datetime.fromisoformat(line["tarih"]).date()
        except (KeyError, ValueError):
            continue
        for period, inside in (("gun", day == today), ("ay", (day.year, day.month) == (today.year, today.month))):
            if not inside:
                continue
            bucket = result[period]
            bucket["usd"] += line.get("usd", 0.0)
            bucket["karakter"] += line.get("karakter", 0)
            if line.get("tur") != "ses":
                bucket["cagri"] += 1
                bucket["turler"][line.get("tur", "?")] = bucket["turler"].get(line.get("tur", "?"), 0.0) + line.get("usd", 0.0)
    return result


def describe(bucket: dict[str, Any]) -> str:
    parts = [f"{KINDS.get(kind, kind)} ${usd:.3f}" for kind, usd in sorted(bucket["turler"].items(), key=lambda i: -i[1])]
    text = f"${bucket['usd']:.3f} · {bucket['cagri']} çağrı"  # ElevenLabs karakteri durum panelinin kendi satırında
    return text + (f" ({', '.join(parts)})" if parts else "")
