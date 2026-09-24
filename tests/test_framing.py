"""Akıllı kadraj: bulanık/siyah kenar tespiti, odak noktası ve render."""

import json
import shutil
import subprocess

import pytest

from apps.video_studio.modules.framing import detect_content_region
from apps.video_studio.modules.rough_cut import Candidate, clip_framing
from shared.edit_models import FramingMode
from shared.media_models import EditorialRole, FocusPoint, Region, VisualType

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")

# Gerçekçi kaynak: kumlu görüntü (gerçek videodaki doku/gürültü gibi).
GRAINY = "testsrc2=size={size}:rate=1:duration=1,noise=alls=25:allf=t"


def frame(path, source, filters):
    """Analiz karesi gibi 960x540 JPG üretir."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source, "-filter_complex", f"{filters},scale=960:540",
         "-frames:v", "1", "-q:v", "4", str(path)],
        check=True,
    )
    return path


def dha_vertical(path):
    """DHA dikey çekimi: 608x1080 görüntü ortada, iki yanda büyütülüp bulanıklaştırılmış kopyası, köşede logo."""
    return frame(
        path, GRAINY.format(size="608x1080"),
        "[0]split[a][b];[a]scale=1920:3411,crop=1920:1080,boxblur=20:2[bg];[bg][b]overlay=656:0,"
        "drawbox=x=60:y=60:w=160:h=50:color=white:t=fill",
    )


def test_dha_blurred_sides_are_detected(tmp_path):
    region = detect_content_region([dha_vertical(tmp_path / "f.jpg")])
    assert region is not None and region.y == 0.0 and region.height == 1.0
    # Gerçek alan 0.3417–0.6583; bulunan alan tamamen içeride ve en fazla %2 dar.
    assert 0.3417 <= region.x <= 0.3617
    assert 0.6383 <= region.x + region.width <= 0.6583


def test_black_bars_are_detected(tmp_path):
    region = detect_content_region([frame(tmp_path / "f.jpg", GRAINY.format(size="1920x800"), "pad=1920:1080:0:140")])
    assert region is not None and region.x == 0.0
    assert 0.1296 <= region.y <= 0.1496 and 0.8504 <= region.y + region.height <= 0.8704


def test_full_frame_video_is_left_alone(tmp_path):
    assert detect_content_region([frame(tmp_path / "f.jpg", GRAINY.format(size="1920x1080"), "null")]) is None


def test_one_sided_flat_area_is_not_mistaken_for_blur(tmp_path):
    # Solda düz duvar/gökyüzü: simetrik değil, kırpılmamalı.
    source = GRAINY.format(size="1500x1080")
    assert detect_content_region([frame(tmp_path / "f.jpg", source, "pad=1920:1080:420:0:color=gray")]) is None


def candidate(focus, region=None):
    return Candidate(
        asset_id="v", shot_id="s", shot_start=0, shot_end=5, start=0, end=5, order=0, tokens=[],
        role=EditorialRole.ACTION, visual_type=VisualType.EVENT, confidence=1, plate=False, description="",
        content_region=region, focus=focus,
    )


def test_focus_is_converted_to_content_coordinates():
    framing = clip_framing(FramingMode.FILL_CROP, candidate(FocusPoint(x=0.5, y=0.3), Region(x=0.34, y=0, width=0.32, height=1)))
    assert (framing.focus_x, framing.focus_y) == (0.5, 0.3)
    framing = clip_framing(FramingMode.FILL_CROP, candidate(FocusPoint(x=0.8, y=0.5)))
    assert framing.focus_x == 0.8 and framing.content_region is None
    assert clip_framing(FramingMode.FILL_CROP, candidate(None)).focus_x == 0.5


def test_render_crops_away_blur_and_follows_focus(tmp_path, monkeypatch):
    """Sol yarısı kırmızı, sağ yarısı mavi yatay video: odak sağdaysa çıktı mavi olmalı."""
    from apps.video_studio.modules import render
    from tests.test_rough_cut import library, plan_rough_cut
    from apps.video_studio.modules.edit_plan import build_edit_project

    monkeypatch.setattr(render, "amd_encoder_available", lambda: False)
    source, audio = tmp_path / "dha.mp4", tmp_path / "tts.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:size=960x1080:rate=25:duration=6",
         "-f", "lavfi", "-i", "color=blue:size=960x1080:rate=25:duration=6",
         "-filter_complex", "[0][1]hstack", str(source)],
        check=True,
    )
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=2", str(audio)], check=True)
    lib = library([(0.0, 6.0, "event", "establishing", "Kaza", "")], source=str(source))
    lib["assets"][0]["shots"][0]["analysis_windows"][0]["visual"]["focus_point"] = {"x": 0.85, "y": 0.5}
    text = "Kaza oldu."
    project = plan_rough_cut(build_edit_project(lib, text, str(audio), 2.0, {"tts_text": text, "headline_1": "K", "headline_2": "B", "caption": "c"}), lib)
    output = tmp_path / "out.mp4"
    render.render_rough_cut(project, lib, output)

    pixel = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output), "-vf", "scale=1:1", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    red, _, blue = pixel
    assert blue > 200 and red < 50


@pytest.mark.parametrize("mode", ["fill_crop", "fit_blur"])
def test_render_with_detected_region_leaves_no_blurred_strip(tmp_path, monkeypatch, mode):
    """Yeşil dikey görüntü + gri bulanık kenarlar: Doldur modunda çıktının kenarları da yeşil olmalı."""
    from apps.video_studio.modules import render
    from apps.video_studio.modules.edit_plan import build_edit_project
    from apps.video_studio.modules.rough_cut import set_framing
    from tests.test_rough_cut import library, plan_rough_cut

    monkeypatch.setattr(render, "amd_encoder_available", lambda: False)
    source, audio = tmp_path / "dha.mp4", tmp_path / "tts.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=gray:size=1920x1080:rate=25:duration=4",
         "-f", "lavfi", "-i", "color=green:size=608x1080:rate=25:duration=4",
         "-filter_complex", "[0][1]overlay=656:0", str(source)],
        check=True,
    )
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=2", str(audio)], check=True)
    lib = library([(0.0, 4.0, "event", "establishing", "Kaza", "")], source=str(source))
    lib["assets"][0]["shots"][0]["content_region"] = {"x": 0.3543, "y": 0.0, "width": 0.2934, "height": 1.0}
    text = "Kaza oldu."
    project = set_framing(plan_rough_cut(build_edit_project(lib, text, str(audio), 2.0, {"tts_text": text, "headline_1": "K", "headline_2": "B", "caption": "c"}), lib), mode)
    output = tmp_path / "out.mp4"
    render.render_rough_cut(project, lib, output)

    column = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output), "-vf", "crop=20:ih:0:0,scale=1:1", "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    ).stdout
    red, green, blue = column
    if mode == "fill_crop":
        assert green > 90 and red < 40  # sol kenar da asıl (yeşil) görüntü
    else:
        assert green > 60  # bulanık arka plan asıl görüntüden (yeşil) üretilir, DHA'nın gri kenarından değil


def test_real_dha_overshoot_snaps_to_vertical_phone_aspect():
    """Manavgat videosu (Windows, v1.9.0): bulanık kenarlı sahnelerde tespit ~0.286–0.714 çıktı, gerçek 9:16 alan
    0.342–0.658. Dar standart orana oturtulunca bulanık kenar kadraja girmez."""
    from apps.video_studio.modules.framing import _snap_to_vertical_aspect

    start, end = _snap_to_vertical_aspect(0.286, 0.714, 16 / 9)
    assert abs(start - 0.3418) < 0.002 and abs(end - 0.6582) < 0.002
    # Kare (1:1) çekim ~0.56 genişlikte: 9:16'ya değil 1:1'e oturur.
    start, end = _snap_to_vertical_aspect(0.21, 0.79, 16 / 9)
    assert abs((end - start) - 0.5625) < 0.002
    # Standart orandan dar tespit (ör. 0.30) olduğu gibi kalır.
    assert _snap_to_vertical_aspect(0.35, 0.65, 16 / 9) == (0.35, 0.65)
