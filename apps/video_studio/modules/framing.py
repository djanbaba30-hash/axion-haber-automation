"""Akıllı kadraj: kenarları bulanık/siyah videolarda asıl görüntü alanını bulur (API yok).

DHA dikey çekimleri çoğunlukla yatay (16:9) verir: ortada keskin görüntü, iki yanda bulanık kopyası.
Bulanık ve siyah alanlarda komşu pikseller arası fark çok düşüktür; analiz karelerinin sütun/satır
keskinlik profilinden içerik sınırları bulunur. numpy ve Pillow Streamlit ile birlikte gelir.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from shared.media_models import Region

SAMPLE_SIZE = (480, 270)
SHARP_RATIO = 0.3       # Merkez keskinliğinin bu oranının altı "bulanık/boş" sayılır.
EDGE_PEAK_RATIO = 2.5   # Görüntü/kenar sınır çizgisi merkez keskinliğinin bu katı kadar belirgin olmalı.
GAP_TOLERANCE = 0.03    # İçerikte bu genişliğe kadar düz alan (duvar, gökyüzü şeridi) kesinti sayılmaz.
MIN_MARGIN = 0.06       # Daha dar kenarlar yok sayılır (gürültü).
MAX_ASYMMETRY = 0.05    # Bulanık kenarlar iki yanda yaklaşık eşit olmalı (tek yanda düz alan değil).
SAFETY_INSET = 0.02     # Yumuşak geçişteki son bulanık/siyah çizgi büyütmede görünmesin.
VERTICAL_ASPECTS = (9 / 16, 1.0, 4 / 3)  # Yanları bulanık verilen çekimler: telefon dikey, kare, eski 4:3.
SNAP_TOLERANCE = 0.02
CENTER_TOLERANCE = 0.06


def _profiles(path: Path) -> tuple[np.ndarray, np.ndarray, float]:
    with Image.open(path) as image:
        aspect = image.width / image.height
        gray = np.asarray(image.convert("L").resize(SAMPLE_SIZE), dtype=np.float32)
    energy = np.abs(np.diff(gray, axis=1))[:-1, :] + np.abs(np.diff(gray, axis=0))[:, :-1]
    # Yüzdelik: kenardaki küçük logo/yazı (ör. DHA) sütunu "keskin" göstermesin.
    return np.percentile(energy, 70, axis=0), np.percentile(energy, 70, axis=1), aspect


def _bounds(profile: np.ndarray) -> tuple[float, float]:
    """Keskin bölgenin [başlangıç, bitiş) oranı; simetrik bulanık/boş kenar yoksa (0, 1)."""
    size = len(profile)
    smooth = np.convolve(profile, np.ones(5) / 5, mode="same")
    middle = smooth[int(size * 0.4): int(size * 0.6)]
    reference = float(np.median(middle))
    if reference <= 0:
        return 0.0, 1.0
    threshold = reference * SHARP_RATIO
    gap = max(2, int(size * GAP_TOLERANCE))

    def edge(direction: int) -> int:
        # Merkezden dışa doğru yürü; içerikteki kısa düz alanları (duvar, gökyüzü şeridi) atla.
        last = index = size // 2
        while 0 <= index < size and abs(index - last) <= gap:
            if smooth[index] >= threshold:
                last = index
            index += direction
        return last

    first, last = edge(-1), edge(1)
    # Keskin görüntü ile bulanık kenar arasında genelde belirgin bir çizgi olur; yakındaysa sınırı ona oturt.
    reach = gap * 2
    peak = reference * EDGE_PEAK_RATIO
    inward = [i for i in range(first, min(size, first + reach)) if profile[i] >= peak]
    if inward:
        first = inward[0] + 1
    outward = [i for i in range(last, max(-1, last - reach), -1) if profile[i] >= peak]
    if outward:
        last = outward[0]
    start, end = first / size, (last + 1) / size
    left, right = start, 1.0 - end
    if min(left, right) < MIN_MARGIN or abs(left - right) > MAX_ASYMMETRY:
        return 0.0, 1.0
    # Kenarlar genelde bulanık/boş olmalı (medyan: sınır çizgisi veya tek tük keskin şekil sayılmaz).
    if np.median(profile[:first]) >= threshold or np.median(profile[last + 1:]) >= threshold:
        return 0.0, 1.0
    return start, end


def _snap_to_vertical_aspect(start: float, end: float, frame_aspect: float) -> tuple[float, float]:
    """Yanları bulanık alan, en yakın küçük standart orana (9:16, 1:1, 4:3) daraltılır.

    Bulanık kenar asıl görüntüye yakın yerde az bulanık olduğu için tespit dışa taşar (gerçek DHA videosunda
    %31,7 yerine ~%42). Hata hep "biraz fazla yakınlaştır" yönünde olsun: bulanık kenar asla kadraja girmez.
    """
    width = end - start
    fits = [aspect / frame_aspect for aspect in VERTICAL_ASPECTS if aspect / frame_aspect <= width + SNAP_TOLERANCE]
    if not fits:
        return start, end
    snapped = min(max(fits), width)
    center = (start + end) / 2
    if abs(center - 0.5) <= CENTER_TOLERANCE:
        center = 0.5  # DHA dikey görüntüyü hep ortalar; tespitin tek yana kayması şerit bırakmasın.
    return center - snapped / 2, center + snapped / 2


def detect_content_region(frame_paths: list[Path]) -> Region | None:
    """Karelerdeki asıl görüntü alanı (0–1). Tüm kare doluysa None."""
    profiles = [_profiles(Path(path)) for path in frame_paths if Path(path).exists()]
    if not profiles:
        return None
    x0, x1 = _bounds(np.median([p[0] for p in profiles], axis=0))
    y0, y1 = _bounds(np.median([p[1] for p in profiles], axis=0))
    if (x0, x1, y0, y1) == (0.0, 1.0, 0.0, 1.0):
        return None
    if (y0, y1) == (0.0, 1.0):
        x0, x1 = _snap_to_vertical_aspect(x0, x1, profiles[0][2])
    x0, x1 = (x0, x1) if (x0, x1) == (0.0, 1.0) else (x0 + SAFETY_INSET, x1 - SAFETY_INSET)
    y0, y1 = (y0, y1) if (y0, y1) == (0.0, 1.0) else (y0 + SAFETY_INSET, y1 - SAFETY_INSET)
    x, y = math.floor(x0 * 10_000) / 10_000, math.floor(y0 * 10_000) / 10_000
    # Aşağı yuvarlama: x + width 1'i hiç aşmaz (Region doğrulaması).
    return Region(x=x, y=y, width=math.floor((x1 - x) * 10_000) / 10_000, height=math.floor((y1 - y) * 10_000) / 10_000)
