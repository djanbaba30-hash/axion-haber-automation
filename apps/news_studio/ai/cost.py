"""Haber başına tahmini maliyet ve önbellek durumu (API yok; kullanım sayılarından).

Fiyatlar ($ / 1M token) 2026-09-25'te kontrol edildi; değişirse burayı güncelle:
- OpenAI GPT-5.6: Luna 0,20 girdi / 1,20 çıktı; Sol 4 / 20 (Sol'da kampanya fiyatı, en az 2026-11-21'e kadar).
  Önbellekten okuma girdinin 0,1 katı, önbelleğe yazma 1,25 katı (ikincil kaynaklar; developers.openai.com bu
  ortamdan açılmadı). Önbellek süresi: GPT-5.6'da `prompt_cache_options.ttl` varsayılanı ve tek değeri "30m" (en az
  30 dk; openai SDK 3.15 tanımı). 24 saatlik saklama (`prompt_cache_retention`) 5.6'da yok.
- Claude Sonnet 5: 2 girdi / 10 çıktı; okuma 0,1 katı, 1 saatlik yazma 2 katı (platform.claude.com prompt caching).
  En az önbelleklenebilir uzunluk 1.024 token (Sonnet 5); haber sistem komutu ~1.700 token, başlık komutu altında kalır.
Kullanım alanları: OpenAI `input_tokens` önbellekten okunanı ve yazılanı içerir, Claude içermez. Düşünme token'ı
çıktı token'ının içindedir (ayrıca eklenmez).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

PRICES_CHECKED = "2026-09-25"
PRICES = {  # model: (girdi, önbellekten okuma, önbelleğe yazma, çıktı) $ / 1M token
    "gpt-5.6-luna": (0.20, 0.02, 0.25, 1.20),
    "gpt-5.6-sol": (4.00, 0.40, 5.00, 20.00),
    "claude-sonnet-5": (2.00, 0.20, 4.00, 10.00),
}
CACHE_MINUTES = {"OpenAI": 30, "Claude": 60}
CACHE_FILENAME = "onbellek.json"


def cost_usd(usage: dict[str, Any]) -> float | None:
    prices = PRICES.get(usage.get("model", ""))
    if prices is None:
        return None
    base, read, write, out = prices
    cached, written = usage.get("cached_input_tokens", 0), usage.get("cache_creation_input_tokens", 0)
    uncached = usage.get("input_tokens", 0)
    if usage.get("provider") == "OpenAI":
        uncached = max(0, uncached - cached - written)
    return (uncached * base + cached * read + written * write + usage.get("output_tokens", 0) * out) / 1_000_000


def cache_share(usage: dict[str, Any]) -> float:
    """Girdinin ne kadarı önbellekten geldi (0–1)."""
    cached = usage.get("cached_input_tokens", 0)
    total = usage.get("input_tokens", 0)
    if usage.get("provider") != "OpenAI":
        total += cached + usage.get("cache_creation_input_tokens", 0)
    return cached / total if total else 0.0


def _read(folder: Path) -> dict[str, float]:
    try:
        data = json.loads((folder / CACHE_FILENAME).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def touch(folder: Path, usage: dict[str, Any], now: float | None = None) -> None:
    """Haber sistem komutu önbelleğe yazıldı ya da okundu: süre baştan başlar. İkisi de 0 ise önbellek tutmadı."""
    if not (usage.get("cached_input_tokens") or usage.get("cache_creation_input_tokens")):
        return
    data = _read(folder)
    data[f"{usage.get('provider')}|{usage.get('model')}"] = time.time() if now is None else now
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CACHE_FILENAME).write_text(json.dumps(data), encoding="utf-8")


def minutes_left(folder: Path, provider: str, model: str, now: float | None = None) -> int:
    """Tahmini kalan önbellek süresi (dk); 0 = soğuk. Sunucudan doğrulanmış değil: son kullanım + süre."""
    last = _read(folder).get(f"{provider}|{model}")
    if not last:
        return 0
    left = CACHE_MINUTES.get(provider, 0) - ((time.time() if now is None else now) - last) / 60
    return max(0, int(left))
