"""v4.0.0-alpha.4: müzik altlığı — hazır parçalar, editörün müziği, son videoda karışım (konuşurken kısılır)."""

import re
import shutil
import subprocess

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
                                music=(music.path("gerilim"), -3.5))
    graph = mixed[mixed.index("-filter_complex") + 1]
    assert mixed[mixed.index("-stream_loop") + 3] == str(music.path("gerilim"))  # döngülü giriş
    assert "[4:a]" in graph and "volume=-3.5dB" in graph and "sidechaincompress" in graph
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


@needs_ffmpeg
def test_music_fills_silence_and_stays_under_the_voice(tmp_path):
    rough = tmp_path / "kaba_kurgu.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=960x1226:r=30:d=8", "-f", "lavfi",
                    "-i", "sine=f=300:duration=8,volume='if(lt(t,4),2,0)':eval=frame", "-c:v", "libx264", "-preset",
                    "ultrafast", "-c:a", "aac", "-shortest", str(rough)], check=True)
    results = {}
    for track in ("gundem", music.OFF):
        design = load_design({"version": 2, "music": track}, "A", "B", 8.0)
        output = tmp_path / f"son_{track}.mp4"
        render_final(rough, design, assets.backgrounds()[0], 30, 8.0, output)
        results[track] = (_loudness(output, 0.5, 3.5), _loudness(output, 5, 7.5))
    (voice_music, gap_music), (voice_plain, gap_plain) = results["gundem"], results[music.OFF]
    assert gap_plain < -60 and -30 < gap_music < -20  # sessiz kısımda müzik duyulur
    assert -20 < voice_plain < -15  # seslendirme düzeyi (TTS -18 LUFS)
    assert abs(voice_music - voice_plain) < 1.0  # konuşurken müzik altta kalır (kısılır)
