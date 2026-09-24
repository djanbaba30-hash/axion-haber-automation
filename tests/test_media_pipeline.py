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


def fake_luna(shots, images, api_key):
    for shot in shots:
        for frame in shot["analysis_frames"]:
            assert Path(frame["path"]).exists()
    analyzed = [
        {**shot, "visual_asset": {"visual_type": "olay yeri", "subjects": ["Hasarlı araç"], "editorial_role": "genel plan", "confidence": 0.9}}
        for shot in shots
    ]
    analyzed_images = [{**image, "visual_asset": {"visual_type": "fotoğraf"}} for image in images]
    return analyzed, analyzed_images, {"model": "test", "estimated_cost_usd": 0.001, "api_calls": 1}


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

    assert (library["video_count"], library["image_count"]) == (1, 1)
    video_asset = library["assets"][0]
    assert video_asset["source"]["filename"] == "dha.mp4"
    assert [(s["start_seconds"], s["end_seconds"]) for s in video_asset["shots"]] == [(0.0, 4.0), (4.0, 8.0)]
    assert library["assets"][1]["path"] == str(image)
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
    assert [(r["Shot"], r["Başlangıç"], r["Görüntü"]) for r in rows] == [(1, "00:00.00", "olay yeri"), (2, "00:04.00", "olay yeri")]
