"""Elle blur ve mozaik (editör kararı: otomatik tespit yok).

Editör Tasarım Stüdyosu'nda kutu ekler: efekt (bulanık/mozaik), şekil (dikdörtgen–kare, yuvarlak köşeli, elips–daire),
güç, opaklık ve kenar yumuşaklığı. Videoyu bir ana getirip kutuyu taşır, boyutlandırır, döndürür: o an bir anahtar
kare olur; kutu anahtar kareler arasında doğrusal hareket eder (konum, boyut, açı). Koordinatlar video alanına göre 0–1.
Son videoda her kutu için maske kareleri yazılır; FFmpeg videonun yalnızca kutunun geçtiği bölgesini (tüm süre
boyunca kapladığı alan + bulanıklık payı) bulanıklaştırır/mozaikler ve maskeyle bindirir (tüm kareyi işlemek çok yavaş).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

SHAPES = {"dikdortgen": "Dikdörtgen / kare", "yuvarlak": "Yuvarlak köşeli", "elips": "Elips / daire"}
EFFECTS = {"blur": "Bulanık", "mozaik": "Mozaik"}
MIN_SIZE = 0.02


def _number(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:  # NaN
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
            w = _number(key.get("w"), 0.2, MIN_SIZE, 1.5)
            h = _number(key.get("h"), 0.1, MIN_SIZE, 1.5)
            keys.append({
                "t": round(_number(key.get("t"), 0.0, 0.0, duration), 3),
                "x": round(_number(key.get("x"), 0.4, -w + MIN_SIZE, 1 - MIN_SIZE), 4),
                "y": round(_number(key.get("y"), 0.4, -h + MIN_SIZE, 1 - MIN_SIZE), 4),
                "w": round(w, 4),
                "h": round(h, 4),
                "r": round(_number(key.get("r"), 0.0, -3600, 3600), 2),
            })
        if not keys:
            continue
        keys.sort(key=lambda k: k["t"])
        start = round(_number(item.get("start"), 0.0, 0.0, duration), 3)
        end = round(_number(item.get("end"), duration, 0.0, duration), 3)
        if end <= start:
            continue
        blurs.append({
            "id": str(item.get("id") or f"blur{index + 1}")[:40],
            "effect": item.get("effect") if item.get("effect") in EFFECTS else "blur",
            "shape": item.get("shape") if item.get("shape") in SHAPES else "yuvarlak",
            "strength": round(_number(item.get("strength"), 6, 1, 10)),
            "opacity": round(_number(item.get("opacity"), 1.0, 0.1, 1.0), 2),
            "feather": round(_number(item.get("feather"), 0.3, 0.0, 1.0), 2),
            "start": start,
            "end": end,
            "keys": keys,
        })
    return blurs


def box_at(blur: dict[str, Any], t: float) -> tuple[float, float, float, float, float]:
    """t anında kutu (x, y, w, h, açı°): anahtar kareler arasında doğrusal; ilkinden önce ilki, sonra sonuncusu."""
    fields = ("x", "y", "w", "h", "r")
    keys = blur["keys"]
    if t <= keys[0]["t"]:
        return tuple(keys[0].get(k, 0.0) for k in fields)  # type: ignore[return-value]
    for left, right in zip(keys, keys[1:]):
        if left["t"] <= t <= right["t"]:
            span = right["t"] - left["t"]
            p = (t - left["t"]) / span if span > 0 else 1.0
            return tuple(left.get(k, 0.0) + (right.get(k, 0.0) - left.get(k, 0.0)) * p for k in fields)  # type: ignore[return-value]
    return tuple(keys[-1].get(k, 0.0) for k in fields)  # type: ignore[return-value]


def sigma(blur: dict[str, Any]) -> float:
    """Bulanık: güç 1–10 → Gauss bulanıklığı (960 px genişlikte)."""
    return 4.0 * blur["strength"]


def mosaic_block(blur: dict[str, Any]) -> int:
    """Mozaik: güç 1–10 → kare boyutu (px)."""
    return 6 + 4 * int(blur["strength"])


def feather_px(blur: dict[str, Any], w: float, h: float) -> float:
    """Kenar yumuşaklığı: 0 keskin, 1 kutunun yarısı boyunca tamamen solar."""
    return blur.get("feather", 0.0) * min(w, h) / 2


def mask_state(blur: dict[str, Any], t: float, width: int, height: int) -> tuple | None:
    if not blur["start"] <= t < blur["end"]:
        return None
    x, y, w, h, r = box_at(blur, t)
    return (round(x * width), round(y * height), max(1, round(w * width)), max(1, round(h * height)), round(r, 1))


def shape_mask(shape: str, w: int, h: int, value: int, feather: float) -> Image.Image:
    """Kutunun kendi maskesi (dönmeden önce); yumuşak kenar içeri doğru solar."""
    inset = round(feather / 2)
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    box = (inset, inset, max(inset, w - 1 - inset), max(inset, h - 1 - inset))
    if shape == "elips":
        draw.ellipse(box, fill=value)
    elif shape == "yuvarlak":
        draw.rounded_rectangle(box, radius=round(min(w, h) * 0.25), fill=value)
    else:
        draw.rectangle(box, fill=value)
    radius = max(1.0, feather / 2)
    return mask.filter(ImageFilter.GaussianBlur(radius))


def render_mask(blur: dict[str, Any], state: tuple | None, width: int, height: int, origin: tuple[int, int] = (0, 0)) -> Image.Image:
    """Maske (width x height); `origin` maskenin video alanındaki sol üstü (bölge kırpılınca)."""
    mask = Image.new("L", (width, height), 0)
    if state is None:
        return mask
    x, y, w, h, angle = state
    local = shape_mask(blur["shape"], w, h, round(255 * blur["opacity"]), feather_px(blur, w, h))
    if angle:
        local = local.rotate(-angle, resample=Image.BICUBIC, expand=True)  # açı saat yönünde
    cx, cy = x + w / 2 - origin[0], y + h / 2 - origin[1]
    mask.paste(local, (round(cx - local.width / 2), round(cy - local.height / 2)))
    return mask


def _margin(blur: dict[str, Any]) -> int:
    """Bölgenin kutudan taşma payı: bulanıklık kenardan içeri görüntü çeker; mozaikte bir kare."""
    return mosaic_block(blur) if blur["effect"] == "mozaik" else math.ceil(3 * sigma(blur))


def blur_region(blur: dict[str, Any], fps: int, total_frames: int, width: int, height: int) -> tuple[int, int, int, int] | None:
    """Kutunun görünür olduğu tüm kareleri kapsayan bölge (x, y, w, h; çift sayılar, mozaikte kare ızgarasına oturur).

    Kutu hiç görünmüyorsa None (o blur son videoya hiç eklenmez).
    """
    left = top = math.inf
    right = bottom = -math.inf
    for frame in range(total_frames):
        state = mask_state(blur, frame / fps, width, height)
        if state is None:
            continue
        x, y, w, h, angle = state
        a = math.radians(angle)
        half_w = (w * abs(math.cos(a)) + h * abs(math.sin(a))) / 2 + 1
        half_h = (w * abs(math.sin(a)) + h * abs(math.cos(a))) / 2 + 1
        cx, cy = x + w / 2, y + h / 2
        left, right = min(left, cx - half_w), max(right, cx + half_w)
        top, bottom = min(top, cy - half_h), max(bottom, cy + half_h)
    if left == math.inf:
        return None
    margin = _margin(blur)
    step = mosaic_block(blur) if blur["effect"] == "mozaik" else 2  # mozaik kareleri video alanının ızgarasında kalsın
    x0 = max(0, int(left - margin) // step * step)
    y0 = max(0, int(top - margin) // step * step)
    x1 = min(width, -(-math.ceil(right + margin) // step) * step)
    y1 = min(height, -(-math.ceil(bottom + margin) // step) * step)
    x1, y1 = x1 - (x1 - x0) % 2, y1 - (y1 - y0) % 2  # 4:2:0 çift boyut ister
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return x0, y0, x1 - x0, y1 - y0


@dataclass
class BlurPass:
    """Son videoda tek blur/mozaik: ayarları, maske kareleri (bölge boyutunda) ve video alanındaki bölgesi."""

    blur: dict[str, Any]
    mask: Path
    region: tuple[int, int, int, int]


def write_mask_sequences(folder: Path, blurs: list[dict[str, Any]], fps: int, total_frames: int, width: int, height: int) -> list[BlurPass]:
    from .template import write_sequence  # döngüsel içe aktarmayı önle

    passes = []
    for number, blur in enumerate(blurs):
        region = blur_region(blur, fps, total_frames, width, height)
        if region is None:
            continue
        path = write_sequence(
            folder, f"blur{number}", fps, total_frames,
            lambda t, f, b=blur: mask_state(b, t, width, height),
            lambda state, b=blur, r=region: render_mask(b, state, r[2], r[3], (r[0], r[1])),
        )
        passes.append(BlurPass(blur, path, region))
    return passes
