"""Kaynak sesli kesitler: seslendirme öncesi/sonrası, kendi sesiyle."""

import re
import shutil
import subprocess

import pytest

from apps.video_studio.modules.soundbites import Soundbite, parse_soundbites, total_seconds
from shared.edit_models import EditProject
from tests.test_rough_cut import SHOTS, TTS, edit_project, library, plan_rough_cut, video_clips


def bite(start, end, placement, path="C:/dha.mp4"):
    return Soundbite(path=path, filename="dha.mp4", start_s=start, end_s=end, placement=placement)


def test_soundbites_wrap_the_voiceover():
    bites = [bite(22.72, 25.72, "before"), bite(90.0, 96.0, "after"), bite(100.0, 104.0, "after")]
    project = plan_rough_cut(edit_project(), library(), soundbites=bites)
    EditProject.model_validate(project)
    clips = video_clips(project)
    assert clips[0]["use_source_audio"] and clips[0]["start_f"] == 0 and clips[0]["duration_f"] == 90
    assert [c["use_source_audio"] for c in clips[-2:]] == [True, True]
    assert all(a["start_f"] + a["duration_f"] == b["start_f"] for a, b in zip(clips, clips[1:]))
    tts = next(t for t in project["edit_plan"]["timeline"]["tracks"] if t["kind"] == "audio")["clips"][0]
    assert tts["start_f"] == 90  # seslendirme, öncesindeki kesit bitince başlar
    assert clips[-1]["start_f"] + clips[-1]["duration_f"] == 90 + round(21.27 * 30) + 180 + 120


def test_broll_does_not_repeat_the_soundbite_footage():
    shot_4 = SHOTS[3]  # vitrine çarpmış otomobil: açılış için en güçlü sahne
    project = plan_rough_cut(edit_project(), library(), soundbites=[bite(shot_4[0], shot_4[1], "before")])
    broll = [c for c in video_clips(project) if not c["use_source_audio"]]
    assert "video_001_shot_004" not in {c["shot_id"] for c in broll}


def test_short_voiceover_plus_soundbites_still_reach_twenty_seconds():
    text = "Otomobil dükkâna çarptı. Beş kişi yaralandı."
    project = plan_rough_cut(edit_project(text=text, duration=10.0), library(), soundbites=[bite(90.0, 94.0, "after")])
    clips = video_clips(project)
    assert clips[-1]["use_source_audio"]
    assert clips[-1]["start_f"] + clips[-1]["duration_f"] == 20 * 30  # 10 sn TTS + 6 sn sessiz dolgu + 4 sn kesit


def test_unanalysed_video_is_reported():
    with pytest.raises(ValueError, match="analiz edilmedi"):
        plan_rough_cut(edit_project(), library(), soundbites=[Soundbite(path="C:/baska.mp4", filename="baska.mp4", start_s=0, end_s=3, placement="before")])


def test_saved_soundbites_are_parsed_and_bad_ones_skipped():
    data = [bite(1, 4, "before").model_dump(), {"path": "x", "filename": "x", "start_s": 5, "end_s": 2, "placement": "before"}]
    parsed = parse_soundbites(data)
    assert len(parsed) == 1 and total_seconds(parsed) == 3


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_render_plays_soundbite_audio_then_voiceover(tmp_path, monkeypatch):
    from apps.video_studio.modules import render
    from apps.video_studio.modules.edit_plan import build_edit_project

    monkeypatch.setattr(render, "amd_encoder_available", lambda: False)
    source, audio = tmp_path / "dha.mp4", tmp_path / "tts.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=12",
         "-f", "lavfi", "-i", "sine=frequency=1000:duration=12", "-shortest", str(source)],
        check=True,
    )
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=4", str(audio)], check=True)
    lib = library([(0.0, 6.0, "event", "establishing", "Kaza", ""), (6.0, 12.0, "vehicle", "context", "Ambulans", "")], source=str(source))
    lib["assets"][0]["audio"] = {"codec": "aac"}
    text = "Kaza oldu. Yaralılar var."
    project = plan_rough_cut(
        build_edit_project(lib, text, str(audio), 4.0, {"tts_text": text, "headline_1": "K", "headline_2": "B", "caption": "c"}),
        lib, soundbites=[bite(1.0, 4.0, "before", path=str(source))],
    )
    output = tmp_path / "out.mp4"
    render.render_rough_cut(project, lib, output)

    def loudness(start, seconds):
        log = subprocess.run(
            ["ffmpeg", "-ss", str(start), "-t", str(seconds), "-i", str(output), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True,
        ).stderr
        return float(re.search(r"mean_volume: (-?[\d.]+) dB", log).group(1))

    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(output)],
        capture_output=True, text=True, check=True,
    ).stdout)
    assert abs(duration - 20.0) < 0.2       # 3 sn kesit + 4 sn TTS + sessiz dolgu = şablonun en kısa süresi
    assert loudness(0.5, 2.0) > -35          # kesitin kendi sesi
    assert loudness(3.5, 3.0) > -35          # seslendirme
    assert loudness(12.0, 6.0) < -60         # seslendirme bitti: sessiz dolgu


def test_soundbite_outside_the_video_is_reported_and_overhang_is_trimmed():
    lib = library()
    lib["assets"][0]["source"]["duration_seconds"] = 157.28
    with pytest.raises(ValueError, match="süresini"):
        plan_rough_cut(edit_project(), lib, soundbites=[bite(158.0, 162.0, "after")])
    clips = video_clips(plan_rough_cut(edit_project(), lib, soundbites=[bite(155.0, 160.0, "after")]))
    assert clips[-1]["use_source_audio"] and clips[-1]["source_out_s"] <= 157.28
    assert clips[-1]["duration_f"] == round((157.28 - 155.0) * 30)


def test_broll_next_to_a_soundbite_does_not_run_into_it():
    """Kesit aralığı aynı sahnenin komşu penceresinden uzayan dolgu klibiyle de görüntüye girmez."""
    shots = [(0.0, 40.0, "event", "action", "Yanan tır dorsesi ve itfaiye", "")]  # tek uzun sahne: 4 pencere
    for reserved in [(12.0, 20.0), (2.4, 9.0), (0.0, 6.0)]:  # (2.4: ilk dolgu klibinin tam bittiği yer)
        project = plan_rough_cut(edit_project(), library(shots), soundbites=[bite(*reserved, "after")])
        for clip in video_clips(project):
            if not clip["use_source_audio"]:
                assert clip["source_out_s"] <= reserved[0] + 1e-6 or clip["source_in_s"] >= reserved[1] - 1e-6, (reserved, clip)
