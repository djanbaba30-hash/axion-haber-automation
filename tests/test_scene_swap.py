"""v4.0.0-alpha.2: kurguda sahne değiştirme (API yok): seçenekler, editörün seçimi Luna planının üstünde, küçük kareler."""

import json
import shutil
import subprocess

import pytest
from PIL import Image

from apps.video_studio.modules import luna_edit, scene_swap
from apps.video_studio.modules.rough_cut import plan_rough_cut
from shared.media_models import MediaLibrary, Region
from test_luna_edit import REAL_REQUEST, FakeLuna
from test_photos import photo, photo_asset
from apps.video_studio.modules.edit_plan import build_edit_project
from test_rough_cut import TTS, edit_project, library, video_clips


def moments(project):
    return [(c["scene"], c["shot_id"], c["source_in_s"]) for c in video_clips(project)]


def test_scenes_are_numbered_and_soundbites_are_not_swappable():
    project = plan_rough_cut(edit_project(), library())
    items = scene_swap.scenes(project)
    assert [s.number for s in items] == list(range(len(items))) and len(items) >= 5
    assert items[0].start_s == 0 and not any(s.user for s in items)
    assert abs(sum(s.seconds for s in items) - 21.27) < 0.1


def test_alternatives_skip_the_current_window_and_moments_used_elsewhere(tmp_path):
    lib = library()
    lib["assets"].append(photo_asset(photo(tmp_path)))
    project = plan_rough_cut(build_edit_project(lib, TTS, "C:/tts.mp3", 21.27, {
        "tts_text": TTS, "headline_1": "KAZA", "headline_2": "B", "caption": "c"}), lib)
    prep = luna_edit.prepare(project, lib)
    options = scene_swap.alternatives(prep, project, 2)
    assert 1 <= len(options) <= scene_swap.ALTERNATIVE_COUNT
    assert len({prep.candidates[o.index].shot_id for o in options}) == len(options)  # her seçenek başka çekim
    here = [c for c in video_clips(project) if c["scene"] == 2][0]
    others = [(c["shot_id"], c["source_in_s"], c["source_out_s"]) for c in video_clips(project) if c["scene"] != 2]
    for option in options:
        candidate = prep.candidates[option.index]
        assert not (candidate.shot_id == here["shot_id"] and candidate.start <= here["source_in_s"] < candidate.end)
        assert not any(shot == candidate.shot_id and start <= option.start < end for shot, start, end in others)
    used = [c["scene"] for c in video_clips(project) if c["asset_id"] == "image_001"]
    other = next(n for n in range(len(prep.slots())) if n not in used)
    photos = [o for o in scene_swap.alternatives(prep, project, other, count=30) if o.asset_id == "image_001"]
    # Fotoğraf kurguda zaten varsa (başka sahnede) seçenek olmaz; o sahnenin kendisinde yine seçilebilir çekim değil.
    assert bool(photos) != bool(used)
    if photos:
        assert photos[0].framing.view_region_end is not None  # yakınlaşmalı


def test_only_the_chosen_scene_changes_on_top_of_lunas_plan(tmp_path, monkeypatch):
    project, lib = edit_project(), library()
    scenes = [{"parca": 1, "pencere": "P2"}, {"parca": 2, "pencere": "P4"}, {"parca": 3, "pencere": "P10"},
              {"parca": 4, "pencere": "P12"}, {"parca": 5, "pencere": "P6"}]
    fake = FakeLuna([{**s, "kaynak_bas": 0.0} for s in scenes])
    monkeypatch.setattr(luna_edit, "request", REAL_REQUEST)  # conftest'in "Luna yok"u yerine sahte istemci
    first, info = luna_edit.plan(project, lib, None, "sk", tmp_path, client=fake)
    assert info["kaynak"] == "luna"
    prep = luna_edit.prepare(first, lib)
    option = scene_swap.alternatives(prep, first, 2)[0]
    scene_swap.choose(tmp_path, prep, first, 2, option)
    stored = json.loads((tmp_path / luna_edit.PLAN_FILENAME).read_text(encoding="utf-8"))
    assert stored["sahneler"] and "temel" not in stored  # Luna'nın planı korunur, üstüne editör satırı
    assert stored["editor"] == [{"parca": 3, "pencere": luna_edit.window_ids(prep)[option.index], "kaynak_bas": option.start}]
    second, info = luna_edit.plan(project, lib, None, "sk", tmp_path, client=fake)
    assert info["kaynak"] == "kayitli" and info["editor"] == 1 and len(fake.calls) == 1  # yeni çağrı yok
    changed = {m[0] for m in set(moments(first)) ^ set(moments(second))}
    assert changed == {2}
    chosen = [c for c in video_clips(second) if c["scene"] == 2][0]
    assert chosen["origin"] == "user" and chosen["source_in_s"] == option.start
    assert any("Editörün değiştirdiği: 3." in line for line in luna_edit.plan_summary(stored))
    # Yeniden seçim (Luna'dan farklı kurgu) editörün seçimini de siler.
    third, _ = luna_edit.plan(project, lib, None, "sk", tmp_path, replan=True, client=fake)
    assert "editor" not in json.loads((tmp_path / luna_edit.PLAN_FILENAME).read_text(encoding="utf-8"))
    assert all(c["origin"] != "user" for c in video_clips(third))


def test_choice_is_dropped_when_the_inputs_change(tmp_path):
    project, lib = edit_project(), library()
    cut = plan_rough_cut(project, lib)
    prep = luna_edit.prepare(cut, lib)
    scene_swap.choose(tmp_path, prep, cut, 1, scene_swap.alternatives(prep, cut, 1)[0])
    assert luna_edit.plan(project, lib, None, "", tmp_path)[1]["editor"] == 1
    lib["assets"][0]["shots"][0]["analysis_windows"][0]["visual"]["description"] = "Yeniden analiz edildi"
    result, info = luna_edit.plan(project, lib, None, "", tmp_path)
    assert info["editor"] == 0 and all(c["origin"] != "user" for c in video_clips(result))


def test_old_cut_without_scene_numbers_offers_nothing():
    project = plan_rough_cut(edit_project(), library())
    for track in project["edit_plan"]["timeline"]["tracks"]:
        for clip in track["clips"]:
            clip.pop("scene", None)
    assert scene_swap.scenes(project) == []


def test_photo_thumbnail_is_cropped_to_the_scene_and_cached(tmp_path):
    lib = MediaLibrary.model_validate({"assets": [photo_asset(photo(tmp_path, size=(1200, 800), orientation=6))]})
    view = Region(x=0.5, y=0, width=0.5, height=0.4)  # sağ üst: dik fotoğrafta kırmızı köşe
    first = scene_swap.thumbnail(lib, "image_001", 0.0, view, tmp_path)
    with Image.open(first) as image:
        assert image.width == scene_swap.THUMB_WIDTH and image.getpixel((image.width - 3, 3))[0] > 200
    assert scene_swap.thumbnail(lib, "image_001", 0.0, view, tmp_path) == first
    assert scene_swap.thumbnail(lib, "yok", 0.0, view, tmp_path) is None


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_video_thumbnail_from_the_scene_moment(tmp_path):
    source = tmp_path / "dha.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=4", str(source)], check=True)
    lib = MediaLibrary.model_validate(library([(0.0, 4.0, "event", "action", "Mavi", "")], source=str(source)))
    thumb = scene_swap.thumbnail(lib, "video_001", 1.0, Region(x=0.3, y=0, width=0.44, height=1), tmp_path)
    with Image.open(thumb) as image:
        red, _, blue = image.getpixel((10, 10))
    assert blue > 150 and red < 80
    assert not list((tmp_path / scene_swap.THUMB_FOLDER).glob("*.tam.jpg"))  # ara kare silindi
