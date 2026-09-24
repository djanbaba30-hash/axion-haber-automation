from __future__ import annotations

import base64
mimetypes
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel


LUNA_MODEL = "gpt-5.6-luna"

LUNA_INPUT_PRICE_PER_MILLION = 0.20
LUNA_OUTPUT_PRICE_PER_MILLION = 1.20


class ShotVisualAnalysis(BaseModel):
    asset_id: str
    shot_id: str
    shot_number: int

    description: str
    visual_type: str

    visible_people: bool

    location: str

    text_visible: bool
    visible_text: str

    editorial_role: str

    confidence: float


class ImageVisualAnalysis(BaseModel):
    asset_id: str

    description: str
    visual_type: str

    visible_people: bool

    location: str

    text_visible: bool
    visible_text: str

    editorial_role: str

    confidence: float


class VisualAnalysisResponse(BaseModel):
    shots: list[ShotVisualAnalysis]
    images: list[ImageVisualAnalysis]


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
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:

    if not shots and not images:

        return (
            [],
            [],
            {
                "model": LUNA_MODEL,
                "input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "api_calls": 0,
                "frame_count": 0,
                "estimated_cost_usd": 0.0,
            },
        )

    if not api_key:

        raise ValueError(
            "OPENAI_API_KEY bulunamadı."
        )

    try:
        client = OpenAI(api_key=api_key, timeout=90.0)
    except TypeError:
        client = OpenAI(api_key=api_key)

    content = [
        {
            "type": "input_text",
            "text": (
                "Bir haber videosu için görsel "
                "asset indeksleme yapıyorsun.\n\n"

                "Aşağıda bir veya daha fazla video "
                "ve ayrıca tekil görseller bulunmaktadır.\n\n"

                "Her görüntü için yalnızca gerçekten "
                "görülebilen bilgileri çıkar.\n\n"

                "Görüntüde olmayan ayrıntıları tahmin etme.\n"
                "Kişilerin kimliğini tahmin etme.\n"
                "Okunamayan yazıları tahmin etme.\n"
                "Haber metninden görselde olmayan "
                "bilgileri çıkarma.\n\n"

                "Video shot'ları için görsel indeksleme yap.\n"
                "Tekil görseller için de aynı görsel "
                "indekslemeyi yap.\n\n"

                "Kısa, somut ve edit kullanımına uygun "
                "sonuçlar üret."
            ),
        }
    ]

    total_frame_count = 0


    # =================================================
    # VIDEO SHOT'LARI
    # =================================================

    for shot in shots:

        asset_id = shot.get(
            "asset_id",
            "",
        )

        shot_number = int(
            shot.get(
                "shot_number",
                0,
            )
        )

        shot_id = (
            f"{asset_id}_shot_"
            f"{shot_number:03d}"
        )

        analysis_frames = shot.get(
            "analysis_frames",
            [],
        )

        content.append(
            {
                "type": "input_text",
                "text": (
                    f"VIDEO ASSET: {asset_id}\n"
                    f"SHOT ID: {shot_id}\n"
                    f"SHOT NUMBER: {shot_number}\n"
                    f"Zaman: "
                    f"{shot.get('start_formatted', '')} → "
                    f"{shot.get('end_formatted', '')}\n"
                    f"Frame sayısı: "
                    f"{len(analysis_frames)}"
                ),
            }
        )

        for frame in analysis_frames:

            frame_path = Path(
                frame["path"]
            )

            image_base64 = encode_image(
                frame_path
            )

            content.append(
                {
                    "type": "input_text",
                    "text": (
                        f"{shot_id} "
                        f"Frame "
                        f"{frame['frame_index']}"
                    ),
                }
            )

            content.append(
                {
                    "type": "input_image",
                    "image_url": (
                        f"data:{mimetypes.guess_type(str(frame_path))[0] or 'image/jpeg'};base64,"
                        f"{image_base64}"
                    ),
                    "detail": "auto",
                }
            )

            total_frame_count += 1


    # =================================================
    # TEKİL GÖRSELLER
    # =================================================

    for image in images:

        asset_id = image[
            "asset_id"
        ]

        image_path = Path(
            image["path"]
        )

        image_base64 = encode_image(
            image_path
        )

        content.append(
            {
                "type": "input_text",
                "text": (
                    f"IMAGE ASSET: "
                    f"{asset_id}\n"
                    "Bu tekil görsel "
                    "1 frame olarak değerlendirilmelidir."
                ),
            }
        )

        content.append(
            {
                "type": "input_image",
                "image_url": (
                    f"data:{mimetypes.guess_type(str(image_path))[0] or 'image/jpeg'};base64,"
                    f"{image_base64}"
                ),
                "detail": "auto",
            }
        )

        total_frame_count += 1


    # =================================================
    # LUNA
    # =================================================

    response = client.responses.parse(
        model=LUNA_MODEL,

        input=[
            {
                "role": "system",
                "content": (
                    "Sen bir haber video edit sistemi "
                    "için görsel asset indeksleme "
                    "motorusun.\n\n"

                    "Her sonucu kendisine verilen "
                    "asset_id ve shot_id ile ilişkilendir.\n\n"

                    "Bir görüntünün gerçekten gösterdiği "
                    "şey ile haber metninde anlatılan şeyi "
                    "birbirine karıştırma."
                ),
            },

            {
                "role": "user",
                "content": content,
            },
        ],

        text_format=VisualAnalysisResponse,
    )


    parsed = response.output_parsed

    if parsed is None:

        raise RuntimeError(
            "Luna yapılandırılmış görsel "
            "analiz sonucu döndürmedi."
        )


    # =================================================
    # USAGE
    # =================================================

    usage = getattr(
        response,
        "usage",
        None,
    )


    if usage is None:

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        reasoning_tokens = 0

    else:

        input_tokens = get_usage_value(
            usage,
            "input_tokens",
        )

        output_tokens = get_usage_value(
            usage,
            "output_tokens",
        )

        total_tokens = get_usage_value(
            usage,
            "total_tokens",
        )

        reasoning_tokens = (
            get_reasoning_tokens(
                usage
            )
        )


    estimated_cost = calculate_cost(
        input_tokens,
        output_tokens,
    )


    usage_data = {
        "model": LUNA_MODEL,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "api_calls": 1,
        "frame_count": total_frame_count,
        "estimated_cost_usd": estimated_cost,
    }


    # =================================================
    # SHOT ANALİZLERİNİ ID İLE EŞLEŞTİR
    # =================================================

    analysis_by_shot = {
        item.shot_id: item.model_dump()
        for item in parsed.shots
    }


    analyzed_shots = []


    for shot in shots:

        asset_id = shot.get(
            "asset_id",
            "",
        )

        shot_number = int(
            shot.get(
                "shot_number",
                0,
            )
        )

        shot_id = (
            f"{asset_id}_shot_"
            f"{shot_number:03d}"
        )

        shot_data = dict(
            shot
        )

        analysis = (
            analysis_by_shot.get(
                shot_id
            )
        )


        if analysis:

            shot_data[
                "visual_asset"
            ] = {
                "visual_type": analysis.get(
                    "visual_type",
                    "unknown",
                ),

                "subjects": (
                    [analysis.get(
                        "description",
                        ""
                    )]
                    if analysis.get(
                        "description",
                        ""
                    )
                    else []
                ),

                "location": analysis.get(
                    "location",
                    "unknown",
                ),

                "editorial_role": analysis.get(
                    "editorial_role",
                    "",
                ),

                "confidence": analysis.get(
                    "confidence",
                    0.0,
                ),
            }

        else:

            shot_data[
                "visual_asset"
            ] = {
                "visual_type": "unknown",
                "subjects": [],
                "location": "unknown",
                "editorial_role": "",
                "confidence": 0.0,
            }


        analyzed_shots.append(
            shot_data
        )


    # =================================================
    # IMAGE ANALİZLERİ
    # =================================================

    analysis_by_image = {
        item.asset_id: item.model_dump()
        for item in parsed.images
    }


    analyzed_images = []


    for image in images:

        asset_id = image[
            "asset_id"
        ]

        image_data = dict(
            image
        )

        analysis = (
            analysis_by_image.get(
                asset_id
            )
        )


        if analysis:

            image_data[
                "visual_asset"
            ] = {
                "visual_type": analysis.get(
                    "visual_type",
                    "unknown",
                ),

                "subjects": (
                    [analysis.get(
                        "description",
                        ""
                    )]
                    if analysis.get(
                        "description",
                        ""
                    )
                    else []
                ),

                "location": analysis.get(
                    "location",
                    "unknown",
                ),

                "editorial_role": analysis.get(
                    "editorial_role",
                    "",
                ),

                "confidence": analysis.get(
                    "confidence",
                    0.0,
                ),
            }

        else:

            image_data[
                "visual_asset"
            ] = {
                "visual_type": "unknown",
                "subjects": [],
                "location": "unknown",
                "editorial_role": "",
                "confidence": 0.0,
            }


        analyzed_images.append(
            image_data
        )


    return (
        analyzed_shots,
        analyzed_images,
        usage_data,
    )
