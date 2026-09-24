"""Axion şablon katmanları (Faz 5): arka plan, video çerçevesi, başlık/slogan animasyonları, logo kutusu.

Grafikler Pillow ile PNG olarak hazırlanır, FFmpeg bunları videonun üstüne bindirir (`render.py`). Animasyonlu
anlar kare kare, sabit anlar tek kare olarak yazılır (FFmpeg concat listesi süreleriyle). API yok.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from shared.axion_template import (
    BACKGROUND_COUNT,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    FRAME_BORDER,
    FRAME_COLOR,
    FRAME_RADIUS,
    HEADLINE_1_EXIT,
    HEADLINE_2_ENTER_START,
    HEADLINE_CENTER_Y,
    HEADLINE_FONT_SIZE,
    HEADLINE_LINE_PITCH,
    HEADLINE_MAX_WIDTH,
    HEADLINE_MIN_FONT_SIZE,
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

ASSETS = Path(__file__).resolve().parents[2] / "assets" / "sablon"
FONT_PATH = ASSETS / "fontlar" / "GoogleSans-Bold.ttf"
# Arka plan sırası bu iş gününde 1'den başlar; sonra her gün bir sonraki (8'den sonra yine 1).
BACKGROUND_FIRST_DAY = date(2026, 9, 24)

# Başlık/slogan şeridi: kanvasın bu yatay bandı (video alanının üstü) tek katman olarak bindirilir.
STRIP_Y = 230
STRIP_HEIGHT = 220
GLOW_RADIUS = 6
GLOW_STRENGTH = 0.38
TEXT_COLOR = (255, 255, 255)

# "merge" girişi (2. başlık): kelimeler arası gecikme, kelimenin belirme süresi, kayma mesafesi ve süresi.
WORD_STAGGER = 0.045
LINE_GAP = 0.1
WORD_FADE = 0.12
WORD_SLIDE_PX = 24
WORD_SLIDE_SECONDS = 0.6
EXIT_SLIDE_PX = 13


def ease_out(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def ease_in(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p**3


def _clamp(p: float) -> float:
    return min(1.0, max(0.0, p))


# ---------------------------------------------------------------------------------------------------------------
# Arka plan ve çerçeve
# ---------------------------------------------------------------------------------------------------------------

def background_index(day: date) -> int:
    """İş gününün arka planı (1..8)."""
    return (day - BACKGROUND_FIRST_DAY).days % BACKGROUND_COUNT + 1


def background_path(index: int) -> Path:
    return ASSETS / f"arka_plan_{index}.png"


@lru_cache(maxsize=2)
def background_image(index: int) -> Image.Image:
    """Arka plan, 1080x1920'yi tam kaplayacak şekilde ölçeklenip ortadan kırpılır."""
    image = Image.open(background_path(index)).convert("RGB")
    scale = max(CANVAS_WIDTH / image.width, CANVAS_HEIGHT / image.height)
    size = (math.ceil(image.width * scale), math.ceil(image.height * scale))
    image = image.resize(size, Image.LANCZOS)
    left, top = (size[0] - CANVAS_WIDTH) // 2, (size[1] - CANVAS_HEIGHT) // 2
    return image.crop((left, top, left + CANVAS_WIDTH, top + CANVAS_HEIGHT))


def _rounded_mask(size: tuple[int, int], box: tuple[int, int, int, int], radius: int, supersample: int = 4) -> Image.Image:
    big = Image.new("L", (size[0] * supersample, size[1] * supersample), 0)
    ImageDraw.Draw(big).rounded_rectangle([v * supersample for v in box], radius=radius * supersample, fill=255)
    return big.resize(size, Image.LANCZOS)


def frame_overlay(index: int) -> Image.Image:
    """Video alanının üstüne gelen katman: beyaz çerçeve + yuvarlak köşelerin dışında arka plan (tam kanvas, RGBA)."""
    x, y, w, h = VIDEO_SLOT["x"], VIDEO_SLOT["y"], VIDEO_SLOT["width"], VIDEO_SLOT["height"]
    size = (CANVAS_WIDTH, CANVAS_HEIGHT)
    outer = _rounded_mask(size, (x, y, x + w - 1, y + h - 1), FRAME_RADIUS)
    b = FRAME_BORDER
    inner = _rounded_mask(size, (x + b, y + b, x + w - 1 - b, y + h - 1 - b), FRAME_RADIUS - b)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    # Köşeler (dış yuvarlağın dışı, video alanının içi) arka planı gösterir.
    slot = Image.new("L", size, 0)
    ImageDraw.Draw(slot).rectangle((x, y, x + w - 1, y + h), fill=255)
    outside = Image.fromarray(np.minimum(np.asarray(slot), 255 - np.asarray(outer)).astype(np.uint8))
    overlay.paste(background_image(index).convert("RGBA"), (0, 0), outside)
    ring = Image.fromarray(np.clip(np.asarray(outer).astype(int) - np.asarray(inner), 0, 255).astype(np.uint8))
    overlay.paste(Image.new("RGBA", size, (*FRAME_COLOR, 255)), (0, 0), ring)
    return overlay


# ---------------------------------------------------------------------------------------------------------------
# Başlıklar
# ---------------------------------------------------------------------------------------------------------------

def turkish_upper(text: str) -> str:
    return text.replace("i", "İ").replace("ı", "I").upper()


@lru_cache(maxsize=1)
def _font_bytes() -> bytes:
    return FONT_PATH.read_bytes()


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont:
    # Bellekten: Windows'ta yol Türkçe karakter içerirse FreeType dosyayı açamayabiliyor.
    return ImageFont.truetype(io.BytesIO(_font_bytes()), size)


def _width(text: str, font: ImageFont.FreeTypeFont) -> float:
    return font.getlength(text)


def _balanced_lines(words: list[str], font: ImageFont.FreeTypeFont, lines: int) -> list[str]:
    """Kelimeleri `lines` satıra, en geniş satır en kısa olacak şekilde böler."""
    if lines <= 1 or len(words) <= 1:
        return [" ".join(words)]
    best: list[str] | None = None
    best_width = math.inf
    for cut in range(1, len(words)):
        rest = _balanced_lines(words[cut:], font, lines - 1)
        candidate = [" ".join(words[:cut]), *rest]
        widest = max(_width(line, font) for line in candidate)
        if widest < best_width - 0.5:
            best, best_width = candidate, widest
    return best or [" ".join(words)]


@dataclass
class Word:
    text: str
    line: int
    x: float  # şerit içinde sol kenar
    y: float  # şerit içinde yazının üst hizası (font çizim noktası)


@dataclass
class HeadlineLayout:
    lines: list[str]
    font_size: int
    words: list[Word]


def layout_headline(text: str) -> HeadlineLayout:
    """Başlığı büyük harfe çevirip en fazla 2 satıra yerleştirir (editör satır sonu koyduysa o geçerli).

    Satırlar 920 px'e sığmazsa yazı küçülür; 42 px'te de sığmazsa 3 satıra geçilir (gerekirse daha küçük).
    """
    text = turkish_upper(text.strip())
    manual = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    lines: list[str] = []
    size = HEADLINE_FONT_SIZE
    for size in range(HEADLINE_FONT_SIZE, HEADLINE_MIN_FONT_SIZE - 1, -2):
        font = _font(size)
        if len(manual) > 1:
            lines = manual
        else:
            words = (manual[0] if manual else "").split()
            lines = next(
                (_balanced_lines(words, font, n) for n in (1, 2)
                 if max(_width(l, font) for l in _balanced_lines(words, font, n)) <= HEADLINE_MAX_WIDTH),
                _balanced_lines(words, font, 2),
            )
        if max((_width(line, font) for line in lines), default=0) <= HEADLINE_MAX_WIDTH:
            break
    else:  # En küçük boyutta 2 satıra sığmadı: 3 satır, gerekirse daha da küçük.
        words = " ".join(manual).split()
        for size in range(HEADLINE_MIN_FONT_SIZE, 29, -2):
            lines = _balanced_lines(words, _font(size), 3)
            if max(_width(line, _font(size)) for line in lines) <= HEADLINE_MAX_WIDTH:
                break
    font = _font(size)
    pitch = HEADLINE_LINE_PITCH * size / HEADLINE_FONT_SIZE
    cap_top, cap_bottom = font.getbbox("H")[1], font.getbbox("H")[3]
    block = pitch * (len(lines) - 1) + (cap_bottom - cap_top)
    first_top = HEADLINE_CENTER_Y - block / 2 - STRIP_Y - cap_top
    space = _width(" ", font)
    words_out: list[Word] = []
    for number, line in enumerate(lines):
        x = (CANVAS_WIDTH - _width(line, font)) / 2
        y = first_top + number * pitch
        for word in line.split(" "):
            words_out.append(Word(word, number, x, y))
            x += _width(word, font) + space
    return HeadlineLayout(lines, size, words_out)


def _glow(text_layer: Image.Image) -> Image.Image:
    """Yazının altına beyaz, yumuşak parıltı ekler (Canva "glow")."""
    alpha = text_layer.getchannel("A").filter(ImageFilter.GaussianBlur(GLOW_RADIUS))
    glow = Image.new("RGBA", text_layer.size, (*TEXT_COLOR, 0))
    glow.putalpha(alpha.point(lambda v: int(v * GLOW_STRENGTH)))
    return Image.alpha_composite(glow, text_layer)


def render_headline(layout: HeadlineLayout, alphas: list[float] | None = None, offsets: list[float] | None = None) -> Image.Image:
    """Başlık şeridi (1080 x STRIP_HEIGHT, RGBA); kelime başına saydamlık ve yatay kayma."""
    font = _font(layout.font_size)
    strip = Image.new("RGBA", (CANVAS_WIDTH, STRIP_HEIGHT), (0, 0, 0, 0))
    for index, word in enumerate(layout.words):
        alpha = 1.0 if alphas is None else alphas[index]
        if alpha <= 0.004:
            continue
        dx = 0.0 if offsets is None else offsets[index]
        layer = Image.new("RGBA", strip.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((word.x + dx, word.y), word.text, font=font, fill=(*TEXT_COLOR, round(255 * alpha)))
        strip = Image.alpha_composite(strip, layer)
    return _glow(strip)


def headline_exit_params(layout: HeadlineLayout, p: float) -> tuple[list[float], list[float]]:
    """1. başlık çıkışı ("merge"): blok sola kayar, önce 1. satır, sonra diğerleri söner. p: 0..1."""
    dx = -EXIT_SLIDE_PX * ease_in(p)
    alphas = []
    for word in layout.words:
        if word.line == 0:
            alphas.append(1 - _clamp((p - 0.35) / 0.2))
        else:
            alphas.append(1 - ease_in((p - 0.55) / 0.45))
    return alphas, [dx] * len(layout.words)


def _enter_order(layout: HeadlineLayout) -> list[float]:
    """Her kelimenin giriş başlangıcı (sn): 1. satır sağdan sola, sonraki satırlar soldan sağa."""
    order: list[int] = []
    for line in sorted({w.line for w in layout.words}):
        indexes = [i for i, w in enumerate(layout.words) if w.line == line]
        order += list(reversed(indexes)) if line == 0 else indexes
    stagger = min(WORD_STAGGER, 0.55 / max(1, len(order)))
    starts = [0.0] * len(layout.words)
    delay = 0.0
    previous_line = layout.words[order[0]].line if order else 0
    for index in order:
        if layout.words[index].line != previous_line:
            delay += LINE_GAP  # satır arası kısa bekleme
            previous_line = layout.words[index].line
        starts[index] = delay
        delay += stagger
    return starts


def headline_enter_seconds(layout: HeadlineLayout) -> float:
    return max(_enter_order(layout), default=0.0) + WORD_SLIDE_SECONDS


def headline_enter_params(layout: HeadlineLayout, seconds: float) -> tuple[list[float], list[float]]:
    """2. başlık girişi ("merge"): kelimeler sırayla belirir; 1. satır sağdan, diğerleri soldan kayarak oturur."""
    alphas, offsets = [], []
    for word, start in zip(layout.words, _enter_order(layout)):
        local = seconds - start
        direction = 1 if word.line == 0 else -1
        alphas.append(_clamp(local / WORD_FADE))
        offsets.append(direction * WORD_SLIDE_PX * (1 - ease_out(local / WORD_SLIDE_SECONDS)))
    return alphas, offsets


# ---------------------------------------------------------------------------------------------------------------
# Sloganlar ("old tv")
# ---------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=4)
def slogan_image(file: str) -> Image.Image:
    image = Image.open(ASSETS / file).convert("RGBA")
    return image.resize((round(image.width * SLOGAN_SCALE), round(image.height * SLOGAN_SCALE)), Image.LANCZOS)


def old_tv_scale(openness: float) -> tuple[float, float]:
    """Açıklık (0 kapalı .. 1 tam) → (yatay, dikey) ölçek: nokta → ince çizgi → tam yazı."""
    a = _clamp(openness)
    sx = _clamp((a - 0.08) / 0.30)
    sx = sx * sx * (3 - 2 * sx)
    sy = 0.2 + 0.25 * a / 0.38 if a < 0.38 else 0.45 + 0.55 * ease_out((a - 0.38) / 0.3)
    return max(sx, 0.02 if a > 0 else 0.0), sy


def _rgb_split(image: Image.Image, shift: int) -> Image.Image:
    """Eski TV renk kayması: kırmızı sola, mavi sağa."""
    if shift <= 0:
        return image
    array = np.asarray(image).astype(np.uint8)
    out = np.zeros((array.shape[0], array.shape[1] + 2 * shift, 4), dtype=np.uint8)
    width = array.shape[1]
    red = np.zeros_like(out)
    red[:, 0:width] = array
    green = np.zeros_like(out)
    green[:, shift:shift + width] = array
    blue = np.zeros_like(out)
    blue[:, 2 * shift:2 * shift + width] = array
    out[..., 0] = red[..., 0]
    out[..., 1] = green[..., 1]
    out[..., 2] = blue[..., 2]
    out[..., 3] = np.maximum(np.maximum(red[..., 3], green[..., 3]), blue[..., 3])
    return Image.fromarray(out)


def render_slogan(file: str, openness: float, frame: int = 0) -> Image.Image:
    strip = Image.new("RGBA", (CANVAS_WIDTH, STRIP_HEIGHT), (0, 0, 0, 0))
    sx, sy = old_tv_scale(openness)
    if sx <= 0 or sy <= 0:
        return strip
    image = slogan_image(file)
    size = (max(1, round(image.width * sx)), max(1, round(image.height * sy)))
    shaped = image.resize(size, Image.BILINEAR)
    if openness < 0.97:
        shaped = _rgb_split(shaped, round(7 * (1 - openness)) + 1)
        if frame % 2:  # titreşim
            shaped.putalpha(shaped.getchannel("A").point(lambda v: int(v * 0.8)))
    center_y = HEADLINE_CENTER_Y - 4 - STRIP_Y
    strip.alpha_composite(shaped, (round((CANVAS_WIDTH - shaped.width) / 2), round(center_y - shaped.height / 2)))
    return strip


# ---------------------------------------------------------------------------------------------------------------
# Üst şerit zaman çizelgesi
# ---------------------------------------------------------------------------------------------------------------

def top_state(t: float, frame: int, h2_enter_seconds: float) -> tuple:
    """t anında üst şeridin durumu. Aynı durum = aynı görüntü (sabit anlar tek kare yazılır)."""
    exit_start, exit_end = HEADLINE_1_EXIT
    if t < exit_start:
        return ("h1",)
    if t < exit_end:
        return ("h1_exit", round((t - exit_start) / (exit_end - exit_start), 4))
    for number, slogan in enumerate(SLOGANS):
        (in_start, in_end), (out_start, out_end) = slogan["enter"], slogan["exit"]
        if in_start <= t < in_end:
            return ("slogan", number, round((t - in_start) / (in_end - in_start), 4), frame % 2)
        if in_end <= t < out_start:
            return ("slogan", number, 1.0, 0)
        if out_start <= t < out_end:
            return ("slogan", number, round(1 - (t - out_start) / (out_end - out_start), 4), frame % 2)
    if t < HEADLINE_2_ENTER_START:
        return ("blank",)
    local = t - HEADLINE_2_ENTER_START
    if local < h2_enter_seconds:
        return ("h2_enter", round(local, 4))
    return ("h2",)


def render_top(state: tuple, headline_1: HeadlineLayout, headline_2: HeadlineLayout) -> Image.Image:
    kind = state[0]
    if kind == "h1":
        return render_headline(headline_1)
    if kind == "h1_exit":
        return render_headline(headline_1, *headline_exit_params(headline_1, state[1]))
    if kind == "slogan":
        _, number, openness, frame = state
        return render_slogan(SLOGANS[number]["file"], openness, frame)
    if kind == "h2_enter":
        return render_headline(headline_2, *headline_enter_params(headline_2, state[1]))
    if kind == "h2":
        return render_headline(headline_2)
    return Image.new("RGBA", (CANVAS_WIDTH, STRIP_HEIGHT), (0, 0, 0, 0))


# ---------------------------------------------------------------------------------------------------------------
# Logo kutusu
# ---------------------------------------------------------------------------------------------------------------

def render_logo_box(glint: float | None = None) -> Image.Image:
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


@lru_cache(maxsize=1)
def _logo_image() -> Image.Image:
    logo = Image.open(ASSETS / "logo.png").convert("RGBA")
    width = LOGO_BOX["logo_width"]
    return logo.resize((width, round(logo.height * width / logo.width)), Image.LANCZOS)


def logo_y(t: float) -> float:
    """Logo kutusunun üst kenarının y'si (1920 = görünmüyor)."""
    rise = CANVAS_HEIGHT - LOGO_BOX["rest_y"]
    if t < LOGO_RISE_START or t >= LOGO_DROP_START + LOGO_DROP_SECONDS:
        return float(CANVAS_HEIGHT)
    if t < LOGO_DROP_START:
        return CANVAS_HEIGHT - rise * (1 - math.exp(-(t - LOGO_RISE_START) / LOGO_RISE_TAU))
    top = CANVAS_HEIGHT - rise * (1 - math.exp(-(LOGO_DROP_START - LOGO_RISE_START) / LOGO_RISE_TAU))
    return top + (CANVAS_HEIGHT - top) * ((t - LOGO_DROP_START) / LOGO_DROP_SECONDS) ** 1.5


def logo_y_expression() -> str:
    """logo_y() ile aynı eğri, FFmpeg overlay ifadesi olarak (t = videonun zamanı)."""
    rise = CANVAS_HEIGHT - LOGO_BOX["rest_y"]
    s, tau, d, n = LOGO_RISE_START, LOGO_RISE_TAU, LOGO_DROP_START, LOGO_DROP_SECONDS
    top = CANVAS_HEIGHT - rise * (1 - math.exp(-(d - s) / tau))
    return (
        f"if(lt(t,{s}),{CANVAS_HEIGHT},"
        f"if(lt(t,{d}),{CANVAS_HEIGHT}-{rise}*(1-exp(-(t-{s})/{tau})),"
        f"if(lt(t,{d + n:.3f}),{top:.3f}+{CANVAS_HEIGHT - top:.3f}*pow((t-{d})/{n},1.5),{CANVAS_HEIGHT})))"
    )


def logo_state(t: float) -> float | None:
    start, end = LOGO_GLINT
    return round((t - start) / (end - start), 4) if start <= t < end else None


# ---------------------------------------------------------------------------------------------------------------
# Katman dosyaları
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class Layers:
    base: Path       # arka plan (1080x1920)
    frame: Path      # çerçeve + köşeler (RGBA)
    top: Path        # üst şerit concat listesi
    logo: Path       # logo kutusu concat listesi


def write_sequence(folder: Path, prefix: str, fps: int, total_frames: int, state_at, render) -> Path:
    """Durumu değişen her kare için PNG yazar; sabit anlar tek kare + süre (FFmpeg concat listesi)."""
    entries: list[tuple[str, int]] = []
    previous = object()
    for frame in range(total_frames):
        state = state_at(frame / fps, frame)
        if state == previous:
            name, count = entries[-1]
            entries[-1] = (name, count + 1)
            continue
        previous = state
        name = f"{prefix}_{len(entries):05d}.png"
        render(state).save(folder / name, compress_level=1)
        entries.append((name, 1))
    lines = ["ffconcat version 1.0"]
    for name, count in entries:
        lines += [f"file '{name}'", f"duration {count / fps:.6f}"]
    lines.append(f"file '{entries[-1][0]}'")  # concat son dosyanın süresini ancak tekrar edilirse uygular
    path = folder / f"{prefix}.ffconcat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_layers(folder: Path, headline_1: str, headline_2: str, background: int, fps: int, seconds: float) -> Layers:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / "zemin.png"
    background_image(background).save(base, compress_level=1)
    frame = folder / "cerceve.png"
    frame_overlay(background).save(frame, compress_level=1)
    layout_1, layout_2 = layout_headline(headline_1), layout_headline(headline_2)
    enter_seconds = headline_enter_seconds(layout_2)
    total = max(1, round(seconds * fps))
    top = write_sequence(
        folder, "ust", fps, total,
        lambda t, f: top_state(t, f, enter_seconds),
        lambda state: render_top(state, layout_1, layout_2),
    )
    logo = write_sequence(folder, "logo", fps, total, lambda t, f: logo_state(t), render_logo_box)
    return Layers(base, frame, top, logo)


def preview_image(background: int, headline: str, video_frame: Image.Image | None = None, width: int = 360) -> Image.Image:
    """Şablonun sabit hâli (arka plan + video karesi + çerçeve + başlık), küçük önizleme."""
    canvas = background_image(background).convert("RGBA")
    if video_frame is not None:
        x, y, w, h = VIDEO_SLOT["x"], VIDEO_SLOT["y"], VIDEO_SLOT["width"], VIDEO_SLOT["height"]
        canvas.alpha_composite(video_frame.convert("RGBA").resize((w, h)), (x, y))
    canvas.alpha_composite(frame_overlay(background))
    canvas.alpha_composite(render_headline(layout_headline(headline)), (0, STRIP_Y))
    return canvas.convert("RGB").resize((width, round(width * CANVAS_HEIGHT / CANVAS_WIDTH)), Image.LANCZOS)
