from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NEWS_PACKAGE_VERSION = "1.1"
SUPPORTED_NEWS_PACKAGE_VERSIONS = {"1.0", "1.1"}


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
                f"NewsPackage schema_version {NEWS_PACKAGE_VERSION} olmalı; gelen: {value!r}"
            )
        return value

    @model_validator(mode="after")
    def validate_tts_alignment(self) -> "NewsPackage":
        if self.tts_alignment is not None and "".join(self.tts_alignment.characters) != self.tts_text:
            raise ValueError("TTS alignment karakterleri tts_text ile birebir eşleşmiyor.")
        return self


def migrate_news_package_v1_to_v1_1(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate the flat NewsPackage 1.0 payload to 1.1 without rejecting it."""
    if not isinstance(data, dict):
        raise TypeError("NewsPackage payload bir dict olmalı.")
    version = str(data.get("schema_version", "1.0"))
    if version != "1.0":
        raise ValueError(f"1.0 migration için beklenen sürüm 1.0; gelen: {version!r}")
    migrated = dict(data)
    migrated["schema_version"] = NEWS_PACKAGE_VERSION
    migrated.setdefault("tts_alignment", None)
    return migrated


def normalize_news_package_payload(data: dict[str, Any]) -> dict[str, Any]:
    version = str(data.get("schema_version", "1.0"))
    if version == "1.0":
        return migrate_news_package_v1_to_v1_1(data)
    if version == NEWS_PACKAGE_VERSION:
        return data
    raise ValueError(f"Desteklenmeyen NewsPackage schema_version: {version!r}")


def build_news_package(**kwargs: Any) -> NewsPackage:
    return NewsPackage(**kwargs)


def save_news_package(package: NewsPackage, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    return target


def load_news_package(path: str | Path) -> NewsPackage:
    raw = Path(path).read_text(encoding="utf-8")
    import json
    payload = normalize_news_package_payload(json.loads(raw))
    return NewsPackage.model_validate(payload)
