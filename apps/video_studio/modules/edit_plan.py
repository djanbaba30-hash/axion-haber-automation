from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


PROJECT_VERSION = "1.1"
PLAN_VERSION = "1.1"


class TimelineItem(BaseModel):
    """Edit timeline üzerinde kullanılacak tek medya parçası."""

    item_id: str
    media_type: str
    asset_id: str
    shot_id: str | None = None
    timeline_start: float
    timeline_end: float
    duration_seconds: float
    source_start: float | None = None
    source_end: float | None = None
    role: str = "b_roll"
    order: int
    transition_in: str | None = None
    transition_out: str | None = None


class NewsSegment(BaseModel):
    """Edit planındaki anlamlı haber/TTS bölümü."""

    segment_id: str
    order: int
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None


class AudioInfo(BaseModel):
    """TTS veya başka bir ses kaynağının proje içindeki referansı."""

    available: bool = False
    path: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    duration_seconds: float = 0.0


class EditPlan(BaseModel):
    plan_version: str = PLAN_VERSION
    timeline_duration_seconds: float = 0.0
    news_segments: list[NewsSegment] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)


class EditProject(BaseModel):
    project_version: str = PROJECT_VERSION
    project_type: str = "news_video"
    news: dict[str, Any] = Field(default_factory=dict)
    audio: AudioInfo = Field(default_factory=AudioInfo)
    media: dict[str, Any] = Field(default_factory=dict)
    edit_plan: EditPlan = Field(default_factory=EditPlan)


def _clean_news_package(news_package: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(news_package, dict):
        return {}

    news = news_package.get("news")
    if not isinstance(news, dict):
        news = {}

    # Farklı sürümlerde görülebilecek alan adlarını kontrollü biçimde destekle.
    return {
        "schema_version": news_package.get("schema_version"),
        "headline_1": news.get("headline_1", news.get("baslik1", "")) or "",
        "headline_2": news.get("headline_2", news.get("baslik2", "")) or "",
        "caption": news.get("caption", news.get("icerik", "")) or "",
        "tts_text": news.get("tts_text", news.get("tts", "")) or "",
        "source_text": news.get("source_text", news.get("raw_text", "")) or "",
        "metadata": news_package.get("metadata") or {},
    }


def build_edit_project(
    media_library: dict[str, Any],
    news_text: str = "",
    audio_path: str | None = None,
    audio_duration_seconds: float = 0.0,
    news_package: dict[str, Any] | None = None,
    audio_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Media Library + haber + TTS'den başlangıç EditProject oluşturur.

    Bu fonksiyon medya seçimi yapmaz. Edit Plan timeline'ı sonraki katmanlarda
    doldurulur. TTS süresi, başlangıç timeline süresinin tek kaynağıdır.
    """

    package = _clean_news_package(news_package)
    audio_meta = audio_metadata if isinstance(audio_metadata, dict) else {}

    package_caption = str(package.get("caption") or "").strip()
    package_tts = str(package.get("tts_text") or "").strip()
    package_source = str(package.get("source_text") or "").strip()

    final_news_text = str(news_text or "").strip()
    if not final_news_text and package_caption:
        final_news_text = package_caption

    duration = float(audio_duration_seconds or 0.0)
    audio_available = bool(audio_path) and duration > 0

    audio = AudioInfo(
        available=audio_available,
        path=str(audio_path) if audio_available else None,
        filename=audio_meta.get("filename"),
        mime_type=audio_meta.get("mime_type"),
        size_bytes=audio_meta.get("size_bytes"),
        duration_seconds=round(duration, 3) if audio_available else 0.0,
    )

    news = {
        "text": final_news_text,
        "character_count": len(final_news_text),
        "headline_1": package.get("headline_1", ""),
        "headline_2": package.get("headline_2", ""),
        "caption": package_caption or final_news_text,
        "tts_text": package_tts,
        "source_text": package_source,
        "package_schema_version": package.get("schema_version"),
        "package_metadata": package.get("metadata", {}),
    }

    project = EditProject(
        project_version=PROJECT_VERSION,
        news=news,
        audio=audio,
        media=media_library or {},
        edit_plan=EditPlan(
            timeline_duration_seconds=audio.duration_seconds,
        ),
    )

    return project.model_dump()


def validate_edit_project(project: dict[str, Any]) -> list[str]:
    """Render/Edit Planner öncesi deterministik proje bütünlük kontrolü."""

    errors: list[str] = []
    if not isinstance(project, dict):
        return ["EditProject bir sözlük olmalı."]

    if project.get("project_type") != "news_video":
        errors.append("project_type news_video olmalı.")

    news = project.get("news") or {}
    audio = project.get("audio") or {}
    media = project.get("media") or {}
    plan = project.get("edit_plan") or {}

    if not str(news.get("text", "")).strip():
        errors.append("Haber metni boş.")

    if not audio.get("available"):
        errors.append("Kullanılabilir TTS sesi yok.")
    elif float(audio.get("duration_seconds", 0) or 0) <= 0:
        errors.append("TTS süresi geçersiz.")

    if not media.get("assets"):
        errors.append("Media Library boş.")

    expected_duration = float(audio.get("duration_seconds", 0) or 0)
    plan_duration = float(plan.get("timeline_duration_seconds", 0) or 0)
    if expected_duration > 0 and abs(expected_duration - plan_duration) > 0.01:
        errors.append("Edit Plan başlangıç süresi TTS süresiyle eşleşmiyor.")

    return errors


def add_timeline_item(
    edit_plan: dict[str, Any],
    media_type: str,
    asset_id: str,
    duration_seconds: float,
    source_start: float | None = None,
    source_end: float | None = None,
    shot_id: str | None = None,
    role: str = "b_roll",
    transition_in: str | None = None,
    transition_out: str | None = None,
) -> dict[str, Any]:
    timeline = edit_plan.setdefault("timeline", [])
    order = len(timeline) + 1
    timeline_start = float(timeline[-1].get("timeline_end", 0.0)) if timeline else 0.0
    duration_seconds = max(0.0, float(duration_seconds))
    timeline_end = timeline_start + duration_seconds

    item = TimelineItem(
        item_id=f"timeline_{order:03d}",
        media_type=media_type,
        asset_id=asset_id,
        shot_id=shot_id,
        timeline_start=round(timeline_start, 3),
        timeline_end=round(timeline_end, 3),
        duration_seconds=round(duration_seconds, 3),
        source_start=source_start,
        source_end=source_end,
        role=role,
        order=order,
        transition_in=transition_in,
        transition_out=transition_out,
    )

    timeline.append(item.model_dump())
    edit_plan["timeline_duration_seconds"] = round(timeline_end, 3)
    return edit_plan


def add_news_segment(
    edit_plan: dict[str, Any],
    text: str,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    segments = edit_plan.setdefault("news_segments", [])
    order = len(segments) + 1

    segment = NewsSegment(
        segment_id=f"segment_{order:03d}",
        order=order,
        text=str(text or "").strip(),
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
    )

    segments.append(segment.model_dump())
    return edit_plan
