from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


NEWS_PACKAGE_VERSION = "1.0"


class NewsPackage(BaseModel):
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
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_news_package(**kwargs: Any) -> NewsPackage:
    return NewsPackage(**kwargs)


def save_news_package(package: NewsPackage, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.model_dump_json(indent=2), encoding="utf-8")
    return target


def load_news_package(path: str | Path) -> NewsPackage:
    return NewsPackage.model_validate_json(Path(path).read_text(encoding="utf-8"))
