"""Kaynak sesli kesitin varsayılan aralığı olay anı (editör v3.2: "kazanın olduğu yerden alakasız")."""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest

from apps.video_studio.modules import moment

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")


def cctv(path, event: bool) -> None:
    """Sabit kamera (gürültülü gri), 12 sn; event=True ise 6. sn'de küçük bir cisim fırlar ve çarpma sesi gelir."""
    box = "drawbox=x='40+200*(t-6)':y=150:w=40:h=30:color=white:t=fill:enable='between(t,6,6.8)'," if event else ""
    bang = "volume='if(between(t,6,6.25),1,0.03)':eval=frame" if event else "volume=0.03"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:size=480x270:rate=25:duration=12",
         "-f", "lavfi", "-i", "anoisesrc=d=12:c=pink:a=0.5",
         "-vf", f"{box}noise=alls=8:allf=t", "-af", bang, "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
         str(path)],
        check=True,
    )


@needs_ffmpeg
def test_finds_the_crash_moment(tmp_path):
    video = tmp_path / "kamera.mp4"
    cctv(video, event=True)
    start, end = moment.suggested_range(video, 12.0)
    assert 3.5 <= start <= 4.5 and end == pytest.approx(start + 5)
    assert video.with_suffix(".an.json").exists()  # bir kez hesaplanır


@needs_ffmpeg
def test_no_clear_moment_is_not_presented_as_one(tmp_path):
    video = tmp_path / "bos.mp4"
    cctv(video, event=False)
    assert moment.suggested_range(video, 12.0) is None


def test_cut_and_handheld_are_not_events():
    rate = moment.RATE
    local = np.full(12 * rate, 10.0)
    whole = np.full(12 * rate, 0.5)
    whole[60] = 40.0  # kesme: tek örnekte tüm kare değişir
    local[60] = 200.0
    assert moment.find_moment(moment.scores(local, whole, np.zeros(0))) is None
    shaky = np.full(12 * rate, 8.0)  # elde çekim: kamera sürekli sallanıyor
    local[80:85] = 40.0
    assert moment.find_moment(moment.scores(local, shaky, np.zeros(0))) is None
    assert moment.find_moment(moment.scores(local, whole, np.zeros(0))) == pytest.approx(8.2, abs=0.3)


def test_music_starting_is_not_a_bang():
    rate = moment.RATE
    loud = np.full(12 * rate, -120.0)
    loud[40:] = -18.0  # sessizlikten sonra sürekli ses (müzik, konuşma)
    assert moment.find_moment(moment.scores(np.zeros(0), np.zeros(0), loud)) is None


def test_luna_action_windows_lead():
    library = {"assets": [{"source": {"filename": "a.mp4"}, "shots": [
        {"start_seconds": 0, "end_seconds": 10, "visual": {"editorial_role": "aftermath"}, "analysis_windows": [
            {"start_seconds": 0, "end_seconds": 5, "visual": {"editorial_role": "aftermath"}},
            {"start_seconds": 5, "end_seconds": 10, "visual": {"editorial_role": "action"}},
        ]},
    ]}, {"source": {"filename": "b.mp4"}, "shots": [
        {"start_seconds": 0, "end_seconds": 4, "visual": {"editorial_role": "action"}},
    ]}]}
    assert moment.action_windows(library, "a.mp4") == [(5.0, 10.0)]
    assert moment.action_windows(library, "b.mp4") == [(0.0, 4.0)]
    assert moment.action_windows(None, "a.mp4") == []
    flat = np.zeros(15 * moment.RATE)
    assert moment.find_moment(flat, [(5.0, 10.0)]) == 7.0  # işaret yok: olay penceresinin başı
    weak = flat.copy()
    weak[80] = 0.5  # tek başına eşiğin altında, olay penceresinde → seçilir
    weak[20] = 0.9
    assert moment.find_moment(weak, [(5.0, 10.0)]) == 8.0


def test_range_is_clamped_to_the_video():
    assert moment.moment_range(1.0, 20.0) == (0.0, 5.0)
    assert moment.moment_range(19.5, 20.0) == (15.0, 20.0)
    assert moment.moment_range(3.0, 4.0) == (0.0, 4.0)
    assert moment.moment_range(None, 20.0) is None
