from __future__ import annotations

import json
from typing import Any


SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1"}


def normalize_news_package(data: dict[str, Any]) -> dict[str, Any]:
    """Axion Haber'den gelen JSON'u Video Studio'nun ortak sözleşmesine normalize eder."""
    if not isinstance(data, dict):
        raise ValueError("NewsPackage JSON nesnesi olmalı.")

    news = data.get("news") if isinstance(data.get("news"), dict) else {}

    normalized = {
        "schema_version": str(data.get("schema_version") or "1.0"),
        "news": {
            "headline_1": str(news.get("headline_1", news.get("baslik1", "")) or "").strip(),
            "headline_2": str(news.get("headline_2", news.get("baslik2", "")) or "").strip(),
            "caption": str(news.get("caption", news.get("icerik", "")) or "").strip(),
            "tts_text": str(news.get("tts_text", news.get("tts", "")) or "").strip(),
            "source_text": str(news.get("source_text", news.get("raw_text", "")) or "").strip(),
        },
        "audio": data.get("audio") if isinstance(data.get("audio"), dict) else {},
        "metadata": data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
    }

    return normalized


def parse_news_package_bytes(raw_bytes: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"NewsPackage okunamadı: {exc}") from exc

    package = normalize_news_package(data)
    schema = package["schema_version"]
    if schema not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Desteklenmeyen NewsPackage sürümü: {schema}. "
            f"Desteklenen: {', '.join(sorted(SUPPORTED_SCHEMA_VERSIONS))}."
        )

    if not package["news"]["caption"] and not package["news"]["source_text"]:
        raise ValueError("NewsPackage içinde caption veya source_text bulunamadı.")

    return package
