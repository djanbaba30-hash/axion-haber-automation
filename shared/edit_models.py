from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from .media_models import MediaAssetRef
from .news_package import TTSAlignment


EDIT_PROJECT_VERSION = "2.1"
EDIT_PLAN_VERSION = "2.1"


class FramingMode(str, Enum):
    FILL_CROP = "fill_crop"
    FIT_BLUR = "fit_blur"
    VERTICAL_CROP = "vertical_crop"


class ClipOrigin(str, Enum):
    LLM = "llm"
    USER = "user"


class TrackKind(str, Enum):
    VIDEO = "video"
    OVERLAY = "overlay"
    AUDIO = "audio"


class TransitionType(str, Enum):
    NONE = "none"
    CUT = "cut"
    FADE = "fade"


class ClipType(str, Enum):
    MEDIA = "media"
    OVERLAY_TEXT = "overlay_text"
    AUDIO = "audio"


class Framing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: FramingMode = FramingMode.FILL_CROP
    focus_x: float = 0.5
    focus_y: float = 0.5
    zoom: float = 1.0

    @field_validator("focus_x", "focus_y")
    @classmethod
    def normalized_focus(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("focus_x/focus_y 0–1 aralığında olmalı.")
        return value

    @field_validator("zoom")
    @classmethod
    def positive_zoom(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("zoom pozitif olmalı.")
        return value


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: TransitionType = TransitionType.NONE
    duration_f: int = 0

    @field_validator("duration_f")
    @classmethod
    def non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("transition duration_f negatif olamaz.")
        return value


class Clip(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    clip_type: ClipType = ClipType.MEDIA
    asset_id: str | None = None
    shot_id: str | None = None
    segment_id: str | None = None
    source_in_s: float | None = None
    source_out_s: float | None = None
    start_f: int
    duration_f: int
    speed: float = 1.0
    framing: Framing = Field(default_factory=Framing)
    transition_in: Transition = Field(default_factory=Transition)
    transition_out: Transition = Field(default_factory=Transition)
    locked: bool = False
    origin: ClipOrigin = ClipOrigin.LLM
    reason: str = ""
    confidence: float | None = None
    text: str | None = None

    @field_validator("start_f", "duration_f")
    @classmethod
    def non_negative_frames(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Timeline frame değerleri negatif olamaz.")
        return value

    @field_validator("source_in_s", "source_out_s")
    @classmethod
    def non_negative_source(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("source zamanları negatif olamaz.")
        return value

    @field_validator("speed")
    @classmethod
    def positive_speed(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("speed pozitif olmalı.")
        return value

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("confidence 0–1 aralığında olmalı.")
        return value

    @model_validator(mode="after")
    def validate_clip(self) -> "Clip":
        if self.duration_f <= 0:
            raise ValueError("Clip duration_f sıfırdan büyük olmalı.")
        if self.clip_type == ClipType.OVERLAY_TEXT:
            if self.asset_id is not None or not self.text or not self.text.strip():
                raise ValueError("overlay_text clip asset_id içermemeli ve text taşımalı.")
            return self
        if not self.asset_id:
            raise ValueError("media/audio clip asset_id taşımalı.")
        if self.source_in_s is None or self.source_out_s is None:
            raise ValueError("media/audio clip source_in_s/source_out_s taşımalı.")
        if self.source_in_s >= self.source_out_s:
            raise ValueError("source_in_s < source_out_s olmalı.")
        return self


class Track(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: TrackKind
    clips: list[Clip] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_clip_kinds(self) -> "Track":
        expected = {
            TrackKind.VIDEO: {ClipType.MEDIA},
            TrackKind.OVERLAY: {ClipType.OVERLAY_TEXT},
            TrackKind.AUDIO: {ClipType.AUDIO},
        }[self.kind]
        for clip in self.clips:
            if clip.clip_type not in expected:
                raise ValueError(f"{self.kind.value} track içinde {clip.clip_type.value} clip kullanılamaz.")
        return self


class NewsSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segment_id: str
    order: int
    text: str
    char_start: int
    char_end: int

    @field_validator("order", "char_start", "char_end")
    @classmethod
    def non_negative_or_positive(cls, value: int, info) -> int:
        if info.field_name == "order" and value < 1:
            raise ValueError("segment order 1 veya daha büyük olmalı.")
        if info.field_name != "order" and value < 0:
            raise ValueError("character index negatif olamaz.")
        return value

    @model_validator(mode="after")
    def validate_chars(self) -> "NewsSegment":
        if self.char_start >= self.char_end:
            raise ValueError("char_start < char_end olmalı.")
        if len(self.text) != self.char_end - self.char_start:
            raise ValueError("NewsSegment text uzunluğu char_start/char_end ile eşleşmeli.")
        return self


class Timeline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fps: int = 30
    width: int = 1080
    height: int = 1440
    tracks: list[Track] = Field(default_factory=list)

    @field_validator("fps", "width", "height")
    @classmethod
    def positive_integer(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Timeline fps/width/height pozitif olmalı.")
        return value

    @model_validator(mode="after")
    def validate_clip_durations(self) -> "Timeline":
        for track in self.tracks:
            for clip in track.clips:
                if clip.clip_type == ClipType.OVERLAY_TEXT:
                    continue
                source_duration = (clip.source_out_s or 0) - (clip.source_in_s or 0)
                expected_frames = round((source_duration / clip.speed) * self.fps)
                if abs(expected_frames - clip.duration_f) > 1:
                    raise ValueError(f"Clip {clip.id} duration_f, source süresi/speed ile tutarlı değil.")
        return self


class AudioReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    path: str | None = None
    filename: str | None = None
    mime_type: str = "audio/mpeg"
    duration_seconds: float
    sha256: str | None = None


class EditPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_version: str = EDIT_PLAN_VERSION
    status: Literal["draft", "approved", "rendered"] = "draft"
    segments: list[NewsSegment] = Field(default_factory=list)
    timeline: Timeline = Field(default_factory=Timeline)
    snapshot_id: str | None = None


class NewsReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    package_schema_version: str
    headline_1: str
    headline_2: str
    caption: str
    tts_text: str
    source_text: str = ""
    tts_alignment: TTSAlignment | None = None


class EditProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_version: str = EDIT_PROJECT_VERSION
    project_type: Literal["news_video"] = "news_video"
    project_id: str
    library_id: str
    news: NewsReference
    audio: AudioReference
    media: list[MediaAssetRef] = Field(default_factory=list)
    edit_plan: EditPlan = Field(default_factory=EditPlan)
