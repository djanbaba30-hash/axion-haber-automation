"""Tasarım Stüdyosu belgesi (`tasarim.json`, sürüm 2): editörün şablon üzerindeki tüm seçimleri.

Her şeyin varsayılanı Canva şablonudur; editör yalnızca değiştirmek istediğini değiştirir. Sürüm 1 (v2.5.0: düz
başlık metinleri + arka plan numarası + blurlar) otomatik olarak yükseltilir. Tarayıcıdan gelen veri burada doğrulanır.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from shared.axion_template import HEADLINE_FONT_SIZE
from shared.fonts import DEFAULT_FAMILY, DEFAULT_STYLE

from .blur import clean_blurs
from .effects import FRAME_STYLES, LOGO_EFFECTS, SLOGAN_EFFECTS, TEXT_ENTER, TEXT_EXIT

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color(value: Any, default: str) -> str:
    return value if isinstance(value, str) and _HEX.match(value) else default


class TextStyle(BaseModel):
    family: str = DEFAULT_FAMILY
    style: str = DEFAULT_STYLE
    size: int = Field(HEADLINE_FONT_SIZE, ge=16, le=160)
    color: str = "#FFFFFF"
    glow: float = Field(0.38, ge=0.0, le=1.0)
    upper: bool = True

    @field_validator("color", mode="before")
    @classmethod
    def _valid_color(cls, value: Any) -> str:
        return _color(value, "#FFFFFF")


class Headline(BaseModel):
    text: str = ""
    enter: str = "yok"
    exit: str = "yok"

    @field_validator("enter", mode="before")
    @classmethod
    def _enter(cls, value: Any) -> str:
        return value if value in TEXT_ENTER else "yok"

    @field_validator("exit", mode="before")
    @classmethod
    def _exit(cls, value: Any) -> str:
        return value if value in TEXT_EXIT else "yok"


class TextLayer(TextStyle, Headline):
    """Editörün videoya eklediği yazı (şablonun parçası olur). x, y: yazının ortası, kanvasa göre 0–1."""
    id: str = "yazi1"
    size: int = Field(48, ge=16, le=160)
    upper: bool = False
    x: float = Field(0.5, ge=0.0, le=1.0)
    y: float = Field(0.88, ge=0.0, le=1.0)
    start: float = Field(0.0, ge=0.0)
    end: float = Field(5.0, ge=0.0)
    enter: str = "fade"
    exit: str = "fade"


class Toggle(BaseModel):
    enabled: bool = True
    effect: str = "yok"


class FrameSettings(BaseModel):
    style: str = "sabit"
    color: str = "#F6F6F6"
    accent: str = "#BEE1E8"
    speed: float = Field(1.0, ge=0.25, le=3.0)

    @field_validator("style", mode="before")
    @classmethod
    def _style(cls, value: Any) -> str:
        return value if value in FRAME_STYLES else "sabit"

    @field_validator("color", "accent", mode="before")
    @classmethod
    def _colors(cls, value: Any, info) -> str:
        return _color(value, "#F6F6F6" if info.field_name == "color" else "#BEE1E8")


class Design(BaseModel):
    version: int = 2
    background: str | None = None  # arka plan dosya adı; None = günün arka planı
    headline_style: TextStyle = Field(default_factory=TextStyle)
    headline_1: Headline = Field(default_factory=lambda: Headline(exit="merge"))
    headline_2: Headline = Field(default_factory=lambda: Headline(enter="merge"))
    slogans: Toggle = Field(default_factory=lambda: Toggle(effect="old_tv"))
    logo: Toggle = Field(default_factory=lambda: Toggle(effect="slow_baseline"))
    frame: FrameSettings = Field(default_factory=FrameSettings)
    texts: list[TextLayer] = Field(default_factory=list)
    blurs: list[dict[str, Any]] = Field(default_factory=list)
    rendered: str | None = None  # son videoyu üreten ayarların imzası

    @field_validator("slogans", mode="after")
    @classmethod
    def _slogan_effect(cls, value: Toggle) -> Toggle:
        value.effect = value.effect if value.effect in SLOGAN_EFFECTS else "old_tv"
        return value

    @field_validator("logo", mode="after")
    @classmethod
    def _logo_effect(cls, value: Toggle) -> Toggle:
        value.effect = value.effect if value.effect in LOGO_EFFECTS else "slow_baseline"
        return value


def load_design(raw: Any, headline_1: str, headline_2: str, duration: float) -> Design:
    """Kayıtlı belge (sürüm 1 veya 2) → Design. Başlık metni boşsa haberin başlığı kullanılır."""
    data = dict(raw) if isinstance(raw, dict) else {}
    if data.get("version") != 2:  # v2.5.0 biçimi
        background = data.get("background")
        data = {
            "background": f"arka_plan_{background}.png" if isinstance(background, int) else None,
            "headline_1": {"text": data.get("headline_1") or "", "exit": "merge"},
            "headline_2": {"text": data.get("headline_2") or "", "enter": "merge"},
            "blurs": data.get("blurs") or [],
            "rendered": None,
        }
    try:
        design = Design.model_validate(data)
    except ValueError:
        design = Design()
    design.headline_1.text = design.headline_1.text or headline_1
    design.headline_2.text = design.headline_2.text or headline_2
    design.blurs = clean_blurs(design.blurs, duration)
    for layer in design.texts:
        layer.end = min(max(layer.end, layer.start + 0.2), duration)
        layer.start = min(layer.start, max(0.0, layer.end - 0.2))
    return design


def dump_design(design: Design) -> dict[str, Any]:
    return design.model_dump(mode="json")


def signature_payload(design: Design) -> dict[str, Any]:
    """Son videoyu etkileyen her şey (imza için); `rendered` hariç."""
    payload = dump_design(design)
    payload.pop("rendered", None)
    return payload
