from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel

from shared.media_models import EditorialRole, VisualMetadata, VisualType


LUNA_MODEL = "gpt-5.6-luna"

LUNA_INPUT_PRICE_PER_MILLION = 0.20
LUNA_OUTPUT_PRICE_PER_MILLION = 1.20


# Luna sabit kategorilerden seçmek zorunda (structured output enum); "unknown" seçeneği yok.
LunaVisualType = Literal[tuple(v.value for v in VisualType if v is not VisualType.UNKNOWN)]
LunaEditorialRole = Literal[tuple(v.value for v in EditorialRole if v is not EditorialRole.UNKNOWN)]


class LunaVisual(BaseModel):
    description: str
    visual_type: LunaVisualType
    editorial_role: LunaEditorialRole
    visible_people: bool
    location: str
    text_visible: bool
    visible_text: str
    confidence: float


class _WindowId(BaseModel):
    window_id: str


class _AssetId(BaseModel):
    asset_id: str


# Kimlik alanı şemada ilk sırada olsun diye önce yazılan taban sonda (pydantic alan sırası).
class WindowVisualAnalysis(LunaVisual, _WindowId):
    pass


class ImageVisualAnalysis(LunaVisual, _AssetId):
    pass


class VisualAnalysisResponse(BaseModel):
    windows: list[WindowVisualAnalysis]
    images: list[ImageVisualAnalysis]


SYSTEM_PROMPT = """Haber videosu kurgu sistemi için görsel indeksleme yapıyorsun.
Her WINDOW ve IMAGE için, verilen id ile tam bir sonuç döndür. Yalnızca karede görüneni yaz;
kimlik, okunamayan yazı veya haber metni tahmini yapma.

description: Türkçe, tek kısa cümle; kurgucunun sahneyi seçebileceği somut içerik
  (ör. "Ön kısmı hasar görmüş beyaz otomobil ve etrafında toplanan kalabalık").
visual_type — karedeki ana özne:
  person=tek kişi, people=kalabalık/grup, place=mekân/bina/sokak, event=olay anı (kaza, yangın, kavga, müdahale),
  vehicle=araç, document=belge/kâğıt, screen=ekran/monitör, product=nesne/ürün, landscape=doğa/manzara,
  graphic=grafik/altyazı/logo, other=hiçbiri.
editorial_role — kurgudaki işlevi:
  establishing=genel plan/olay yerini tanıtan, action=olayın hareketli anı, reaction=tepki/ağlama/şaşkınlık,
  detail=yakın plan ayrıntı (hasar, kan, eşya), context=çevre/bağlam, evidence=kanıt (kamera kaydı, belge),
  portrait=konuşan kişi/röportaj, generic_broll=genel dolgu görüntü, other=hiçbiri.
location: görünen mekân türü (ör. "cadde", "dükkân içi"); belirsizse "unknown".
confidence: 0-1."""


def _visual_metadata(item: LunaVisual) -> dict[str, Any]:
    """Luna sonucunu ortak VisualMetadata sözleşmesine dönüştürür."""
    return VisualMetadata(
        description=item.description.strip(),
        visual_type=item.visual_type,
        editorial_role=item.editorial_role,
        visible_people=item.visible_people,
        location=item.location.strip() or "unknown",
        text_visible=item.text_visible,
        visible_text=item.visible_text.strip(),
        confidence=min(1.0, max(0.0, item.confidence)),
    ).model_dump(mode="json")


def image_mime_type(image_path: Path) -> str:
    mapping = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mapping.get(image_path.suffix.lower())
    if not mime:
        raise ValueError(f"Desteklenmeyen görsel MIME türü: {image_path.suffix}")
    return mime


def encode_image(
    image_path: Path,
) -> str:

    if not image_path.exists():

        raise FileNotFoundError(
            f"Görüntü bulunamadı: "
            f"{image_path}"
        )

    image_bytes = (
        image_path.read_bytes()
    )

    return base64.b64encode(
        image_bytes
    ).decode("utf-8")


def image_data_url(
    image_path: Path,
) -> str:
    return f"data:{image_mime_type(image_path)};base64,{encode_image(image_path)}"


def get_usage_value(
    usage: Any,
    attribute: str,
    default: int = 0,
) -> int:

    value = getattr(
        usage,
        attribute,
        default,
    )

    try:

        return int(
            value or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def get_reasoning_tokens(
    usage: Any,
) -> int:

    output_details = getattr(
        usage,
        "output_tokens_details",
        None,
    )

    if output_details is None:
        return 0

    return get_usage_value(
        output_details,
        "reasoning_tokens",
        0,
    )


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
) -> float:

    input_cost = (
        input_tokens
        / 1_000_000
        * LUNA_INPUT_PRICE_PER_MILLION
    )

    output_cost = (
        output_tokens
        / 1_000_000
        * LUNA_OUTPUT_PRICE_PER_MILLION
    )

    return round(
        input_cost + output_cost,
        8,
    )


def analyze_media_with_luna(
    shots: list[dict[str, Any]],
    images: list[dict[str, Any]],
    api_key: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    """Tüm shot pencerelerini ve görselleri tek Luna çağrısında analiz eder.

    Döndürür: (window_id → VisualMetadata, image asset_id → VisualMetadata, kullanım).
    """
    windows = [window for shot in shots for window in shot.get("analysis_windows", [])]
    usage_data = {
        "model": LUNA_MODEL,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "api_calls": 0,
        "frame_count": 0,
        "estimated_cost_usd": 0.0,
    }
    if not windows and not images:
        return {}, {}, usage_data
    if not api_key:
        raise ValueError("OPENAI_API_KEY bulunamadı.")

    content: list[dict[str, Any]] = []
    frame_total = 0
    for window in windows:
        frames = window.get("frames", [])
        content.append(
            {
                "type": "input_text",
                "text": f"WINDOW {window['window_id']} ({window['start_seconds']:.1f}-{window['end_seconds']:.1f} sn, {len(frames)} kare)",
            }
        )
        for frame in frames:
            content.append({"type": "input_image", "image_url": image_data_url(Path(frame["path"])), "detail": "auto"})
            frame_total += 1
    for image in images:
        content.append({"type": "input_text", "text": f"IMAGE {image['asset_id']}"})
        content.append({"type": "input_image", "image_url": image_data_url(Path(image["path"])), "detail": "auto"})
        frame_total += 1

    response = OpenAI(api_key=api_key).responses.parse(
        model=LUNA_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        text_format=VisualAnalysisResponse,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("Luna yapılandırılmış görsel analiz sonucu döndürmedi.")

    usage = getattr(response, "usage", None)
    if usage is not None:
        input_tokens = get_usage_value(usage, "input_tokens")
        output_tokens = get_usage_value(usage, "output_tokens")
        usage_data.update(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=get_reasoning_tokens(usage),
            total_tokens=get_usage_value(usage, "total_tokens"),
            estimated_cost_usd=calculate_cost(input_tokens, output_tokens),
        )
    usage_data.update(api_calls=1, frame_count=frame_total)

    window_visuals = {item.window_id: _visual_metadata(item) for item in parsed.windows}
    image_visuals = {item.asset_id: _visual_metadata(item) for item in parsed.images}
    return window_visuals, image_visuals, usage_data
