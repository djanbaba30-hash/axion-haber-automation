from __future__ import annotations

import json
from typing import Any


SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1"}


def normalize_news_package(data: dict[str, Any]) -> dict[str, Any]:
    """Axion Haber'den gelen JSON'u Video Studio'nun ortak sözleşmesine normalize eder.

    Hem mevcut Axion Haber formatını (haber alanları root seviyesinde)
    hem de nested ``news`` yapısını destekler.
    """
    if not isinstance(data, dict):
        raise ValueError("NewsPackage JSON nesnesi olmalı.")

    nested_news = data.get("news") if isinstance(data.get("news"), dict) else {}

    def first_value(*values: Any) -> str:
        for value in values:
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    normalized = {
        "schema_version": str(data.get("schema_version") or "1.0"),
        "news": {
            "headline_1": first_value(
                nested_news.get("headline_1"),
                nested_news.get("baslik1"),
                data.get("headline_1"),
                data.get("baslik1"),
            ),
            "headline_2": first_value(
                nested_news.get("headline_2"),
                nested_news.get("baslik2"),
                data.get("headline_2"),
                data.get("baslik2"),
            ),
            "caption": first_value(
                nested_news.get("caption"),
                nested_news.get("icerik"),
                data.get("caption"),
                data.get("icerik"),
            ),
            "tts_text": first_value(
                nested_news.get("tts_text"),
                nested_news.get("tts"),
                data.get("tts_text"),
                data.get("tts"),
            ),
            "source_text": first_value(
                nested_news.get("source_text"),
                nested_news.get("raw_text"),
                data.get("source_text"),
                data.get("raw_text"),
            ),
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
