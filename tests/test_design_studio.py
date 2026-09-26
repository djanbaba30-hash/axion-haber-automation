"""Tasarım Stüdyosu: yazı tipleri, başlık yerleşimi, tasarım belgesi, efektler, çerçeve, blur/mozaik, son video."""

import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

from apps.axion_local import store
from apps.design_studio import assets, effects as fx, template
from apps.design_studio.blur import BlurPass, blur_region, box_at, clean_blurs, mask_state, render_mask, write_mask_sequences
from apps.design_studio.design import Design, dump_design, load_design
from apps.design_studio.render import build_final_command, render_final, timeline_seconds
from shared.axion_template import HEADLINE_MAX_WIDTH, SLOGANS
from shared.fonts import DEFAULT_FAMILY, families, load_font, resolve
from shared.text_layout import fit_text, parse_lines


# ---------------------------------------------------------------- varlıklar ve yazı tipleri

def test_template_assets_exist():
    assert len(assets.backgrounds()) >= 8
    for name in ["logo.png", "slogan_1.png", "slogan_2.png", "fontlar/GoogleSans-Bold.ttf", "fontlar/OFL.txt"]:
        assert (template.ASSETS / name).is_file(), name


def test_font_registry_reads_family_and_weight_from_file():
    assert {"ExtraBold", "Black"} <= set(families()[DEFAULT_FAMILY])  # v3.1: daha kalın varsayılan
    assert "Bold" in families()["Google Sans"]  # eski tasarımlar kendi fontunu korur
    assert resolve("Yok Böyle Font", "Bold").family == DEFAULT_FAMILY  # bilinmeyen → varsayılan
    assert resolve(DEFAULT_FAMILY, "Bold").style == "ExtraBold"  # en yakın kalınlık
    assert resolve("Google Sans", "Black").style == "Bold"
    assert load_font(size=40).size == 40


def test_user_fonts_and_backgrounds_are_picked_up(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    font_path, repo_font = assets.save_asset("font", "Başlık Font.ttf", (template.ASSETS / "fontlar/GoogleSans-Bold.ttf").read_bytes())
    assert font_path.parent == tmp_path / "varliklar" / "fontlar" and repo_font == "assets/sablon/fontlar/Baslik_Font.ttf"
    count = len(assets.backgrounds())
    bg_path, repo_bg = assets.save_asset("arka_plan", "yeni.png", assets.backgrounds()[0].read_bytes())
    assert bg_path.name == f"arka_plan_{count + 1}.png" and repo_bg == f"assets/sablon/arka_plan_{count + 1}.png"
    assert assets.backgrounds()[-1] == bg_path
    with pytest.raises(ValueError):
        assets.save_asset("font", "virus.exe", b"x")


def test_background_rotates_every_work_day():
    items = assets.backgrounds()
    assert assets.background_for_day(date(2026, 9, 24)) == items[0]
    assert assets.background_for_day(date(2026, 9, 25)) == items[1]
    assert assets.background_for_day(date(2026, 9, 24) + timedelta(days=len(items))) == items[0]
    assert assets.background_by_name("arka_plan_3.png", date(2026, 9, 24)).name == "arka_plan_3.png"
    assert template.background_image(items[0]).size == (1080, 1920)


def test_project_work_day_starts_at_two_am(tmp_path):
    assert store.NewsProject(tmp_path / "20260925-013000_h", "H", "").work_day == date(2026, 9, 24)
    assert store.NewsProject(tmp_path / "20260925-020000_h", "H", "").work_day == date(2026, 9, 25)


# ---------------------------------------------------------------- başlık yerleşimi ve sansür

def test_strike_markup_marks_words():
    lines = parse_lines("~~silah~~ ile ~~iki kelime~~ son")
    assert [(t.text, t.strike) for t in lines[0]] == [("SİLAH", True), ("İLE", False), ("İKİ", True), ("KELİME", True), ("SON", False)]
    assert [t.text for t in parse_lines("küçük harf", upper=False)[0]] == ["küçük", "harf"]


def test_headline_fits_two_lines_or_shrinks():
    assert [" ".join(t.text for t in line) for line in fit_text("Mansur Yavaş CHP'den istifa etti").lines] == ["MANSUR YAVAŞ", "CHP'DEN İSTİFA ETTİ"]
    manual = fit_text("Mansur Yavaş CHP'den\nistifa etti")
    assert len(manual.lines) == 2 and manual.fits
    long = fit_text("Savrulan otomobil berber dükkânına çarptı, kazada yaralanan beş kişi hastaneye kaldırıldı ve tedavi altına alındı")
    assert not long.fits and long.size < 58
    font = load_font(size=long.size)
    assert all(font.getlength(" ".join(t.text for t in line)) <= HEADLINE_MAX_WIDTH for line in long.lines)


# ---------------------------------------------------------------- tasarım belgesi

def test_design_defaults_are_the_canva_template():
    design = load_design(None, "KAZA", "B", 20.0)
    assert design.headline_1.text == "KAZA" and design.headline_1.exit == "merge"
    assert design.headline_2.enter == "merge"
    assert design.slogans.effect == "old_tv" and design.logo.effect == "slow_baseline"
    assert design.frame.style == "sabit" and design.background is None
    assert design.headline_style.family == DEFAULT_FAMILY and design.headline_style.size == 58


def test_design_v1_file_is_upgraded():
    old = {"headline_1": "BİR", "headline_2": "", "background": 3, "blurs": [
        {"id": "b", "shape": "elips", "strength": 5, "opacity": 1, "start": 0, "end": 3, "keys": [{"t": 0, "x": .1, "y": .1, "w": .2, "h": .1}]}]}
    design = load_design(old, "KAZA", "B", 20.0)
    assert design.headline_1.text == "BİR" and design.headline_2.text == "B"
    assert design.background == "arka_plan_3.png"
    assert design.blurs[0]["effect"] == "blur" and design.blurs[0]["keys"][0]["r"] == 0
    assert dump_design(design)["version"] == 2


def test_design_rejects_bad_browser_values():
    design = load_design({"version": 2, "headline_style": {"color": "kırmızı", "size": 999},
                          "frame": {"style": "disko"}, "logo": {"effect": "uç"}}, "A", "B", 20.0)
    assert design.headline_style == Design().headline_style  # geçersiz → varsayılan belge
    design = load_design({"version": 2, "frame": {"style": "disko"}, "logo": {"effect": "uç"},
                          "headline_1": {"text": "X", "exit": "patla"}}, "A", "B", 20.0)
    assert design.frame.style == "sabit" and design.logo.effect == "slow_baseline" and design.headline_1.exit == "yok"


# ---------------------------------------------------------------- efektler

@pytest.mark.parametrize("effect", list(fx.TEXT_ENTER))
def test_every_enter_effect_ends_fully_visible(effect):
    lines = [0, 0, 0, 1, 1, 1, 1]
    start = fx.enter_state(effect, lines, 0.0)
    end = fx.enter_state(effect, lines, fx.enter_seconds(effect, lines) + 0.01)
    assert all(w.alpha == pytest.approx(1) and abs(w.dx) < 0.01 and abs(w.dy) < 0.01 for w in end.words)
    assert end.scale == pytest.approx(1)
    if effect != "yok":
        assert min(w.alpha for w in start.words) < 1


@pytest.mark.parametrize("effect", list(fx.TEXT_EXIT))
def test_every_exit_effect_ends_invisible(effect):
    lines = [0, 0, 1, 1]
    state = fx.text_state("yok", effect, lines, 0.0, 9.0, 9.0 - 1e-6)
    assert all(w.alpha < 0.05 for w in state.words) or effect == "yok"
    assert fx.text_state("yok", effect, lines, 0.0, 9.0, 9.0) is None


def test_merge_enters_first_line_right_to_left():
    lines = [0, 0, 0, 1, 1]
    state = fx.enter_state("merge", lines, 0.05)
    assert state.words[2].alpha > state.words[0].alpha  # 1. satır sağdan
    assert state.words[3].alpha == 0                  # 2. satır sonra


@pytest.mark.parametrize("effect", list(fx.SLOGAN_EFFECTS))
def test_slogan_effects_are_full_in_the_middle(effect):
    start, end = SLOGANS[0]["enter"][0], SLOGANS[0]["exit"][1]
    state = fx.slogan_state(effect, start, end, (start + end) / 2, 0)
    assert (state.alpha, state.sx, state.sy, state.split) == (1.0, 1.0, 1.0, 0)
    assert fx.slogan_state(effect, start, end, end + 0.01, 0) is None


def test_old_tv_opens_from_a_line():
    assert fx.old_tv_scale(0.0)[0] == 0
    sx, sy = fx.old_tv_scale(0.3)
    assert sx > 0.5 and sy < 0.5
    assert fx.old_tv_scale(1.0) == (1.0, 1.0)


def test_logo_rises_settles_and_drops():
    args = (15.03, 17.685, 1737, 200)
    rest = dict(tau=0.34, drop_start=17.47, glint=(17.15, 17.45))
    assert fx.logo_state("slow_baseline", *args, 15.0, **rest) is None
    rising = fx.logo_state("slow_baseline", *args, 15.1, **rest)
    settled = fx.logo_state("slow_baseline", *args, 17.0, **rest)
    assert rising.dy > 100 and abs(settled.dy) < 2
    assert fx.logo_state("slow_baseline", *args, 17.3, **rest).glint is not None


# ---------------------------------------------------------------- çerçeve

def test_frame_path_runs_clockwise_from_top_centre():
    f = fx.frame_field()
    ring = abs(f.d) < 0.6
    assert f.perimeter == pytest.approx(2 * (960 + 1225) - 4 * 6 - (8 - 2 * 3.1416) * 19, rel=0.02)
    top_centre = ring & (abs(f.xs - f.width / 2) < 2) & (f.ys < f.height / 2)
    right_centre = ring & (abs(f.ys - f.height / 2) < 2) & (f.xs > f.width / 2)
    assert f.s[top_centre].min() < 0.01 or f.s[top_centre].max() > 0.99
    assert 0.2 < f.s[right_centre].mean() < 0.3


@pytest.mark.parametrize("style", [s for s in fx.FRAME_STYLES if s != "yok"])
def test_frame_styles_draw_on_the_ring_only(style):
    rgba = fx.frame_rgba(style, "#F6F6F6", "#BEE1E8", 0.7)
    f = fx.frame_field()
    assert rgba[..., 3].max() > 200
    assert rgba[f.height // 2, f.width // 2, 3] == 0  # video alanının ortası boş


def test_animated_frame_loops_one_period():
    keys = {fx.frame_state_key("kovalayan", t / 30, 1.0, 30) for t in range(30 * 20)}
    assert len(keys) == round(3.5 * 30)
    assert {fx.frame_state_key("sabit", t / 30, 1.0, 30) for t in range(300)} == {("sabit",)}


def test_frame_overlay_has_ring_and_background_corners():
    overlay = template.frame_overlay(assets.backgrounds()[0])
    ox, oy = template.frame_origin()
    assert all(v >= 240 for v in overlay.getpixel((62 - ox, 1000 - oy))[:3])
    assert overlay.getpixel((540 - ox, 1000 - oy))[3] == 0
    assert overlay.getpixel((61 - ox, 454 - oy))[3] == 255  # yuvarlak köşenin dışı arka plan


# ---------------------------------------------------------------- blur / mozaik

def _blur(**changes):
    blur = {"id": "b1", "effect": "blur", "shape": "elips", "strength": 5, "opacity": 0.8, "feather": 0.0, "start": 1.0, "end": 4.0,
            "keys": [{"t": 1.0, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1, "r": 0}, {"t": 3.0, "x": 0.5, "y": 0.3, "w": 0.4, "h": 0.2, "r": 90}]}
    blur.update(changes)
    return blur


def test_clean_blurs_validates_browser_data():
    cleaned = clean_blurs([_blur(strength=99, opacity=5, shape="kalp", effect="lazer", feather=7), _blur(start=5, end=2), _blur(keys=[]), "bozuk"], 20.0)
    assert len(cleaned) == 1
    b = cleaned[0]
    assert (b["strength"], b["opacity"], b["shape"], b["effect"], b["feather"]) == (10, 1.0, "yuvarlak", "blur", 1.0)
    assert clean_blurs(None, 20.0) == []


def test_blur_box_moves_and_rotates_between_keys():
    blur = clean_blurs([_blur()], 20.0)[0]
    assert box_at(blur, 0.0) == (0.1, 0.1, 0.2, 0.1, 0)
    assert box_at(blur, 2.0) == pytest.approx((0.3, 0.2, 0.3, 0.15, 45))
    assert mask_state(blur, 0.5, 960, 1226) is None


def test_mask_rotation_feather_and_opacity():
    blur = clean_blurs([_blur(shape="dikdortgen", keys=[{"t": 0, "x": 0.3, "y": 0.4, "w": 0.4, "h": 0.05, "r": 90}])], 20.0)[0]
    blur["start"] = 0.0
    state = mask_state(blur, 1.0, 960, 1226)
    mask = render_mask(blur, state, 960, 1226)
    left, top, right, bottom = mask.getbbox()
    assert bottom - top > right - left  # 90° döndü: yatay kutu dikey oldu
    assert mask.getpixel((480, 613)) == pytest.approx(round(255 * 0.8), abs=3)
    soft = clean_blurs([dict(blur, feather=1.0)], 20.0)[0]
    soft_mask = render_mask(soft, mask_state(soft, 1.0, 960, 1226), 960, 1226)
    edge = (480 + 20, 613)  # kenara yakın: yumuşak kenarda daha saydam
    assert soft_mask.getpixel(edge) < mask.getpixel(edge) or soft_mask.getpixel((480, 613 + 150)) < mask.getpixel((480, 613 + 150))


# ---------------------------------------------------------------- sahne ve katmanlar

def test_scene_timeline_follows_template():
    design = load_design(None, "Mansur Yavaş CHP'den istifa etti", "Yola devam kararı verdi", 20.0)
    scene = template.build_scene(design, 20.0)
    names = lambda t: [n for n, _ in scene.items(t, 0)]  # noqa: E731
    assert names(1.0) == ["h1"]
    assert names(10.2) == ["s0"]
    assert names(12.0) == ["s1"]
    assert names(16.5) == ["h2", "logo"]
    assert names(19.0) == ["h2"]
    design.slogans.enabled = False
    design.logo.enabled = False
    scene = template.build_scene(design, 20.0)
    assert [n for n, _ in scene.items(10.2, 0)] == [] and [n for n, _ in scene.items(16.5, 0)] == ["h2"]


def test_text_layers_are_drawn_where_the_editor_put_them():
    design = load_design({"version": 2, "texts": [{"id": "t1", "text": "Ankara", "x": 0.5, "y": 0.9, "start": 1, "end": 5, "enter": "yok", "exit": "yok"}]}, "A", "B", 20.0)
    scene = template.build_scene(design, 20.0)
    assert [n for n, _ in scene.items(2.0, 0)] == ["h1", "t:t1"]
    image = scene.render(2.0, 60)
    left, top, right, bottom = image.crop((0, 1600, 1080, 1920)).getbbox()
    assert 1600 + top < 0.9 * 1920 < 1600 + bottom


@pytest.mark.parametrize("effect", ["merge", "slide", "typewriter", "pop", "fade"])
def test_first_frame_is_the_cover_with_the_full_headline(effect, tmp_path):
    """v4.0.0-alpha.3: Reels/Shorts kapak seçiminde ilk kare hazır: 1. başlık giriş animasyonunun son hâliyle."""
    design = load_design({"version": 2, "headline_1": {"enter": effect}}, "Mansur Yavaş CHP'den istifa etti", "B", 20.0)
    scene = template.build_scene(design, 20.0)
    full = fx.enter_seconds(effect, scene.headline_1.lines)
    cover, second = dict(scene.items(0.0, 0)), dict(scene.items(1 / 30, 1))
    assert fx.state_key(cover["h1"]) == fx.state_key(dict(scene.items(full + 0.5, 90))["h1"])
    assert fx.state_key(second.get("h1")) != fx.state_key(cover["h1"])  # animasyon ikinci kareden başlar
    box = (60, 260, 1020, 420)
    assert scene.render(0.0, 0).crop(box).getbbox() == scene.render(full + 0.5, 90).crop(box).getbbox()
    layers = template.write_layers(tmp_path, design, assets.backgrounds()[0], 30, 20.0)
    lines = layers.graphics.read_text().splitlines()
    assert lines[2] == f"duration {1 / 30:.6f}"  # kapak tek kare
    first, second_file = (tmp_path / lines[1][6:-1]), (tmp_path / lines[3][6:-1])
    assert first.read_bytes() != second_file.read_bytes()


def _concat_seconds(path: Path) -> float:
    return sum(float(v) for v in re.findall(r"^duration ([\d.]+)$", path.read_text(), re.M))


def test_layers_write_only_distinct_frames(tmp_path):
    design = load_design({"version": 2, "frame": {"style": "kovalayan"}}, "Mansur Yavaş CHP'den istifa etti", "Yola devam", 20.0)
    layers = template.write_layers(tmp_path, design, assets.backgrounds()[0], 30, 20.0)
    assert _concat_seconds(layers.graphics) == pytest.approx(20.0, abs=0.01)
    assert _concat_seconds(layers.frame) == pytest.approx(20.0, abs=0.01)
    assert len(list(tmp_path.glob("cerceve_*.png"))) == round(3.5 * 30)   # bir periyot, döngüyle tekrar
    assert len(list(tmp_path.glob("grafik_*.png"))) < 250                # 600 kareden çok daha az
    assert layers.graphics.read_text().strip().splitlines()[-1].startswith("file ")


def test_final_command_applies_blur_and_mosaic_before_template(tmp_path):
    layers = template.Layers(*(tmp_path / n for n in ["zemin.png", "cerceve.ffconcat", "grafik.ffconcat"]))
    blurs = clean_blurs([_blur(), _blur(id="m", effect="mozaik", strength=4)], 20.0)
    passes = [BlurPass(blurs[0], tmp_path / "blur0.ffconcat", (40, 60, 300, 200)),
              BlurPass(blurs[1], tmp_path / "blur1.ffconcat", (44, 66, 330, 220))]
    command = build_final_command(tmp_path / "kaba.mp4", layers, 30, 20.0, tmp_path / "son.mp4", ["-c:v", "libx264"], passes)
    graph = command[command.index("-filter_complex") + 1]
    assert "gblur=sigma=20.0" in graph and "flags=neighbor" in graph and graph.count("alphamerge") == 2
    assert graph.index("alphamerge") < graph.index("[base][slot]overlay")
    assert "crop=300:200:40:60" in graph and "overlay=40:60:enable='between(t,1.000,4.000)'" in graph  # yalnız kutunun bölgesi
    assert "scale=15:10:flags=area" in graph                                                         # 22 px mozaik kareleri
    assert command.count("concat") == 4
    assert "-loop" not in command and "loop=loop=599:size=1" in graph  # zemin bir kez okunur


def test_blur_region_covers_moving_rotated_box_with_margin():
    blur = clean_blurs([_blur(feather=0.5)], 20.0)[0]
    region = blur_region(blur, 30, 600, 960, 1226)
    x, y, w, h = region
    assert x % 2 == y % 2 == w % 2 == h % 2 == 0
    margin = 3 * 20
    # ilk kutu (96,123) ve son kutu (döndürülmüş 384x245, merkez 672,490) bölgede, bulanıklık payıyla
    assert x <= 96 - margin + 2 and y <= max(0, 123 - margin) + 2
    assert x + w >= min(960, 672 + 245 / 2 + margin - 2) and y + h >= 490 + 384 / 2 + margin - 2
    assert w < 960 or h < 1226  # tüm kare değil
    mosaic = clean_blurs([_blur(effect="mozaik", strength=4)], 20.0)[0]
    mx, my, _, _ = blur_region(mosaic, 30, 600, 960, 1226)
    assert mx % 22 == 0 and my % 22 == 0  # mozaik kareleri video alanının ızgarasında
    assert blur_region(clean_blurs([_blur(start=19.99, end=20.0)], 20.0)[0], 30, 599, 960, 1226) is None


def test_mask_sequences_are_cropped_to_region(tmp_path):
    from PIL import Image

    blur = clean_blurs([_blur(end=2.0)], 20.0)[0]
    passes = write_mask_sequences(tmp_path, [blur, clean_blurs([_blur(id="x", start=19.99, end=20.0)], 20.0)[0]], 30, 599, 960, 1226)
    assert len(passes) == 1  # hiç görünmeyen blur atlanır
    x, y, w, h = passes[0].region
    first = Image.open(next(tmp_path.glob("blur0_*.png")))
    assert first.size == (w, h)
    full = render_mask(blur, mask_state(blur, 1.0, 960, 1226), 960, 1226)
    cropped = render_mask(blur, mask_state(blur, 1.0, 960, 1226), w, h, (x, y))
    assert full.crop((x, y, x + w, y + h)).tobytes() == cropped.tobytes()


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
    design = load_design({"version": 2, "frame": {"style": "nefes"},
                          "blurs": [_blur(start=0.0, end=3.0), _blur(id="m", effect="mozaik", start=0.0, end=3.0)]}, "Başlık bir", "İki", 3.0)
    render_final(rough, design, assets.backgrounds()[1], 30, 3.0, output)
    info = subprocess.run(["ffmpeg", "-i", str(output)], capture_output=True, text=True).stderr
    assert "1080x1920" in info and "Audio" in info
    assert not list(tmp_path.glob("*.yaziliyor.mp4"))


def test_upload_to_github_creates_or_updates_file(monkeypatch):
    import io
    import json as _json
    import urllib.error

    requests = []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=0):
        requests.append((request.get_method(), request.full_url, request.data))
        if request.get_method() == "GET":
            raise urllib.error.HTTPError(request.full_url, 404, "yok", {}, None)
        return Response(_json.dumps({"commit": {"html_url": "https://github.com/x/y/commit/1"}}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    url = assets.upload_to_github("assets/sablon/fontlar/Yeni.ttf", b"font", "tok", repo="sahip/repo")
    assert url.endswith("/commit/1")
    method, address, body = requests[-1]
    assert method == "PUT" and address == "https://api.github.com/repos/sahip/repo/contents/assets/sablon/fontlar/Yeni.ttf"
    payload = _json.loads(body)
    assert payload["branch"] == "main" and "sha" not in payload


def test_editor_patch_changes_design_but_not_headline_texts():
    from apps.design_studio.design import apply_editor_patch

    design = load_design(None, "KAZA", "B", 20.0)
    patch = {
        "headline_1": {"text": "BAŞKA", "enter": "fade", "exit": "slide"},
        "headline_style": {"family": "Google Sans", "style": "Bold", "size": 64, "color": "#D0E491", "glow": 0.2, "upper": True},
        "frame": {"style": "kovalayan", "color": "#FFFFFF", "accent": "#BEE1E8", "speed": 1.5},
        "background": "arka_plan_2.png",
        "texts": [{"id": "t1", "text": "Ankara", "start": 3, "end": 99, "x": 0.5, "y": 0.9}],
        "blurs": [_blur(effect="mozaik")],
        "slogans": {"enabled": False, "effect": "fade"},
    }
    updated = apply_editor_patch(design, patch, 20.0)
    assert updated.headline_1.text == "KAZA"  # metin kenar çubuğundan gelir
    assert (updated.headline_1.enter, updated.headline_1.exit) == ("fade", "slide")
    assert updated.headline_style.size == 64 and updated.frame.style == "kovalayan"
    assert updated.background == "arka_plan_2.png" and updated.slogans.enabled is False
    assert updated.texts[0].end == 20.0 and updated.blurs[0]["effect"] == "mozaik"
    assert apply_editor_patch(design, "bozuk", 20.0) is design


def test_strike_toggle_by_word_index_keeps_lines():
    from shared.text_layout import toggle_strike

    assert toggle_strike("Bir iki\nüç", 1) == "Bir ~~iki~~\nüç"
    assert toggle_strike("Bir ~~iki~~\nüç", 1) == "Bir iki\nüç"
    assert toggle_strike("Bir iki", 9) == "Bir iki"


def _probe_result(width=1080, height=1920, duration="20.02", audio=True):
    streams = [{"codec_type": "video", "width": width, "height": height}] + ([{"codec_type": "audio"}] if audio else [])
    return {"streams": streams, "format": {"duration": duration}}


def test_check_final_catches_broken_output(tmp_path, monkeypatch):
    from apps.design_studio import render

    rough, output = tmp_path / "kaba.mp4", tmp_path / "son.mp4"
    results = {}
    monkeypatch.setattr(render, "_probe", lambda path: results.get(path.name))
    results.update({"kaba.mp4": _probe_result(960, 1226), "son.mp4": _probe_result()})
    assert render.check_final(output, 20.0, rough) is None
    results["son.mp4"] = _probe_result(audio=False)
    assert "ses yok" in render.check_final(output, 20.0, rough)
    results["son.mp4"] = _probe_result(width=720, height=1280)
    assert "1080x1920" in render.check_final(output, 20.0, rough)
    results["son.mp4"] = _probe_result(duration="12.5")
    assert "12.5 sn" in render.check_final(output, 20.0, rough)
    results["son.mp4"] = {"error": "moov atom not found"}
    assert "açılamıyor" in render.check_final(output, 20.0, rough)
    results["kaba.mp4"] = _probe_result(960, 1226, audio=False)
    results["son.mp4"] = _probe_result(audio=False)
    assert render.check_final(output, 20.0, rough) is None  # kurguda ses yoksa ses aranmaz
    results.clear()
    assert render.check_final(output, 20.0, rough) is None  # FFprobe yoksa kontrol atlanır


def test_render_final_falls_back_to_x264_when_amf_output_is_broken(tmp_path, monkeypatch):
    from apps.design_studio import render

    rough = tmp_path / "kaba_kurgu.mp4"
    rough.write_bytes(b"x")
    calls = []

    def fake_run(command, timeout, label):
        calls.append(command[command.index("-c:v") + 1])
        Path(command[-1]).write_bytes(b"video")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(render, "amd_encoder_available", lambda: True)
    monkeypatch.setattr(render, "run_ffmpeg", fake_run)
    monkeypatch.setattr(render, "write_layers", lambda folder, *a: template.Layers(folder / "z.png", folder / "c", folder / "g"))
    monkeypatch.setattr(render, "check_final", lambda path, seconds, source: "Videoda ses yok (kurguda var)." if calls[-1] == "h264_amf" else None)
    output = tmp_path / "son_video.mp4"
    name = render.render_final(rough, load_design({}, "Başlık", "İkinci", 3.0), assets.backgrounds()[0], 30, 3.0, output)
    assert calls == ["h264_amf", "libx264"] and name.startswith("x264") and output.exists()
    assert not (tmp_path / "son_video.yaziliyor.mp4").exists()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_cancel_stops_running_ffmpeg_quickly():
    import threading
    import time

    from apps.design_studio.render import Cancelled, _run_cancellable

    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    started = time.monotonic()
    with pytest.raises(Cancelled):
        _run_cancellable(["ffmpeg", "-v", "error", "-re", "-f", "lavfi", "-i", "testsrc=duration=60", "-f", "null", "-"], 120, "Test", cancel)
    assert time.monotonic() - started < 5


def _synthetic_rough(path: Path, seconds: float) -> Path:
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=960x1226:rate=30:duration={seconds}",
        "-f", "lavfi", "-i", f"sine=duration={seconds}", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
        "-shortest", str(path),
    ], check=True)
    return path


def _frame_count(video: Path) -> int:
    log = subprocess.run(["ffmpeg", "-i", str(video), "-map", "0:v", "-f", "null", "-"], capture_output=True, text=True).stderr
    return int(re.findall(r"frame=\s*(\d+)", log)[-1])


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
@pytest.mark.parametrize("rough_seconds", [2.0, 4.0])
def test_final_video_has_exact_frames_when_rough_cut_is_shorter_or_longer(tmp_path, rough_seconds):
    rough = _synthetic_rough(tmp_path / "kaba_kurgu.mp4", rough_seconds)
    output = tmp_path / "son_video.mp4"
    render_final(rough, load_design({"version": 2}, "Başlık", "İki", 3.0), assets.backgrounds()[0], 30, 3.0, output)
    assert _frame_count(output) == 90  # zemin döngüsü tam 3 sn; kısa kurguda son kare sürer, uzunda kesilir
    info = subprocess.run(["ffmpeg", "-i", str(output)], capture_output=True, text=True).stderr
    assert "Duration: 00:00:03.0" in info and "Audio" in info


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_cropped_blur_matches_full_frame_blur_at_edges_and_rotation(tmp_path):
    """Kırpılmış bölgede işlenen blur, tüm karede işlenenle aynı görünmeli (kenara taşan, dönen, yumuşak kenarlı)."""
    from apps.design_studio.blur import render_mask as full_mask
    from apps.design_studio.render import build_final_command
    from apps.video_studio.modules.render import X264

    seconds, fps, width, height = 2.0, 30, 960, 1226
    rough = _synthetic_rough(tmp_path / "kaba.mp4", seconds)
    edge = {"t": 0.0, "x": 0.8, "y": 0.85, "w": 0.35, "h": 0.2, "r": 0}
    blurs = clean_blurs([
        _blur(id="kenar", start=0.0, end=2.0, feather=1.0, strength=8, opacity=1.0, shape="dikdortgen",
              keys=[edge, {**edge, "t": 2.0, "x": 0.75, "r": 90}]),
        _blur(id="sol", start=0.5, end=1.5, feather=0.6, shape="elips",
              keys=[{"t": 0.5, "x": -0.1, "y": 0.02, "w": 0.3, "h": 0.25, "r": 45}]),
    ], seconds)
    design = load_design({"version": 2, "blurs": blurs}, "Başlık", "İki", seconds)
    layers = template.write_layers(tmp_path / "katman", design, assets.backgrounds()[0], fps, seconds)
    total = round(seconds * fps)
    (tmp_path / "kirpik").mkdir()
    cropped = write_mask_sequences(tmp_path / "kirpik", blurs, fps, total, width, height)
    assert all(p.region[2] < width or p.region[3] < height for p in cropped)
    (tmp_path / "tam").mkdir()
    full = [BlurPass(b, template.write_sequence(tmp_path / "tam", f"tam{i}", fps, total,
                                                lambda t, f, b=b: mask_state(b, t, width, height),
                                                lambda state, b=b: full_mask(b, state, width, height)), (0, 0, width, height))
            for i, b in enumerate(blurs)]
    outputs = []
    for name, passes in (("kirpik", cropped), ("tam", full)):
        out = tmp_path / f"{name}.mp4"
        command = build_final_command(rough, layers, fps, seconds, out, X264, passes)
        subprocess.run(command, check=True)
        outputs.append(out)
    log = subprocess.run(["ffmpeg", "-i", str(outputs[0]), "-i", str(outputs[1]), "-lavfi", "[0:v][1:v]psnr", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    worst = float(re.search(r"min:([\d.]+|inf)", log).group(1))
    assert worst > 40, log[-400:]


def test_skipped_final_check_is_logged(tmp_path, monkeypatch, caplog):
    from apps.design_studio import render

    def missing(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    monkeypatch.setattr(render, "run_ffmpeg", missing)
    with caplog.at_level("WARNING"):
        assert render.check_final(tmp_path / "son.mp4", 20.0, tmp_path / "kaba.mp4") is None
    assert "Son video kontrolü atlandı" in caplog.text


def test_design_follows_news_headlines_but_keeps_own_edits():
    design = load_design({}, "KAZA", "YARALI VAR", 20.0)
    design.headline_1.text = "KAZA\\n~~YERİ~~"  # Tasarım Stüdyosu'nda satır kırıldı, sansürlendi
    stored = dump_design(design)
    assert load_design(stored, "KAZA", "YARALI VAR", 20.0).headline_1.text == "KAZA\\n~~YERİ~~"  # haber aynı: korunur
    changed = load_design(stored, "YENİ BAŞLIK", "İKİNCİ", 20.0)  # Haber Stüdyosu'nda değişti
    assert (changed.headline_1.text, changed.headline_2.text) == ("YENİ BAŞLIK", "İKİNCİ")
    assert changed.news_headlines == ["YENİ BAŞLIK", "İKİNCİ"]
    legacy = {k: v for k, v in stored.items() if k != "news_headlines"}  # v2.9 ve öncesi belge
    assert load_design(legacy, "BAŞKA", "X", 20.0).headline_1.text == "KAZA\\n~~YERİ~~"
    from apps.design_studio.design import signature_payload

    assert "news_headlines" not in signature_payload(changed)
