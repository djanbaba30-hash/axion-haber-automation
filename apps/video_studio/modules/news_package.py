from __future__ import annotations

from typing import Any

from shared.news_package import NewsPackage


def news_package_to_state(package: NewsPackage) -> dict[str, Any]:
    """Video Studio session state'inde kullanılan sözlük görünümü."""
    return {
        "schema_version": package.schema_version,
        "news": {
            "headline_1": package.headline_1,
            "headline_2": package.headline_2,
            "caption": package.caption,
            "tts_text": package.tts_text,
            "source_text": package.source_text,
        },
        "tts_alignment": (
            package.tts_alignment.model_dump() if package.tts_alignment else None
        ),
        "metadata": package.metadata,
    }
