"""Başlık yerleşimi: satırlara bölme, sığdırma ve "iki satıra sığıyor mu" ölçümü.

Haber Stüdyosu (başlık üretimi/doğrulama) ve Tasarım Stüdyosu (videoya yazma) aynı ölçümü kullanır: başlık gerçek
yazı tipiyle (varsayılan Google Sans Bold 58 px) piksel olarak ölçülür, 920 px genişliğe en fazla 2 satır.
Sansür: `~~kelime~~` işaretli kelimelerin üstü videoda çizilir (işaretler görünmez).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import ImageFont

from .axion_template import HEADLINE_FONT_SIZE, HEADLINE_MAX_WIDTH, HEADLINE_MIN_FONT_SIZE
from .fonts import DEFAULT_FAMILY, DEFAULT_STYLE, load_font

MAX_LINES = 2
STRIKE = "~~"


def turkish_upper(text: str) -> str:
    return text.replace("i", "İ").replace("ı", "I").upper()


@dataclass
class Token:
    text: str
    strike: bool = False


def parse_lines(text: str, upper: bool = True) -> list[list[Token]]:
    """Metni satırlara ve kelimelere ayırır; `~~...~~` arasındaki kelimeler üstü çizili (birden çok kelime olabilir)."""
    if upper:
        text = turkish_upper(text)
    lines: list[list[Token]] = []
    strike = False
    for raw_line in text.splitlines():
        tokens: list[Token] = []
        for word in raw_line.split():
            struck, clean = strike, ""
            for index, piece in enumerate(word.split(STRIKE)):
                if index:
                    strike = not strike
                if piece:
                    clean += piece
                    struck = struck or strike
            if clean:
                tokens.append(Token(clean, struck))
        if tokens:
            lines.append(tokens)
    return lines


def plain_text(text: str) -> str:
    return text.replace(STRIKE, "")


def _line_width(tokens: list[Token], font: ImageFont.FreeTypeFont) -> float:
    return font.getlength(" ".join(t.text for t in tokens))


def balanced_lines(tokens: list[Token], font: ImageFont.FreeTypeFont, lines: int) -> list[list[Token]]:
    """Kelimeleri `lines` satıra, en geniş satır en kısa olacak şekilde böler (sıra korunur)."""
    if lines <= 1 or len(tokens) <= 1:
        return [tokens]
    best: list[list[Token]] | None = None
    best_width = math.inf
    for cut in range(1, len(tokens)):
        candidate = [tokens[:cut], *balanced_lines(tokens[cut:], font, lines - 1)]
        widest = max(_line_width(line, font) for line in candidate)
        if widest < best_width - 0.5:
            best, best_width = candidate, widest
    return best or [tokens]


@dataclass
class Fitted:
    lines: list[list[Token]]
    size: int
    fits: bool  # varsayılan boyutta en fazla 2 satıra sığdı mı


def fit_text(
    text: str,
    family: str | None = DEFAULT_FAMILY,
    style: str | None = DEFAULT_STYLE,
    size: int = HEADLINE_FONT_SIZE,
    min_size: int = HEADLINE_MIN_FONT_SIZE,
    max_width: float = HEADLINE_MAX_WIDTH,
    max_lines: int = MAX_LINES,
    upper: bool = True,
) -> Fitted:
    """Editör satır sonu koyduysa o satırlar; yoksa 1 satıra, sığmazsa en dengeli 2 satıra. Sığmazsa yazı küçülür;
    en küçük boyutta da sığmazsa 3 satır (gerekirse daha küçük). `fits`: istenen boyutta 2 satıra sığdı mı."""
    manual = parse_lines(text, upper)
    words = [t for line in manual for t in line]
    if not words:
        return Fitted([], size, True)

    def attempt(font_size: int, lines_allowed: int) -> list[list[Token]] | None:
        font = load_font(family, style, font_size)
        if len(manual) > 1:
            candidate = manual
        else:
            candidate = next(
                (balanced_lines(words, font, n) for n in range(1, lines_allowed + 1)
                 if max(_line_width(l, font) for l in balanced_lines(words, font, n)) <= max_width),
                None,
            )
        if candidate and len(candidate) <= max(lines_allowed, len(manual)) and all(
            _line_width(l, font) <= max_width for l in candidate
        ):
            return candidate
        return None

    first = attempt(size, max_lines)
    if first is not None:
        return Fitted(first, size, len(first) <= max_lines)
    for smaller in range(size - 2, min_size - 1, -2):
        found = attempt(smaller, max_lines)
        if found is not None:
            return Fitted(found, smaller, False)
    for smaller in range(min_size, 23, -2):
        found = attempt(smaller, max_lines + 1)
        if found is not None:
            return Fitted(found, smaller, False)
    font = load_font(family, style, 24)
    return Fitted(balanced_lines(words, font, max_lines + 1), 24, False)


@dataclass
class HeadlineCheck:
    fits: bool
    lines: list[str]
    over_chars: int  # yaklaşık kaç karakter kısalmalı (sığıyorsa 0)


def check_headline(text: str) -> HeadlineCheck:
    """Başlık, videodaki varsayılan yazıyla (Google Sans Bold 58 px) 2 satıra sığıyor mu?"""
    fitted = fit_text(text)
    lines = [" ".join(t.text for t in line) for line in fitted.lines]
    if fitted.fits:
        return HeadlineCheck(True, lines, 0)
    font = load_font(size=HEADLINE_FONT_SIZE)
    full = turkish_upper(plain_text(" ".join(text.split())))
    per_char = font.getlength(full) / max(1, len(full))
    # 2 satır × 920 px'e (dengeli bölmenin kaybı için %8 pay) göre fazlalık.
    over = font.getlength(full) - 2 * HEADLINE_MAX_WIDTH * 0.92
    return HeadlineCheck(False, lines, max(1, math.ceil(over / per_char)))


def headline_char_budget() -> int:
    """Modele verilecek yaklaşık karakter sınırı (ölçüm ne derse o geçerli; bu yalnızca yön gösterir)."""
    font = load_font(size=HEADLINE_FONT_SIZE)
    sample = "OTOMOBİL KALDIRIMDAKİ YAYALARA ÇARPTI, 3 KİŞİ YARALANDI"
    per_char = font.getlength(sample) / len(sample)
    return int(2 * HEADLINE_MAX_WIDTH * 0.85 / per_char)



def toggle_strike(text: str, index: int) -> str:
    """`index`. kelimenin (metindeki sırasıyla, 0'dan) sansür çizgisini açar/kapatır; satır sonları korunur."""
    out, position = [], 0
    for line in parse_lines(text, upper=False):
        parts = []
        for token in line:
            struck = token.strike != (position == index)
            parts.append(f"{STRIKE}{token.text}{STRIKE}" if struck else token.text)
            position += 1
        out.append(" ".join(parts))
    return "\n".join(out)
