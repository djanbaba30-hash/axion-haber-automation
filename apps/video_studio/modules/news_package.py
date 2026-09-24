from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from shared.news_package import NewsPackage, parse_news_package


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


def parse_news_package_bytes(raw_bytes: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"NewsPackage okunamadı: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("NewsPackage JSON nesnesi olmalı.")

    try:
        package = parse_news_package(data)
    except ValidationError as exc:
        raise ValueError(f"NewsPackage doğrulanamadı: {exc}") from exc

    if not package.caption.strip() and not package.source_text.strip():
        raise ValueError("NewsPackage içinde caption veya source_text bulunamadı.")

    return news_package_to_state(package)
