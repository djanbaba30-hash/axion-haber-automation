import json

import pytest

from shared.edit_models import (
    Clip,
    ClipOrigin,
    ClipType,
    FramingMode,
    NewsSegment,
    Timeline,
    Track,
    TrackKind,
)
from shared.media_models import (
    AnalysisWindow,
    DisplayGeometry,
    EditorialRole,
    FocusPoint,
    ImageAsset,
    ImageGeometry,
    MediaSource,
    Region,
    Shot,
    VisualMetadata,
    VisualType,
)


def source():
    return MediaSource(
        filename="video.mp4",
        extension=".mp4",
        sha256="a" * 64,
        original_path="/tmp/original.mp4",
        proxy_path="/tmp/proxy.mp4",
        size_bytes=100,
    )


def test_visual_metadata_supports_other_enum_value():
    visual = VisualMetadata(
        description="Belirsiz",
        visual_type=VisualType.OTHER,
        editorial_role=EditorialRole.OTHER,
        focus_point=FocusPoint(x=0.4, y=0.6),
    )
    assert visual.visual_type == VisualType.OTHER


def test_region_must_stay_inside_normalized_bounds():
    with pytest.raises(ValueError):
        Region(x=0.8, y=0.0, width=0.3, height=0.1)


def test_rotation_is_normalized():
    geometry = DisplayGeometry(width=1080, height=1920, rotation_degrees=450)
    assert geometry.rotation_degrees == 90


def test_analysis_window_requires_strict_range():
    with pytest.raises(ValueError, match="start_seconds < end_seconds"):
        AnalysisWindow(window_id="w1", shot_id="s1", start_seconds=2.0, end_seconds=2.0)


def test_shot_requires_duration_consistency():
    with pytest.raises(ValueError, match="duration_seconds"):
        Shot(
            shot_id="s1",
            asset_id="a1",
            shot_number=1,
            start_seconds=0.0,
            end_seconds=2.0,
            duration_seconds=3.0,
        )


def test_shot_visual_can_be_none_when_not_analyzed():
    shot = Shot(
        shot_id="s1",
        asset_id="a1",
        shot_number=1,
        start_seconds=0.0,
        end_seconds=2.0,
        duration_seconds=2.0,
    )
    assert shot.visual is None


def test_image_geometry_contains_exif_orientation():
    asset = ImageAsset(
        asset_id="img1",
        source=source(),
        geometry=ImageGeometry(width=1200, height=800, exif_orientation=6),
    )
    assert asset.geometry.exif_orientation == 6
    assert asset.visual is None


def test_clip_source_range_is_seconds():
    clip = Clip(
        id="clip_a1",
        clip_type=ClipType.MEDIA,
        asset_id="video_abc",
        shot_id="video_abc_shot_001",
        source_in_s=1.0,
        source_out_s=3.9,
        start_f=0,
        duration_f=87,
        speed=1.0,
        origin=ClipOrigin.LLM,
        framing={"mode": FramingMode.FILL_CROP},
    )
    timeline = Timeline(
        fps=30,
        width=1080,
        height=1440,
        tracks=[Track(id="video_1", kind=TrackKind.VIDEO, clips=[clip])],
    )
    assert timeline.tracks[0].clips[0].source_in_s == 1.0


def test_model_validate_json_runs_clip_source_validator():
    payload = {
        "id": "bad",
        "clip_type": "media",
        "asset_id": "a",
        "source_in_s": 4.0,
        "source_out_s": 2.0,
        "start_f": 0,
        "duration_f": 60,
    }
    with pytest.raises(ValueError, match="source_in_s < source_out_s"):
        Clip.model_validate_json(json.dumps(payload))


def test_timeline_validates_duration_and_speed_consistency():
    clip = Clip(
        id="clip_bad",
        clip_type=ClipType.MEDIA,
        asset_id="a",
        source_in_s=0.0,
        source_out_s=2.0,
        start_f=0,
        duration_f=30,
        speed=1.0,
    )
    with pytest.raises(ValueError, match="duration_f"):
        Timeline(tracks=[Track(id="v", kind=TrackKind.VIDEO, clips=[clip])])


def test_overlay_text_clip_does_not_require_asset():
    clip = Clip(
        id="overlay1",
        clip_type=ClipType.OVERLAY_TEXT,
        start_f=0,
        duration_f=30,
        text="BAŞLIK",
    )
    timeline = Timeline(tracks=[Track(id="o", kind=TrackKind.OVERLAY, clips=[clip])])
    assert timeline.tracks[0].clips[0].asset_id is None


def test_news_segment_uses_character_offsets():
    segment = NewsSegment(
        segment_id="seg1",
        order=1,
        text="Merhaba",
        char_start=0,
        char_end=7,
    )
    assert segment.char_end - segment.char_start == len(segment.text)


def test_media_asset_discriminator_and_missing_visual_state():
    assert ImageAsset.model_validate({"asset_id": "i", "source": source()}).visual is None
