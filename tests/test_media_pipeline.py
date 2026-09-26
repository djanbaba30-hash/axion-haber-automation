import shutil
import subprocess
from pathlib import Path

import pytest

from apps.video_studio.modules import media_pipeline
from apps.video_studio.modules.local_media import LocalMediaFile

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")


def make_video(path):
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=4:size=640x360:rate=25",
            "-f", "lavfi", "-i", "color=c=red:duration=4:size=640x360:rate=25",
            "-f", "lavfi", "-i", "sine=duration=8",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-map", "2:a", "-shortest",
            str(path),
        ],
        check=True,
    )


VISUAL = {"description": "Hasarlı araç", "visual_type": "vehicle", "editorial_role": "detail", "confidence": 0.9}


def fake_luna(shots, images, api_key, context=""):
    windows = [w for shot in shots for w in shot["analysis_windows"]]
    for window in windows:
        for frame in window["frames"]:
            assert Path(frame["path"]).exists()
    return (
        {w["window_id"]: VISUAL for w in windows},
        {image["asset_id"]: {**VISUAL, "visual_type": "graphic"} for image in images},
        {"model": "test", "estimated_cost_usd": 0.001, "api_calls": 1},
    )


def test_local_video_and_image_become_media_library(tmp_path, monkeypatch):
    video = tmp_path / "dha.mp4"
    make_video(video)
    image = tmp_path / "foto.png"
    image.write_bytes(b"\x89PNG")
    monkeypatch.setattr(media_pipeline, "analyze_media_with_luna", fake_luna)
    messages = []

    library, usage = media_pipeline.prepare_media_library(
        [LocalMediaFile(video), LocalMediaFile(image)], 1, "Ekonomik", "sk-test", progress=messages.append
    )

    assert media_pipeline.is_current_media_library(library)
    video_asset, image_asset = library["assets"]
    assert video_asset["source"]["filename"] == "dha.mp4"
    assert [(s["start_seconds"], s["end_seconds"]) for s in video_asset["shots"]] == [(0.0, 4.0), (4.0, 8.0)]
    assert video_asset["shots"][0]["visual"]["description"] == "Hasarlı araç"
    assert video_asset["shots"][0]["analysis_windows"][0]["window_id"] == "video_001_shot_001_w01"
    assert image_asset["source"]["original_path"] == str(image)
    assert image_asset["visual"]["visual_type"] == "graphic"
    assert usage["estimated_cost_usd"] == 0.001
    assert any("sahneler" in m for m in messages)

    created = []
    original_ingest = media_pipeline._ingest_video

    def spy_ingest(*args, **kwargs):
        metadata, shots = original_ingest(*args, **kwargs)
        created.extend(media_pipeline._scratch_files(metadata, shots))
        return metadata, shots

    monkeypatch.setattr(media_pipeline, "_ingest_video", spy_ingest)
    media_pipeline.prepare_media_library([LocalMediaFile(video)], 1, "Ekonomik", "sk-test")
    assert len(created) == 3 and not any(path.exists() for path in created)
    assert video.exists()

    rows = media_pipeline.shot_rows(library)
    assert [(r["Sahne"], r["Başlangıç"], r["Görüntü"]) for r in rows] == [
        (1, "00:00.00", "vehicle"), (2, "00:04.00", "vehicle"), (None, "fotoğraf", "graphic")]  # v4.0: fotoğraf da


def test_uploaded_image_is_kept_in_project_folder(tmp_path, monkeypatch):
    class Upload:
        name = "foto.png"
        size = 4

        def getbuffer(self):
            return b"\x89PNG"

    monkeypatch.setattr(media_pipeline, "analyze_media_with_luna", fake_luna)
    storage = tmp_path / "media"
    library, _ = media_pipeline.prepare_media_library([Upload()], 1, "Ekonomik", "sk-test", storage_dir=storage)
    library_again, _ = media_pipeline.prepare_media_library([Upload()], 1, "Ekonomik", "sk-test", storage_dir=storage)

    assert [p.name for p in storage.iterdir()] == ["foto.png"]
    assert library["assets"][0]["source"]["original_path"] == str(storage / "foto.png")
    assert library_again["assets"][0]["source"]["sha256"] == library["assets"][0]["source"]["sha256"]


def test_old_analysis_is_not_current():
    assert not media_pipeline.is_current_media_library({"assets": [{"asset_type": "video", "shots": []}]})
    assert not media_pipeline.is_current_media_library(None)


def test_failed_frame_extraction_leaves_no_temp_frames(tmp_path, monkeypatch):
    from apps.video_studio.modules import representative_sampling as sampling

    video = tmp_path / "dha.mp4"
    make_video(video)
    made = []
    real = sampling.extract_single_frame

    def flaky(*args):
        if len(made) == 2:
            raise RuntimeError("FFmpeg temsilci frame oluşturamadı.")
        made.append(real(*args))
        return made[-1]

    monkeypatch.setattr(sampling, "extract_single_frame", flaky)
    shots = [{"shot_number": 1, "start_seconds": 0.0, "end_seconds": 8.0, "duration_seconds": 8.0}]
    with pytest.raises(RuntimeError):
        sampling.extract_representative_frames(video, shots, frame_count=4)
    assert made and not any(path.exists() for path in made)


def test_frame_count_is_capped_for_long_videos():
    shots = [{"start_seconds": 0.0, "end_seconds": 300.0}]  # 5 dk tek sahne → 30 pencere
    assert media_pipeline.capped_frame_count(shots, 4) == 1   # 120 kare yerine 30
    assert media_pipeline.capped_frame_count(shots[:0] + [{"start_seconds": 0.0, "end_seconds": 60.0}], 4) == 4
    assert media_pipeline.capped_frame_count(shots, 1) == 1   # ekonomik mod: her pencerede 1 kare kalır


def test_same_name_same_size_different_upload_is_not_reused(tmp_path):
    from apps.video_studio.modules.video_ingestion import store_upload

    class Upload:
        name = "dha.mp4"

        def __init__(self, data):
            self.data = data

        def getbuffer(self):
            return memoryview(self.data)

    first = store_upload(Upload(b"AAAA"), tmp_path)
    again = store_upload(Upload(b"AAAA"), tmp_path)
    different = store_upload(Upload(b"BBBB"), tmp_path)  # aynı ad, aynı boyut, farklı içerik
    assert first == again and different != first
    assert different.read_bytes() == b"BBBB" and first.read_bytes() == b"AAAA"
