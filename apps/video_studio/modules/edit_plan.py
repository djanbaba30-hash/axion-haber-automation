from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# =================================================
# TIMELINE ITEM
# =================================================


class TimelineItem(BaseModel):
    """
    Edit timeline üzerinde kullanılacak tek medya parçası.
    """

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


# =================================================
# NEWS SEGMENT
# =================================================


class NewsSegment(BaseModel):
    """
    Haber metninin edit planındaki anlamlı bölümü.
    """

    segment_id: str

    order: int

    text: str

    start_seconds: float | None = None

    end_seconds: float | None = None

    duration_seconds: float | None = None


# =================================================
# AUDIO INFO
# =================================================


class AudioInfo(BaseModel):
    """
    TTS veya başka bir ses kaynağı için temel bilgiler.
    """

    available: bool = False

    path: str | None = None

    duration_seconds: float = 0.0


# =================================================
# EDIT PLAN
# =================================================


class EditPlan(BaseModel):
    """
    Haber videosunun zaman çizelgesi.
    """

    plan_version: str = "1.0"

    timeline_duration_seconds: float = 0.0

    news_segments: list[NewsSegment] = Field(
        default_factory=list
    )

    timeline: list[TimelineItem] = Field(
        default_factory=list
    )


# =================================================
# EDIT PROJECT
# =================================================


class EditProject(BaseModel):
    """
    Haber + ses + medya + edit planını
    tek proje altında birleştirir.
    """

    project_version: str = "1.0"

    project_type: str = "news_video"

    news: dict[str, Any] = Field(
        default_factory=dict
    )

    audio: AudioInfo = Field(
        default_factory=AudioInfo
    )

    media: dict[str, Any] = Field(
        default_factory=dict
    )

    edit_plan: EditPlan = Field(
        default_factory=EditPlan
    )


# =================================================
# BUILD PROJECT
# =================================================


def build_edit_project(
    media_library: dict[str, Any],
    news_text: str = "",
    audio_path: str | None = None,
    audio_duration_seconds: float = 0.0,
) -> dict[str, Any]:
    """
    Media Library'den başlangıç EditProject oluşturur.

    Bu aşamada herhangi bir medya seçimi yapılmaz.
    Timeline daha sonra Edit Plan motoru tarafından
    doldurulacaktır.
    """

    audio_available = (
        bool(audio_path)
        and audio_duration_seconds > 0
    )

    audio = AudioInfo(
        available=audio_available,

        path=audio_path,

        duration_seconds=(
            float(audio_duration_seconds)
            if audio_available
            else 0.0
        ),
    )

    news = {
        "text": news_text,

        "character_count": len(
            news_text
        ),
    }

    project = EditProject(
        news=news,

        audio=audio,

        media=media_library,

        edit_plan=EditPlan(
            timeline_duration_seconds=(
                audio.duration_seconds
            )
        ),
    )

    return project.model_dump()


# =================================================
# ADD TIMELINE ITEM
# =================================================


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
    """
    Edit Plan'a yeni bir timeline item ekler.

    Bu fonksiyon henüz otomatik seçim yapmaz.
    Yalnızca planın teknik olarak oluşturulmasını sağlar.
    """

    timeline = edit_plan.setdefault(
        "timeline",
        []
    )

    order = len(timeline) + 1

    if timeline:

        timeline_start = float(
            timeline[-1].get(
                "timeline_end",
                0.0,
            )
        )

    else:

        timeline_start = 0.0

    duration_seconds = max(
        0.0,
        float(duration_seconds),
    )

    timeline_end = (
        timeline_start
        + duration_seconds
    )

    item = TimelineItem(
        item_id=(
            f"timeline_{order:03d}"
        ),

        media_type=media_type,

        asset_id=asset_id,

        shot_id=shot_id,

        timeline_start=round(
            timeline_start,
            3,
        ),

        timeline_end=round(
            timeline_end,
            3,
        ),

        duration_seconds=round(
            duration_seconds,
            3,
        ),

        source_start=source_start,

        source_end=source_end,

        role=role,

        order=order,

        transition_in=transition_in,

        transition_out=transition_out,
    )

    timeline.append(
        item.model_dump()
    )

    edit_plan[
        "timeline_duration_seconds"
    ] = round(
        timeline_end,
        3,
    )

    return edit_plan


# =================================================
# ADD NEWS SEGMENT
# =================================================


def add_news_segment(
    edit_plan: dict[str, Any],
    text: str,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    """
    Haber metnine ait bir segment ekler.

    Segmentlerin gerçek zamanları ileride
    TTS/transcription katmanından beslenecektir.
    """

    segments = edit_plan.setdefault(
        "news_segments",
        []
    )

    order = len(segments) + 1

    segment = NewsSegment(
        segment_id=(
            f"segment_{order:03d}"
        ),

        order=order,

        text=text,

        start_seconds=start_seconds,

        end_seconds=end_seconds,

        duration_seconds=duration_seconds,
    )

    segments.append(
        segment.model_dump()
    )

    return edit_plan
