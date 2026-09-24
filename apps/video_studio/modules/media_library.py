from __future__ import annotations

from typing import Any
from pathlib import Path


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}


def detect_media_type(
    filename: str,
) -> str:

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    if extension in VIDEO_EXTENSIONS:
        return "video"

    if extension in IMAGE_EXTENSIONS:
        return "image"

    raise ValueError(
        f"Desteklenmeyen medya formatı: "
        f"{extension}"
    )


def build_image_asset(
    uploaded_file,
    asset_number: int,
) -> dict[str, Any]:

    filename = Path(
        uploaded_file.name
    ).name

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    asset_id = (
        f"image_{asset_number:03d}"
    )

    return {
        "asset_id": asset_id,

        "asset_type": "image",

        "source": {
            "filename": filename,
            "extension": extension,
            "size_bytes": uploaded_file.size,
            "size_mb": round(
                uploaded_file.size
                / (1024 * 1024),
                2,
            ),
        },

        "analysis": {
            "frame_count": 1,
        },

        "path": "",
    }


def build_media_library(
    assets: list[dict[str, Any]],
    usage: dict[str, Any],
) -> dict[str, Any]:

    videos = [
        asset
        for asset in assets
        if asset.get("asset_type")
        == "video"
    ]

    images = [
        asset
        for asset in assets
        if asset.get("asset_type")
        == "image"
    ]

    return {
        "library_type": "media_library",

        "schema_version": "1.0",

        "asset_count": len(
            assets
        ),

        "video_count": len(
            videos
        ),

        "image_count": len(
            images
        ),

        "analysis": {
            "model": usage.get(
                "model",
                "",
            ),

            "api_calls": usage.get(
                "api_calls",
                0,
            ),

            "frame_count": usage.get(
                "frame_count",
                0,
            ),

            "input_tokens": usage.get(
                "input_tokens",
                0,
            ),

            "output_tokens": usage.get(
                "output_tokens",
                0,
            ),

            "reasoning_tokens": usage.get(
                "reasoning_tokens",
                0,
            ),

            "total_tokens": usage.get(
                "total_tokens",
                0,
            ),

            "estimated_cost_usd": usage.get(
                "estimated_cost_usd",
                0,
            ),
        },

        "assets": assets,
    }
