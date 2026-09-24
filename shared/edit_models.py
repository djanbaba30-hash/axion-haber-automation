from __future__ import annotations

import math
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from .axion_template import MIN_VIDEO_SECONDS, video_seconds
from .media_models import MediaAssetRef, Region
from .news_package import TTSAlignment, ensure_alignment_matches_text


EDIT_PROJECT_VERSION = "2.1"
EDIT_PLAN_VERSION = "2.1"


class FramingMode(str, Enum):
    """Kaynağın timeline kadrajına (ör. şablonun 960x1226 video alanı) yerleştirilme biçimi.

    FILL_CROP: Kaynak kadrajı tamamen dolduracak kadar ölçeklenir; taşan kısım
        focus_x/focus_y merkez alınarak kırpılır. Yatay videodan dikey kesit de budur.
    FIT_BLUR: Kaynağın tamamı kadraja sığdırılır; boş kalan alan aynı kaynağın
        büyütülmüş ve bulanıklaştırılmış kopyasıyla doldurulur.
    """

    FILL_CROP = "fill_crop"
    FIT_BLUR = "fit_blur"


class ClipOrigin(str, Enum):
    LLM = "llm"
    RULE = "rule"  # Kural tabanlı kaba kurgu (API'siz)
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
    """content_region: kaynakta önce kırpılacak asıl görüntü alanı (0–1; bulanık/siyah kenarlar atılır).
    focus_x/focus_y: FILL_CROP'ta kadrajın ortalanacağı nokta, content_region'a göre (0–1).
    view_region: planlayıcının seçtiği son görüntü alanı (öznenin tamamı + mümkün olan en dolu kadraj)."""

    model_config = ConfigDict(extra="forbid")
    mode: FramingMode = FramingMode.FILL_CROP
    focus_x: float = 0.5
    focus_y: float = 0.5
    zoom: float = 1.0
    content_region: Region | None = None
    # Kaynakta gösterilecek dikdörtgen (0–1, tüm kareye göre). Oranı video alanından genişse üst/alt boşluk
    # aynı görüntünün bulanık kopyasıyla dolar. Doluysa render content_region/focus yerine bunu kullanır.
    view_region: Region | None = None
    # Doluysa kadraj klip boyunca view_region'dan buna yavaşça kayar (aynı boyut): geniş özne bulanık dolgu
    # olmadan gösterilir.
    view_region_end: Region | None = None

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

    @model_validator(mode="after")
    def duration_matches_type(self) -> "Transition":
        if self.type in {TransitionType.NONE, TransitionType.CUT} and self.duration_f != 0:
            raise ValueError(f"{self.type.value} geçişinin duration_f değeri 0 olmalı.")
        if self.type == TransitionType.FADE and self.duration_f == 0:
            raise ValueError("fade geçişinin duration_f değeri 0'dan büyük olmalı.")
        return self


class Clip(BaseModel):
    """Timeline öğesi. Kaynak tarafı saniye (source_*_s), timeline tarafı frame (*_f).

    duration_f ile source süresi/speed tutarlılığı fps gerektirdiği için Timeline'da doğrulanır.
    """

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
    # Klibin kendi sesi kullanılır (seslendirme öncesi/sonrası tanık, röportaj veya dikkat çekici kesit).
    use_source_audio: bool = False
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

    @property
    def end_f(self) -> int:
        return self.start_f + self.duration_f

    @model_validator(mode="after")
    def validate_clip(self) -> "Clip":
        if self.duration_f <= 0:
            raise ValueError("Clip duration_f sıfırdan büyük olmalı.")
        if self.transition_in.duration_f + self.transition_out.duration_f > self.duration_f:
            raise ValueError(f"Clip {self.id} geçiş süreleri toplamı klip süresini aşamaz.")
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
    def validate_clips(self) -> "Track":
        expected = {
            TrackKind.VIDEO: {ClipType.MEDIA},
            TrackKind.OVERLAY: {ClipType.OVERLAY_TEXT},
            TrackKind.AUDIO: {ClipType.AUDIO},
        }[self.kind]
        for clip in self.clips:
            if clip.clip_type not in expected:
                raise ValueError(f"{self.kind.value} track içinde {clip.clip_type.value} clip kullanılamaz.")
        ordered = sorted(self.clips, key=lambda clip: clip.start_f)
        for previous, current in zip(ordered, ordered[1:]):
            if current.start_f < previous.end_f:
                raise ValueError(
                    f"Track {self.id} içinde {previous.id} ile {current.id} çakışıyor."
                )
        return self


class NewsSegment(BaseModel):
    """tts_text içindeki [char_start, char_end) aralığı; zamanlar TTS alignment'tan türetilir."""

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

    @property
    def clips(self) -> list[Clip]:
        return [clip for track in self.tracks for clip in track.clips]

    @property
    def end_f(self) -> int:
        return max((clip.end_f for clip in self.clips), default=0)

    @model_validator(mode="after")
    def validate_timeline(self) -> "Timeline":
        track_ids = [track.id for track in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("Track id'leri benzersiz olmalı.")
        clip_ids = [clip.id for clip in self.clips]
        if len(clip_ids) != len(set(clip_ids)):
            raise ValueError("Clip id'leri timeline genelinde benzersiz olmalı.")
        for clip in self.clips:
            if clip.clip_type == ClipType.OVERLAY_TEXT:
                continue
            source_duration = clip.source_out_s - clip.source_in_s
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

    @field_validator("duration_seconds")
    @classmethod
    def positive_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Ses süresi pozitif olmalı.")
        return value


class EditPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_version: str = EDIT_PLAN_VERSION
    status: Literal["draft", "approved", "rendered"] = "draft"
    segments: list[NewsSegment] = Field(default_factory=list)
    timeline: Timeline = Field(default_factory=Timeline)

    @model_validator(mode="after")
    def validate_segments(self) -> "EditPlan":
        ids = [segment.segment_id for segment in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("segment_id değerleri benzersiz olmalı.")
        orders = sorted(segment.order for segment in self.segments)
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("Segment order değerleri 1'den başlayıp ardışık olmalı.")
        return self


class NewsReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    package_schema_version: str
    headline_1: str
    headline_2: str
    caption: str
    tts_text: str
    source_text: str = ""
    tts_alignment: TTSAlignment | None = None

    @model_validator(mode="after")
    def validate_tts_alignment(self) -> "NewsReference":
        ensure_alignment_matches_text(self.tts_alignment, self.tts_text)
        return self


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

    @model_validator(mode="after")
    def validate_references(self) -> "EditProject":
        self._validate_segments_cover_tts_text()

        media_ids = [ref.asset_id for ref in self.media]
        if len(media_ids) != len(set(media_ids)):
            raise ValueError("media listesinde aynı asset_id birden fazla kez var.")
        media_id_set = set(media_ids)
        segment_ids = {segment.segment_id for segment in self.edit_plan.segments}

        timeline = self.edit_plan.timeline
        for clip in timeline.clips:
            if clip.clip_type == ClipType.MEDIA and clip.asset_id not in media_id_set:
                raise ValueError(f"Clip {clip.id} asset_id {clip.asset_id!r} media listesinde yok.")
            if clip.clip_type == ClipType.AUDIO and clip.asset_id not in media_id_set | {self.audio.asset_id}:
                raise ValueError(f"Clip {clip.id} asset_id {clip.asset_id!r} bilinen bir ses değil.")
            if clip.segment_id is not None and clip.segment_id not in segment_ids:
                raise ValueError(f"Clip {clip.id} segment_id {clip.segment_id!r} segmentlerde yok.")

        # Şablon videosu en az MIN_VIDEO_SECONDS; TTS daha kısaysa görüntü sessiz devam eder.
        # Kaynak sesli kesitler seslendirmeye ek süredir.
        soundbite_seconds = sum(
            clip.duration_f for clip in timeline.clips if clip.use_source_audio
        ) / timeline.fps
        allowed = video_seconds(self.audio.duration_seconds, soundbite_seconds)
        max_frames = math.ceil(allowed * timeline.fps) + 1
        if timeline.end_f > max_frames:
            raise ValueError(
                f"Timeline süresi ({timeline.end_f} frame) izin verilen süreyi "
                f"({allowed:.2f} sn: TTS + kaynak sesli kesitler, en az {MIN_VIDEO_SECONDS:.0f} sn) aşıyor."
            )
        return self

    def _validate_segments_cover_tts_text(self) -> None:
        """Segmentler sırayla birleşince (aradaki boşluklar hariç) tts_text'in tamamını vermeli."""
        segments = sorted(self.edit_plan.segments, key=lambda segment: segment.order)
        if not segments:
            return
        text = self.news.tts_text
        cursor = 0
        for segment in segments:
            if segment.char_end > len(text):
                raise ValueError(f"Segment {segment.segment_id} tts_text sınırının dışında.")
            if segment.char_start < cursor:
                raise ValueError(f"Segment {segment.segment_id} önceki segmentle çakışıyor veya sırası yanlış.")
            if text[cursor:segment.char_start].strip():
                raise ValueError(f"Segment {segment.segment_id} öncesinde segmentlere girmemiş metin var.")
            if text[segment.char_start:segment.char_end] != segment.text:
                raise ValueError(f"Segment {segment.segment_id} metni tts_text aralığıyla eşleşmiyor.")
            cursor = segment.char_end
        if text[cursor:].strip():
            raise ValueError("Son segmentten sonra segmentlere girmemiş metin var.")
