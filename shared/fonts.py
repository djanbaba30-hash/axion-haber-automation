"""Yazı tipi kaydı: `assets/sablon/fontlar/` (repodaki) + `data/varliklar/fontlar/` (editörün uygulamadan ekledikleri).

Aile ve kalınlık font dosyasının kendi bilgisinden okunur. Değişken (variable) fontların adlandırılmış kalınlıkları
(Regular, Medium, Bold...) ayrı seçenek olarak görünür. Metin her zaman Pillow ile çizilir (FFmpeg yazı çizmez),
önizleme ile son video aynı görünür.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPO_FONT_DIR = ROOT / "assets" / "sablon" / "fontlar"
FONT_EXTENSIONS = {".ttf", ".otf"}
DEFAULT_FAMILY = "Google Sans"
DEFAULT_STYLE = "Bold"

_WEIGHT_ORDER = ["thin", "extralight", "light", "regular", "book", "medium", "semibold", "bold", "extrabold", "black"]


def user_font_dir() -> Path:
    return Path(os.environ.get("AXION_DATA_DIR") or ROOT / "data") / "varliklar" / "fontlar"


def font_dirs() -> list[Path]:
    return [REPO_FONT_DIR, user_font_dir()]


@dataclass(frozen=True)
class FontFace:
    family: str
    style: str
    path: Path
    variation: str | None = None  # değişken fontta adlandırılmış kalınlık


def _style_key(style: str) -> tuple[int, int, str]:
    lowered = style.lower().replace(" ", "").replace("-", "")
    italic = int("italic" in lowered or "oblique" in lowered)
    base = lowered.replace("italic", "").replace("oblique", "") or "regular"
    weight = next((i for i, name in enumerate(_WEIGHT_ORDER) if base == name), len(_WEIGHT_ORDER))
    return italic, weight, style


@lru_cache(maxsize=64)
def _file_bytes(path: str, mtime: float) -> bytes:
    return Path(path).read_bytes()


def _read(path: Path) -> bytes:
    return _file_bytes(str(path), path.stat().st_mtime)


def _faces_in(path: Path) -> list[FontFace]:
    try:
        font = ImageFont.truetype(io.BytesIO(_read(path)), 20)
    except OSError:
        return []
    family, style = (name or "" for name in font.getname())
    family = family or path.stem
    try:
        variations = [v.decode() if isinstance(v, bytes) else str(v) for v in font.get_variation_names()]
    except (OSError, AttributeError):
        variations = []
    if variations:
        return [FontFace(family, name, path, name) for name in dict.fromkeys(variations)]
    return [FontFace(family, style or "Regular", path)]


def _signature() -> tuple:
    files = []
    for folder in font_dirs():
        if folder.is_dir():
            files += [(str(p), p.stat().st_mtime) for p in sorted(folder.iterdir()) if p.suffix.lower() in FONT_EXTENSIONS]
    return tuple(files)


@lru_cache(maxsize=4)
def _scan(signature: tuple) -> dict[str, dict[str, FontFace]]:
    registry: dict[str, dict[str, FontFace]] = {}
    for path, _ in signature:
        for face in _faces_in(Path(path)):
            registry.setdefault(face.family, {}).setdefault(face.style, face)  # repodaki önce gelir
    return {
        family: dict(sorted(styles.items(), key=lambda item: _style_key(item[0])))
        for family, styles in sorted(registry.items())
    }


def registry() -> dict[str, dict[str, FontFace]]:
    return _scan(_signature())


def families() -> dict[str, list[str]]:
    """Aile → kalınlıklar (inceden kalına)."""
    return {family: list(styles) for family, styles in registry().items()}


def resolve(family: str | None, style: str | None) -> FontFace:
    """İstenen yüz yoksa aynı ailenin en yakın kalınlığı, o da yoksa varsayılan (Google Sans Bold)."""
    faces = registry()
    styles = faces.get(family or "") or faces.get(DEFAULT_FAMILY) or next(iter(faces.values()), None)
    if not styles:
        raise FileNotFoundError("Yazı tipi bulunamadı: assets/sablon/fontlar klasörü boş.")
    if style in styles:
        return styles[style]
    wanted = _style_key(style or DEFAULT_STYLE)
    return min(styles.values(), key=lambda f: (abs(_style_key(f.style)[1] - wanted[1]), _style_key(f.style)[0] != wanted[0]))


@lru_cache(maxsize=64)
def _load(path: str, mtime: float, variation: str | None, size: int) -> ImageFont.FreeTypeFont:
    # Bellekten: Windows'ta yol Türkçe karakter içerirse FreeType dosyayı açamayabiliyor.
    font = ImageFont.truetype(io.BytesIO(_file_bytes(path, mtime)), size)
    if variation:
        font.set_variation_by_name(variation)
    return font


def load_font(family: str | None = None, style: str | None = None, size: int = 58) -> ImageFont.FreeTypeFont:
    face = resolve(family, style)
    return _load(str(face.path), face.path.stat().st_mtime, face.variation, int(size))
