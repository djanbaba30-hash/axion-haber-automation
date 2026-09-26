"""Axion şablon katmanları (Faz 5): arka plan, video çerçevesi, başlıklar, sloganlar, logo kutusu, editörün yazıları.

Tüm grafikler Pillow ile çizilir (önizleme ile son video aynı), FFmpeg yalnızca bindirir (`render.py`). Yazılar
kelime kelime "sprite" olarak hazırlanır (parıltı ve sansür çizgisi dahil); efektler kelime başına saydamlık/kayma ve
blok ölçeği verir (`effects.py`). Animasyonlu anlar kare kare, sabit anlar süreli tek kare yazılır (FFmpeg concat).
"""

from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from collections.abc import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from shared.axion_template import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    FRAME_RADIUS,
    HEADLINE_1_EXIT,
    HEADLINE_2_ENTER_START,
    HEADLINE_CENTER_Y,
    HEADLINE_FONT_SIZE,
    HEADLINE_LINE_PITCH,
    HEADLINE_MAX_WIDTH,
    LOGO_BOX,
    LOGO_DROP_SECONDS,
    LOGO_DROP_START,
    LOGO_GLINT,
    LOGO_RISE_START,
    LOGO_RISE_TAU,
    SLOGAN_SCALE,
    SLOGANS,
    VIDEO_SLOT,
)
from shared.fonts import load_font
from shared.text_layout import fit_text

from . import effects as fx
from .design import Design, TextLayer, TextStyle

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "sablon"
HEADLINE_1_END = HEADLINE_1_EXIT[1]
TEXT_MAX_WIDTH = 960
GLOW_RADIUS = 6
LOGO_END = LOGO_DROP_START + LOGO_DROP_SECONDS


# ---------------------------------------------------------------------------------------------------------------
# Arka plan ve çerçeve
# ---------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _background(path: str, mtime: float) -> Image.Image:
    image = Image.open(path).convert("RGB")
    scale = max(CANVAS_WIDTH / image.width, CANVAS_HEIGHT / image.height)
    size = (math.ceil(image.width * scale), math.ceil(image.height * scale))
    image = image.resize(size, Image.LANCZOS)
    left, top = (size[0] - CANVAS_WIDTH) // 2, (size[1] - CANVAS_HEIGHT) // 2
    return image.crop((left, top, left + CANVAS_WIDTH, top + CANVAS_HEIGHT))


def background_image(path: Path) -> Image.Image:
    """Arka plan, 1080x1920'yi tam kaplayacak şekilde ölçeklenip ortadan kırpılır."""
    return _background(str(path), path.stat().st_mtime)


def _rounded_mask(size: tuple[int, int], box: tuple[float, float, float, float], radius: float, supersample: int = 4) -> Image.Image:
    big = Image.new("L", (size[0] * supersample, size[1] * supersample), 0)
    ImageDraw.Draw(big).rounded_rectangle([v * supersample for v in box], radius=radius * supersample, fill=255)
    return big.resize(size, Image.LANCZOS)


def frame_origin() -> tuple[int, int]:
    """Çerçeve katmanının kanvastaki sol üstü (video alanı + parıltı payı)."""
    return VIDEO_SLOT["x"] - fx.FRAME_PAD, VIDEO_SLOT["y"] - fx.FRAME_PAD


@lru_cache(maxsize=4)
def _corners(path: str, mtime: float) -> Image.Image:
    """Video alanının yuvarlak köşelerinin dışı arka planla örtülür (çerçeve katmanı boyutunda)."""
    f = fx.frame_field()
    ox, oy = frame_origin()
    pad = fx.FRAME_PAD
    w, h = VIDEO_SLOT["width"], VIDEO_SLOT["height"]
    outer = _rounded_mask((f.width, f.height), (pad, pad, pad + w - 1, pad + h - 1), FRAME_RADIUS)
    slot = Image.new("L", (f.width, f.height), 0)
    ImageDraw.Draw(slot).rectangle((pad, pad, pad + w - 1, pad + h), fill=255)
    outside = Image.fromarray(np.minimum(np.asarray(slot), 255 - np.asarray(outer)).astype(np.uint8))
    layer = Image.new("RGBA", (f.width, f.height), (0, 0, 0, 0))
    background = _background(path, mtime).crop((ox, oy, ox + f.width, oy + f.height)).convert("RGBA")
    layer.paste(background, (0, 0), outside)
    return layer


def frame_overlay(background: Path, style: str = "sabit", color: str = "#F6F6F6", accent: str = "#BEE1E8",
                  t: float = 0.0, speed: float = 1.0) -> Image.Image:
    """Çerçeve katmanı (`frame_origin()`'e konur): köşe arka planı + çizgi (stil ve an)."""
    layer = _corners(str(background), background.stat().st_mtime).copy()
    if style != "yok":
        layer.alpha_composite(Image.fromarray(fx.frame_rgba(style, color, accent, t, speed)))
    return layer


# ---------------------------------------------------------------------------------------------------------------
# Yazılar (kelime sprite'ları)
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class WordSprite:
    text: str
    line: int
    image: Image.Image
    x: int  # kanvasta sprite'ın sol üstü (efektsiz)
    y: int


@dataclass
class TextBlock:
    words: list[WordSprite]
    center: tuple[float, float]
    size: int
    fits: bool = True

    @property
    def lines(self) -> list[int]:
        return [w.line for w in self.words]

    def bbox(self) -> tuple[int, int, int, int]:
        if not self.words:
            x, y = self.center
            return round(x), round(y), round(x), round(y)
        return (min(w.x for w in self.words), min(w.y for w in self.words),
                max(w.x + w.image.width for w in self.words), max(w.y + w.image.height for w in self.words))


def _hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


@lru_cache(maxsize=512)
def _word_image(text: str, strike: bool, family: str, style: str, size: int, color: str, glow: float) -> tuple[Image.Image, int, int]:
    """Kelime sprite'ı ve çizim noktasına göre sol üst kayması."""
    font = load_font(family, style, size)
    left, top, right, bottom = font.getbbox(text)
    margin = GLOW_RADIUS * 3 if glow > 0 else 2
    image = Image.new("RGBA", (right - left + 2 * margin, bottom - top + 2 * margin), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    origin = (margin - left, margin - top)
    rgb = _hex_rgb(color)
    draw.text(origin, text, font=font, fill=(*rgb, 255))
    if strike:  # sansür: büyük harf yüksekliğinin ortasından çizgi
        cap_top, cap_bottom = font.getbbox("H")[1], font.getbbox("H")[3]
        y = origin[1] + (cap_top + cap_bottom) / 2
        thickness = max(3, round(size * 0.09))
        draw.rectangle((margin - 2, y - thickness / 2, image.width - margin + 2, y + thickness / 2), fill=(*rgb, 255))
    if glow > 0:
        alpha = image.getchannel("A").filter(ImageFilter.GaussianBlur(GLOW_RADIUS))
        halo = Image.new("RGBA", image.size, (*rgb, 0))
        halo.putalpha(alpha.point(lambda v: int(v * glow)))
        image = Image.alpha_composite(halo, image)
    return image, left - margin, top - margin


def build_block(text: str, style: TextStyle, center: tuple[float, float], max_width: float, max_lines: int,
                shrink: bool, pitch_ratio: float = HEADLINE_LINE_PITCH / HEADLINE_FONT_SIZE) -> TextBlock:
    """Metni satırlara yerleştirir (büyük harf yüksekliği bloğu `center`'da ortalanır), kelime sprite'larını hazırlar."""
    min_size = max(16, style.size - 16) if shrink else style.size
    fitted = fit_text(text, style.family, style.style, style.size, min_size, max_width, max_lines, style.upper)
    font = load_font(style.family, style.style, fitted.size)
    pitch = fitted.size * pitch_ratio
    cap_top, cap_bottom = font.getbbox("H")[1], font.getbbox("H")[3]
    height = pitch * (len(fitted.lines) - 1) + (cap_bottom - cap_top)
    first = center[1] - height / 2 - cap_top
    space = font.getlength(" ")
    words: list[WordSprite] = []
    for number, line in enumerate(fitted.lines):
        x = center[0] - font.getlength(" ".join(t.text for t in line)) / 2
        y = first + number * pitch
        for token in line:
            image, ox, oy = _word_image(token.text, token.strike, style.family, style.style, fitted.size, style.color, style.glow)
            words.append(WordSprite(token.text, number, image, round(x + ox), round(y + oy)))
            x += font.getlength(token.text) + space
    return TextBlock(words, center, fitted.size, fitted.fits)


def headline_block(text: str, style: TextStyle) -> TextBlock:
    return build_block(text, style, (CANVAS_WIDTH / 2, HEADLINE_CENTER_Y), HEADLINE_MAX_WIDTH, 2, shrink=True)


def layer_block(layer: TextLayer) -> TextBlock:
    return build_block(layer.text, layer, (layer.x * CANVAS_WIDTH, layer.y * CANVAS_HEIGHT), TEXT_MAX_WIDTH, 8, shrink=False)


def _blit(canvas: Image.Image, image: Image.Image, x: int, y: int) -> None:
    """Kanvas dışına taşan kısmı kırparak bindirir (Pillow negatif hedef kabul etmez)."""
    left, top = max(0, -x), max(0, -y)
    right, bottom = min(image.width, canvas.width - x), min(image.height, canvas.height - y)
    if right <= left or bottom <= top:
        return
    if (left, top, right, bottom) != (0, 0, image.width, image.height):
        image = image.crop((left, top, right, bottom))
    canvas.alpha_composite(image, (x + left, y + top))


def _with_alpha(image: Image.Image, alpha: float) -> Image.Image:
    if alpha >= 0.999:
        return image
    faded = image.copy()
    faded.putalpha(image.getchannel("A").point(lambda v: int(v * alpha)))
    return faded


def draw_block(canvas: Image.Image, block: TextBlock, state: fx.BlockState) -> None:
    cx, cy = block.center
    for sprite, word in zip(block.words, state.words):
        if word.alpha <= 0.004:
            continue
        image = sprite.image
        x, y = sprite.x + word.dx, sprite.y + word.dy
        if abs(state.scale - 1) > 0.001:
            size = (max(1, round(image.width * state.scale)), max(1, round(image.height * state.scale)))
            mid_x, mid_y = x + image.width / 2, y + image.height / 2
            image = image.resize(size, Image.BILINEAR)
            x = cx + (mid_x - cx) * state.scale - size[0] / 2
            y = cy + (mid_y - cy) * state.scale - size[1] / 2
        _blit(canvas, _with_alpha(image, word.alpha), round(x), round(y))


# ---------------------------------------------------------------------------------------------------------------
# Sloganlar ve logo kutusu
# ---------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=4)
def slogan_image(file: str) -> Image.Image:
    image = Image.open(ASSETS / file).convert("RGBA")
    return image.resize((round(image.width * SLOGAN_SCALE), round(image.height * SLOGAN_SCALE)), Image.LANCZOS)


def slogan_center() -> tuple[float, float]:
    return CANVAS_WIDTH / 2, HEADLINE_CENTER_Y - 4


def rgb_split(image: Image.Image, shift: int) -> Image.Image:
    """Eski TV renk kayması: kırmızı sola, mavi sağa."""
    if shift <= 0:
        return image
    array = np.asarray(image)
    height, width = array.shape[:2]
    out = np.zeros((height, width + 2 * shift, 4), dtype=np.uint8)
    alpha = np.zeros((height, width + 2 * shift), dtype=np.uint8)
    for channel, offset in ((0, 0), (1, shift), (2, 2 * shift)):
        out[:, offset:offset + width, channel] = array[..., channel]
        alpha[:, offset:offset + width] = np.maximum(alpha[:, offset:offset + width], array[..., 3])
    out[..., 3] = alpha
    return Image.fromarray(out)


def draw_sprite(canvas: Image.Image, image: Image.Image, center: tuple[float, float], state: fx.SpriteState) -> None:
    if state.alpha <= 0.004 or state.sx <= 0 or state.sy <= 0:
        return
    if (state.sx, state.sy) != (1.0, 1.0):
        image = image.resize((max(1, round(image.width * state.sx)), max(1, round(image.height * state.sy))), Image.BILINEAR)
    image = rgb_split(image, state.split)
    alpha = state.alpha * (0.8 if state.flicker else 1.0)
    _blit(canvas, _with_alpha(image, alpha), round(center[0] - image.width / 2), round(center[1] - image.height / 2 + state.dy))


@lru_cache(maxsize=1)
def _logo_image() -> Image.Image:
    logo = Image.open(ASSETS / "logo.png").convert("RGBA")
    width = LOGO_BOX["logo_width"]
    return logo.resize((width, round(logo.height * width / logo.width)), Image.LANCZOS)


@lru_cache(maxsize=32)
def logo_box(glint: float | None = None) -> Image.Image:
    """Beyaz, yumuşak köşeli kutu + Axion Haber logosu; glint 0..1 ise üzerinden çapraz ışık geçer."""
    w, h, radius = LOGO_BOX["width"], LOGO_BOX["height"], LOGO_BOX["radius"]
    mask = _rounded_mask((w, h), (0, 0, w - 1, h + radius), radius)  # alt köşeler kanvasın dışında kalır
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    box.paste(Image.new("RGBA", (w, h), (255, 255, 255, 255)), (0, 0), mask)
    logo = _logo_image()
    box.alpha_composite(logo, ((w - logo.width) // 2, LOGO_BOX["logo_top"]))
    if glint is not None and 0 <= glint <= 1:
        band = Image.new("L", (w, h), 0)
        center = -60 + (w + 120) * glint
        ImageDraw.Draw(band).polygon(
            [(center - 18, h), (center + 18, h), (center + 18 + h * 0.55, 0), (center - 18 + h * 0.55, 0)], fill=110
        )
        band = Image.fromarray(np.minimum(np.asarray(band), np.asarray(mask)).astype(np.uint8))
        shine = Image.new("RGBA", (w, h), (205, 205, 205, 0))
        shine.putalpha(band)
        box = Image.alpha_composite(box, shine)
    return box


def logo_center() -> tuple[float, float]:
    return LOGO_BOX["x"] + LOGO_BOX["width"] / 2, LOGO_BOX["rest_y"] + LOGO_BOX["height"] / 2


# ---------------------------------------------------------------------------------------------------------------
# Grafik katmanı zaman çizelgesi
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class Scene:
    """Bir tasarımın zaman içindeki tüm grafikleri (çerçeve hariç)."""
    design: Design
    seconds: float
    headline_1: TextBlock
    headline_2: TextBlock
    layers: list[tuple[TextLayer, TextBlock]] = field(default_factory=list)

    def items(self, t: float, frame: int) -> list[tuple[str, object]]:
        d = self.design
        out: list[tuple[str, object]] = []
        # Kapak (v4.0): videonun ilk karesinde 1. başlık giriş animasyonunun son hâliyle tam görünür; Reels/Shorts kapak
        # seçiminde ilk kare hazır, ayrı kapak yüklemek gerekmez. Animasyon ikinci kareden her zamanki gibi başlar.
        h1_t = max(t, fx.enter_seconds(d.headline_1.enter, self.headline_1.lines)) if frame == 0 and t < 1e-3 else t
        h1 = fx.text_state(d.headline_1.enter, d.headline_1.exit, self.headline_1.lines, 0.0, HEADLINE_1_END, h1_t)
        if h1:
            out.append(("h1", h1))
        if d.slogans.enabled:
            for number, slogan in enumerate(SLOGANS):
                state = fx.slogan_state(d.slogans.effect, slogan["enter"][0], slogan["exit"][1], t, frame)
                if state:
                    out.append((f"s{number}", state))
        h2 = fx.text_state(d.headline_2.enter, d.headline_2.exit, self.headline_2.lines, HEADLINE_2_ENTER_START,
                           self.seconds + 1, t)
        if h2:
            out.append(("h2", h2))
        if d.logo.enabled:
            state = fx.logo_state(d.logo.effect, LOGO_RISE_START, LOGO_END, LOGO_BOX["rest_y"], LOGO_BOX["height"], t,
                                  LOGO_RISE_TAU, LOGO_DROP_START, LOGO_GLINT)
            if state:
                out.append(("logo", state))
        for layer, block in self.layers:
            state = fx.text_state(layer.enter, layer.exit, block.lines, layer.start, layer.end, t)
            if state:
                out.append((f"t:{layer.id}", state))
        return out

    def key(self, t: float, frame: int) -> tuple:
        parts = []
        for name, state in self.items(t, frame):
            if isinstance(state, fx.BlockState):
                parts.append((name, fx.state_key(state)))
            else:
                s = state
                parts.append((name, round(s.alpha, 3), round(s.sx, 3), round(s.sy, 3), round(s.dy, 1), s.split, s.flicker,
                              None if s.glint is None else round(s.glint, 3)))
        return tuple(parts)

    def render(self, t: float, frame: int) -> Image.Image:
        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
        blocks = {"h1": self.headline_1, "h2": self.headline_2, **{f"t:{layer.id}": b for layer, b in self.layers}}
        for name, state in self.items(t, frame):
            if name in blocks:
                draw_block(canvas, blocks[name], state)
            elif name == "logo":
                glint = state.glint
                draw_sprite(canvas, logo_box(None if glint is None else round(glint, 3)), logo_center(), state)
            else:
                draw_sprite(canvas, slogan_image(SLOGANS[int(name[1:])]["file"]), slogan_center(), state)
        return canvas


def build_scene(design: Design, seconds: float) -> Scene:
    return Scene(
        design, seconds,
        headline_block(design.headline_1.text, design.headline_style),
        headline_block(design.headline_2.text, design.headline_style),
        [(layer, layer_block(layer)) for layer in design.texts if layer.text.strip()],
    )


# ---------------------------------------------------------------------------------------------------------------
# Katman dosyaları
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class Layers:
    base: Path       # arka plan (1080x1920)
    frame: Path      # çerçeve (köşeler + çizgi) concat listesi; `frame_origin()`'e konur
    graphics: Path   # yazılar, sloganlar, logo concat listesi (tam kanvas)


def write_sequence(folder: Path, prefix: str, fps: int, total_frames: int, state_at: Callable, render: Callable) -> Path:
    """Durumu değişen kareler için PNG yazar; aynı durum tekrar gelirse aynı PNG kullanılır (döngüler ucuz).

    Önce tüm karelerin durumu hesaplanır (hızlı), sonra her farklı durum paralel çizilip yazılır.
    """
    entries: list[tuple[str, int]] = []
    names: dict = {}
    order: list = []
    previous = object()
    for frame in range(total_frames):
        state = state_at(frame / fps, frame)
        if state == previous:
            name, count = entries[-1]
            entries[-1] = (name, count + 1)
            continue
        previous = state
        if state not in names:
            names[state] = f"{prefix}_{len(names):05d}.png"
            order.append(state)
        entries.append((names[state], 1))

    def save(state) -> None:
        render(state).save(folder / names[state], compress_level=1)

    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
        list(pool.map(save, order))  # Pillow ve zlib GIL'i bırakır: çekirdek sayısı kadar hızlanır
    lines = ["ffconcat version 1.0"]
    for name, count in entries:
        lines += [f"file '{name}'", f"duration {count / fps:.6f}"]
    lines.append(f"file '{entries[-1][0]}'")  # concat son dosyanın süresini ancak tekrar edilirse uygular
    path = folder / f"{prefix}.ffconcat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_layers(folder: Path, design: Design, background: Path, fps: int, seconds: float) -> Layers:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / "zemin.png"
    background_image(background).save(base, compress_level=1)
    total = max(1, round(seconds * fps))
    settings = design.frame
    frame = write_sequence(
        folder, "cerceve", fps, total,
        lambda t, f: fx.frame_state_key(settings.style, t, settings.speed, fps),
        lambda key: frame_overlay(background, settings.style, settings.color, settings.accent,
                                  key[1] / fps if len(key) > 1 else 0.0, settings.speed),
    )
    scene = build_scene(design, seconds)
    first_time: dict[tuple, tuple[float, int]] = {}

    def graphics_key(t: float, f: int) -> tuple:
        key = scene.key(t, f)
        first_time.setdefault(key, (t, f))
        return key

    graphics = write_sequence(folder, "grafik", fps, total, graphics_key, lambda key: scene.render(*first_time[key]))
    return Layers(base, frame, graphics)
