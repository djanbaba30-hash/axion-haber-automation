"""Elle blur (Faz 5, editör kararı: otomatik tespit yok).

Editör Tasarım Stüdyosu'nda blur kutusu ekler; şekil, güç ve opaklığı ayarlar, videoda sürükleyerek anahtar kareler
koyar. Kutu anahtar kareler arasında doğrusal hareket eder (konum ve boyut). Koordinatlar video alanına göre 0–1.
Son videoda her blur için maske kareleri yazılır; FFmpeg videonun bulanık kopyasını maskeyle bindirir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

SHAPES = {"dikdortgen": "Dikdörtgen", "yuvarlak": "Yuvarlak köşeli", "elips": "Elips"}
MIN_SIZE = 0.02
EDGE_SOFTNESS = 3  # maske kenarı yumuşaklığı (px)


def _number(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(high, max(low, number))


def clean_blurs(raw: Any, duration: float) -> list[dict[str, Any]]:
    """Tarayıcıdan gelen blur listesini doğrular (bozuk kayıtlar atlanır)."""
    blurs = []
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(item, dict):
            continue
        keys = []
        for key in item.get("keys") or []:
            if not isinstance(key, dict):
                continue
            w = _number(key.get("w"), 0.2, MIN_SIZE, 1.0)
            h = _number(key.get("h"), 0.1, MIN_SIZE, 1.0)
            keys.append({
                "t": round(_number(key.get("t"), 0.0, 0.0, duration), 3),
                "x": round(_number(key.get("x"), 0.4, -w + MIN_SIZE, 1 - MIN_SIZE), 4),
                "y": round(_number(key.get("y"), 0.4, -h + MIN_SIZE, 1 - MIN_SIZE), 4),
                "w": round(w, 4),
                "h": round(h, 4),
            })
        if not keys:
            continue
        keys.sort(key=lambda k: k["t"])
        start = round(_number(item.get("start"), 0.0, 0.0, duration), 3)
        end = round(_number(item.get("end"), duration, 0.0, duration), 3)
        if end <= start:
            continue
        shape = item.get("shape") if item.get("shape") in SHAPES else "yuvarlak"
        blurs.append({
            "id": str(item.get("id") or f"blur{index + 1}")[:40],
            "shape": shape,
            "strength": round(_number(item.get("strength"), 6, 1, 10)),
            "opacity": round(_number(item.get("opacity"), 1.0, 0.1, 1.0), 2),
            "start": start,
            "end": end,
            "keys": keys,
        })
    return blurs


def box_at(blur: dict[str, Any], t: float) -> tuple[float, float, float, float]:
    """t anında kutu (x, y, w, h): anahtar kareler arasında doğrusal; ilkinden önce ilki, sonuncudan sonra sonuncusu."""
    keys = blur["keys"]
    if t <= keys[0]["t"]:
        key = keys[0]
        return key["x"], key["y"], key["w"], key["h"]
    for left, right in zip(keys, keys[1:]):
        if left["t"] <= t <= right["t"]:
            span = right["t"] - left["t"]
            p = (t - left["t"]) / span if span > 0 else 1.0
            return tuple(left[k] + (right[k] - left[k]) * p for k in ("x", "y", "w", "h"))  # type: ignore[return-value]
    key = keys[-1]
    return key["x"], key["y"], key["w"], key["h"]


def sigma(blur: dict[str, Any]) -> float:
    """Güç 1–10 → Gauss bulanıklığı (960 px genişlikte)."""
    return 4.0 * blur["strength"]


def mask_state(blur: dict[str, Any], t: float, width: int, height: int) -> tuple | None:
    if not blur["start"] <= t < blur["end"]:
        return None
    x, y, w, h = box_at(blur, t)
    return (round(x * width), round(y * height), round(w * width), round(h * height))


def render_mask(blur: dict[str, Any], state: tuple | None, width: int, height: int) -> Image.Image:
    mask = Image.new("L", (width, height), 0)
    if state is None:
        return mask
    x, y, w, h = state
    value = round(255 * blur["opacity"])
    draw = ImageDraw.Draw(mask)
    box = (x, y, x + max(1, w) - 1, y + max(1, h) - 1)
    if blur["shape"] == "elips":
        draw.ellipse(box, fill=value)
    elif blur["shape"] == "yuvarlak":
        draw.rounded_rectangle(box, radius=round(min(w, h) * 0.25), fill=value)
    else:
        draw.rectangle(box, fill=value)
    return mask.filter(ImageFilter.GaussianBlur(EDGE_SOFTNESS))


def write_mask_sequences(folder: Path, blurs: list[dict[str, Any]], fps: int, total_frames: int, width: int, height: int) -> list[Path]:
    from .template import write_sequence  # döngüsel içe aktarmayı önle

    paths = []
    for number, blur in enumerate(blurs):
        paths.append(write_sequence(
            folder, f"blur{number}", fps, total_frames,
            lambda t, f, b=blur: mask_state(b, t, width, height),
            lambda state, b=blur: render_mask(b, state, width, height),
        ))
    return paths
