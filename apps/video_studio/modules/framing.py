"""Akıllı kadraj: kenarları bulanık/siyah videolarda asıl görüntü alanını bulur (API yok).

DHA dikey çekimleri çoğunlukla yatay (16:9) verir: ortada keskin görüntü, iki yanda bulanık kopyası.
Bulanık ve siyah alanlarda komşu pikseller arası fark çok düşüktür; analiz karelerinin sütun/satır
keskinlik profilinden içerik sınırları bulunur. numpy ve Pillow Streamlit ile birlikte gelir.
"""

from __future__ import annotations

import math
import subprocess
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
# DHA net görüntüyü bulanık kopyasının üstüne yapıştırır: sınırda her karede aynı yerde, iki yanda simetrik keskin bir
# dikey çizgi olur. Çizgi sıradan sütunlardan bu kat güçlüyse sınır odur (en-boy tahmini gerekmez; v3.4).
PAIR_RATIO = 8.0
PAIR_SLACK = 2  # piksel: iki çizginin ortaya göre simetri payı
# Sabit kamerada olayın yeri (v4.0, editör: "Heimlich anında şahıslar kenarda kalmış"): Luna'nın özne kutusu tek
# kareden (güvenlik kamerasında masaları/vitrini gösterebilir); olay karede hareketin olduğu yerdedir.
MOTION_SIZE = (160, 90)
MOTION_RATE = 5  # kare/sn
MOTION_PIXEL = 20  # bu kadar değişen piksel "hareket" (sıkıştırma gürültüsü değil)
MOTION_STATIC = 3.0  # kare farkı medyanı bunun altındaysa kamera sabit (üstü elde çekim/kaydırma: hareket her yerde)
MOTION_MIN_SHARE = 0.003  # hareketli piksel payı bunun altındaysa olay yok (boş sokak)
MOTION_MASS = 0.1  # hareketin iki yandan %10'u atılır (tek geçen araç kutuyu büyütmesin)


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


def standard_vertical_region(frame_aspect: float) -> Region:
    """Ortalanmış 9:16 telefon görüntüsü (DHA'nın yanları bulanık verdiği dikey çekimin varsayılan yeri)."""
    width = (9 / 16) / frame_aspect - 2 * SAFETY_INSET
    return Region(x=math.ceil((1 - width) / 2 * 10_000) / 10_000, y=0.0, width=math.floor(width * 10_000) / 10_000, height=1.0)


def _edge_pair(frame_paths: list[Path]) -> tuple[float, float] | None:
    """Yanları bulanık/siyah dolgunun net görüntüyle sınırı (x başlangıç, x bitiş; 0–1) ya da None.

    Editör (v3.4): "blurun bittiği yere kadar kırpsın, daha fazla yakınlaştırmasın". Eski tahmin (en yakın standart
    orana daraltma) 3:4 dikey çekimi 9:16'ya indirip net görüntünün üçte birini kesiyordu.
    """
    grays = []
    for path in frame_paths:
        try:
            with Image.open(path) as image:
                grays.append(np.asarray(image.convert("L"), dtype=np.float32))
        except OSError:
            continue
    if not grays or any(g.shape != grays[0].shape for g in grays):
        return None
    width = grays[0].shape[1]
    profile = np.median([np.abs(np.diff(g, axis=1)).mean(axis=0) for g in grays], axis=0)  # i: i ile i+1 arası
    typical = float(np.median(profile)) or 1e-6
    best = None
    for left in range(max(2, int(width * MIN_MARGIN) - 1), int(width * 0.45)):
        mirror = width - 2 - left
        for right in range(mirror - PAIR_SLACK, mirror + PAIR_SLACK + 1):
            strength = min(profile[left], profile[right])
            if best is None or strength > best[0]:
                best = (strength, left, right)
    if best is None or best[0] < PAIR_RATIO * typical:
        return None
    _, left, right = best
    inside = float(profile[left + 3:right - 2].mean())
    outside = float(np.concatenate([profile[:max(0, left - 2)], profile[right + 3:]]).mean())
    if outside >= 0.5 * inside:  # kenarlar içeriden belirgin daha düz olmalı (bulanık/siyah)
        return None
    return (left + 2) / width, right / width  # 1 piksel içeride: JPEG'in sınırdaki halkası görünmesin


def detect_content_region(frame_paths: list[Path]) -> Region | None:
    """Karelerdeki asıl görüntü alanı (0–1). Tüm kare doluysa None."""
    pair = _edge_pair([Path(path) for path in frame_paths if Path(path).exists()])
    if pair is not None:
        x0, x1 = pair
        x = math.ceil(x0 * 10_000) / 10_000
        return Region(x=x, y=0.0, width=math.floor((x1 - x) * 10_000) / 10_000, height=1.0)
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


def motion_from_frames(frames: np.ndarray) -> Region | None:
    """Gri karelerden (sayı, yükseklik, genişlik) hareket bölgesi (0–1): kamera sabitse ve karede hareket varsa."""
    if len(frames) < 3:
        return None
    diff = np.abs(np.diff(frames.astype(np.float32), axis=0))
    if float(np.median(diff.mean((1, 2)))) > MOTION_STATIC:
        return None
    moving = (diff > MOTION_PIXEL).sum(0).astype(np.float64)
    if moving.sum() < MOTION_MIN_SHARE * diff.size:
        return None

    def span(profile: np.ndarray) -> tuple[float, float]:
        share = np.cumsum(profile) / profile.sum()
        return (float(np.searchsorted(share, MOTION_MASS)) / len(profile),
                float(np.searchsorted(share, 1 - MOTION_MASS) + 1) / len(profile))

    (x0, x1), (y0, y1) = span(moving.sum(0)), span(moving.sum(1))
    x, y = math.floor(x0 * 10_000) / 10_000, math.floor(y0 * 10_000) / 10_000
    return Region(x=x, y=y, width=math.floor((min(x1, 1.0) - x) * 10_000) / 10_000,
                  height=math.floor((min(y1, 1.0) - y) * 10_000) / 10_000)


def motion_region(video: Path, start: float, end: float) -> Region | None:
    """Videonun [start, end] aralığında sabit kamerada hareketin olduğu bölge (API yok; proxy'den, pencere başına
    ~0,3 sn). Okunamazsa None (kadraj Luna'nın kutusuyla kalır)."""
    width, height = MOTION_SIZE
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{max(0.1, end - start):.3f}", "-i", str(video),
             "-vf", f"fps={MOTION_RATE},scale={width}:{height},format=gray", "-f", "rawvideo", "-"],
            capture_output=True, timeout=120,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    frames = np.frombuffer(raw, np.uint8)
    return motion_from_frames(frames[: len(frames) // (width * height) * width * height].reshape(-1, height, width))
