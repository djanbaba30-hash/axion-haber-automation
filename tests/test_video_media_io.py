import base64
import sys
from pathlib import Path

import pytest

from apps.video_studio.modules import ffmpeg_runner, video_ingestion
from apps.video_studio.modules.visual_analysis import image_data_url, image_mime_type


@pytest.mark.parametrize(
    ("name", "mime"),
    [("a.jpg", "image/jpeg"), ("a.JPEG", "image/jpeg"), ("a.png", "image/png"), ("a.webp", "image/webp")],
)
def test_image_mime_type_from_extension(name, mime):
    assert image_mime_type(Path(name)) == mime


def test_unsupported_image_extension_is_rejected():
    with pytest.raises(ValueError, match="MIME"):
        image_mime_type(Path("a.gif"))


def test_image_data_url_uses_real_mime_and_content(tmp_path):
    path = tmp_path / "frame.png"
    path.write_bytes(b"\x89PNG-test")
    url = image_data_url(path)
    assert url == "data:image/png;base64," + base64.b64encode(b"\x89PNG-test").decode()
    assert "{" not in url


def test_long_job_timeout_scales_with_duration():
    assert ffmpeg_runner.long_job_timeout(10) == ffmpeg_runner.LONG_JOB_MIN_TIMEOUT_SECONDS
    assert ffmpeg_runner.long_job_timeout(200) == 200 * ffmpeg_runner.LONG_JOB_REALTIME_FACTOR
    assert ffmpeg_runner.long_job_timeout(100_000) == ffmpeg_runner.LONG_JOB_MAX_TIMEOUT_SECONDS


@pytest.mark.parametrize("value", [None, 0, -5, "bozuk"])
def test_unknown_duration_gets_max_timeout(value):
    assert ffmpeg_runner.long_job_timeout(value) == ffmpeg_runner.LONG_JOB_MAX_TIMEOUT_SECONDS


def test_run_ffmpeg_converts_timeout_to_readable_error():
    with pytest.raises(RuntimeError, match="saniye içinde tamamlanamadı"):
        ffmpeg_runner.run_ffmpeg([sys.executable, "-c", "import time; time.sleep(5)"], 0.2, "Test işlemi")


def test_create_proxy_removes_temp_file_on_timeout(monkeypatch):
    created = []

    def fake_run(command, timeout_seconds, label):
        created.append((Path(command[-1]), timeout_seconds))
        raise RuntimeError("zaman aşımı")

    monkeypatch.setattr(video_ingestion, "run_ffmpeg", fake_run)
    with pytest.raises(RuntimeError):
        video_ingestion.create_proxy(Path("input.mp4"), duration_seconds=600)
    proxy_path, timeout = created[0]
    assert not proxy_path.exists()
    assert timeout == ffmpeg_runner.long_job_timeout(600)
