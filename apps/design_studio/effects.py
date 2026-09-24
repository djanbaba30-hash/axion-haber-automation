"""Tasarım Stüdyosu efekt kütüphanesi: yazı giriş/çıkış animasyonları, slogan ve logo efektleri, çerçeve stilleri.

Her efekt seçilebilir veya "Yok" ile kapatılabilir. Aynı formüller tarayıcı önizlemesinde (editor.py, JS) de var;
son video bu dosyadaki Python hesabıyla üretilir. Süreler saniye, mesafeler 1080x1920 kanvas pikseli.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from shared.axion_template import FRAME_BORDER, FRAME_RADIUS, VIDEO_SLOT

TEXT_ENTER = {"merge": "Birleşerek", "fade": "Belirerek", "slide": "Alttan kayarak", "typewriter": "Daktilo", "pop": "Büyüyerek", "yok": "Yok"}
TEXT_EXIT = {"merge": "Birleşerek", "fade": "Solarak", "slide": "Yukarı kayarak", "pop": "Küçülerek", "yok": "Yok"}
SLOGAN_EFFECTS = {"old_tv": "Eski TV", "fade": "Belirerek", "pop": "Büyüyerek", "yok": "Yok"}
LOGO_EFFECTS = {"slow_baseline": "Alttan yükselip iner", "fade": "Belirerek", "pop": "Büyüyerek", "yok": "Yok"}
FRAME_STYLES = {"sabit": "Sabit beyaz çizgi", "kovalayan": "Kovalayan ışıklar", "nefes": "Nefes alan parıltı", "akis": "Renk akışı", "yok": "Çizgi yok"}


def clamp(p: float) -> float:
    return min(1.0, max(0.0, p))


def ease_out(p: float) -> float:
    return 1 - (1 - clamp(p)) ** 3


def ease_in(p: float) -> float:
    return clamp(p) ** 3


def ease_out_back(p: float) -> float:
    p = clamp(p)
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


@dataclass
class WordState:
    alpha: float = 1.0
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class BlockState:
    words: list[WordState]
    scale: float = 1.0  # blok ortasına göre


# --- Yazı giriş/çıkış ---------------------------------------------------------------------------------------------

MERGE_STAGGER, MERGE_LINE_GAP, MERGE_FADE, MERGE_SLIDE, MERGE_MOVE = 0.045, 0.1, 0.12, 24.0, 0.6
MERGE_EXIT_SECONDS, MERGE_EXIT_SLIDE = 0.26, 13.0


def _merge_delays(lines: list[int]) -> list[float]:
    """"merge" girişi: 1. satır sağdan sola, sonraki satırlar soldan sağa; satır arası kısa bekleme (Canva örneği)."""
    order: list[int] = []
    for line in sorted(set(lines)):
        indexes = [i for i, value in enumerate(lines) if value == line]
        order += list(reversed(indexes)) if line == 0 else indexes
    stagger = min(MERGE_STAGGER, 0.55 / max(1, len(order)))
    delays = [0.0] * len(lines)
    delay, previous = 0.0, (lines[order[0]] if order else 0)
    for index in order:
        if lines[index] != previous:
            delay += MERGE_LINE_GAP
            previous = lines[index]
        delays[index] = delay
        delay += stagger
    return delays


def _stagger(count: int, step: float, limit: float) -> float:
    return min(step, limit / max(1, count))


def enter_seconds(effect: str, lines: list[int]) -> float:
    n = len(lines)
    if effect == "merge":
        return max(_merge_delays(lines), default=0.0) + MERGE_MOVE
    if effect == "fade":
        return 0.4
    if effect == "slide":
        return _stagger(n, 0.06, 0.5) * max(0, n - 1) + 0.45
    if effect == "typewriter":
        return _stagger(n, 0.11, 1.2) * n
    if effect == "pop":
        return 0.35
    return 0.0


def exit_seconds(effect: str, lines: list[int]) -> float:
    n = len(lines)
    if effect == "merge":
        return MERGE_EXIT_SECONDS
    if effect == "fade":
        return 0.35
    if effect == "slide":
        return _stagger(n, 0.03, 0.2) * max(0, n - 1) + 0.35
    if effect == "pop":
        return 0.25
    return 0.0


def enter_state(effect: str, lines: list[int], t: float) -> BlockState:
    """Girişin t. saniyesi (0 = giriş başı) için kelime durumları."""
    n = len(lines)
    if effect == "merge":
        states = []
        for line, delay in zip(lines, _merge_delays(lines)):
            local = t - delay
            direction = 1 if line == 0 else -1
            states.append(WordState(clamp(local / MERGE_FADE), direction * MERGE_SLIDE * (1 - ease_out(local / MERGE_MOVE))))
        return BlockState(states)
    if effect == "fade":
        return BlockState([WordState(ease_out(t / 0.4)) for _ in range(n)])
    if effect == "slide":
        step = _stagger(n, 0.06, 0.5)
        return BlockState([
            WordState(clamp((t - i * step) / 0.2), 0.0, 36 * (1 - ease_out((t - i * step) / 0.45))) for i in range(n)
        ])
    if effect == "typewriter":
        step = _stagger(n, 0.11, 1.2)
        return BlockState([WordState(1.0 if t >= i * step else 0.0) for i in range(n)])
    if effect == "pop":
        return BlockState([WordState(clamp(t / 0.15)) for _ in range(n)], 0.6 + 0.4 * ease_out_back(t / 0.35))
    return BlockState([WordState() for _ in range(n)])


def exit_state(effect: str, lines: list[int], t: float) -> BlockState:
    """Çıkışın t. saniyesi (0 = çıkış başı) için kelime durumları."""
    n = len(lines)
    if effect == "merge":
        p = t / MERGE_EXIT_SECONDS
        dx = -MERGE_EXIT_SLIDE * ease_in(p)
        return BlockState([
            WordState(1 - clamp((p - 0.35) / 0.2) if line == 0 else 1 - ease_in((p - 0.55) / 0.45), dx) for line in lines
        ])
    if effect == "fade":
        return BlockState([WordState(1 - ease_in(t / 0.35)) for _ in range(n)])
    if effect == "slide":
        step = _stagger(n, 0.03, 0.2)
        return BlockState([
            WordState(1 - clamp((t - i * step) / 0.35), 0.0, -30 * ease_in((t - i * step) / 0.35)) for i in range(n)
        ])
    if effect == "pop":
        p = t / 0.25
        return BlockState([WordState(1 - clamp(p)) for _ in range(n)], 1 - 0.3 * ease_in(p))
    return BlockState([WordState(0.0) for _ in range(n)])


def text_state(enter: str, exit: str, lines: list[int], start: float, end: float, t: float) -> BlockState | None:
    """Görünür aralığı [start, end) olan yazının t anındaki durumu; görünmüyorsa None. Çıkış `end`'de biter."""
    if t < start or t >= end:
        return None
    exit_len = min(exit_seconds(exit, lines), max(0.0, end - start))
    if t >= end - exit_len:
        return exit_state(exit, lines, t - (end - exit_len))
    if t - start < enter_seconds(enter, lines):
        return enter_state(enter, lines, t - start)
    return BlockState([WordState() for _ in lines])


def state_key(state: BlockState | None) -> tuple | None:
    """Aynı görüntü = aynı anahtar (sabit anlar tek kare yazılır)."""
    if state is None:
        return None
    return (round(state.scale, 3), tuple((round(w.alpha, 3), round(w.dx, 1), round(w.dy, 1)) for w in state.words))


# --- Sloganlar -----------------------------------------------------------------------------------------------------

SLOGAN_IN = {"old_tv": 0.56, "fade": 0.3, "pop": 0.35, "yok": 0.0}
SLOGAN_OUT = {"old_tv": 0.23, "fade": 0.3, "pop": 0.2, "yok": 0.0}


def old_tv_scale(openness: float) -> tuple[float, float]:
    """Açıklık (0 kapalı .. 1 tam) → (yatay, dikey) ölçek: nokta → ince çizgi → tam yazı."""
    a = clamp(openness)
    sx = clamp((a - 0.08) / 0.30)
    sx = sx * sx * (3 - 2 * sx)
    sy = 0.2 + 0.25 * a / 0.38 if a < 0.38 else 0.45 + 0.55 * ease_out((a - 0.38) / 0.3)
    return max(sx, 0.02 if a > 0 else 0.0), sy


@dataclass
class SpriteState:
    alpha: float = 1.0
    sx: float = 1.0
    sy: float = 1.0
    dy: float = 0.0
    split: int = 0      # eski TV renk kayması (px)
    flicker: bool = False
    glint: float | None = None  # logo ışık geçişi 0..1


def slogan_state(effect: str, start: float, end: float, t: float, frame: int) -> SpriteState | None:
    if t < start or t >= end:
        return None
    rise, fall = SLOGAN_IN.get(effect, 0.0), SLOGAN_OUT.get(effect, 0.0)
    if t < start + rise:
        p, entering = (t - start) / rise, True
    elif t >= end - fall:
        p, entering = 1 - (t - (end - fall)) / fall, False
    else:
        return SpriteState()
    if effect == "old_tv":
        sx, sy = old_tv_scale(p)
        return SpriteState(1.0, sx, sy, split=round(7 * (1 - p)) + 1 if p < 0.97 else 0, flicker=bool(frame % 2) and p < 0.97)
    if effect == "fade":
        return SpriteState(ease_out(p) if entering else ease_in(p))
    if effect == "pop":
        scale = 0.5 + 0.5 * ease_out_back(p) if entering else 0.7 + 0.3 * p
        return SpriteState(clamp(p / 0.4), scale, scale)
    return SpriteState()


# --- Logo kutusu ---------------------------------------------------------------------------------------------------

def logo_state(effect: str, start: float, end: float, rest_y: float, height: float, t: float,
               tau: float, drop_start: float, glint: tuple[float, float]) -> SpriteState | None:
    """Logo kutusu: dy = dinlenme konumuna göre aşağı kayma (px). Canvas altı = görünmez."""
    if t < start or t >= end:
        return None
    rise = 1920 - rest_y
    glint_p = (t - glint[0]) / (glint[1] - glint[0]) if glint[0] <= t < glint[1] else None
    if effect == "slow_baseline":
        if t < drop_start:
            y = 1920 - rise * (1 - math.exp(-(t - start) / tau))
        else:
            top = 1920 - rise * (1 - math.exp(-(drop_start - start) / tau))
            y = top + (1920 - top) * clamp((t - drop_start) / (end - drop_start)) ** 1.5
        return SpriteState(dy=y - rest_y, glint=glint_p)
    if effect == "fade":
        alpha = min(ease_out((t - start) / 0.4), 1 - ease_in((t - (end - 0.3)) / 0.3))
        return SpriteState(alpha, glint=glint_p)
    if effect == "pop":
        p_in, p_out = (t - start) / 0.35, (t - (end - 0.25)) / 0.25
        scale = (0.3 + 0.7 * ease_out_back(p_in)) if p_in < 1 else (1 - 0.7 * ease_in(p_out) if p_out > 0 else 1.0)
        return SpriteState(clamp(p_in / 0.3) * (1 - clamp(p_out)), scale, scale, glint=glint_p)
    return SpriteState(glint=glint_p)


# --- Çerçeve (video alanının çizgisi) -------------------------------------------------------------------------------

FRAME_PAD = 24  # parıltı için çerçeve katmanının video alanından taşma payı
FRAME_PERIOD = {"kovalayan": 3.5, "nefes": 2.4, "akis": 6.0}
COMET_TAIL = 0.22
COMET_HEAD = 8.0
COMET_CAP = 0.004  # baş ucunun yumuşaklığı (çevrenin oranı)


def _hex(color: str) -> np.ndarray:
    color = color.lstrip("#")
    return np.array([int(color[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


@dataclass
class FrameField:
    """Çerçeve bandındaki her pikselin çizgi üzerindeki konumu (s: 0–1, üst ortadan saat yönünde) ve uzaklığı (d)."""
    width: int
    height: int
    ys: np.ndarray
    xs: np.ndarray
    s: np.ndarray
    d: np.ndarray
    perimeter: float


@lru_cache(maxsize=1)
def frame_field() -> FrameField:
    x0, y0, w, h = VIDEO_SLOT["x"], VIDEO_SLOT["y"], VIDEO_SLOT["width"], VIDEO_SLOT["height"]
    half = FRAME_BORDER / 2
    cx, cy = x0 + w / 2, y0 + h / 2
    hx, hy = w / 2 - half, h / 2 - half           # çizginin (orta hattı) yarı genişliği/yüksekliği
    r = FRAME_RADIUS - half
    width, height = w + 2 * FRAME_PAD, h + 2 * FRAME_PAD
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    px = xx + (x0 - FRAME_PAD) + 0.5 - cx
    py = yy + (y0 - FRAME_PAD) + 0.5 - cy
    # Yuvarlak dikdörtgenin (orta hat) işaretli uzaklık alanı.
    qx, qy = np.abs(px) - (hx - r), np.abs(py) - (hy - r)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    band = np.abs(d) <= FRAME_PAD - 1
    ys, xs = np.nonzero(band)
    px, py, qx, qy, d = (a[band] for a in (px, py, qx, qy, d))
    # Çevre boyunca konum (üst ortadan saat yönünde).
    top_len, side_len, arc = 2 * (hx - r), 2 * (hy - r), math.pi * r / 2
    perimeter = 2 * top_len + 2 * side_len + 4 * arc
    corner = (qx > 0) & (qy > 0)
    horizontal = ~corner & (qy >= qx)  # üst/alt kenara daha yakın
    pos = np.zeros_like(px)
    pos = np.where(horizontal & (py < 0), px % perimeter, pos)
    pos = np.where(~corner & ~horizontal & (px > 0), top_len / 2 + arc + (py + side_len / 2), pos)
    pos = np.where(horizontal & (py > 0), top_len / 2 + 2 * arc + side_len + (top_len / 2 - px), pos)
    pos = np.where(~corner & ~horizontal & (px < 0), top_len * 1.5 + 3 * arc + side_len + (side_len / 2 - py), pos)
    angle = np.degrees(np.arctan2(py - np.sign(py) * (hy - r), px - np.sign(px) * (hx - r))) % 360
    pos = np.where(corner & (px > 0) & (py < 0), top_len / 2 + ((angle - 270) % 360) / 90 * arc, pos)
    pos = np.where(corner & (px > 0) & (py > 0), top_len / 2 + arc + side_len + angle / 90 * arc, pos)
    pos = np.where(corner & (px < 0) & (py > 0), top_len * 1.5 + 2 * arc + side_len + (angle - 90) / 90 * arc, pos)
    pos = np.where(corner & (px < 0) & (py < 0), top_len * 1.5 + 3 * arc + 2 * side_len + (angle - 180) / 90 * arc, pos)
    s = (pos % perimeter) / perimeter
    return FrameField(width, height, ys, xs, s.astype(np.float32), d.astype(np.float32), perimeter)


def frame_period(style: str, speed: float) -> float | None:
    period = FRAME_PERIOD.get(style)
    return period / max(0.2, speed) if period else None


def frame_rgba(style: str, color: str, accent: str, t: float, speed: float = 1.0) -> np.ndarray:
    """Çerçeve bandının RGBA'sı (FrameField boyutunda). Köşe arka planı ayrıca eklenir (template.frame_overlay)."""
    f = frame_field()
    base = _hex(color)
    glow_color = _hex(accent)
    ad = np.abs(f.d)
    out = np.zeros((f.height, f.width, 4), dtype=np.uint8)
    rgb = np.tile(base, (len(ad), 1))
    alpha = np.zeros_like(ad)
    half = FRAME_BORDER / 2
    if style == "sabit":
        alpha = np.clip(half + 0.5 - ad, 0, 1)
    elif style == "kovalayan":
        period = frame_period(style, speed) or 1
        alpha = 0.35 * np.clip(1.5 - ad, 0, 1)
        for offset in (0.0, 0.5):                      # simetrik iki ışık
            head = (t / period + offset) % 1.0
            behind = (head - f.s) % 1.0                # başın ne kadar gerisinde (0 = baş)
            k = np.clip(1 - behind / COMET_TAIL, 0, 1)  # 1 baş → 0 kuyruk ucu
            front = np.clip(1 - ((f.s - head) % 1.0) / COMET_CAP, 0, 1)  # başın önünde yuvarlak uç
            k = np.maximum(k, np.sqrt(front) * (front < 1))
            width = 0.6 + COMET_HEAD * k ** 1.3        # kalından inceye
            core = np.clip(width / 2 + 0.5 - ad, 0, 1) * (k > 0)
            glow = np.exp(-(ad ** 2) / (2 * (2 + 5 * k) ** 2)) * 0.55 * k ** 2
            a = np.maximum(core * (0.35 + 0.65 * k), glow)
            mix = (k ** 0.7)[:, None]
            rgb = np.where((a > alpha)[:, None], glow_color * (1 - mix) + np.array([255, 255, 255]) * mix, rgb)
            alpha = np.maximum(alpha, a)
    elif style == "nefes":
        period = frame_period(style, speed) or 1
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t / period)
        width = 2.5 + 2.5 * pulse
        core = np.clip(width / 2 + 0.5 - ad, 0, 1)
        glow = np.exp(-(ad ** 2) / (2 * 7 ** 2)) * (0.15 + 0.45 * pulse)
        alpha = np.maximum(core, glow)
        rgb = np.where((glow > core)[:, None], glow_color, rgb)
    elif style == "akis":
        period = frame_period(style, speed) or 1
        palette = np.array([base, glow_color, _hex("#D0E491"), base], dtype=np.float32)
        u = ((f.s - t / period) % 1.0) * 3
        i = np.floor(u).astype(int)
        frac = (u - i)[:, None]
        rgb = palette[i] * (1 - frac) + palette[np.minimum(i + 1, 3)] * frac
        alpha = np.clip(2.5 - ad, 0, 1)
    out[f.ys, f.xs, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[f.ys, f.xs, 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    return out


def frame_state_key(style: str, t: float, speed: float, fps: int) -> tuple:
    """Döngüsel stillerde bir periyodun kare sırası; sabit stillerde tek kare."""
    period = frame_period(style, speed)
    if not period:
        return (style,)
    frames = max(1, round(period * fps))
    return (style, round(t * fps) % frames)
