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
    shots = [{
        "shot_id": "video_001_shot_001",
        "asset_id": "video_001",
        "shot_number": 1,
        "start_seconds": 0.0,
        "end_seconds": 2.0,
        "duration_seconds": 2.0,
        "analysis_frames": [{
            "frame_index": 1,
            "timestamp_seconds": 1.0,
            "path": str(tmp_path / "frame.jpg"),
        }],
        "visual_asset": {
            "description": "Araç",
            "visual_type": "vehicle",
            "editorial_role": "action",
            "confidence": 0.9,
        },
    }]
    payload = build_video_asset(
        metadata, shots, {"model": "gpt-5.6-luna"}, "Ekonomik", 1, "video_001"
    )
    library = MediaLibrary.model_validate({"assets": [payload]})
    assert library.assets[0].shots[0].visual.visual_type == VisualType.VEHICLE
    assert library.assets[0].shots[0].visual.editorial_role == EditorialRole.ACTION
    assert library.assets[0].shots[0].analysis_windows[0].frames[0].timestamp_seconds == 1.0
