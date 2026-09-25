"""Faz 3: kural tabanlı kaba kurgu ve FFmpeg render. Fixture: gerçek Bayrampaşa analizi (v1.7.1, Windows)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from apps.video_studio.modules import render
from apps.video_studio.modules.rough_cut import clip_rows, has_rough_cut, matches_template, plan_rough_cut, segment_times
from shared.edit_models import EditProject

TTS = (
    "İstanbul Bayrampaşa’da iki otomobilin çarpışmasıyla savrulan araç, kaldırımdaki 4 kişiye ve bir berber "
    "dükkânına çarptı. Kazada 2’si ağır 5 kişi yaralandı. Yaralılar hastanelere kaldırılırken, ağır yaralılar "
    "arasında bir temizlik görevlisinin bulunduğu belirtildi. Çarpışmaya karışan iki sürücü gözaltına alındı. "
    "Polis olay yerinde güvenlik önlemi aldı."
)
# (başlangıç, bitiş, visual_type, editorial_role, açıklama, görünen yazı)
SHOTS = [
    (0.0, 8.32, "event", "establishing", "Ağaç önünde, dükkân girişinde toplanmış insanlar ve beyaz araç çevresindeki enkaz.", "DHA"),
    (8.32, 15.04, "event", "establishing", "Dükkânların bulunduğu caddede kalabalık ve yol üzerinde duran hasarlı beyaz otomobil.", "DHA"),
    (15.04, 22.72, "vehicle", "context", "Cadde üzerinde duran beyaz ambulansın yandan görünümü.", "AMBULANS"),
    (22.72, 30.4, "event", "action", "Dükkân vitrinine çarpmış beyaz otomobil, kaldırımdaki parçalar ve çevresindeki insanlar.", "DHA"),
    (30.4, 36.16, "vehicle", "context", "Kalabalık cadde üzerinde yakından görülen beyaz ambulans.", "AMBULANS"),
    (36.16, 41.92, "event", "establishing", "Caddede hasarlı beyaz otomobil, arkasındaki itfaiye aracı ve yolu izleyen kalabalık.", "DHA"),
    (41.92, 48.64, "event", "detail", "Yolun ortasında ön kısmı hasarlı beyaz otomobil ve arkasında bekleyen itfaiye aracı.", "DHA"),
    (48.64, 54.4, "vehicle", "context", "Hasarlı otomobilin yanında duran büyük kırmızı itfaiye aracı.", "112, İTFAİYE"),
    (54.4, 60.16, "event", "context", "Cadde üzerinde duran ambulans ve ön planda yürüyen itfaiye görevlisi.", "112"),
    (60.16, 63.88, "vehicle", "detail", "Dükkân cephesine çarpmış, ön ve arka kısmı ağır hasarlı beyaz otomobil.", "DHA"),
    (63.88, 68.68, "vehicle", "detail", "Ön tamponu ve kaputu parçalanmış beyaz otomobilin karşıdan görünümü.", "34 FPR 116, DHA"),
    (68.68, 71.56, "event", "evidence", "Kaldırım kenarında ağır hasarlı beyaz otomobil ve yere saçılmış parçalar.", "34 FPR 116"),
    (71.56, 78.0, "event", "detail", "Kırılmış dükkân vitrini önünde yürüyen adam ve hasarlı otomobil.", "DHA"),
    (78.0, 85.68, "event", "context", "Hasarlı otomobil ve kırık vitrin önünden geçen motosikletli kurye.", "DHA"),
    (85.68, 157.28, "person", "portrait", "Dükkân girişinde DHA mikrofonuna konuşan sakallı adam.", "DHA"),
]


def visual(kind, role, description, text):
    return {"description": description, "visual_type": kind, "editorial_role": role, "visible_text": text, "confidence": 0.99}


def library(shots=SHOTS, source="C:/dha.mp4"):
    items = []
    for number, (start, end, kind, role, description, text) in enumerate(shots, 1):
        shot_id = f"video_001_shot_{number:03d}"
        count = max(1, round((end - start) / 10))
        step = (end - start) / count
        windows = [
            {"window_id": f"{shot_id}_w{i + 1:02d}", "shot_id": shot_id, "start_seconds": start + i * step,
             "end_seconds": end if i == count - 1 else start + (i + 1) * step, "visual": visual(kind, role, description, text)}
            for i in range(count)
        ]
        items.append({"shot_id": shot_id, "asset_id": "video_001", "shot_number": number, "start_seconds": start,
                      "end_seconds": end, "duration_seconds": round(end - start, 3), "analysis_windows": windows,
                      "visual": visual(kind, role, description, text)})
    return {"assets": [{
        "asset_id": "video_001", "asset_type": "video", "source": {"filename": "dha.mp4", "sha256": "a" * 64, "original_path": source},
        "geometry": {"encoded_width": 1920, "encoded_height": 1080, "display": {"width": 1920, "height": 1080}},
        "shots": items,
    }]}


def edit_project(text=TTS, duration=21.27, audio_path="C:/tts.mp3", alignment=True):
    from apps.video_studio.modules.edit_plan import build_edit_project

    package = {"headline_1": "KAZA", "headline_2": "B", "caption": "c", "tts_text": text}
    if alignment:
        step = duration / len(text)
        package["tts_alignment"] = {
            "characters": list(text),
            "start_seconds": [round(i * step, 3) for i in range(len(text))],
            "end_seconds": [round((i + 1) * step, 3) for i in range(len(text))],
        }
    return build_edit_project(library(), text, audio_path, duration, package)


def video_clips(project):
    return next(t for t in project["edit_plan"]["timeline"]["tracks"] if t["kind"] == "video")["clips"]


def test_rough_cut_covers_whole_voiceover_without_gaps():
    project = plan_rough_cut(edit_project(), library())
    EditProject.model_validate(project)
    clips = video_clips(project)
    assert clips[0]["start_f"] == 0
    assert all(a["start_f"] + a["duration_f"] == b["start_f"] for a, b in zip(clips, clips[1:]))
    assert clips[-1]["start_f"] + clips[-1]["duration_f"] == round(21.27 * 30)
    assert all(2 * 30 <= c["duration_f"] <= 5 * 30 + 1 for c in clips)  # ne çok hızlı ne çok uzun
    assert all(c["origin"] == "rule" for c in clips)
    assert has_rough_cut(project)
    assert matches_template(project)
    assert len(clip_rows(project)) == len(clips)


def test_rough_cut_matches_news_to_visuals():
    clips = video_clips(plan_rough_cut(edit_project(), library()))
    shots = {int(c["shot_id"][-3:]) - 1: c for c in clips}
    by_segment = {}
    for clip in clips:
        by_segment.setdefault(clip["segment_id"], []).append(SHOTS[int(clip["shot_id"][-3:]) - 1])
    # Açılış: olay yeri / olay anı
    assert by_segment["segment_001"][0][3] in {"establishing", "action"}
    # "yaralandı / hastanelere kaldırıldı" → ambulans görüntüsü
    assert any("ambulans" in s[4] for s in by_segment["segment_002"] + by_segment["segment_003"])
    # Röportaj görüntüsü sessiz dolgu olarak kullanılmaz; aynı shot art arda gelmez.
    assert not any(s[3] == "portrait" for s in sum(by_segment.values(), []))
    assert all(a["shot_id"] != b["shot_id"] for a, b in zip(clips, clips[1:]))
    assert shots


def test_segment_times_without_alignment_are_proportional():
    project = EditProject.model_validate(edit_project(alignment=False))
    times = segment_times(project)
    assert times[0][1] == 0.0 and times[-1][2] == 21.27
    assert all(a[2] == b[1] for a, b in zip(times, times[1:]))


def test_short_material_is_reused_instead_of_leaving_gaps():
    project = plan_rough_cut(edit_project(), library(SHOTS[2:4]))
    clips = video_clips(project)
    assert sum(c["duration_f"] for c in clips) == round(21.27 * 30)


def test_every_clip_fills_the_video_area_without_blur_bars():
    """Editör kararı: hiçbir sahnede bulanık dolgu yok; gösterilen alan hep video alanı oranında."""
    for clip in video_clips(plan_rough_cut(edit_project(), library())):
        view = clip["framing"]["view_region"]
        assert abs(view["width"] * 16 / 9 / view["height"] - 960 / 1226) < 0.01


def test_render_never_builds_a_blur_fill_even_for_old_fit_blur_clips():
    """Eski kayıtta mode=fit_blur kalmış olsa bile render bulanık dolgu üretmez (tek kadraj yolu)."""
    from apps.video_studio.modules.render import _clip_filter
    from shared.edit_models import Framing

    for framing in (Framing(mode="fit_blur"), Framing(mode="fit_blur", view_region={"x": 0.2, "y": 0, "width": 0.44, "height": 1})):
        graph = _clip_filter(0, framing, 960, 1226, 30, 90)
        assert "boxblur" not in graph and "overlay" not in graph

def test_render_command_reports_missing_source(tmp_path):
    audio = tmp_path / "tts.mp3"
    audio.write_bytes(b"mp3")
    project = plan_rough_cut(edit_project(audio_path=str(audio)), library(source=str(tmp_path / "yok.mp4")))
    with pytest.raises(FileNotFoundError, match="yeniden seçip analiz"):
        render.build_render_command(project, library(source=str(tmp_path / "yok.mp4")), tmp_path / "out.mp4", render.X264)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_render_produces_template_sized_mp4_matching_voiceover(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "amd_encoder_available", lambda: False)
    source, audio = tmp_path / "dha.mp4", tmp_path / "tts.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=12:size=640x360:rate=25", str(source)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=4", str(audio)], check=True)
    text = "Otomobil dükkâna çarptı. Beş kişi yaralandı."
    shots = [(0.0, 6.0, "event", "establishing", "Hasarlı otomobil", ""), (6.0, 12.0, "vehicle", "context", "Ambulans", "")]
    lib = library(shots, source=str(source))
    from apps.video_studio.modules.edit_plan import build_edit_project

    project = plan_rough_cut(build_edit_project(lib, text, str(audio), 4.0, {"tts_text": text, "headline_1": "K", "headline_2": "B", "caption": "c"}), lib)
    output = tmp_path / "kaba_kurgu.mp4"

    assert render.render_rough_cut(project, lib, output) == "x264 (işlemci)"
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(output)],
        capture_output=True, text=True, check=True,
    ).stdout
    import json

    info = json.loads(probe)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (960, 1226)  # Canva şablonundaki video alanı
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert abs(float(info["format"]["duration"]) - 20.0) < 0.15  # 4 sn TTS, şablon en az 20 sn
    assert not (tmp_path / "kaba_kurgu.yaziliyor.mp4").exists()


def test_short_voiceover_is_extended_to_template_minimum():
    text = "Otomobil dükkâna çarptı. Beş kişi yaralandı."
    project = plan_rough_cut(edit_project(text=text, duration=15.0), library())
    clips = video_clips(project)
    assert project["audio"]["duration_seconds"] == 15.0
    assert clips[-1]["start_f"] + clips[-1]["duration_f"] == 20 * 30
    assert all(a["start_f"] + a["duration_f"] == b["start_f"] for a, b in zip(clips, clips[1:]))


def test_cuts_fall_in_pauses_between_words():
    project = plan_rough_cut(edit_project(), library())
    step = 21.27 / len(TTS)
    for clip in video_clips(project)[1:]:
        char = TTS[min(len(TTS) - 1, int(clip["start_f"] / 30 / step))]
        neighbours = TTS[max(0, int(clip["start_f"] / 30 / step) - 1): int(clip["start_f"] / 30 / step) + 2]
        assert " " in neighbours or char in ".,", f"kesme kelime ortasında: {neighbours!r}"


def test_sentence_end_is_preferred_over_word_gap():
    from apps.video_studio.modules.rough_cut import _cut_times

    project = EditProject.model_validate(edit_project())
    cuts = _cut_times(project, 21.27)
    sentence_ends = [21.27 / len(TTS) * (i + 1.5) for i, ch in enumerate(TTS[:-1]) if ch == "." and TTS[i + 1] == " "]
    assert any(abs(cut - end) < 0.1 for cut in cuts for end in sentence_ends)


def test_clock_time_is_not_a_sentence_end():
    from apps.video_studio.modules.edit_plan import _segment_ranges

    text = "Kaza meydana geldi. Saat 17.00’de ekipler geldi."
    assert [text[a:b] for a, b in _segment_ranges(text)] == ["Kaza meydana geldi.", "Saat 17.00’de ekipler geldi."]


def test_amd_failure_falls_back_to_x264(tmp_path, monkeypatch):
    """AMD donanım kodlayıcısı hata verirse video işlemciyle (x264) yine üretilir; yarım dosya kalmaz."""
    import types

    audio = tmp_path / "tts.mp3"
    audio.write_bytes(b"mp3")
    source = tmp_path / "dha.mp4"
    source.write_bytes(b"video")
    project = plan_rough_cut(edit_project(audio_path=str(audio)), library(source=str(source)))
    calls = []

    def fake_ffmpeg(command, timeout, label):
        if command[-1] == "-":  # ses yüksekliği ölçümü (sahte dosyalar: ölçülemez, kazanç 0)
            return types.SimpleNamespace(returncode=1, stderr="", stdout="")
        calls.append(command)
        output = Path(command[-1])
        output.write_bytes(b"partial")
        if "h264_amf" in command:
            return types.SimpleNamespace(returncode=1, stderr="AMF init failed", stdout="")
        return types.SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(render, "amd_encoder_available", lambda: True)
    monkeypatch.setattr(render, "run_ffmpeg", fake_ffmpeg)
    output = tmp_path / "kaba_kurgu.mp4"
    assert render.render_rough_cut(project, library(source=str(source)), output) == "x264 (işlemci)"
    assert [("h264_amf" in c, "libx264" in c) for c in calls] == [(True, False), (False, True)]
    assert output.exists() and not (tmp_path / "kaba_kurgu.yaziliyor.mp4").exists()
