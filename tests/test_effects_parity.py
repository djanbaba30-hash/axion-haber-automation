"""Canlı önizleme (editor.js) ile son video (effects.py) aynı animasyonu mu hesaplıyor?

editor.js'in efekt bölümü (@efektler-başı … @efektler-sonu) Node'da çalıştırılır ve her efekt, satır düzeni ve an için
Python sonucuyla karşılaştırılır. Bir taraftaki formül değişip öteki unutulursa bu test kırılır. Node yoksa atlanır.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.design_studio import effects as fx
from apps.design_studio import template
from shared.axion_template import LOGO_BOX, LOGO_DROP_START, LOGO_GLINT, LOGO_RISE_START, LOGO_RISE_TAU

EDITOR_JS = Path(fx.__file__).with_name("editor.js")
LINES = [[0], [0, 0], [0, 0, 0, 1, 1], [0, 0, 0, 0, 1, 1, 1, 2]]
TIMES = [round(i * 0.01, 2) for i in range(0, 301)]
FRAMES = [i * 3 // 10 for i in range(0, 301)]  # t * 30, tam sayı (iki tarafta aynı kare numarası)
HARNESS = """
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = {
  text: cases.text.map(([enter, exit, lines]) => cases.times.map((t) => textState(enter, exit, lines, 0, 3, t))),
  slogan: cases.slogan.map((e) => cases.times.map((t, i) => sloganState(e, 0.2, 2.6, t, cases.frames[i]))),
  logo: cases.logo.map((e) => cases.logo_times.map((t) => logoState(cases.L, e, t))),
};
process.stdout.write(JSON.stringify(out));
"""


def _effects_source() -> str:
    source = EDITOR_JS.read_text(encoding="utf-8")
    source = source[:source.index("// @efektler-sonu")]
    assert "/*FX*/null" in source
    return source.replace("/*FX*/null", json.dumps(fx.FX), 1)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js kurulu değil")
def test_editor_js_effects_match_python(tmp_path):
    script = tmp_path / "efektler.cjs"
    script.write_text(_effects_source() + HARNESS, encoding="utf-8")
    text_cases = [[e, x, lines] for e in fx.TEXT_ENTER for x in fx.TEXT_EXIT for lines in LINES]
    logo_start, logo_end = LOGO_RISE_START, template.LOGO_END
    logo_times = [round(logo_start - 0.1 + i * 0.01, 2) for i in range(int((logo_end - logo_start + 0.2) / 0.01))]
    L = {"start": logo_start, "end": logo_end, "rest_y": LOGO_BOX["rest_y"], "tau": LOGO_RISE_TAU,
         "drop_start": LOGO_DROP_START, "glint": list(LOGO_GLINT)}
    cases = {"times": TIMES, "frames": FRAMES, "text": text_cases, "slogan": list(fx.SLOGAN_EFFECTS), "logo": list(fx.LOGO_EFFECTS),
             "logo_times": logo_times, "L": L}
    result = subprocess.run(["node", str(script)], input=json.dumps(cases), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    js = json.loads(result.stdout)

    for (enter, exit_, lines), series in zip(text_cases, js["text"]):
        for t, got in zip(TIMES, series):
            want = fx.text_state(enter, exit_, lines, 0, 3, t)
            where = f"yazı {enter}/{exit_} {lines} t={t}"
            assert (got is None) == (want is None), where
            if want is None:
                continue
            assert _close(got["scale"], want.scale), where
            for w_js, w_py in zip(got["words"], want.words, strict=True):
                assert _close(w_js["a"], w_py.alpha) and _close(w_js["dx"], w_py.dx) and _close(w_js["dy"], w_py.dy), where

    for effect, series in zip(cases["slogan"], js["slogan"]):
        for t, frame, got in zip(TIMES, FRAMES, series):
            want = fx.slogan_state(effect, 0.2, 2.6, t, frame)
            where = f"slogan {effect} t={t}"
            assert (got is None) == (want is None), where
            if want is None:
                continue
            assert _close(got["a"], want.alpha) and _close(got["sx"], want.sx) and _close(got["sy"], want.sy), where
            assert got["split"] == want.split and bool(got.get("flicker")) == want.flicker, where

    for effect, series in zip(cases["logo"], js["logo"]):
        for t, got in zip(logo_times, series):
            want = fx.logo_state(effect, logo_start, logo_end, LOGO_BOX["rest_y"], LOGO_BOX["height"], t,
                                 LOGO_RISE_TAU, LOGO_DROP_START, LOGO_GLINT)
            where = f"logo {effect} t={t}"
            assert (got is None) == (want is None), where
            if want is None:
                continue
            assert _close(got["a"], want.alpha) and _close(got["sx"], want.sx) and _close(got["dy"], want.dy), where
            assert (got["glint"] is None) == (want.glint is None), where
            if want.glint is not None:
                assert _close(got["glint"], want.glint), where


def test_editor_gets_effect_parameters_from_json():
    from apps.design_studio.editor import JS

    assert "/*FX*/null" not in JS and json.dumps(fx.FX, ensure_ascii=False) in JS
