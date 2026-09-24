"""Tasarım Stüdyosu (Faz 5): Axion şablon katmanları, elle blur ve son video komutu."""

import math
import re
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest

from apps.axion_local import store
from apps.design_studio import template
from apps.design_studio.blur import box_at, clean_blurs, mask_state, render_mask
from apps.design_studio.render import build_final_command, render_final, timeline_seconds
from shared.axion_template import (
    CANVAS_HEIGHT,
    HEADLINE_1_EXIT,
    HEADLINE_2_ENTER_START,
    HEADLINE_MAX_WIDTH,
    LOGO_BOX,
    LOGO_DROP_SECONDS,
    LOGO_DROP_START,
    LOGO_RISE_START,
    SLOGANS,
)


def test_template_assets_exist():
    for index in range(1, template.BACKGROUND_COUNT + 1):
        assert template.background_path(index).is_file()
    for name in ["logo.png", "slogan_1.png", "slogan_2.png", "fontlar/GoogleSans-Bold.ttf", "fontlar/OFL.txt"]:
        assert (template.ASSETS / name).is_file(), name


def test_background_changes_every_work_day_and_wraps_after_eight():
    assert template.background_index(date(2026, 9, 24)) == 1
    assert template.background_index(date(2026, 9, 25)) == 2
    assert template.background_index(date(2026, 10, 1)) == 8
    assert template.background_index(date(2026, 10, 2)) == 1
    image = template.background_image(1)
    assert image.size == (1080, 1920)


def test_project_work_day_starts_at_two_am(tmp_path):
    before = store.NewsProject(tmp_path / "20260925-013000_haber", "H", "")
    after = store.NewsProject(tmp_path / "20260925-020000_haber", "H", "")
    assert before.work_day == date(2026, 9, 24)
    assert after.work_day == date(2026, 9, 25)


def test_turkish_upper_keeps_dotted_and_dotless_i():
    assert template.turkish_upper("istifa ığdır") == "İSTİFA IĞDIR"


def test_headline_layout_one_two_or_manual_lines_within_box():
    short = template.layout_headline("5 kişi yaralandı")
    assert short.lines == ["5 KİŞİ YARALANDI"]
    assert short.font_size == 58
    sample = template.layout_headline("Mansur Yavaş CHP'den istifa etti")
    assert sample.lines == ["MANSUR YAVAŞ", "CHP'DEN İSTİFA ETTİ"]  # editörün Canva örneğindeki bölünme
    manual = template.layout_headline("Mansur Yavaş CHP'den\nistifa etti")
    assert manual.lines == ["MANSUR YAVAŞ CHP'DEN", "İSTİFA ETTİ"]
    long = template.layout_headline(
        "Savrulan otomobil berber dükkânına çarptı, kazada yaralanan beş kişi hastaneye kaldırıldı ve tedavi altına alındı"
    )
    font = template._font(long.font_size)
    assert long.font_size < 58
    assert 2 <= len(long.lines) <= 3
    assert all(font.getlength(line) <= HEADLINE_MAX_WIDTH for line in long.lines)
    assert [w.text for w in long.words] == " ".join(long.lines).split(" ")


def test_top_strip_timeline_follows_canva_sample():
    enter = 0.6
    assert template.top_state(0.0, 0, enter) == ("h1",)
    assert template.top_state(8.5, 0, enter) == ("h1",)
    assert template.top_state(8.9, 0, enter)[0] == "h1_exit"
    assert template.top_state(9.2, 0, enter) == ("blank",)
    assert template.top_state(9.6, 1, enter)[:2] == ("slogan", 0)
    assert template.top_state(10.2, 0, enter) == ("slogan", 0, 1.0, 0)
    assert template.top_state(12.0, 0, enter) == ("slogan", 1, 1.0, 0)
    assert template.top_state(13.0, 0, enter) == ("blank",)
    assert template.top_state(HEADLINE_2_ENTER_START + 0.1, 0, enter)[0] == "h2_enter"
    assert template.top_state(30.0, 0, enter) == ("h2",)


def test_headline_2_words_enter_one_by_one_and_settle():
    layout = template.layout_headline("Bağımsız siyasi olarak yola devam kararı verdi")
    alphas, _ = template.headline_enter_params(layout, 0.0)
    assert alphas[-1] == 0  # henüz hiçbir kelime tam görünmüyor
    first_line = [i for i, w in enumerate(layout.words) if w.line == 0]
    alphas, _ = template.headline_enter_params(layout, 0.1)
    assert alphas[first_line[-1]] > alphas[first_line[0]]  # 1. satır sağdan sola
    alphas, offsets = template.headline_enter_params(layout, template.headline_enter_seconds(layout))
    assert all(a == 1 for a in alphas)
    assert all(abs(o) < 0.01 for o in offsets)


def test_headline_1_exit_fades_first_line_first():
    layout = template.layout_headline("Mansur Yavaş CHP'den istifa etti")
    alphas, offsets = template.headline_exit_params(layout, 0.6)
    assert alphas[0] < alphas[-1]
    assert offsets[0] < 0  # sola kayar
    assert all(a == pytest.approx(0) for a in template.headline_exit_params(layout, 1.0)[0])


def test_old_tv_opens_from_a_line():
    assert template.old_tv_scale(0.0)[0] == 0
    sx, sy = template.old_tv_scale(0.3)
    assert sx > 0.5 and sy < 0.5  # çizgi gibi: geniş ama basık
    assert template.old_tv_scale(1.0) == (1.0, 1.0)
    assert template.render_slogan(SLOGANS[0]["file"], 1.0).getbbox() is not None
    assert template.render_slogan(SLOGANS[0]["file"], 0.0).getbbox() is None


def _evaluate(expression: str, t: float) -> float:
    python = expression.replace("if(", "_if(").replace("lt(", "_lt(")
    return eval(python, {"_if": lambda c, a, b: a if c else b, "_lt": lambda a, b: a < b,
                         "exp": math.exp, "pow": pow, "t": t})


def test_logo_rises_settles_and_drops_same_in_python_and_ffmpeg():
    expression = template.logo_y_expression()
    assert template.logo_y(LOGO_RISE_START - 0.1) == CANVAS_HEIGHT
    assert template.logo_y(17.0) == pytest.approx(LOGO_BOX["rest_y"], abs=2)
    assert template.logo_y(LOGO_DROP_START + LOGO_DROP_SECONDS + 0.01) == CANVAS_HEIGHT
    for t in [15.0, 15.1, 15.5, 16.0, 17.0, 17.5, 17.6, 17.7, 25.0]:
        assert _evaluate(expression, t) == pytest.approx(template.logo_y(t), abs=0.01), t
    assert template.render_logo_box(0.5).size == (LOGO_BOX["width"], LOGO_BOX["height"])


def _concat_seconds(path: Path) -> float:
    return sum(float(v) for v in re.findall(r"^duration ([\d.]+)$", path.read_text(), re.M))


def test_layers_write_only_changing_frames(tmp_path):
    layers = template.write_layers(tmp_path, "Mansur Yavaş CHP'den istifa etti", "Yola devam kararı verdi", 3, 30, 20.0)
    assert layers.base.is_file() and layers.frame.is_file()
    assert _concat_seconds(layers.top) == pytest.approx(20.0, abs=0.01)
    assert _concat_seconds(layers.logo) == pytest.approx(20.0, abs=0.01)
    # Sabit anlar tek kare: 600 karelik videoda çok daha az PNG yazılır.
    assert len(list(tmp_path.glob("ust_*.png"))) < 120
    assert len(list(tmp_path.glob("logo_*.png"))) < 20
    text = layers.top.read_text()
    assert text.startswith("ffconcat version 1.0")
    assert text.strip().splitlines()[-1].startswith("file ")  # son kare tekrar edilir (concat süresi için)


def test_frame_overlay_has_white_ring_and_transparent_video_area():
    overlay = template.frame_overlay(1)
    assert all(v >= 240 for v in overlay.getpixel((62, 1000))[:3])
    assert overlay.getpixel((540, 1000))[3] == 0
    assert overlay.getpixel((61, 454))[3] == 255  # yuvarlak köşenin dışı arka plan


def _blur(**changes):
    blur = {"id": "b1", "shape": "elips", "strength": 5, "opacity": 0.8, "start": 1.0, "end": 4.0,
            "keys": [{"t": 1.0, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1}, {"t": 3.0, "x": 0.5, "y": 0.3, "w": 0.4, "h": 0.2}]}
    blur.update(changes)
    return blur


def test_clean_blurs_validates_browser_data():
    cleaned = clean_blurs([
        _blur(strength=99, opacity=5, shape="kalp"),
        _blur(start=5, end=2),                     # bitiş başlangıçtan önce
        _blur(keys=[]),                            # anahtar kare yok
        "bozuk",
    ], duration=20.0)
    assert len(cleaned) == 1
    assert cleaned[0]["strength"] == 10 and cleaned[0]["opacity"] == 1.0 and cleaned[0]["shape"] == "yuvarlak"
    assert clean_blurs(None, 20.0) == []


def test_blur_box_moves_linearly_between_keys():
    blur = clean_blurs([_blur()], 20.0)[0]
    assert box_at(blur, 0.0) == (0.1, 0.1, 0.2, 0.1)
    assert box_at(blur, 2.0) == pytest.approx((0.3, 0.2, 0.3, 0.15))
    assert box_at(blur, 10.0) == (0.5, 0.3, 0.4, 0.2)
    assert mask_state(blur, 0.5, 960, 1226) is None
    state = mask_state(blur, 2.0, 960, 1226)
    mask = render_mask(blur, state, 960, 1226)
    x, y, w, h = state
    assert mask.getpixel((x + w // 2, y + h // 2)) == pytest.approx(round(255 * 0.8), abs=2)
    assert mask.getpixel((5, 5)) == 0


def test_final_command_blurs_video_before_template(tmp_path):
    layers = template.Layers(*(tmp_path / n for n in ["zemin.png", "cerceve.png", "ust.ffconcat", "logo.ffconcat"]))
    blur = clean_blurs([_blur()], 20.0)
    command = build_final_command(tmp_path / "kaba.mp4", layers, 30, 20.0, tmp_path / "son.mp4", ["-c:v", "libx264"],
                                  blur, [tmp_path / "blur0.ffconcat"])
    graph = command[command.index("-filter_complex") + 1]
    assert "gblur=sigma=20.0" in graph and "alphamerge" in graph
    assert graph.index("alphamerge") < graph.index("[base][slot]overlay")
    assert "crop=960:1225" in graph
    assert command.count("concat") == 3


def test_timeline_seconds_from_edit_project():
    project = {"edit_plan": {"timeline": {"fps": 30, "tracks": [{"clips": [{"start_f": 0, "duration_f": 300}, {"start_f": 300, "duration_f": 330}]}]}}}
    assert timeline_seconds(project) == (30, 21.0)
    assert timeline_seconds(None) is None


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_render_final_produces_1080x1920_video(tmp_path):
    rough = tmp_path / "kaba_kurgu.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=960x1226:rate=30:duration=3",
        "-f", "lavfi", "-i", "sine=duration=3", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(rough),
    ], check=True)
    output = tmp_path / "son_video.mp4"
    blur = clean_blurs([_blur(start=0.0, end=3.0)], 3.0)
    render_final(rough, "Başlık bir", "Başlık iki", 2, 30, 3.0, output, blur)
    info = subprocess.run(["ffmpeg", "-i", str(output)], capture_output=True, text=True).stderr
    assert "1080x1920" in info
    assert "Audio" in info
    assert not list(tmp_path.glob("*.yaziliyor.mp4"))
