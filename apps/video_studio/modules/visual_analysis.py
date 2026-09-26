from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Literal

import numpy as np
from openai import OpenAI
from PIL import Image, ImageOps
from pydantic import BaseModel

from shared.media_models import EditorialRole, FocusPoint, Region, VisualMetadata, VisualType


LUNA_MODEL = "gpt-5.6-luna"

LUNA_INPUT_PRICE_PER_MILLION = 0.20
LUNA_OUTPUT_PRICE_PER_MILLION = 1.20
LUNA_REASONING_EFFORT = "low"
LUNA_TIMEOUT_SECONDS = 180
# GPT-5.6 görseli 32 px'lik parçalarla sayar (parça başı 1,2 token; "auto" ayrıntıda sınır yok). Kareler yerelde 640 px
# (kadraj tespiti); Luna'ya uzun kenarı 512 px gider: dikey 640x1138 kare ~864 yerine ~173 token. Sahne türü ve özne
# kutusu için 512 yeter (384 altı kadraj isabetini düşürür).
LUNA_IMAGE_MAX_SIDE = 512
# Aynı sahnede öncekinin neredeyse aynısı olan kare gönderilmez (sabit kamera). Küçük bir bölgedeki olay (yayanın
# savrulması) blok farkını yükseltir, elenmez.
SAME_FRAME_MEAN, SAME_FRAME_BLOCK = 3.0, 12.0  # SDK'nın kendi 2 yeniden denemesi geçici ağ hatalarını karşılar.


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
    subject_left: float
    subject_right: float
    subject_top: float
    subject_bottom: float
    side_bars: bool
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

description: Türkçe, en fazla 8 kelime; kurgucunun sahneyi seçebileceği somut içerik
  (ör. "Ön kısmı hasarlı beyaz otomobil, etrafında toplanan kalabalık").
visual_type — karedeki ana özne:
  person=tek kişi, people=kalabalık/grup, place=mekân/bina/sokak, event=olay anı (kaza, yangın, kavga, müdahale),
  vehicle=araç, document=belge/kâğıt, screen=ekran/monitör, product=nesne/ürün, landscape=doğa/manzara,
  graphic=grafik/altyazı/logo, other=hiçbiri.
editorial_role — kurgudaki işlevi:
  establishing=genel plan/olay yerini tanıtan, action=olayın hareketli anı, reaction=tepki/ağlama/şaşkınlık,
  detail=yakın plan ayrıntı (hasar, kan, eşya), context=çevre/bağlam, evidence=kanıt (kamera kaydı, belge),
  portrait=konuşan kişi/röportaj, generic_broll=genel dolgu görüntü, other=hiçbiri.
location: görünen mekân türü (ör. "cadde", "dükkân içi"); belirsizse "unknown".
subject_left/right/top/bottom: haberin ana öznesinin (hasarlı araç, konuşan kişi, olay anı) TAMAMINI içeren kutu,
  0-1 (sol/üst=0, sağ/alt=1). Kare dikey kadraja kırpılacak; bu kutu kesilmeyecek. Genel planda kutu geniş olur.
side_bars: görüntü dikey (telefon) çekilmiş ve yatay karenin iki yanı bulanık kopya veya siyah dolguysa true.
confidence: 0-1."""


def _unit(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _visual_metadata(item: LunaVisual, crop: dict[str, float] | None = None) -> dict[str, Any]:
    """Luna sonucunu ortak VisualMetadata sözleşmesine dönüştürür. `crop`: Luna'ya yalnız net şerit gittiyse onun
    kaynak karedeki yeri; kutu tam kare koordinatına çevrilir."""
    left, right = sorted((_unit(item.subject_left), _unit(item.subject_right)))
    top, bottom = sorted((_unit(item.subject_top), _unit(item.subject_bottom)))
    if crop:
        left, right = crop["x"] + left * crop["width"], crop["x"] + right * crop["width"]
        top, bottom = crop["y"] + top * crop["height"], crop["y"] + bottom * crop["height"]
    return VisualMetadata(
        description=item.description.strip(),
        visual_type=item.visual_type,
        editorial_role=item.editorial_role,
        visible_people=item.visible_people,
        location=item.location.strip() or "unknown",
        text_visible=item.text_visible,
        visible_text=item.visible_text.strip(),
        focus_point=FocusPoint(x=(left + right) / 2, y=(top + bottom) / 2),
        side_bars=item.side_bars or bool(crop),
        subject_region=Region(x=left, y=top, width=right - left, height=bottom - top) if right > left and bottom > top else None,
        confidence=_unit(item.confidence),
    ).model_dump(mode="json")


def image_mime_type(image_path: Path) -> str:
    mapping = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mapping.get(image_path.suffix.lower())
    if not mime:
        raise ValueError(f"Desteklenmeyen görsel MIME türü: {image_path.suffix}")
    return mime


def exif_orientation(image: Image.Image) -> int:
    """Ham EXIF yön etiketi (1 = düz; 6 = telefonda dik çekilmiş, 90° dönmeli)."""
    value = image.getexif().get(0x0112, 1)
    return value if isinstance(value, int) and 1 <= value <= 8 else 1


def image_data_url(image_path: Path, max_side: int | None = None, crop: dict[str, float] | None = None) -> str:
    """Görsel (data URL). `crop` (0–1): yalnız bu bölge gider (yanları bulanık videoda net şerit: özne daha büyük
    görünür, token daha az)."""
    if not image_path.exists():
        raise FileNotFoundError(f"Görüntü bulunamadı: {image_path}")
    mime = image_mime_type(image_path)
    data = image_path.read_bytes()
    if max_side or crop:
        with Image.open(image_path) as image:
            turned = exif_orientation(image) != 1  # telefon fotoğrafı: Luna ekranda görüneni görsün (kadraj ona göre)
            if turned:
                image = ImageOps.exif_transpose(image)
            if crop:
                w, h = image.size
                image = image.crop((round(crop["x"] * w), round(crop["y"] * h),
                                    round((crop["x"] + crop["width"]) * w), round((crop["y"] + crop["height"]) * h)))
            if turned or crop or (max_side and max(image.size) > max_side):
                image = image.convert("RGB")
                if max_side:
                    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                image.save(buffer, "JPEG", quality=85)
                data, mime = buffer.getvalue(), "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _thumb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L").resize((64, 64)), dtype=np.float32)


def same_frame(a: np.ndarray, b: np.ndarray) -> bool:
    diff = np.abs(a - b)
    return float(diff.mean()) < SAME_FRAME_MEAN and float(diff.reshape(8, 8, 8, 8).mean((1, 3)).max()) < SAME_FRAME_BLOCK


def frames_to_send(shots: list[dict[str, Any]]) -> tuple[list[tuple[dict[str, Any], list[dict[str, Any]], Any]], dict[str, str]]:
    """Luna'ya gidecek pencereler ve kareleri; aynı sahnede öncekiyle aynı görünen kareler elenir. Tüm kareleri elenen
    pencere gönderilmez, sonucu aynı sahnenin son gönderilen penceresinden kopyalanır (window_id → kaynak window_id).
    Her pencereyle çekimin net görüntü alanı (`content_region`, yoksa None) da döner: Luna'ya yalnız o gider."""
    send, copies = [], {}
    for shot in shots:
        last, last_window = None, None
        for window in shot.get("analysis_windows", []):
            kept = []
            for frame in window.get("frames", []):
                try:
                    thumb = _thumb(Path(frame["path"]))
                except OSError:
                    kept.append(frame)
                    continue
                if last is None or not same_frame(thumb, last):
                    kept.append(frame)
                    last = thumb
            if not kept and last_window is not None:
                copies[window["window_id"]] = last_window
                continue
            send.append((window, kept or window.get("frames", [])[:1], shot.get("content_region")))
            last_window = window["window_id"]
    return send, copies


def get_usage_value(usage: Any, attribute: str, default: int = 0) -> int:
    try:
        return int(getattr(usage, attribute, default) or 0)
    except (TypeError, ValueError):
        return default


def get_reasoning_tokens(usage: Any) -> int:
    details = getattr(usage, "output_tokens_details", None)
    return get_usage_value(details, "reasoning_tokens") if details is not None else 0


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens / 1_000_000 * LUNA_INPUT_PRICE_PER_MILLION
        + output_tokens / 1_000_000 * LUNA_OUTPUT_PRICE_PER_MILLION,
        8,
    )


NEWS_CONTEXT = ("HABER (yalnız hangi görünen ayrıntının haber için önemli olduğunu seçmen ve editorial_role'ü doğru "
                "vermen için; karede görmediğin hiçbir şeyi yazma, kişileri tanımlama): {context}")


def analyze_media_with_luna(
    shots: list[dict[str, Any]],
    images: list[dict[str, Any]],
    api_key: str,
    context: str = "",
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    """Tüm shot pencerelerini ve görselleri tek Luna çağrısında analiz eder. `context` (v3.7): haberin başlıkları ve
    seslendirmesi; açıklama ve rol haberle ilgili görünen ayrıntıya göre seçilsin (kurguda Luna olay örgüsünü kurar).

    Döndürür: (window_id → VisualMetadata, image asset_id → VisualMetadata, kullanım).
    """
    windows, copies = frames_to_send(shots)
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
    if context.strip():
        content.append({"type": "input_text", "text": NEWS_CONTEXT.format(context=" ".join(context.split())[:900])})
    frame_total = 0
    crops = {window["window_id"]: crop for window, _, crop in windows}
    for window, frames, crop in windows:
        content.append(
            {
                "type": "input_text",
                "text": f"WINDOW {window['window_id']} ({window['start_seconds']:.1f}-{window['end_seconds']:.1f} sn, {len(frames)} kare)",
            }
        )
        for frame in frames:
            content.append({"type": "input_image", "image_url": image_data_url(Path(frame["path"]), LUNA_IMAGE_MAX_SIDE, crop),
                            "detail": "auto"})
            frame_total += 1
    for image in images:
        content.append({"type": "input_text", "text": f"IMAGE {image['asset_id']}"})
        content.append({"type": "input_image", "image_url": image_data_url(Path(image["path"]), LUNA_IMAGE_MAX_SIDE),
                        "detail": "auto"})
        frame_total += 1

    response = OpenAI(api_key=api_key, timeout=LUNA_TIMEOUT_SECONDS).responses.parse(
        model=LUNA_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        text_format=VisualAnalysisResponse,
        # Görsel indeksleme uzun akıl yürütme gerektirmiyor: düşük seviye yeterli ve ucuz (editör kararı).
        reasoning={"effort": LUNA_REASONING_EFFORT},
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

    window_visuals = {item.window_id: _visual_metadata(item, crops.get(item.window_id)) for item in parsed.windows}
    for window_id, source in copies.items():  # gönderilmeyen (aynı görünen) pencereler
        if source in window_visuals:
            window_visuals[window_id] = window_visuals[source]
    usage_data["skipped_windows"] = len(copies)
    image_visuals = {item.asset_id: _visual_metadata(item) for item in parsed.images}
    return window_visuals, image_visuals, usage_data
