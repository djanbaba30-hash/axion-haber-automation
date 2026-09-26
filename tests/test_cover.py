"""v4.0.0-alpha.3: kapak = videonun ilk karesi (Reels/Shorts kapak seçimi; ayrı kapak yüklemek yok).

Başlık tarafı `test_design_studio.test_first_frame_is_the_cover_with_the_full_headline`'da; burada kurgu tarafı:
seslendirmenin önünde kaynak sesli kesit olsa da ilk kare kapak sahnesinden.
"""

import shutil
import subprocess

import pytest
from PIL import Image

from apps.video_studio.modules import render
from apps.video_studio.modules.edit_plan import build_edit_project
from apps.video_studio.modules.rough_cut import plan_rough_cut
from apps.video_studio.modules.soundbites import Soundbite
from test_rough_cut import library, video_clips

TEXT = "Otomobil dükkâna çarptı. Beş kişi yaralandı. Polis olay yerinde inceleme yaptı."
SHOTS = [(0.0, 6.0, "person", "portrait", "Mikrofona konuşan esnaf", ""),
         (6.0, 12.0, "event", "establishing", "Dükkâna çarpan hasarlı otomobil", "")]


def cut(source, audio="C:/tts.mp3", placement="before"):
    lib = library(SHOTS, source=str(source))
    bite = Soundbite(path=str(source), filename=source.name, start_s=0.5, end_s=3.5, placement=placement)
    package = {"tts_text": TEXT, "headline_1": "KAZA", "headline_2": "B", "caption": "c"}
    return plan_rough_cut(build_edit_project(lib, TEXT, str(audio), 8.0, package), lib, soundbites=[bite]), lib


def test_soundbite_first_still_opens_on_the_cover_scene(tmp_path):
    source, audio = tmp_path / "dha.mp4", tmp_path / "tts.mp3"
    source.write_bytes(b"mp4")
    audio.write_bytes(b"mp3")
    project, lib = cut(source, audio)
    clips = video_clips(project)
    assert clips[0]["use_source_audio"] and clips[1]["scene"] == 0
    graph = render.build_render_command(project, lib, tmp_path / "out.mp4", render.X264)
    graph = graph[graph.index("-filter_complex") + 1]
    assert "split=2[v1][kapak0]" in graph and "[kapak][v0k][v1]" in graph
    assert f"concat=n={len(clips) + 1}:v=1" in graph
    # Kesit sonda ise (ya da hiç yoksa) video zaten kapak sahnesiyle açılır: ek kare yok.
    after, lib = cut(source, audio, placement="after")
    graph = render.build_render_command(after, lib, tmp_path / "out.mp4", render.X264)
    assert "kapak" not in graph[graph.index("-filter_complex") + 1]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_rendered_video_first_frame_is_the_cover(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "amd_encoder_available", lambda: False)
    source, audio = tmp_path / "dha.mp4", tmp_path / "tts.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=640x360:r=25:d=6", "-f", "lavfi",
                    "-i", "color=c=blue:s=640x360:r=25:d=6", "-f", "lavfi", "-i", "sine=duration=12",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
                    "-shortest", str(source)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=8", str(audio)], check=True)
    project, lib = cut(source, audio)
    cover = next(c for c in video_clips(project) if c["scene"] == 0)
    assert cover["source_in_s"] >= 6.0  # kapak: olay görüntüsü (mavi), röportaj değil
    output = tmp_path / "kaba_kurgu.mp4"
    render.render_rough_cut(project, lib, output)
    colors = []
    for number in (0, 1):
        frame = tmp_path / f"kare{number}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-vf", f"select=eq(n\\,{number})", "-frames:v", "1",
                        str(frame)], check=True)
        with Image.open(frame) as image:
            colors.append(image.convert("RGB").getpixel((480, 600)))
    assert colors[0][2] > 200 and colors[0][0] < 60  # ilk kare mavi: kapak sahnesi
    assert colors[1][0] > 200 and colors[1][2] < 60  # ikinci kareden kesit (kırmızı)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(output)],
                           capture_output=True, text=True, check=True).stdout
    assert abs(float(probe) - sum(c["duration_f"] for c in video_clips(project)) / 30) < 0.1  # süre değişmez
