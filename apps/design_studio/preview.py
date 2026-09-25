"""Başlıkların videodaki görünümü (Haber Stüdyosu'nda kalite kontrolü için): günün arka planı, gerçek yazı tipi,
parıltı ve satır kırılımı son videodakiyle aynı (template.py çizer). API yok."""

from __future__ import annotations

import io
from datetime import date
from functools import lru_cache

from PIL import Image

from apps.design_studio import assets, effects as fx
from apps.design_studio.design import TextStyle
from apps.design_studio.template import background_image, draw_block, headline_block
from shared.axion_template import CANVAS_WIDTH, HEADLINE_CENTER_Y

BAND = (HEADLINE_CENTER_Y - 150, HEADLINE_CENTER_Y + 150)  # başlık bandı (kanvasın üst kısmı)
SCALE = 0.5


def _band(text: str, background: Image.Image) -> Image.Image:
    canvas = background.convert("RGBA")
    block = headline_block(text, TextStyle())
    draw_block(canvas, block, fx.BlockState([fx.WordState(1.0, 0.0, 0.0) for _ in block.words]))
    band = canvas.crop((0, BAND[0], CANVAS_WIDTH, BAND[1])).convert("RGB")
    return band.resize((round(band.width * SCALE), round(band.height * SCALE)), Image.LANCZOS)


@lru_cache(maxsize=16)
def headline_preview(headline_1: str, headline_2: str, day: date) -> bytes:
    """İki başlık alt alta (videoda sırayla görünürler), JPEG."""
    background = background_image(assets.background_for_day(day))
    bands = [_band(text, background) for text in (headline_1, headline_2) if text.strip()]
    if not bands:
        return b""
    sheet = Image.new("RGB", (bands[0].width, sum(b.height for b in bands) + 6 * (len(bands) - 1)), "white")
    y = 0
    for band in bands:
        sheet.paste(band, (0, y))
        y += band.height + 6
    out = io.BytesIO()
    sheet.save(out, "JPEG", quality=85)
    return out.getvalue()
