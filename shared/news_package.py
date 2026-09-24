from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NEWS_PACKAGE_VERSION = "1.1"
LEGACY_NEWS_PACKAGE_VERSION = "1.0"
SUPPORTED_NEWS_PACKAGE_VERSIONS = {LEGACY_NEWS_PACKAGE_VERSION, NEWS_PACKAGE_VERSION}

# 1.0 dosyalarında görülen alan adları; ilk dolu olan kazanır.
LEGACY_TEXT_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "headline_1": ("headline_1", "baslik1"),
    "headline_2": ("headline_2", "baslik2"),
    "caption": ("caption", "icerik"),
    "tts_text": ("tts_text", "tts"),
    "source_text": ("source_text", "raw_text"),
}
LEGACY_PASSTHROUGH_FIELDS = (
    "created_at",
    "provider",
    "model",
    "tts_duration_target",
    "tts_actual_duration_seconds",
    "tts_voice_id",
    "tts_speed",
)


class TTSAlignment(BaseModel):
    """Character-level TTS alignment normalized to the NewsPackage contract."""

    model_config = ConfigDict(extra="forbid")

    characters: list[str] = Field(default_factory=list)
    start_seconds: list[float] = Field(default_factory=list)
    end_seconds: list[float] = Field(default_factory=list)

    @field_validator("start_seconds", "end_seconds")
    @classmethod
    def non_negative(cls, values: list[float]) -> list[float]:
        if any(value < 0 for value in values):
            raise ValueError("TTS alignment zamanları negatif olamaz.")
        return values

    @model_validator(mode="after")
    def validate_alignment(self) -> "TTSAlignment":
        lengths = {len(self.characters), len(self.start_seconds), len(self.end_seconds)}
        if len(lengths) != 1:
            raise ValueError(
                "TTS alignment characters/start_seconds/end_seconds aynı uzunlukta olmalı."
            )
        for index, (start, end) in enumerate(zip(self.start_seconds, self.end_seconds)):
            if end < start:
                raise ValueError(f"TTS alignment {index}. karakterinde end < start.")
            if index and start < self.start_seconds[index - 1]:
                raise ValueError("TTS alignment başlangıç zamanları sıralı olmalı.")
        return self

    def duration_seconds(self) -> float:
        return self.end_seconds[-1] if self.end_seconds else 0.0


def ensure_alignment_matches_text(alignment: TTSAlignment | None, tts_text: str) -> None:
    if alignment is not None and "".join(alignment.characters) != tts_text:
        raise ValueError("TTS alignment karakterleri tts_text ile birebir eşleşmiyor.")


class NewsPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = NEWS_PACKAGE_VERSION
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    headline_1: str
    headline_2: str
    caption: str
    tts_text: str
    source_text: str = ""
    provider: str = ""
    model: str = ""
    tts_duration_target: str = ""
    tts_actual_duration_seconds: float | None = None
    tts_voice_id: str = ""
    tts_speed: float | None = None
    tts_alignment: TTSAlignment | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != NEWS_PACKAGE_VERSION:
            raise ValueError(
                f"NewsPackage schema_version {NEWS_PACKAGE_VERSION} olmalı; gelen: {value!r}. "
                "Eski dosyalar için parse_news_package kullan."
            )
        return value

    @model_validator(mode="after")
    def validate_tts_alignment(self) -> "NewsPackage":
        ensure_alignment_matches_text(self.tts_alignment, self.tts_text)
        return self


def _payload_version(data: dict[str, Any]) -> str:
    version = data.get("schema_version")
    if version is None or not str(version).strip():
        return LEGACY_NEWS_PACKAGE_VERSION
    return str(version).strip()


def _first_text(*values: Any) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def migrate_news_package_v1_to_v1_1(data: dict[str, Any]) -> dict[str, Any]:
    """1.0 paketini (düz, iç içe `news` veya Türkçe alan adlı) 1.1 yapısına taşır.

    Tanınmayan alanlar kaybolmasın diye metadata["legacy_fields"] altına alınır.
    """
    if not isinstance(data, dict):
        raise TypeError("NewsPackage payload bir dict olmalı.")
    version = _payload_version(data)
    if version != LEGACY_NEWS_PACKAGE_VERSION:
        raise ValueError(f"1.0 migration için beklenen sürüm 1.0; gelen: {version!r}")

    nested = data.get("news") if isinstance(data.get("news"), dict) else {}
    migrated: dict[str, Any] = {"schema_version": NEWS_PACKAGE_VERSION}
    for field, aliases in LEGACY_TEXT_FIELD_ALIASES.items():
        migrated[field] = _first_text(
            *(nested.get(alias) for alias in aliases),
            *(data.get(alias) for alias in aliases),
        )
    for field in LEGACY_PASSTHROUGH_FIELDS:
        if data.get(field) is not None:
            migrated[field] = data[field]

    metadata = dict(data["metadata"]) if isinstance(data.get("metadata"), dict) else {}
    known = (
        {"schema_version", "news", "metadata", "tts_alignment"}
        | set(LEGACY_PASSTHROUGH_FIELDS)
        | {alias for aliases in LEGACY_TEXT_FIELD_ALIASES.values() for alias in aliases}
    )
    leftovers = {key: value for key, value in data.items() if key not in known}
    if leftovers:
        metadata["legacy_fields"] = leftovers
    migrated["metadata"] = metadata
    migrated["tts_alignment"] = None
    return migrated


def normalize_news_package_payload(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("NewsPackage payload bir dict olmalı.")
    version = _payload_version(data)
    if version == LEGACY_NEWS_PACKAGE_VERSION:
        return migrate_news_package_v1_to_v1_1(data)
    if version == NEWS_PACKAGE_VERSION:
        return data
    raise ValueError(
        f"Desteklenmeyen NewsPackage schema_version: {version!r}. "
        f"Desteklenen: {', '.join(sorted(SUPPORTED_NEWS_PACKAGE_VERSIONS))}."
    )


def parse_news_package(data: dict[str, Any]) -> NewsPackage:
    """Her sürüm için tek giriş noktası: gerekirse migrate eder, sonra doğrular."""
    return NewsPackage.model_validate(normalize_news_package_payload(data))


def build_news_package(**kwargs: Any) -> NewsPackage:
    return NewsPackage(**kwargs)


def save_news_package(package: NewsPackage, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    return target


def load_news_package(path: str | Path) -> NewsPackage:
    return parse_news_package(json.loads(Path(path).read_text(encoding="utf-8-sig")))
