"""v4.0.0-alpha.4: müzik altlığı — hazır parçalar, editörün müziği, son videoda karışım (konuşurken kısılır)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.design_studio import assets, music
from apps.design_studio.design import load_design
from apps.design_studio.render import build_final_command, render_final
from apps.design_studio.template import Layers

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))


def test_builtin_tracks_and_default():
    assert list(music.tracks())[:3] == ["gundem", "gerilim", "sakin"]
    assert load_design(None, "A", "B", 20.0).music == music.DEFAULT == "gundem"  # eski tasarım belgesi: varsayılan açık
    assert music.path("gundem").name == "gundem.mp3"
    assert music.path(music.OFF) is None and music.path("") is None and music.path("yok") is None
    assert music.path("../../secrets") is None


def test_own_music_stays_on_this_computer(tmp_path):
    track = music.add("Haber altlığı?.mp3", b"ID3")
    assert track == "kendi:Haber altlığı_.mp3" and music.tracks()[track] == "Haber altlığı_ (eklenen)"
    assert music.path(track) == tmp_path / "data" / "varliklar" / "muzik" / "Haber altlığı_.mp3"
    with pytest.raises(ValueError):
        music.add("sarki.exe", b"x")
    with pytest.raises(ValueError):
        music.add("bos.mp3", b"")


def test_final_command_mixes_music_under_the_voice(tmp_path):
    layers = Layers(tmp_path / "zemin.png", tmp_path / "cerceve.ffconcat", tmp_path / "grafik.ffconcat")
    plain = build_final_command(tmp_path / "kaba.mp4", layers, 30, 20.0, tmp_path / "son.mp4", ["-c:v", "libx264"])
    assert plain[plain.index("-c:a") + 1] == "copy" and "-stream_loop" not in plain
    mixed = build_final_command(tmp_path / "kaba.mp4", layers, 30, 20.0, tmp_path / "son.mp4", ["-c:v", "libx264"],
                                music=(music.path("gerilim"), -3.5, [(1.0, 5.0)]))
    graph = mixed[mixed.index("-filter_complex") + 1]
    assert mixed[mixed.index("-stream_loop") + 3] == str(music.path("gerilim"))  # döngülü giriş
    assert "[4:a]" in graph and "volume='pow(10,(-3.5+-18.0*clip(min((t-0.500)/0.5,(5.500-t)/0.5),0,1))/20)'" in graph
    assert "afade=t=out:st=18.500:d=1.5" in graph and "atrim=duration=20.000" in graph
    assert mixed[mixed.index("-map", mixed.index("[out]")) + 1] == "[aout]" and mixed[mixed.index("-c:a") + 1] == "aac"


@needs_ffmpeg
def test_builtin_tracks_loop_without_a_gap():
    """Parçalar tam ölçü uzunluğunda (dairesel sentez): döngüde boşluk ya da fazla kare yok."""
    for name, seconds in (("gundem", 80.0), ("gerilim", 32 * 4 * 60 / 110), ("sakin", 72.0)):
        info = subprocess.run(["ffmpeg", "-i", str(music.path(name)), "-f", "null", "-"], capture_output=True,
                              text=True).stderr
        hours, minutes, secs = re.findall(r"time=(\d+):(\d+):([\d.]+)", info)[-1]
        assert abs(float(minutes) * 60 + float(secs) - seconds) < 0.05, name


def _loudness(path, start, end):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", f"atrim={start}:{end},ebur128",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])


def test_duck_expression():
    assert music.duck_expression([], 10.0) == "0"
    assert music.duck_expression(None, 10.0) == "-18.0*clip(min((t--0.500)/0.5,(10.500-t)/0.5),0,1)"  # bilgi yok: hep
    both = music.duck_expression([(0.0, 4.0), (8.0, 11.0)], 14.0)
    assert both.startswith("-18.0*max(clip(") and both.count("clip(") == 2


SPEECH = Path(__file__).parent / "ornekler" / "konusma.mp3"


def _rough_with_soundbites(tmp_path):
    """0–4 sn seslendirme (sentez konuşma), 4–8 sn konuşmasız kesit (uğultu), 8–11 sn konuşmalı kesit, 11–14 sn sessiz."""
    rough = tmp_path / "kaba_kurgu.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=960x1226:r=30:d=14",
                    "-i", str(SPEECH), "-f", "lavfi", "-i", "anoisesrc=color=brown:d=4:a=0.2", "-i", str(SPEECH),
                    "-filter_complex", "[1:a]atrim=0:4,aresample=48000[a];[2:a]aresample=48000[b];"
                    "[3:a]atrim=0:3,aresample=48000[c];anullsrc=r=48000:d=3[d];[a][b][c][d]concat=n=4:v=0:a=1[aud]",
                    "-map", "0:v", "-map", "[aud]", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(rough)],
                   check=True)
    clip = lambda start, seconds, audio: {"start_f": round(start * 30), "duration_f": round(seconds * 30),  # noqa: E731
                                          "use_source_audio": audio, "asset_id": "video_001"}
    edit_project = {"audio": {"asset_id": "tts", "duration_seconds": 4.0}, "edit_plan": {"timeline": {"fps": 30, "tracks": [
        {"kind": "video", "clips": [clip(0, 4, False), clip(4, 4, True), clip(8, 3, True), clip(11, 3, False)]},
        {"kind": "audio", "clips": [{"start_f": 0, "duration_f": 120, "asset_id": "tts"}]}]}}}
    (tmp_path / "edit_project.json").write_text(json.dumps(edit_project), encoding="utf-8")
    return rough, edit_project


@needs_ffmpeg
def test_speech_spans_cover_voiceover_and_talking_soundbites_only(tmp_path):
    rough, edit_project = _rough_with_soundbites(tmp_path)
    assert music.speech_spans(edit_project, rough) == [(0.0, 4.0), (8.0, 11.0)]
    assert music.speech_spans(None, rough) is None


@needs_ffmpeg
def test_music_is_barely_there_under_speech_and_audible_elsewhere(tmp_path):
    """Editör: konuşmada (seslendirme, röportaj) varla yok arası; konuşmasız kesitte ve sessizlikte duyulur, yüksek değil."""
    rough, edit_project = _rough_with_soundbites(tmp_path)
    spans = music.speech_spans(edit_project, rough)
    bed = tmp_path / "altlik.wav"
    track = music.path("gundem")
    graph = ";".join(["anullsrc=r=48000:cl=stereo:d=14[sus]"] + music.mix_filters("sus", "0:a", 14.0,
                                                                                    music.gain_db(track), spans))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(track), "-filter_complex", graph,
                    "-map", "[aout]", "-t", "14", str(bed)], check=True)
    under_voice, under_talk = _loudness(bed, 1, 3.4), _loudness(bed, 8.6, 10.4)
    open_bite, open_tail = _loudness(bed, 4.6, 7.4), _loudness(bed, 11.6, 12.4)
    assert -48 < under_voice < -42 and -48 < under_talk < -42  # varla yok arası (seslendirme -18'in ~27 dB altı)
    assert -30 < open_bite < -24 and -30 < open_tail < -24  # duyulur, kesitin (-20) altında
    # Son videoda da: müzik kapalıyken sessiz son, açıkken müzik; konuşma kısmı neredeyse aynı.
    results = {}
    for choice in ("gundem", music.OFF):
        output = tmp_path / f"son_{choice}.mp4"
        render_final(rough, load_design({"version": 2, "music": choice}, "A", "B", 14.0), assets.backgrounds()[0], 30,
                     14.0, output)
        results[choice] = (_loudness(output, 1, 3.4), _loudness(output, 11.6, 12.4))
    assert abs(results["gundem"][0] - results[music.OFF][0]) < 0.5 and results[music.OFF][1] < -60
    assert -30 < results["gundem"][1] < -24
