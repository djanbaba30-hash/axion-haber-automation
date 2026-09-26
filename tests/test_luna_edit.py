"""Faz 4 (v3.6): sahneleri Luna seçer; kesme zamanı, kadraj ve tekrar önleme kurallarla kalır."""

import json
from types import SimpleNamespace

import pytest

from apps.video_studio.modules import luna_edit
from apps.video_studio.modules.soundbites import Soundbite
from shared.edit_models import ClipOrigin
from test_rough_cut import edit_project, library, video_clips

REAL_REQUEST = luna_edit.request


class FakeLuna:
    """responses.parse taklidi: verilen sahneleri, Luna'nın şemasıyla (pencere enum'u) doğrulayarak döndürür."""

    def __init__(self, scenes):
        self.scenes, self.calls = scenes, []
        self.responses = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        parsed = kwargs["text_format"](sahneler=self.scenes)
        usage = SimpleNamespace(input_tokens=1200, output_tokens=300, output_tokens_details=SimpleNamespace(reasoning_tokens=200))
        return SimpleNamespace(output_parsed=parsed, usage=usage)


@pytest.fixture
def luna(monkeypatch):
    monkeypatch.setattr(luna_edit, "request", REAL_REQUEST)  # conftest'in "Luna yok"u yerine sahte istemci


def run(tmp_path, scenes, **kwargs):
    fake = FakeLuna(scenes)
    result, info = luna_edit.plan(edit_project(), library(), kwargs.pop("soundbites", None), "sk-test", tmp_path,
                                  client=fake, **kwargs)
    return result, info, fake


def test_prompt_lists_voiceover_scenes_and_windows_compactly():
    prep = luna_edit.prepare(edit_project(), library())
    prompt = luna_edit.build_prompt(prep)
    assert "1 (kapak) |" in prompt and "kaldırımdaki 4 kişiye" in prompt
    assert "P4 | video 1 çekim 4 | 22.7–30.4 sn | Dükkân vitrinine çarpmış" in prompt
    # Uzun röportajın aynı görünen 7 penceresi tek satır (token tasarrufu); Luna yine her id'yi seçebilir.
    assert "P15–P21 (7 ardışık pencere" in prompt and "\nP16 |" not in prompt
    assert len(luna_edit.window_ids(prep)) == 21
    assert luna_edit.SYSTEM_PROMPT.count("Olay örgüsü") == 1 and "Tekrar yok" in luna_edit.SYSTEM_PROMPT


def test_luna_picks_scenes_and_the_plan_is_reused(tmp_path, luna):
    scenes = [{"parca": 1, "pencere": "P4", "kaynak_bas": 23.0}, {"parca": 2, "pencere": "P13", "kaynak_bas": 72.0},
              {"parca": 3, "pencere": "P3", "kaynak_bas": 15.5}, {"parca": 4, "pencere": "P5", "kaynak_bas": 31.0},
              {"parca": 5, "pencere": "P9", "kaynak_bas": 55.0}, {"parca": 6, "pencere": "P6", "kaynak_bas": 37.0},
              {"parca": 7, "pencere": "P7", "kaynak_bas": 42.5}]
    result, info, fake = run(tmp_path, scenes)
    clips = video_clips(result)
    assert info["kaynak"] == "luna" and info["secilen"] == 7 and not info["not"]
    assert fake.calls[0]["reasoning"] == {"effort": "low"} and fake.calls[0]["model"] == "gpt-5.6-luna"
    assert [round(c["source_in_s"], 1) for c in clips[:3]] == [23.0, 72.0, 15.5]  # Luna'nın seçtiği anlar
    assert all(c["origin"] == ClipOrigin.LLM.value for c in clips if c["source_in_s"] in {23.0, 72.0, 15.5})
    saved = json.loads((tmp_path / luna_edit.PLAN_FILENAME).read_text(encoding="utf-8"))
    assert saved["sahneler"] == scenes and saved["kullanim"]["input_tokens"] == 1200

    # Girdiler aynı: "Videoyu yeniden oluştur" yeni çağrı yapmaz, aynı kurgu çıkar.
    again, info, fake = run(tmp_path, scenes)
    assert info["kaynak"] == "kayitli" and not fake.calls
    assert video_clips(again) == clips


def test_replan_sends_previous_cut_as_disliked(tmp_path, luna):
    first = [{"parca": 1, "pencere": "P4", "kaynak_bas": 23.0}]
    run(tmp_path, first)
    _, info, fake = run(tmp_path, [{"parca": 1, "pencere": "P2", "kaynak_bas": 9.0}], replan=True)
    prompt = fake.calls[0]["input"][1]["content"]
    assert info["kaynak"] == "luna" and "<onceki_kurgu>" in prompt and "1: P4 @ 23.0" in prompt and "beğenmedi" in prompt
    # Luna yalnız 1. sahneyi seçti: gerisi kurallarla (video yine tam).
    assert "kurallarla" in info["not"]


def test_same_moment_is_not_used_twice_even_if_luna_asks(tmp_path, luna):
    scenes = [{"parca": 1, "pencere": "P4", "kaynak_bas": 23.0}, {"parca": 2, "pencere": "P4", "kaynak_bas": 23.0}]
    result, _, _ = run(tmp_path, scenes)
    first, second = video_clips(result)[:2]
    assert first["shot_id"] == second["shot_id"] and second["source_in_s"] >= first["source_out_s"] - 1e-6


def test_soundbite_range_is_marked_and_invalid_rows_are_skipped(tmp_path, luna):
    bite = Soundbite(path="C:/dha.mp4", filename="dha.mp4", start_s=90.0, end_s=95.0, placement="after")
    prep = luna_edit.prepare(edit_project(), library(), [bite])
    assert "KESİT" in luna_edit.build_prompt(prep)
    picks = luna_edit.to_picks([{"parca": 0, "pencere": "P1", "kaynak_bas": 1.0},    # sahne no yok
                                {"parca": 1, "pencere": "P1", "kaynak_bas": 50.0},   # pencere dışı an → yok sayılır
                                {"parca": 1, "pencere": "P2", "kaynak_bas": 9.0},    # aynı sahne ikinci kez
                                {"parca": 99, "pencere": "P2", "kaynak_bas": 9.0}], prep)
    assert picks == {0: (0, None)}


def test_without_key_or_when_luna_fails_rules_choose(tmp_path, monkeypatch):
    result, info = luna_edit.plan(edit_project(), library(), None, "", tmp_path)
    assert info["kaynak"] == "kural" and "OPENAI_API_KEY" in info["not"]
    assert all(c["origin"] == ClipOrigin.RULE.value for c in video_clips(result))
    result, info = luna_edit.plan(edit_project(), library(), None, "sk-test", tmp_path)  # conftest: Luna yok
    assert info["kaynak"] == "kural" and "ulaşılamadı" in info["not"] and video_clips(result)
    assert not (tmp_path / luna_edit.PLAN_FILENAME).exists()
