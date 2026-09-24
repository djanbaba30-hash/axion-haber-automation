import pytest
from pydantic import ValidationError

from shared.edit_models import (
    AudioReference,
    Clip,
    ClipType,
    EditPlan,
    EditProject,
    NewsReference,
    NewsSegment,
    Timeline,
    Track,
    TrackKind,
    Transition,
)
from shared.media_models import (
    AnalysisFrame,
    AnalysisWindow,
    DisplayGeometry,
    ImageGeometry,
    MediaAssetRef,
    Shot,
)

TTS_TEXT = "Merhaba dünya. Bugün hava güzel."


def media_clip(clip_id="c1", start_f=0, seconds=1.0, asset_id="video_1", **extra):
    return Clip(
        id=clip_id, asset_id=asset_id, source_in_s=0.0, source_out_s=seconds,
        start_f=start_f, duration_f=round(seconds * 30), **extra,
    )


def segments():
    return [
        NewsSegment(segment_id="s1", order=1, text="Merhaba dünya.", char_start=0, char_end=14),
        NewsSegment(segment_id="s2", order=2, text="Bugün hava güzel.", char_start=15, char_end=32),
    ]


def project(clips=(), plan_segments=None, audio_seconds=5.0, alignment=None, media=None):
    return EditProject(
        project_id="p1",
        library_id="lib1",
        news=NewsReference(
            package_schema_version="1.1", headline_1="A", headline_2="B", caption="C",
            tts_text=TTS_TEXT, tts_alignment=alignment,
        ),
        audio=AudioReference(asset_id="tts", duration_seconds=audio_seconds),
        media=[MediaAssetRef(asset_id="video_1", asset_type="video")] if media is None else media,
        edit_plan=EditPlan(
            segments=segments() if plan_segments is None else plan_segments,
            timeline=Timeline(tracks=[Track(id="v", kind=TrackKind.VIDEO, clips=list(clips))]),
        ),
    )


def test_valid_project_is_accepted():
    assert project([media_clip(segment_id="s1")]).library_id == "lib1"


def test_news_reference_alignment_must_match_text():
    alignment = {"characters": list("Selam"), "start_seconds": [0, 0.1, 0.2, 0.3, 0.4], "end_seconds": [0.1, 0.2, 0.3, 0.4, 0.5]}
    with pytest.raises(ValidationError, match="tts_text"):
        project(alignment=alignment)


def test_segment_text_must_match_tts_slice():
    bad = [NewsSegment(segment_id="s1", order=1, text="Xxxxxxxxxxxxxx", char_start=0, char_end=14), segments()[1]]
    with pytest.raises(ValidationError, match="eşleşmiyor"):
        project(plan_segments=bad)


def test_segment_outside_tts_text_is_rejected():
    with pytest.raises(ValidationError, match="sınırının dışında"):
        project(plan_segments=[NewsSegment(segment_id="s1", order=1, text="a" * 7, char_start=100, char_end=107)])


def test_segments_must_cover_whole_tts_text():
    with pytest.raises(ValidationError, match="segmentlere girmemiş"):
        project(plan_segments=segments()[:1])


def test_overlapping_segments_are_rejected():
    overlapping = [
        NewsSegment(segment_id="s1", order=1, text="Merhaba dünya.", char_start=0, char_end=14),
        NewsSegment(segment_id="s2", order=2, text="dünya. Bugün hava güzel.", char_start=8, char_end=32),
    ]
    with pytest.raises(ValidationError, match="çakışıyor"):
        project(plan_segments=overlapping)


def test_segment_order_must_be_sequential():
    with pytest.raises(ValidationError, match="ardışık"):
        EditPlan(segments=[NewsSegment(segment_id="s1", order=2, text="a", char_start=0, char_end=1)])


def test_clip_asset_must_exist_in_media():
    with pytest.raises(ValidationError, match="media listesinde yok"):
        project([media_clip(asset_id="HAYALET")])


def test_clip_segment_must_exist():
    with pytest.raises(ValidationError, match="segmentlerde yok"):
        project([media_clip(segment_id="YOK")])


def test_duplicate_media_refs_are_rejected():
    ref = MediaAssetRef(asset_id="video_1", asset_type="video")
    with pytest.raises(ValidationError, match="birden fazla"):
        project(media=[ref, ref])


def test_timeline_cannot_exceed_tts_duration():
    with pytest.raises(ValidationError, match="TTS süresini"):
        project([media_clip(seconds=30.0)], audio_seconds=5.0)


def test_overlapping_clips_in_same_track_are_rejected():
    with pytest.raises(ValidationError, match="çakışıyor"):
        Track(id="v", kind=TrackKind.VIDEO, clips=[media_clip("c1", 0, 2.0), media_clip("c2", 10, 2.0)])


def test_adjacent_clips_are_accepted():
    track = Track(id="v", kind=TrackKind.VIDEO, clips=[media_clip("c1", 0, 1.0), media_clip("c2", 30, 1.0)])
    assert len(track.clips) == 2


def test_duplicate_clip_ids_are_rejected():
    with pytest.raises(ValidationError, match="benzersiz"):
        Timeline(tracks=[
            Track(id="v1", kind=TrackKind.VIDEO, clips=[media_clip("c1")]),
            Track(id="v2", kind=TrackKind.VIDEO, clips=[media_clip("c1")]),
        ])


def test_transition_longer_than_clip_is_rejected():
    with pytest.raises(ValidationError, match="geçiş süreleri"):
        media_clip(transition_in=Transition(type="fade", duration_f=500))


def test_cut_transition_cannot_have_duration():
    with pytest.raises(ValidationError, match="0 olmalı"):
        Transition(type="cut", duration_f=5)


def test_fade_transition_needs_duration():
    with pytest.raises(ValidationError, match="0'dan büyük"):
        Transition(type="fade", duration_f=0)


def test_overlay_clip_needs_text_and_no_asset():
    with pytest.raises(ValidationError, match="overlay_text"):
        Clip(id="o", clip_type=ClipType.OVERLAY_TEXT, asset_id="x", text="A", start_f=0, duration_f=30)


def test_audio_duration_must_be_positive():
    with pytest.raises(ValidationError, match="pozitif"):
        AudioReference(asset_id="tts", duration_seconds=0)


def test_shot_start_cannot_be_negative():
    with pytest.raises(ValidationError, match="negatif"):
        Shot(shot_id="s", asset_id="a", shot_number=1, start_seconds=-5, end_seconds=2, duration_seconds=7)


def test_reversed_shot_is_rejected():
    with pytest.raises(ValidationError, match="start_seconds < end_seconds"):
        Shot(shot_id="s", asset_id="a", shot_number=1, start_seconds=10, end_seconds=2, duration_seconds=99)


def test_analysis_window_must_be_inside_shot():
    with pytest.raises(ValidationError, match="Shot aralığının dışında"):
        Shot(
            shot_id="s", asset_id="a", shot_number=1, start_seconds=0, end_seconds=2, duration_seconds=2,
            analysis_windows=[AnalysisWindow(window_id="w", shot_id="s", start_seconds=50, end_seconds=60)],
        )


def test_analysis_frame_must_be_inside_window():
    with pytest.raises(ValidationError, match="pencere aralığının dışında"):
        AnalysisWindow(
            window_id="w", shot_id="s", start_seconds=0, end_seconds=1,
            frames=[AnalysisFrame(frame_index=0, timestamp_seconds=5.0, path="f.jpg")],
        )


def test_negative_rotation_is_normalized():
    assert DisplayGeometry(width=10, height=10, rotation_degrees=-90).rotation_degrees == 270


def test_fractional_rotation_is_rejected():
    with pytest.raises(ValidationError, match="tam sayı"):
        DisplayGeometry(width=10, height=10, rotation_degrees=90.7)


def test_integral_float_rotation_is_accepted():
    assert DisplayGeometry(width=10, height=10, rotation_degrees=180.0).rotation_degrees == 180


def test_exif_orientation_must_be_1_to_8():
    with pytest.raises(ValidationError, match="1–8"):
        ImageGeometry(width=10, height=10, exif_orientation=42)
