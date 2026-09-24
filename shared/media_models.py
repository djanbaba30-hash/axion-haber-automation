from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


MEDIA_SCHEMA_VERSION = "1.1"


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"


class VisualType(str, Enum):
    PERSON = "person"
    PEOPLE = "people"
    PLACE = "place"
    EVENT = "event"
    VEHICLE = "vehicle"
    DOCUMENT = "document"
    SCREEN = "screen"
    PRODUCT = "product"
    LANDSCAPE = "landscape"
    GRAPHIC = "graphic"
    OTHER = "other"
    UNKNOWN = "unknown"


class EditorialRole(str, Enum):
    ESTABLISHING = "establishing"
    ACTION = "action"
    REACTION = "reaction"
    DETAIL = "detail"
    CONTEXT = "context"
    EVIDENCE = "evidence"
    PORTRAIT = "portrait"
    GENERIC_BROLL = "generic_broll"
    OTHER = "other"
    UNKNOWN = "unknown"


class FocusPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float = 0.5
    y: float = 0.5

    @field_validator("x", "y")
    @classmethod
    def normalized(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Odak koordinatları 0–1 aralığında olmalı.")
        return value


class Region(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    width: float
    height: float

    @model_validator(mode="after")
    def within_bounds(self) -> "Region":
        if min(self.x, self.y, self.width, self.height) < 0:
            raise ValueError("Bölge değerleri negatif olamaz.")
        if max(self.x, self.y, self.width, self.height) > 1:
            raise ValueError("Bölge değerleri 0–1 aralığında olmalı.")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("Region x+width ve y+height 1'i aşamaz.")
        return self


class VisualMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = ""
    visual_type: VisualType = VisualType.UNKNOWN
    visible_people: bool = False
    location: str = "unknown"
    text_visible: bool = False
    visible_text: str = ""
    text_region: Region | None = None
    focus_point: FocusPoint | None = None
    safe_for_center_crop: bool | None = None
    editorial_role: EditorialRole = EditorialRole.UNKNOWN
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence 0–1 aralığında olmalı.")
        return value


class DisplayGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    width: int
    height: int
    rotation_degrees: int = 0

    @field_validator("width", "height")
    @classmethod
    def positive_dimension(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Görüntü boyutları pozitif olmalı.")
        return value

    @field_validator("rotation_degrees", mode="before")
    @classmethod
    def normalize_rotation(cls, value: int | float) -> int:
        normalized = int(value) % 360
        if normalized not in {0, 90, 180, 270}:
            raise ValueError("Rotasyon 0/90/180/270 dereceye normalize edilebilmeli.")
        return normalized


class ImageGeometry(DisplayGeometry):
    exif_orientation: int | None = None


class VideoGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    encoded_width: int
    encoded_height: int
    display: DisplayGeometry
    fps: float | None = None
    codec: str | None = None
    pixel_format: str | None = None

    @field_validator("encoded_width", "encoded_height")
    @classmethod
    def positive_dimension(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Encoded video boyutları pozitif olmalı.")
        return value


class AudioTechnicalInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None


class MediaSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str
    extension: str = ""
    sha256: str
    original_path: str | None = None
    proxy_path: str | None = None
    size_bytes: int = 0
    duration_seconds: float | None = None

    @field_validator("sha256")
    @classmethod
    def valid_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("sha256 64 karakter hexadecimal olmalı.")
        return value.lower()


class AnalysisFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frame_index: int
    timestamp_seconds: float
    path: str

    @field_validator("frame_index", "timestamp_seconds")
    @classmethod
    def non_negative(cls, value):
        if value < 0:
            raise ValueError("Frame index/zamanı negatif olamaz.")
        return value


class AnalysisWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_id: str
    shot_id: str
    start_seconds: float
    end_seconds: float
    frames: list[AnalysisFrame] = Field(default_factory=list)
    visual: VisualMetadata | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "AnalysisWindow":
        if self.start_seconds >= self.end_seconds:
            raise ValueError("AnalysisWindow start_seconds < end_seconds olmalı.")
        return self


class Shot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shot_id: str
    asset_id: str
    shot_number: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    analysis_windows: list[AnalysisWindow] = Field(default_factory=list)
    visual: VisualMetadata | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "Shot":
        if self.start_seconds >= self.end_seconds:
            raise ValueError("Shot start_seconds < end_seconds olmalı.")
        expected = self.end_seconds - self.start_seconds
        if abs(self.duration_seconds - expected) > 0.01:
            raise ValueError("Shot duration_seconds start/end ile tutarlı olmalı.")
        for window in self.analysis_windows:
            if window.shot_id != self.shot_id:
                raise ValueError("AnalysisWindow shot_id, parent Shot ile eşleşmeli.")
        return self


class VideoAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    asset_type: Literal["video"] = "video"
    schema_version: str = MEDIA_SCHEMA_VERSION
    source: MediaSource
    geometry: VideoGeometry
    audio: AudioTechnicalInfo | None = None
    shots: list[Shot] = Field(default_factory=list)
    analysis_model: str = ""
    analysis_prompt_version: str = ""
    analysis_frame_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    asset_type: Literal["image"] = "image"
    schema_version: str = MEDIA_SCHEMA_VERSION
    source: MediaSource
    geometry: ImageGeometry | None = None
    visual: VisualMetadata | None = None
    analysis_model: str = ""
    analysis_prompt_version: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


MediaAsset = Annotated[VideoAsset | ImageAsset, Field(discriminator="asset_type")]


class MediaAssetRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    asset_type: MediaType


class MediaLibrary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    library_type: Literal["media_library"] = "media_library"
    schema_version: str = MEDIA_SCHEMA_VERSION
    assets: list[MediaAsset] = Field(default_factory=list)
    analysis: dict[str, Any] = Field(default_factory=dict)

    @property
    def asset_refs(self) -> list[MediaAssetRef]:
        return [MediaAssetRef(asset_id=a.asset_id, asset_type=a.asset_type) for a in self.assets]
