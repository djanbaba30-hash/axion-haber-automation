"""v4.0.0-alpha.1: fotoğraflar kurguda (yavaş yakınlaşma, alan tam dolu, bulanık dolgu yok) ve Luna'nın sahne seçiminde."""

import base64
import io
import shutil
import subprocess

import pytest
from PIL import Image, ImageDraw

from apps.video_studio.modules import luna_edit, render
from apps.video_studio.modules.edit_plan import build_edit_project
from apps.video_studio.modules.rough_cut import PHOTO_SECONDS, plan_rough_cut
from apps.video_studio.modules.video_asset import build_image_asset_model, image_geometry
from apps.video_studio.modules.visual_analysis import image_data_url
from test_rough_cut import SHOTS, TTS, edit_project, library, video_clips

SLOT_ASPECT = 960 / 1226
SUBJECT = {"x": 0.3, "y": 0.25, "width": 0.3, "height": 0.4}


def photo(tmp_path, name="foto.jpg", size=(1600, 900), orientation=None):
    """Sol üst köşesi kırmızı fotoğraf; `orientation` EXIF yön etiketi (6 = telefonda dik çekilmiş)."""
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).rectangle((0, 0, size[0] // 4, size[1] // 4), fill="red")
    path = tmp_path / name
    exif = image.getexif()
    if orientation:
        exif[0x0112] = orientation
    image.save(path, exif=exif)
    return path


def photo_asset(path, number=1, description="Kazada yaralanan kadının fotoğrafı", subject=SUBJECT):
    visual = {"description": description, "visual_type": "person", "editorial_role": "context", "confidence": 0.95,
              "subject_region": subject}
    return build_image_asset_model({"asset_id": f"image_{number:03d}", "path": str(path), "source": {"filename": path.name}},
                                   visual, {"model": "gpt-5.6-luna"})


def aspect(region, frame_aspect):
    return region["width"] * frame_aspect / region["height"]


def test_image_geometry_applies_exif_orientation(tmp_path):
    geometry = image_geometry(photo(tmp_path, size=(1200, 800), orientation=6))
    assert (geometry.width, geometry.height, geometry.exif_orientation) == (800, 1200, 6)
    assert image_geometry(photo(tmp_path, "duz.png")).exif_orientation == 1


def test_luna_sees_the_photo_the_way_it_is_displayed(tmp_path):
    url = image_data_url(photo(tmp_path, size=(1200, 800), orientation=6), max_side=512)
    with Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))) as image:
        assert image.size == (341, 512)  # dik
        assert image.getpixel((image.width - 5, 5))[0] > 200  # kırmızı köşe sağ üstte (90° saat yönünde)


def test_photo_is_used_with_slow_zoom_full_frame_and_subject_in_view(tmp_path):
    lib = library()
    lib["assets"].append(photo_asset(photo(tmp_path)))
    text = "Kazada yaralanan kadın hastaneye kaldırıldı. " + TTS
    clips = video_clips(plan_rough_cut(build_edit_project(lib, text, "C:/tts.mp3", 24.0, {
        "tts_text": text, "headline_1": "KAZA", "headline_2": "B", "caption": "c"}), lib))
    photos = [c for c in clips if c["asset_id"] == "image_001"]
    assert len(photos) == 1  # malzeme yeterken fotoğraf tekrar etmez
    framing = photos[0]["framing"]
    start, end = framing["view_region"], framing["view_region_end"]
    assert end and start["width"] != end["width"]  # yakınlaşma ya da uzaklaşma
    for region in (start, end):
        assert abs(aspect(region, 16 / 9) - SLOT_ASPECT) < 0.01  # alan hep dolu (bulanık dolgu yok)
        assert region["x"] <= SUBJECT["x"] and region["x"] + region["width"] >= SUBJECT["x"] + SUBJECT["width"]
        assert region["y"] <= SUBJECT["y"] and region["y"] + region["height"] >= SUBJECT["y"] + SUBJECT["height"]
    assert 0 <= photos[0]["source_in_s"] < photos[0]["source_out_s"] <= PHOTO_SECONDS


def test_news_with_only_photos_still_gets_a_cut(tmp_path):
    lib = {"assets": [photo_asset(photo(tmp_path, f"f{n}.jpg"), n, f"Olay yeri fotoğrafı {n}") for n in (1, 2, 3)]}
    project = plan_rough_cut(build_edit_project(lib, TTS, "C:/tts.mp3", 21.27, {
        "tts_text": TTS, "headline_1": "KAZA", "headline_2": "B", "caption": "c"}), lib)
    clips = video_clips(project)
    assert clips[0]["start_f"] == 0 and max(c["start_f"] + c["duration_f"] for c in clips) >= 21.27 * 30 - 1
    assert all(c["asset_id"].startswith("image_") for c in clips)
    for previous, current in zip(clips, clips[1:]):
        assert previous["asset_id"] != current["asset_id"]  # aynı fotoğraf art arda gelmez


def test_photo_without_file_or_size_is_skipped_not_crashing(tmp_path):
    lib = library()
    asset = photo_asset(photo(tmp_path))
    asset["geometry"] = None  # v4.0 öncesi analiz
    asset["source"]["original_path"] = str(tmp_path / "silindi.jpg")
    lib["assets"].append(asset)
    assert all(c["asset_id"] != "image_001" for c in video_clips(plan_rough_cut(edit_project(), lib)))


def test_render_turns_and_zooms_photos(tmp_path):
    audio = tmp_path / "tts.mp3"
    audio.write_bytes(b"mp3")
    lib = {"assets": [photo_asset(photo(tmp_path, size=(1200, 800), orientation=6))]}
    text = "Kadın yaralandı."
    project = plan_rough_cut(build_edit_project(lib, text, str(audio), 3.0, {
        "tts_text": text, "headline_1": "K", "headline_2": "B", "caption": "c"}), lib)
    command = render.build_render_command(project, lib, tmp_path / "out.mp4", render.X264)
    graph = command[command.index("-filter_complex") + 1]
    assert "-noautorotate" in command and "transpose=1," in graph  # EXIF yönü bir kez, Axion uygular
    assert "zoompan=" in graph and "boxblur" not in graph


def test_render_static_photo_loops_the_frame():
    from shared.edit_models import Clip, Framing
    from shared.media_models import ImageAsset

    asset = ImageAsset(asset_id="image_001", source={"filename": "f.jpg", "sha256": "a" * 64, "original_path": "f.jpg"},
                       geometry={"width": 1600, "height": 900, "exif_orientation": 1})
    view = {"x": 0.3, "y": 0, "width": 0.44, "height": 1}
    clip = Clip(id="c", asset_id="image_001", source_in_s=0.2, source_out_s=3.2, start_f=0, duration_f=90,
                framing=Framing(view_region=view))
    inputs, graph = render._photo_input(asset, "f.jpg", clip, 0, 960, 1226, 30)
    assert inputs[:2] == ["-loop", "1"] and "zoompan" not in graph and "transpose" not in graph


def test_luna_prompt_lists_photos(tmp_path):
    lib = library(SHOTS[:3])
    lib["assets"].append(photo_asset(photo(tmp_path)))
    prompt = luna_edit.build_prompt(luna_edit.prepare(edit_project(), lib))
    assert "| fotoğraf 1 | hareketsiz | Kazada yaralanan kadının fotoğrafı |" in prompt
    assert "fotoğraf en fazla bir kez" in luna_edit.SYSTEM_PROMPT


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_render_photo_cut_to_mp4_upright_and_full_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "amd_encoder_available", lambda: False)
    audio = tmp_path / "tts.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=4", str(audio)], check=True)
    lib = {"assets": [photo_asset(photo(tmp_path, size=(1200, 800), orientation=6), subject=None)]}
    text = "Kadın yaralandı. Hastaneye kaldırıldı."
    project = plan_rough_cut(build_edit_project(lib, text, str(audio), 4.0, {
        "tts_text": text, "headline_1": "K", "headline_2": "B", "caption": "c"}), lib)
    output = tmp_path / "kaba_kurgu.mp4"
    render.render_rough_cut(project, lib, output)
    frame = tmp_path / "kare.png"
    subprocess.run(["ffmpeg", "-v", "error", "-ss", "1", "-i", str(output), "-frames:v", "1", str(frame)], check=True)
    with Image.open(frame) as image:
        assert image.size == (960, 1226)
        top = [image.getpixel((x, 3)) for x in (5, image.width - 5)]
    assert top[0][0] > 200 and top[0][1] > 200  # sol üst beyaz
    assert top[1][0] > 200 and top[1][1] < 80  # sağ üst kırmızı: fotoğraf dik ve doğru yönde
