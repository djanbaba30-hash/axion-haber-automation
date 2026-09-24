import pytest

from shared.media_models import MediaLibrary, VisualType, EditorialRole


def test_media_library_builders_use_shared_2_1_contract(tmp_path):
    from apps.video_studio.modules.video_asset import build_video_asset

    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    metadata = {
        "original_filename": "video.mp4",
        "original_path": str(video),
        "duration_seconds": 2.0,
        "file_size_bytes": 5,
        "video": {
            "width": 1920,
            "height": 1080,
            "fps": 25.0,
            "codec": "h264",
            "pixel_format": "yuv420p",
        },
        "audio": {"codec": "aac", "sample_rate": "48000", "channels": 2, "channel_layout": "stereo"},
    }
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"frame")
    shots = [{
        "shot_id": "video_001_shot_001",
        "asset_id": "video_001",
        "shot_number": 1,
        "start_seconds": 0.0,
        "end_seconds": 2.0,
        "duration_seconds": 2.0,
        "analysis_windows": [{
            "window_id": "video_001_shot_001_w01",
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "frames": [{"frame_index": 1, "timestamp_seconds": 1.0, "path": str(frame)}],
        }],
    }]
    visuals = {"video_001_shot_001_w01": {
        "description": "Araç",
        "visual_type": "vehicle",
        "editorial_role": "action",
        "confidence": 0.9,
    }}
    payload = build_video_asset(
        metadata, shots, visuals, {"model": "gpt-5.6-luna"}, "Ekonomik", 1, "video_001"
    )
    library = MediaLibrary.model_validate({"assets": [payload]})
    assert library.assets[0].shots[0].visual.visual_type == VisualType.VEHICLE
    assert library.assets[0].shots[0].visual.editorial_role == EditorialRole.ACTION
    assert library.assets[0].shots[0].visual.description == "Araç"
    assert library.assets[0].shots[0].analysis_windows[0].visual.description == "Araç"
    assert library.assets[0].shots[0].analysis_windows[0].frames[0].timestamp_seconds == 1.0


def test_long_shot_is_split_into_windows():
    from apps.video_studio.modules.representative_sampling import split_into_windows

    assert split_into_windows(0.0, 8.0) == [(0.0, 8.0)]
    assert split_into_windows(0.0, 10.0) == [(0.0, 10.0)]
    windows = split_into_windows(85.68, 157.28)  # gerçek testteki 71.6 sn röportaj shot'ı
    assert len(windows) == 8
    assert windows[0][0] == 85.68 and windows[-1][1] == 157.28
    assert all(abs((end - start) - 8.95) < 0.01 for start, end in windows)


def test_luna_schema_forces_known_categories_and_maps_all_fields():
    from apps.video_studio.modules.visual_analysis import WindowVisualAnalysis, _visual_metadata

    fields = list(WindowVisualAnalysis.model_fields)
    assert fields[0] == "window_id"
    item = WindowVisualAnalysis(
        window_id="w", description=" Konuşan esnaf ", visual_type="person", editorial_role="portrait",
        visible_people=True, location="dükkân önü", text_visible=True, visible_text="BERBER", confidence=1.3,
    )
    visual = _visual_metadata(item)
    assert visual["description"] == "Konuşan esnaf"
    assert (visual["visual_type"], visual["editorial_role"]) == ("person", "portrait")
    assert (visual["visible_people"], visual["visible_text"], visual["confidence"]) == (True, "BERBER", 1.0)
    with pytest.raises(ValueError):
        WindowVisualAnalysis(**{**item.model_dump(), "visual_type": "olay yeri"})
