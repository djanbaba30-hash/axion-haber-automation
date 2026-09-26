import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from apps.axion_local import store
from shared.news_package import NewsPackage

ROOT = Path(__file__).resolve().parents[1]
NEWS_PAGE = "apps/news_studio/page.py"
VIDEO_PAGE = "apps/video_studio/page.py"
DESIGN_PAGE = "apps/design_studio/page.py"
KEYS = {
    "OPENAI_API_KEY": "sk-test",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "ELEVENLABS_API_KEY": "el-test",
}
TTS = "Bayrampaşa'da savrulan otomobil berber dükkânına çarptı."


def start(password=""):
    at = AppTest.from_file(str(ROOT / "axion_local.py"), default_timeout=120)
    for key, value in {**KEYS, "APP_PASSWORD": password}.items():
        at.secrets[key] = value
    at.run()
    return at


def with_generated_news(at, tts=TTS, audio_text=TTS):
    at.session_state["raw_text"] = "Ham haber"
    at.session_state["baslik1"] = "SAVRULAN OTOMOBİL BERBER DÜKKÂNINA ÇARPTI"
    at.session_state["baslik2"] = "5 KİŞİ YARALANDI"
    at.session_state["icerik"] = TTS
    at.session_state["tts_metni"] = tts
    at.session_state["last_audio_bytes"] = b"mp3"
    at.session_state["last_audio_text"] = audio_text
    return at.run()


def button(at, label):
    return next(b for b in at.button if b.label == label)


def title(at):
    return [t.value for t in at.title]


def test_no_password_opens_directly(local_env):
    at = start()
    assert not at.exception
    assert title(at) == ["Haber Stüdyosu"]
    at.switch_page(VIDEO_PAGE).run()
    assert not at.exception
    assert title(at) == ["Video Stüdyosu"]


def test_optional_password_still_protects(local_env):
    at = start("Gizli-Şifre1")
    assert [t.label for t in at.text_input] == ["Şifre"]
    at.text_input[0].input("yanlis").run()
    assert [e.value for e in at.error] == ["Şifre yanlış."]
    at.text_input[0].input("Gizli-Şifre1").run()
    assert not at.exception
    assert title(at) == ["Haber Stüdyosu"]


def test_shutdown_button_hidden_for_remote_access(local_env):
    at = start()
    assert not any(b.label == "Axion'u kapat" for b in at.button)


@pytest.mark.parametrize("rendering", [False, True])
def test_shutdown_confirmation_warns_while_rendering(local_env, monkeypatch, rendering):
    from streamlit.runtime.context import ContextProxy

    monkeypatch.setattr(ContextProxy, "headers", property(lambda self: {"Host": "localhost:8501"}))
    monkeypatch.setattr("apps.video_studio.jobs.busy", lambda project=None: rendering)
    at = start()
    button(at, "Axion'u kapat").click().run()
    assert not at.exception
    assert any("kapatılsın mı" in w.value for w in at.warning)
    assert any("yarıda kalır" in e.value for e in at.error) == rendering


def test_save_and_continue_opens_project_in_video_studio(local_env):
    at = with_generated_news(start())
    button(at, "Kaydet ve Video Stüdyosu'na geç").click().run()
    assert not at.exception
    assert title(at) == ["Video Stüdyosu"]
    projects = store.list_news_projects()
    assert len(projects) == 1
    assert at.session_state["loaded_news_project"] == projects[0].id
    assert at.session_state["project_news_text"] == TTS
    assert "dha_kaza.mp4" in at.multiselect[0].options[0]


def test_saving_same_news_again_updates_project(local_env):
    at = with_generated_news(start())
    at.session_state["last_usage"] = {"input_tokens": 2000, "output_tokens": 500, "requests": 2, "model": "gpt-5.6-luna"}
    button(at, "Sadece kaydet").click().run()
    button(at, "Sadece kaydet").click().run()
    assert len(store.list_news_projects()) == 1
    # v3.6.2: haber metninin maliyeti pakete yazılır (Video Stüdyosu haberin toplamını gösterir).
    usage = store.load_news_project(store.list_news_projects()[0])[0].metadata["usage"]
    assert usage["estimated_cost_usd"] == pytest.approx(2000 * 0.20e-6 + 500 * 1.20e-6)


def test_audio_alignment_is_kept_as_plain_data_and_saved(local_env):
    """Windows hatası: ses zamanları oturumda nesne olarak durunca, modül yeniden yüklenince NewsPackage reddediyordu."""
    import json

    at = start()
    at.session_state["last_audio_alignment"] = {"characters": list(TTS), "start_seconds": [i / 10 for i in range(len(TTS))],
                                                "end_seconds": [(i + 1) / 10 for i in range(len(TTS))]}
    at = with_generated_news(at)
    button(at, "Sadece kaydet").click().run()
    assert not at.exception
    saved = json.loads((store.list_news_projects()[0].folder / "news_package.json").read_text(encoding="utf-8"))
    assert saved["tts_alignment"]["characters"] == list(TTS)


def test_headline_regeneration_cost_is_counted(local_env, monkeypatch):
    from types import SimpleNamespace

    usage = {"input_tokens": 50, "output_tokens": 10, "requests": 1, "provider": "OpenAI", "model": "gpt-5.6-luna"}
    calls = []

    def regenerate(*args, previous=()):
        calls.append(list(previous))
        return SimpleNamespace(baslik1=f"YENİ {len(calls)}", baslik2="İKİNCİ"), usage

    monkeypatch.setattr("apps.news_studio.ai.clients.regenerate_headlines", regenerate)
    at = with_generated_news(start())
    at.session_state["last_usage"] = {"input_tokens": 1000, "output_tokens": 300, "requests": 1}
    at.run()
    button(at, "↻ Başlıkları yeniden üret").click().run()
    assert not at.exception
    assert (at.session_state["baslik1"], at.session_state["baslik2"]) == ("YENİ 1", "İKİNCİ")
    total = at.session_state["last_usage"]
    assert (total["input_tokens"], total["output_tokens"], total["requests"]) == (1050, 310, 2)
    # Editör (v3.5): yeniden üretince başlık hep aynı geliyordu. Gösterilen başlıklar modele verilir (farklı açı).
    first = ("SAVRULAN OTOMOBİL BERBER DÜKKÂNINA ÇARPTI", "5 KİŞİ YARALANDI")
    button(at, "↻ Başlıkları yeniden üret").click().run()
    assert calls == [[first], [first, ("YENİ 1", "İKİNCİ")]]
    # v4.0 maliyet defteri: her yenileme günlük/aylık toplama yazılır; Geliştirici bilgileri'nde durum paneli.
    from apps.axion_local import ledger

    assert ledger.totals()["gun"]["turler"]["baslik"] == pytest.approx(2 * (50 * 0.20e-6 + 10 * 1.20e-6))
    assert any(m.value == "**🩺 Durum ve maliyet**" for m in at.markdown)


def test_corrections_are_logged_when_saving(local_env, monkeypatch):
    """v4.0.0-alpha.5: modelin son çıktısı ↔ editörün kaydettiği (değişen alanlar), yeniden üretim sayısı ve beğenilmeyen
    başlıklar silinmeyen kayda yazılır; aynı haber yeniden kaydedilince satır güncellenir."""
    from types import SimpleNamespace

    from apps.axion_local import corrections

    usage = {"input_tokens": 50, "output_tokens": 10, "requests": 1, "provider": "OpenAI", "model": "gpt-5.6-luna"}
    monkeypatch.setattr("apps.news_studio.ai.clients.regenerate_headlines",
                        lambda *a, previous=(): (SimpleNamespace(baslik1="YENİ", baslik2="5 KİŞİ YARALANDI"), usage))
    at = start()
    at.session_state["model_output"] = {"baslik1": "SAVRULAN OTOMOBİL BERBER DÜKKÂNINA ÇARPTI",
                                        "baslik2": "5 KİŞİ YARALANDI", "icerik": TTS, "tts": TTS}
    at = with_generated_news(at)
    button(at, "↻ Başlıkları yeniden üret").click().run()
    at.text_input(key="_w_baslik1").set_value("OTOMOBİL DÜKKÂNA DALDI").run()
    button(at, "Sadece kaydet").click().run()
    assert not at.exception
    [entry] = corrections.entries()
    assert entry["tur"] == "haber" and entry["proje"] == store.list_news_projects()[0].id
    assert entry["degisen"] == {"baslik1": {"model": "YENİ", "editor": "OTOMOBİL DÜKKÂNA DALDI"}}
    assert entry["degismeyen"] == ["baslik2", "icerik", "tts"] and entry["ham_haber"] == "Ham haber"
    assert entry["yeniden_uretim"] == {"baslik": 1}
    assert entry["reddedilen_basliklar"] == [["SAVRULAN OTOMOBİL BERBER DÜKKÂNINA ÇARPTI", "5 KİŞİ YARALANDI"]]
    at.text_input(key="_w_baslik2").set_value("BEŞ YARALI").run()
    button(at, "Sadece kaydet").click().run()
    [entry] = corrections.entries()  # aynı haber: son hâl
    assert set(entry["degisen"]) == {"baslik1", "baslik2"}
    assert any(c.value.startswith("Düzeltme kaydı: 1 haber") for c in at.caption)
    assert any(b.label == "📝 Düzeltme kaydını indir" for b in at.get("download_button"))


def test_style_examples_are_remembered(local_env):
    from apps.axion_local.preferences import load_preferences

    at = start()
    at.text_area(key="ex_Mizahi Haber Dili").set_value("Örnek mizahi haber").run()
    assert load_preferences()["news_examples"]["Mizahi Haber Dili"] == "Örnek mizahi haber"
    fresh = start()  # yeni oturum
    assert fresh.session_state["examples"]["Mizahi Haber Dili"] == "Örnek mizahi haber"


def test_stale_audio_blocks_saving(local_env):
    at = with_generated_news(start(), tts="Düzenlenmiş TTS", audio_text="Eski TTS")
    assert any("ses üretildikten sonra değişti" in w.value for w in at.warning)
    assert not any(b.label == "Sadece kaydet" for b in at.button)


def media_library(shots=()):
    from apps.video_studio.modules.video_asset import LUNA_PROMPT_VERSION

    return {
        "analysis": {"estimated_cost_usd": 0.0046},
        "assets": [{
            "asset_id": "video_001", "asset_type": "video", "analysis_prompt_version": LUNA_PROMPT_VERSION,
            "source": {"filename": "dha.mp4", "sha256": "a" * 64},
            "geometry": {"encoded_width": 1920, "encoded_height": 1080, "display": {"width": 1920, "height": 1080}},
            "shots": list(shots),
        }],
    }


def open_page(project, page=VIDEO_PAGE, key="video_project_id"):
    """Uygulama taze açılır (seçili haber yok); editör haberi listeden seçer."""
    at = start()
    at.switch_page(page).run()
    assert at.selectbox(key=key).value is None
    at.selectbox(key=key).select(project.id).run()
    return at


def saved_project(library):
    folder = store.save_news_project(
        NewsPackage(headline_1="KAZA", headline_2="B", caption="Haber", tts_text="TTS"), b"mp3"
    )
    project = store.get_news_project(folder.name)
    store.save_project_json(project, store.MEDIA_LIBRARY_FILENAME, library)
    return project


def test_saved_media_analysis_is_restored(local_env):
    library = media_library([{
        "shot_id": "video_001_shot_001", "asset_id": "video_001", "shot_number": 1,
        "start_seconds": 0.0, "end_seconds": 8.32, "duration_seconds": 8.32,
        "visual": {"description": "Kalabalık", "visual_type": "people", "editorial_role": "establishing"},
    }])
    project = saved_project(library)
    at = open_page(project)
    assert not at.exception
    assert at.session_state["media_library"] == library
    assert at.dataframe[0].value["Görüntü"].tolist() == ["people"]
    assert at.session_state["edit_project"]["audio"]["duration_seconds"] == 24.2
    assert store.load_project_json(project, store.EDIT_PROJECT_FILENAME) is not None
    assert any(b.label == "🎬 Videoyu oluştur" for b in at.button)
    # Tamamlanan adımlar daralır: haber ve görüntüler özet satırı olur.
    labels = [e.label for e in at.expander]
    assert any(label.startswith("✅ 1. Haber — KAZA") for label in labels)
    assert any(label.startswith("✅ 2. Görüntüler — dha.mp4") for label in labels)


def test_render_button_creates_video_full_bleed(local_env, monkeypatch):
    rendered = []

    def fake_render(edit_project, media_library, output):
        rendered.append([c["framing"]["view_region"] for t in edit_project["edit_plan"]["timeline"]["tracks"] for c in t["clips"] if t["kind"] == "video"])
        output.write_bytes(b"mp4")
        return "x264 (işlemci)"

    monkeypatch.setattr("apps.video_studio.modules.render.render_rough_cut", fake_render)
    finals = []
    monkeypatch.setattr("apps.design_studio.pipeline.render_final",
                        lambda rough, design, background, fps, seconds, output: finals.append(design) or output.write_bytes(b"final") or "x264")
    project = saved_project(media_library([{
        "shot_id": "video_001_shot_001", "asset_id": "video_001", "shot_number": 1,
        "start_seconds": 0.0, "end_seconds": 30.0, "duration_seconds": 30.0,
        "visual": {"description": "Kaza", "visual_type": "event", "editorial_role": "establishing"},
    }]))
    at = open_page(project)
    assert not at.segmented_control  # kadraj seçimi yok: hep tam dolu
    button(at, "🎬 Videoyu oluştur").click().run()
    assert not at.exception
    # Üretim arka planda: sayfa beklemez (tablet kapansa da sürer), bitince video görünür.
    from apps.video_studio import jobs as video_jobs

    video_jobs.wait(project)
    at.run()
    assert not at.exception
    assert rendered and all(view is not None for view in rendered[0])
    assert (project.folder / store.ROUGH_CUT_FILENAME).exists()
    assert any(b.label == "Videoyu yeniden oluştur" for b in at.button)
    # Kurguyla birlikte son video (Axion şablonu) de hazır: editör indirmeye hazır videoyu görür.
    assert finals and finals[0].headline_1.text == "KAZA"
    assert (project.folder / store.FINAL_VIDEO_FILENAME).exists()
    assert any(b.label == "⬇️ Son videoyu indir" for b in at.get("download_button"))
    assert any(b.label == "🎨 Tasarım Stüdyosu'nda düzenle →" for b in at.button)
    assert any(c.value == store.load_news_project(project)[0].caption for c in at.code)  # paylaşım metni
    # Faz 4: sahneleri Luna seçer; ulaşılamazsa (testte hep) kurallarla ve editör uyarılır.
    assert any("Luna'ya ulaşılamadı" in w.value for w in at.warning)
    assert any(b.label == "🔀 Sahneleri yeniden seç" for b in at.button)

    # Luna yanıt verince: sahne seçimi kaydedilir, "Sahneleri yeniden seç" önceki kurguyu "beğenilmedi" diye gönderir.
    from apps.video_studio.modules import luna_edit

    prompts = []

    def fake_request(prompt, ids, api_key, client=None):
        prompts.append(prompt)
        return ({"olay_orgusu": "Kaza oldu.", "sahneler": [{"parca": 1, "asama": "olay_ani", "pencere": ids[0],
                                                             "kaynak_bas": 1.0 + len(prompts)}]},
                {"input_tokens": 900, "output_tokens": 80})

    monkeypatch.setattr(luna_edit, "request", fake_request)
    button(at, "Videoyu yeniden oluştur").click().run()
    video_jobs.wait(project)
    at.run()
    saved = json.loads((project.folder / luna_edit.PLAN_FILENAME).read_text(encoding="utf-8"))
    assert len(prompts) == 1 and saved["sahneler"][0]["kaynak_bas"] == 2.0
    from apps.axion_local import ledger  # v4.0: yeni Luna çağrısı maliyet defterine (kayıtlı plan ücretsiz, yazılmaz)

    assert ledger.totals()["gun"]["turler"] == {"sahne": 0.0}
    clips = [c for t in at.session_state["edit_project"]["edit_plan"]["timeline"]["tracks"] if t["kind"] == "video" for c in t["clips"]]
    # Tek çekim: parçalar kaynak sırasına dizilir (v3.3 kuralı); Luna'nın seçtiği parça videoda (etiketiyle) yer alır.
    assert [c["origin"] for c in clips].count("llm") == 1
    button(at, "Videoyu yeniden oluştur").click().run()  # girdiler aynı: kayıtlı plan, yeni çağrı yok
    video_jobs.wait(project)
    assert len(prompts) == 1
    at.run()
    button(at, "🔀 Sahneleri yeniden seç").click().run()
    video_jobs.wait(project)
    assert len(prompts) == 2 and "<onceki_kurgu>" in prompts[1] and "1: P1 @ 2.0" in prompts[1]


def test_editor_swaps_one_scene_without_api(local_env, monkeypatch, tmp_path):
    """v4.0.0-alpha.2: sahneye dokun → aynı görüntülerden seçenekler (fotoğraf dahil) → seç → yalnız o sahne değişir."""
    from PIL import Image

    from apps.video_studio import jobs as video_jobs
    from apps.video_studio.modules import luna_edit

    monkeypatch.setattr("apps.video_studio.modules.render.render_rough_cut",
                        lambda edit_project, media_library, output: output.write_bytes(b"mp4") or "x264")
    monkeypatch.setattr("apps.design_studio.pipeline.render_final",
                        lambda rough, design, background, fps, seconds, output: output.write_bytes(b"final") or "x264")
    photo = tmp_path / "foto.jpg"
    Image.new("RGB", (1600, 900), "red").save(photo)
    shots = [{"shot_id": f"video_001_shot_{n:03d}", "asset_id": "video_001", "shot_number": n,
              "start_seconds": (n - 1) * 6.0, "end_seconds": n * 6.0, "duration_seconds": 6.0,
              "visual": {"description": f"Görüntü {n}", "visual_type": "event", "editorial_role": "establishing"}}
             for n in range(1, 9)]
    library = media_library(shots)
    library["assets"].append({
        "asset_id": "image_001", "asset_type": "image", "analysis_prompt_version": library["assets"][0]["analysis_prompt_version"],
        "source": {"filename": "foto.jpg", "sha256": "b" * 64, "original_path": str(photo)},
        "geometry": {"width": 1600, "height": 900, "exif_orientation": 1},
        "visual": {"description": "Kazanın fotoğrafı", "visual_type": "event", "editorial_role": "evidence"}})
    project = saved_project(library)
    at = open_page(project)
    button(at, "🎬 Videoyu oluştur").click().run()
    video_jobs.wait(project)
    at.run()
    button(at, "🎞️ Sahneleri göster ve değiştir").click().run()
    assert not at.exception
    before = [(c["scene"], c["shot_id"], c["source_in_s"]) for c in video_clips(at.session_state["edit_project"])]
    scene_buttons = [b for b in at.button if b.key and b.key.startswith("sahne_") and b.key != "sahne_vazgec"]
    assert len(scene_buttons) == len({c[0] for c in before}) >= 3
    assert "kapak" in scene_buttons[0].label and "kapak" not in scene_buttons[1].label  # ilk kare = kapak
    button(at, scene_buttons[1].label).click().run()
    options = [b for b in at.button if b.key and b.key.startswith("secenek_")]
    assert 1 <= len(options) <= 4 and not at.exception
    assert any("Kazanın fotoğrafı" in c.value for c in at.caption)  # fotoğraf da seçenek
    options[0].click().run()
    video_jobs.wait(project)
    at.run()
    plan = json.loads((project.folder / luna_edit.PLAN_FILENAME).read_text(encoding="utf-8"))
    assert [e["parca"] for e in plan["editor"]] == [2] and plan["temel"]  # Luna'ya ulaşılamadı: kurgu temel alındı
    from apps.axion_local import corrections  # v4.0 düzeltme kaydı: editörün sahne değişikliği

    [entry] = [e for e in corrections.entries() if e["tur"] == "sahne"]
    assert entry["sahne"] == 2 and entry["onceki"]["secen"] == "rule" and entry["yeni"]["aciklama"]
    after = [(c["scene"], c["shot_id"], c["source_in_s"]) for c in video_clips(at.session_state["edit_project"])]
    changed = {scene for scene in {c[0] for c in before} if [c for c in before if c[0] == scene] != [c for c in after if c[0] == scene]}
    assert changed == {1}  # yalnız o sahne
    user = [c for c in video_clips(at.session_state["edit_project"]) if c["origin"] == "user"]
    assert [c["scene"] for c in user] == [1]
    assert any(b.label.startswith("✋ 2 ·") for b in at.button)  # bölüm açık kalır, değişen sahne işaretli
    # "Sahneleri yeniden seç" editörün seçimlerini de sıfırlar.
    button(at, "🔀 Sahneleri yeniden seç").click().run()
    video_jobs.wait(project)
    at.run()
    assert all(c["origin"] != "user" for c in video_clips(at.session_state["edit_project"]))


def video_clips(edit_project):
    return [c for t in edit_project["edit_plan"]["timeline"]["tracks"] if t["kind"] == "video" for c in t["clips"]]


def test_video_render_failure_is_shown_and_can_be_retried(local_env, monkeypatch):
    from apps.video_studio import jobs as video_jobs

    def broken(edit_project, media_library, output):
        raise RuntimeError("FFmpeg videoyu oluşturamadı.\n\nh264 hatası")

    monkeypatch.setattr("apps.video_studio.modules.render.render_rough_cut", broken)
    project = saved_project(media_library([{
        "shot_id": "video_001_shot_001", "asset_id": "video_001", "shot_number": 1,
        "start_seconds": 0.0, "end_seconds": 30.0, "duration_seconds": 30.0,
        "visual": {"description": "Kaza", "visual_type": "event", "editorial_role": "establishing"},
    }]))
    at = open_page(project)
    button(at, "🎬 Videoyu oluştur").click().run()
    video_jobs.wait(project)
    at.run()
    assert not at.exception
    assert any("Video oluşturulamadı" in e.value for e in at.error)
    assert any("h264 hatası" in c.value for c in at.code)
    assert any(b.label == "🎬 Videoyu oluştur" and not b.disabled for b in at.button)  # yeniden denenebilir

def test_outdated_media_analysis_asks_for_reanalysis(local_env):
    project = saved_project({"assets": [{"asset_type": "video", "source": {"filename": "dha.mp4"}, "shots": []}]})
    at = open_page(project)
    assert not at.exception
    assert "media_library" not in at.session_state
    assert any("yeniden analiz" in i.value for i in at.info)
    assert not any(b.label == "🎬 Videoyu oluştur" for b in at.button)


def test_settings_are_remembered_between_sessions(local_env):
    at = start()
    at.slider(key="speed").set_value(0.95).run()
    at.selectbox(key="thinking").select("Orta").run()
    at.selectbox(key="news_style").select("Son Dakika Dili").run()

    again = start()
    assert again.slider(key="speed").value == 0.95
    assert again.selectbox(key="thinking").value == "Orta"
    assert again.selectbox(key="news_style").value == "Son Dakika Dili"


def test_settings_survive_page_switch(local_env):
    at = start()
    at.slider(key="stability").set_value(0.8).run()
    at.switch_page(VIDEO_PAGE).run()
    at.switch_page(NEWS_PAGE).run()
    assert at.slider(key="stability").value == 0.8


def test_video_studio_shows_no_shot_table_outside_developer_info(local_env):
    project = saved_project(media_library())
    at = open_page(project)
    assert not at.exception
    assert not at.text_area
    assert any(e.label == "✅ 2. Görüntüler — dha.mp4" for e in at.expander)


def test_design_studio_fills_template_and_renders_final_video(local_env, monkeypatch):
    import json

    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    calls = []

    def fake_render(rough, design, background, fps, seconds, output, cancel=None):
        calls.append(design.model_copy(deep=True))
        output.write_bytes(b"final")
        return "x264"

    from apps.design_studio import jobs

    monkeypatch.setattr("apps.design_studio.jobs.render_final", fake_render)
    at = open_page(project, DESIGN_PAGE, "design_project_id")
    assert not at.exception
    # Son video yoksa arka planda standart şablonla üretilir; editör bu sırada çalışabilir.
    jobs.wait(project)
    at.run()
    assert len(calls) == 1 and calls[0].headline_1.text == "KAZA" and calls[0].headline_2.text == "B"
    assert any("güncel" in s.value for s in at.sidebar.success)
    assert any(c.value.startswith("Son oluşturma") and c.value.endswith("· x264") for c in at.sidebar.caption)
    assert any(b.label == "⬇️ İndir" for b in at.sidebar.get("download_button"))
    # Editör (Windows denemesi): videoyu indirirken paylaşım metni de lazım → kopyala düğmesi + kapalı metin.
    assert [c.value for c in at.sidebar.code] == [store.load_news_project(project)[0].caption]

    pid = project.id
    at.sidebar.text_area(key=f"ds_{pid}_h1_text").set_value("KAZA\nYERİ").run()
    saved = json.loads((project.folder / store.DESIGN_FILENAME).read_text(encoding="utf-8"))
    assert saved["version"] == 2 and saved["headline_1"]["text"] == "KAZA\nYERİ"
    assert any("işlenmedi" in w.value for w in at.sidebar.warning)

    next(b for b in at.sidebar.button if b.label == "🎬 Yeniden oluştur").click().run()
    assert not at.exception
    assert any(b.label == "🎬 Oluşturuluyor…" for b in at.sidebar.button) or jobs.get(project).finished
    jobs.wait(project)
    at.run()
    assert calls[-1].headline_1.text == "KAZA\nYERİ"
    assert any("güncel" in s.value for s in at.sidebar.success)


def test_design_studio_music_choice_and_own_music(local_env, monkeypatch):
    """v4.0.0-alpha.4: müzik altlığı varsayılan "Gündem"; kapatılır, başka parça seçilir, kendi müziği eklenir
    (yalnız bu bilgisayarda, GitHub'a gitmez)."""
    import json

    from apps.design_studio import jobs

    monkeypatch.setattr("apps.design_studio.jobs.render_final",
                        lambda rough, design, background, fps, seconds, output, cancel=None: output.write_bytes(b"f") or "x264")
    uploads = []
    monkeypatch.setattr("apps.design_studio.assets.upload_to_github", lambda *a: uploads.append(a))
    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    at = open_page(project, DESIGN_PAGE, "design_project_id")
    jobs.wait(project)
    at.run()
    assert any(e.label == "🎵 Müzik: Gündem (nötr)" for e in at.sidebar.expander)
    box = next(b for b in at.sidebar.selectbox if "Kapalı" in b.options)
    assert box.options[:4] == ["Kapalı", "Gündem (nötr)", "Gerilim (asayiş, son dakika)", "Sakin (insan hikâyesi)"]
    box.select("gerilim").run()
    design = lambda: json.loads((project.folder / store.DESIGN_FILENAME).read_text(encoding="utf-8"))  # noqa: E731
    assert design()["music"] == "gerilim" and any("işlenmedi" in w.value for w in at.sidebar.warning)
    next(b for b in at.sidebar.selectbox if "Kapalı" in b.options).select("kapali").run()
    assert design()["music"] == "kapali" and any(e.label == "🎵 Müzik: Kapalı" for e in at.sidebar.expander)
    from apps.design_studio import music

    music.add("benim parçam.mp3", b"ID3")  # sayfanın yükleme düğmesi aynı işlevi çağırır
    at.run()
    assert "benim parçam (eklenen)" in next(b for b in at.sidebar.selectbox if "Kapalı" in b.options).options
    assert (music.user_dir() / "benim parçam.mp3").exists() and not uploads
    assert not at.exception


def test_design_studio_restarts_running_render_with_new_changes(local_env, monkeypatch):
    import threading

    from apps.design_studio import jobs
    from apps.design_studio.pipeline import load_project_design
    from apps.design_studio.render import Cancelled

    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    (project.folder / store.FINAL_VIDEO_FILENAME).write_bytes(b"eski")
    release, rendered = threading.Event(), []

    def slow_render(rough, design, background, fps, seconds, output, cancel=None):
        while not release.is_set():  # gerçek FFmpeg gibi: iptal gelene kadar sürer
            if cancel.wait(0.01):
                raise Cancelled
        rendered.append(design.headline_1.text)
        output.write_bytes(b"yeni")
        return "x264"

    monkeypatch.setattr("apps.design_studio.jobs.render_final", slow_render)
    design = load_project_design(project, 20.0)
    jobs.start(project, design)
    first = jobs.get(project)
    at = open_page(project, DESIGN_PAGE, "design_project_id")
    assert any(b.label == "🎬 Oluşturuluyor…" and b.disabled for b in at.sidebar.button)

    at.sidebar.text_area(key=f"ds_{project.id}_h1_text").set_value("YENİ BAŞLIK").run()  # üretim sürerken değiştirdi
    restart = next(b for b in at.sidebar.button if b.label == "🔁 Değişikliklerle yeniden başlat")
    restart.click().run()
    assert not at.exception
    second = jobs.get(project)
    assert second is not first and first.cancel.is_set()
    release.set()
    jobs.wait(project)
    assert first.cancelled and not first.error
    assert rendered == ["YENİ BAŞLIK"]  # eski tasarım hiç bitirilmedi
    at.run()
    assert any("güncel" in s.value for s in at.sidebar.success)


def test_editor_save_keeps_signature_written_by_background_render(local_env):
    """Sayfanın elindeki eski kopya (rendered=None), arka planda biten üretimin imzasını ezmemeli; üretim de
    editörün sonradan yaptığı değişikliği ezmemeli."""
    from apps.design_studio.pipeline import final_is_current, load_project_design, mark_rendered, save_project_design

    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    (project.folder / store.FINAL_VIDEO_FILENAME).write_bytes(b"mp4")
    page_copy = load_project_design(project, 20.0)          # sayfa çalışması başında okundu
    rendered_copy = page_copy.model_copy(deep=True)
    mark_rendered(project, rendered_copy)                   # arka plandaki üretim bitti
    save_project_design(project, page_copy)                 # sayfa aynı tasarımı yeniden kaydetti
    assert final_is_current(project, load_project_design(project, 20.0))

    page_copy.headline_1.text = "YENİ"
    save_project_design(project, page_copy)                 # editör değiştirdi
    mark_rendered(project, rendered_copy)                   # eski tasarımın üretimi şimdi bitti
    stored = load_project_design(project, 20.0)
    assert stored.headline_1.text == "YENİ" and not final_is_current(project, stored)


def test_design_studio_waits_for_rough_cut(local_env):
    project = saved_project(media_library())
    at = open_page(project, DESIGN_PAGE, "design_project_id")
    assert not at.exception
    assert any("Videoyu oluştur" in i.value for i in at.info)


def test_soundbites_are_listed_used_in_cut_and_removable(local_env):
    from apps.video_studio.modules.soundbites import SOUNDBITES_FILENAME

    project = saved_project(media_library([{
        "shot_id": "video_001_shot_001", "asset_id": "video_001", "shot_number": 1,
        "start_seconds": 0.0, "end_seconds": 30.0, "duration_seconds": 30.0,
        "visual": {"description": "Kaza", "visual_type": "event", "editorial_role": "establishing"},
    }]))
    store.save_project_json(project, SOUNDBITES_FILENAME, [
        {"path": "C:/dha.mp4", "filename": "dha.mp4", "start_s": 2.0, "end_s": 6.0, "placement": "after"},
    ])
    at = open_page(project)
    assert not at.exception
    assert any("3. Kaynak sesli kesitler (isteğe bağlı) — 1 kesit, 4 sn" in e.label for e in at.expander)
    assert any("Seslendirmeden sonra" in m.value for m in at.markdown)
    clips = next(t for t in at.session_state["edit_project"]["edit_plan"]["timeline"]["tracks"] if t["kind"] == "video")["clips"]
    assert clips[-1]["use_source_audio"] and clips[-1]["duration_f"] == 120

    button(at, "Kaldır").click().run()
    assert not at.exception
    assert store.load_project_json(project, SOUNDBITES_FILENAME) == []
    clips = next(t for t in at.session_state["edit_project"]["edit_plan"]["timeline"]["tracks"] if t["kind"] == "video")["clips"]
    assert not any(c["use_source_audio"] for c in clips)


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="FFmpeg kurulu değil")
def test_pick_soundbite_from_selected_video_before_analysis(local_env, monkeypatch):
    import subprocess

    video = local_env / "Downloads" / "roportaj.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=12",
         "-f", "lavfi", "-i", "sine=duration=12", "-shortest", str(video)],
        check=True,
    )
    project = saved_project({"assets": []})
    at = open_page(project)
    at.multiselect(key="selected_media").select(video).run()
    button(at, "▶️ Videoyu izle ve kesit seç").click().run()
    assert not at.exception
    assert list((project.folder / "onizleme").glob("*.mp4"))
    assert "00:08.5" in at.select_slider[0].options  # dakika:saniye (80 sn değil 01:20)
    assert any("olay" in caption.value for caption in at.caption)  # varsayılan aralık: olay anı ya da "bulunamadı"
    at.select_slider[0].set_range("00:03.0", "00:08.5").run()
    at.segmented_control(key="kesit_placement").set_value("after").run()
    button(at, "➕ Kesiti ekle").click().run()
    assert not at.exception
    from apps.video_studio.modules.soundbites import SOUNDBITES_FILENAME

    assert store.load_project_json(project, SOUNDBITES_FILENAME) == [
        {"path": str(video), "filename": "roportaj.mp4", "start_s": 3.0, "end_s": 8.5, "placement": "after"}
    ]
    from apps.axion_local import corrections  # v4.0 düzeltme kaydı: önerilen aralık ↔ seçilen

    [entry] = [e for e in corrections.entries() if e["tur"] == "kesit"]
    assert entry["video"] == "roportaj.mp4" and entry["secilen"] == [3.0, 8.5] and entry["yer"] == "after"
    assert entry["degisti"] is True


def test_soundbite_is_picked_from_the_transcript(local_env, monkeypatch):
    """v4.0.0-alpha.7: konuşmalar bu bilgisayarda yazıya dökülür; cümleye dokun → kesit aralığı yalnız o cümle (başka
    cümleye dokunmak ona geçer), "sonraki cümleyi de ekle" uzatır (testte sahte model)."""
    import subprocess
    from types import SimpleNamespace

    from apps.video_studio.modules import transcribe

    class FakeWhisper:
        def transcribe(self, audio, **kwargs):
            parts = [(1.0, 3.2, "Müşterimizin boğazına yemek kaçtı."), (3.6, 5.1, "Hemen fark ettim."),
                     (6.0, 9.4, "Heimlich manevrası uyguladım.")]
            return (SimpleNamespace(start=a, end=b, text=t, words=[SimpleNamespace(start=a, end=b, word=" " + t)])
                    for a, b, t in parts), SimpleNamespace(duration=12.0)

    monkeypatch.setattr(transcribe, "_load_model", lambda: FakeWhisper())
    video = local_env / "Downloads" / "roportaj.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=12",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "12", str(video)], check=True)  # sessiz: sınırlar kelimeden
    project = saved_project({"assets": []})
    at = open_page(project)
    at.multiselect(key="selected_media").select(video).run()
    button(at, "▶️ Videoyu izle ve kesit seç").click().run()
    button(at, "📝 Konuşmaları yazıya dök").click().run()
    transcribe.job(video, project.folder).thread.join(10)
    at.run()
    assert not at.exception
    lines = [b for b in at.button if b.key and b.key.startswith("yazi_")]
    # Kelime zamanlarından, biraz önce başlar/sonra biter ama sonraki kelimeye taşmaz (v4.0 editör notu).
    assert [b.label for b in lines] == ["00:00.9–00:03.5 · Müşterimizin boğazına yemek kaçtı.",
                                        "00:03.5–00:05.3 · Hemen fark ettim.", "00:05.9–00:09.7 · Heimlich manevrası uyguladım."]
    assert any("yazıya döküldü" in c.value for c in at.caption)
    lines[1].click().run()
    assert at.select_slider[0].value == ("00:03.5", "00:05.3")
    assert next(b for b in at.button if b.key == "yazi_1").proto.type == "primary"  # seçili cümle vurgulu
    next(b for b in at.button if b.key == "yazi_2").click().run()  # başka cümle: yalnız o (alpha.7.1'de arası seçiliyordu)
    assert at.select_slider[0].value == ("00:05.9", "00:09.7")
    next(b for b in at.button if b.key == "cumle_onceki").click().run()
    assert at.select_slider[0].value == ("00:03.5", "00:09.7")
    assert next(b for b in at.button if b.key == "cumle_sonraki").disabled  # son cümle zaten içinde
    assert not at.exception and not at.warning
    button(at, "➕ Kesiti ekle").click().run()
    from apps.video_studio.modules.soundbites import SOUNDBITES_FILENAME

    assert [(b["start_s"], b["end_s"]) for b in store.load_project_json(project, SOUNDBITES_FILENAME)] == [(3.5, 9.7)]


def test_fresh_start_selects_nothing_and_hides_previous_days(local_env):
    from datetime import timedelta

    old = store.save_news_project(
        NewsPackage(headline_1="DÜNKÜ HABER", headline_2="B", caption="c", tts_text="t"), b"mp3",
        now=store.work_day_start() - timedelta(hours=1),
    )
    today = saved_project(media_library())
    at = start()
    at.switch_page(VIDEO_PAGE).run()
    assert not at.exception
    picker = at.selectbox(key="video_project_id")
    assert picker.value is None and picker.options == [today.label]
    at.checkbox(key="video_project_id_old").check().run()
    assert len(at.selectbox(key="video_project_id").options) == 2
    assert old.name in [p.id for p in store.list_news_projects()]


def test_work_day_starts_at_two_am():
    from datetime import datetime

    assert store.work_day_start(datetime(2026, 9, 25, 1, 30)) == datetime(2026, 9, 24, 2, 0)
    assert store.work_day_start(datetime(2026, 9, 25, 2, 0)) == datetime(2026, 9, 25, 2, 0)
    assert store.work_day_start(datetime(2026, 9, 25, 23, 59)) == datetime(2026, 9, 25, 2, 0)


def test_edited_news_texts_survive_reruns_and_page_switch(local_env):
    at = with_generated_news(start())
    at.text_area(key="_w_tts_metni").input("Düzenlenmiş seslendirme").run()
    at.text_input(key="_w_baslik1").input("YENİ BAŞLIK").run()
    at.run()
    assert at.session_state["tts_metni"] == "Düzenlenmiş seslendirme"
    at.switch_page(VIDEO_PAGE).run()
    at.switch_page(NEWS_PAGE).run()
    assert at.text_area(key="_w_tts_metni").value == "Düzenlenmiş seslendirme"
    assert at.text_input(key="_w_baslik1").value == "YENİ BAŞLIK"


def test_pronunciation_dictionary_changes_only_what_elevenlabs_reads(local_env, monkeypatch):
    """v4.1.0-alpha.1 (editör: "bazen yanlış okuyor, sırf o yüzden sesi yeniden üretiyorum"): sözlük kenar çubuğunda
    doldurulur, hatırlanır; ElevenLabs'a okunuşu gider, ekrandaki ve kaydedilen metin aynı kalır, zamanlar ona göre."""
    import base64
    from types import SimpleNamespace

    import streamlit as st

    from apps.axion_local import ledger
    from apps.news_studio.tts import pronunciation

    sent = []

    def convert(**kwargs):
        sent.append(kwargs["text"])
        text = kwargs["text"]
        return SimpleNamespace(audio_base_64=base64.b64encode(b"mp3").decode(), alignment=SimpleNamespace(
            characters=list(text), character_start_times_seconds=[i / 10 for i in range(len(text))],
            character_end_times_seconds=[(i + 1) / 10 for i in range(len(text))]))

    fake = SimpleNamespace(text_to_speech=SimpleNamespace(convert_with_timestamps=convert), voices=SimpleNamespace(
        get_all=lambda: SimpleNamespace(voices=[SimpleNamespace(name="Cavit Presenter", voice_id="v1")])))
    monkeypatch.setattr("elevenlabs.client.ElevenLabs", lambda **kwargs: fake)
    st.cache_resource.clear()
    st.cache_data.clear()
    try:
        text = "Heimlich manevrasıyla kurtarıldı."
        at = with_generated_news(start(), tts=text, audio_text=None)
        at.sidebar.text_area(key="okunus_sozlugu").input("Heimlich = Haymlih\nbozuk").run()
        assert pronunciation.load() == {"Heimlich": "Haymlih"}
        assert any("bozuk" in w.value for w in at.sidebar.warning)
        button(at, "🎙️ Seslendir").click().run()
        assert not at.exception
        assert sent == ["Haymlih manevrasıyla kurtarıldı."]
        assert at.session_state["tts_metni"] == text and at.session_state["last_audio_text"] == text
        assert "".join(at.session_state["last_audio_alignment"]["characters"]) == text
        assert any(c.value == "Okunuş sözlüğüyle okundu: Heimlich → Haymlih" for c in at.caption)
        assert ledger.totals()["gun"]["karakter"] == len(sent[0])
        assert any("Bu haberin sesi: ElevenLabs'ta 32 karakter (1 kez seslendirildi)" == c.value for c in at.caption)
        button(at, "Sadece kaydet").click().run()
        saved = store.load_news_project(store.list_news_projects()[0])[0]
        assert saved.tts_text == text and saved.metadata["tts_characters"] == 32
    finally:
        st.cache_resource.clear()
        st.cache_data.clear()


BROWSER_PAGE = "apps/remote_browser/page.py"


class FakeBrowser:
    closed = False
    frame_count = 0

    def alive(self):
        return not self.closed

    def __init__(self):
        from apps.remote_browser.service import Screen

        self.calls = []
        self.screen_value = Screen(b"\xff\xd8jpeg", "about:blank", "", [{"title": "", "url": "about:blank", "active": True}])

    def run(self, action, value=None):
        self.calls.append((action, value))

    def screen(self, after_frame=None):
        return self.screen_value

    def download_rows(self):
        return [{"name": "kaza.mp4", "state": "bitti", "mb": 12.5, "error": None, "seconds": 4, "video": True}]

    def login_state(self):
        return {"offer": None, "filled": None}

    def fill_login(self):
        self.calls.append(("fill_login", None))
        return False

    def answer_login_offer(self, save):
        self.calls.append(("answer", save))

    def downloaded(self, name):
        return None


def test_browser_page_explains_missing_brave(local_env, monkeypatch):
    monkeypatch.setattr("apps.remote_browser.service.find_browser", lambda configured=None: None)
    at = start()
    at.switch_page(BROWSER_PAGE).run()
    assert not at.exception
    assert any("Brave" in e.value for e in at.error)


def test_browser_page_lists_and_deletes_saved_logins(local_env, monkeypatch):
    from apps.remote_browser.logins import FILENAME, Logins

    logins = Logins(store.data_dir() / FILENAME)
    logins.save("panel.dha.com.tr", "editor", "gizli")
    monkeypatch.setattr("apps.remote_browser.service.find_browser", lambda configured=None: Path("/brave"))
    monkeypatch.setattr("apps.remote_browser.service.shared", lambda executable, profile, inbox, logins=None: FakeBrowser())
    at = start()
    at.switch_page(BROWSER_PAGE).run()
    assert not at.exception
    assert any("panel.dha.com.tr" in m.value and "gizli" not in m.value for m in at.sidebar.markdown)
    at.sidebar.button(key="giris_sil_panel.dha.com.tr").click().run()
    assert logins.sites() == []


def test_browser_page_opens_dha_news_panel(local_env, monkeypatch):
    fake = FakeBrowser()
    monkeypatch.setattr("apps.remote_browser.service.find_browser", lambda configured=None: Path("/brave"))
    monkeypatch.setattr("apps.remote_browser.service.shared", lambda executable, profile, inbox, logins=None: fake)
    at = start()
    at.switch_page(BROWSER_PAGE).run()
    assert not at.exception
    # Editör: işi yalnız DHA abone paneli; ana sayfa ayarı ve açıklama kenar çubuğundan kalktı (yerine gezinme paneli).
    assert fake.calls == [("goto", "https://dhaabone.dha.com.tr/news")]  # boş sekme: bir kez açılır
    assert not at.sidebar.text_input and not [c for c in at.sidebar.caption if not c.value.startswith("Axion v")]
    at.run()
    assert fake.calls == [("goto", "https://dhaabone.dha.com.tr/news")]


def test_browser_events_are_validated_before_reaching_browser():
    from apps.remote_browser.viewer import apply_events

    fake = FakeBrowser()
    events = [
        {"t": "click", "v": [99999, -5]},            # ekran dışı → kenara kırpılır
        {"t": "wheel", "v": [10, 10, 0]},            # boş kaydırma atlanır
        {"t": "wheel", "v": [10, 10, 99999]},
        {"t": "type", "v": "ş" * 3000},
        {"t": "key", "v": "Enter"}, {"t": "key", "v": "F12"},
        {"t": "password"}, {"t": "home"}, {"t": "goto", "v": "  "},
        {"t": "eval", "v": "alert(1)"}, "bozuk", {"t": "click", "v": ["a", 1]},
        {"t": "tab", "v": "1"}, {"t": "tab", "v": "x"}, {"t": "close_tab", "v": 0}, {"t": "close_tab"},
    ]
    assert apply_events(fake, events, "gizli", "dha.com.tr") == 9
    assert fake.calls == [
        ("click", (1023.0, 0.0)), ("wheel", (10.0, 10.0, 6000.0)), ("type", "ş" * 2000), ("key", "Enter"),
        ("fill_login", None), ("type", "gizli"), ("goto", "dha.com.tr"),
        ("tab", 1), ("close_tab", 0), ("close_tab", None),
    ]  # 🔑: önce kayıtlı giriş, yoksa DHA_SIFRE; sekme seçme/kapatma sırayla
    fake.calls.clear()
    apply_events(fake, [{"t": "password"}, {"t": "save_login"}, {"t": "dismiss_login"}], None, "x")
    assert fake.calls == [("fill_login", None), ("answer", True), ("answer", False)]  # şifre yoksa hiçbir şey yazılmaz
    assert apply_events(fake, [{"t": "click", "v": [1, 1]}] * 500, None, "x") == 60  # olay yağmuru sınırlı


def test_video_studio_preselects_video_sent_from_browser_page(local_env):
    project = saved_project(media_library())
    inbox = local_env / "Downloads"
    at = start()
    at.session_state["selected_media"] = [inbox / "dha_kaza.mp4", inbox / "silinmis.mp4"]
    at.switch_page(VIDEO_PAGE).run()
    at.selectbox(key="video_project_id").select(project.id).run()
    assert not at.exception
    assert at.multiselect(key="selected_media").value == [inbox / "dha_kaza.mp4"]


def test_design_job_cancel_stops_running_render(local_env, monkeypatch):
    import threading

    from apps.design_studio import jobs
    from apps.design_studio.pipeline import load_project_design
    from apps.design_studio.render import Cancelled

    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    started = threading.Event()

    def slow_render(rough, design, background, fps, seconds, output, cancel=None):
        started.set()
        while not cancel.wait(0.01):
            pass
        raise Cancelled

    monkeypatch.setattr("apps.design_studio.jobs.render_final", slow_render)
    jobs.start(project, load_project_design(project, 20.0))
    assert started.wait(5)
    assert jobs.busy()
    assert jobs.cancel(project)  # Video Stüdyosu kurguyu yeniden üretirken
    job = jobs.get(project)
    assert not job.running and job.cancelled and not job.error
    assert not (project.folder / store.FINAL_VIDEO_FILENAME).exists()


def test_video_job_skips_final_when_design_render_does_not_stop(local_env, monkeypatch):
    """Tasarım üretimi zamanında durmazsa Video Stüdyosu aynı son videoya ikinci üretimi yazmaz."""
    import threading

    from apps.video_studio import jobs as video_jobs

    project = saved_project(media_library())
    release, finals = threading.Event(), []

    def slow_rough_cut(edit_project, media_library, output):
        release.wait(5)
        output.write_bytes(b"mp4")
        return "x264"

    monkeypatch.setattr("apps.video_studio.modules.render.render_rough_cut", slow_rough_cut)
    monkeypatch.setattr("apps.design_studio.jobs.cancel", lambda project: False)
    monkeypatch.setattr("apps.design_studio.pipeline.render_project_final", finals.append)
    assert video_jobs.start(project, {}, {})
    assert video_jobs.busy(project) and video_jobs.busy()
    release.set()
    video_jobs.wait(project)
    job = video_jobs.get(project)
    assert not job.running and not job.error and "durdurulamadı" in job.final_error
    assert not finals and not video_jobs.busy(project)


def test_design_page_waits_while_video_studio_renders(local_env, monkeypatch):
    """Video Stüdyosu aynı haberi üretirken Tasarım Stüdyosu ikinci bir üretim başlatmaz."""
    import threading

    from apps.design_studio import jobs as design_jobs
    from apps.video_studio import jobs as video_jobs

    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    release = threading.Event()

    def slow_rough_cut(edit_project, media_library, output):
        release.wait(10)
        raise RuntimeError("test")

    monkeypatch.setattr("apps.video_studio.modules.render.render_rough_cut", slow_rough_cut)
    video_jobs.start(project, {}, {})
    try:
        at = open_page(project, DESIGN_PAGE, "design_project_id")
        assert not at.exception
        assert any("Video Stüdyosu bu haberin videosunu" in i.value for i in at.info)
        assert design_jobs.get(project) is None  # son video yok ama otomatik üretim başlamadı
        # Başlatma tek kilitte: sayfa kontrolünden bağımsız olarak da ikinci üretim başlamaz.
        from apps.design_studio.pipeline import load_project_design

        assert not design_jobs.start(project, load_project_design(project, 20.0), restart=True)
    finally:
        release.set()
        video_jobs.wait(project)


def test_news_text_is_imported_from_downloaded_txt(local_env):
    """DHA'nın "metni kopyala"sı uzaktan çalışmıyor; "TXT indir" İndirilenler'e iner, Haber Stüdyosu oradan alır."""
    (local_env / "Downloads" / "dha_haber.txt").write_bytes("KAZA\r\nİnegöl'de otomobil devrildi.".encode("cp1254"))
    at = with_generated_news(start())
    at.session_state["active_news_project"] = "eski-proje"
    button(at, "Aktar").click().run()
    assert not at.exception
    assert at.session_state["raw_text"] == "KAZA\nİnegöl'de otomobil devrildi."
    assert at.session_state["baslik1"] == "" and "active_news_project" not in at.session_state  # eski proje korunur


def test_browser_txt_download_opens_in_news_studio(local_env):
    at = start()
    at.session_state["haber_aktar"] = "Ham DHA metni"
    at.run()
    assert not at.exception
    assert at.session_state["raw_text"] == "Ham DHA metni" and "haber_aktar" not in at.session_state


def test_update_indicator_in_sidebar(local_env, monkeypatch):
    """Editör: "PC'de güncellemeyi unutursam görünsün" — kenar çubuğunda yeşil/kırmızı tek satır."""
    from apps.axion_local import update_check

    monkeypatch.setattr(update_check, "status", lambda now=None: "var")
    at = start()
    assert any("🔴 Güncelleme var" in c.value for c in at.sidebar.caption)
    monkeypatch.setattr(update_check, "status", lambda now=None: "guncel")
    at.run()
    assert any("🟢 Axion güncel" in c.value for c in at.sidebar.caption)


def test_update_check_compares_local_and_remote_and_runs_in_background(monkeypatch):
    import time

    from apps.axion_local import update_check

    answers = {("rev-parse", "HEAD"): "abc", ("ls-remote", "origin", "refs/heads/main"): "abc\trefs/heads/main"}
    monkeypatch.setattr(update_check, "_git", lambda *args: answers[args])
    assert update_check.check() == "guncel"
    answers[("ls-remote", "origin", "refs/heads/main")] = "def\trefs/heads/main"
    assert update_check.check() == "var"

    def offline(*args):
        raise RuntimeError("internet yok")

    monkeypatch.setattr(update_check, "_git", offline)
    assert update_check.check() is None  # gösterilmez

    # Arka planda: ilk çağrı beklemeden None döner, kontrol bitince sonuç görünür; 2 dk dolmadan yeniden sorulmaz.
    calls = []
    monkeypatch.setattr(update_check, "_state", {"checked": 0.0, "status": None, "running": False})
    monkeypatch.setattr(update_check, "check", lambda: calls.append(1) or "var")
    assert update_check._status(now=1000.0) is None
    deadline = time.monotonic() + 3
    while update_check._state["running"] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert update_check._status(now=1000.0 + 60) == "var" and len(calls) == 1
    update_check._status(now=1000.0 + update_check.INTERVAL_SECONDS + 1)
    deadline = time.monotonic() + 3
    while update_check._state["running"] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(calls) == 2


def test_update_and_restart_from_the_app(local_env, monkeypatch):
    """Editör: dükkândayken bilgisayara erişim yok — uygulamadan güncelle ve kendini yeniden başlatsın (bekçiyle)."""
    import threading

    from apps.axion_local import update_check

    monkeypatch.setattr(update_check, "status", lambda now=None: "var")
    restarts = []

    real_timer = threading.Timer

    def timer(delay, function, *args, **kwargs):  # yeniden başlatma yakalanır (test süreci kapanmasın)
        if getattr(function, "__qualname__", "") == "restart_after_update.<locals>.stop":
            restarts.append(delay)
            idle = real_timer(3600, lambda: None)
            idle.daemon = True
            return idle
        return real_timer(delay, function, *args, **kwargs)

    monkeypatch.setattr(threading, "Timer", timer)
    monkeypatch.delenv(update_check.SUPERVISOR_ENV, raising=False)
    at = start()
    assert not [b for b in at.sidebar.button if "Güncelle" in b.label]  # bekçisiz (sorun_giderme.bat) yeniden başlayamaz
    assert any("masaüstündeki simgeyle" in c.value for c in at.sidebar.caption)

    monkeypatch.setenv(update_check.SUPERVISOR_ENV, "1")
    at.run()
    button(at, "⬇️ Güncelle ve yeniden başlat").click().run()
    monkeypatch.setattr(update_check, "apply_update", lambda: "Your local changes would be overwritten")
    button(at, "Evet, güncelle").click().run()
    assert any("Güncelleme olmadı" in e.value for e in at.error) and restarts == []

    monkeypatch.setattr(update_check, "apply_update", lambda: None)
    at.run()
    button(at, "⬇️ Güncelle ve yeniden başlat").click().run()
    button(at, "Evet, güncelle").click().run()
    assert not at.exception and len(restarts) == 1
    assert any("yeniden başlıyor" in s.value for s in at.success)


def test_watchdog_restarts_after_in_app_update():
    from pathlib import Path

    watchdog = (Path(__file__).resolve().parents[1] / "windows" / "axion_calistir.ps1").read_text()
    assert "$env:AXION_BEKCI = '1'" in watchdog and "if ($code -eq 3)" in watchdog
    assert "pip install" in watchdog.split("if ($code -eq 3)")[1].split("continue")[0]
    # Geri dönüş (v3.5): açılış kontrolü geçmezse ya da hemen çökerse önceki sürüm; dosya adları Python'la aynı.
    from apps.axion_local import update_check

    after_update = watchdog.split("if ($code -eq 3)")[1]
    assert "apps.axion_local.self_check" in after_update and "Invoke-Rollback 'kontrol'" in after_update
    assert "Invoke-Rollback 'cokme'" in watchdog and "git reset --keep $previous" in watchdog
    assert f"'{update_check.PREVIOUS_FILE}'" in watchdog and f"'{update_check.ROLLBACK_FILE}'" in watchdog


def test_update_check_and_pull_with_real_git(tmp_path, monkeypatch):
    """Gerçek git: repoda yeni commit → "var"; uygulamadan güncelle → dosya gelir, "guncel"."""
    import shutil
    import subprocess

    from apps.axion_local import update_check

    if shutil.which("git") is None:
        pytest.skip("git yok")

    def git(*args, cwd):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                       capture_output=True)

    origin, home, dev = tmp_path / "origin.git", tmp_path / "Axion", tmp_path / "dev"
    git("init", "--bare", "-b", "main", str(origin), cwd=tmp_path)
    git("clone", str(origin), str(dev), cwd=tmp_path)
    (dev / "a.txt").write_text("1")
    git("add", ".", cwd=dev)
    git("commit", "-m", "ilk", cwd=dev)
    git("push", "origin", "HEAD:main", cwd=dev)
    git("clone", str(origin), str(home), cwd=tmp_path)
    monkeypatch.setattr(update_check, "ROOT", home)
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))
    assert update_check.check() == "guncel"
    old_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=home, capture_output=True, text=True).stdout.strip()
    (dev / "b.txt").write_text("2")
    git("add", ".", cwd=dev)
    git("commit", "-m", "yeni", cwd=dev)
    git("push", "origin", "HEAD:main", cwd=dev)
    assert update_check.check() == "var"
    notice = tmp_path / "data" / update_check.ROLLBACK_FILE
    notice.parent.mkdir(parents=True, exist_ok=True)
    notice.write_text("failed=eski\n")
    assert update_check.apply_update() is None
    assert (home / "b.txt").read_text() == "2" and update_check.check() == "guncel"
    # Geri dönüş (v3.5): bekçi yeni sürüm açılmazsa buna döner; eski uyarı yeni güncellemeyle kalkar.
    assert (tmp_path / "data" / update_check.PREVIOUS_FILE).read_text().strip() == old_head
    assert not notice.exists()


def test_rollback_notice_blocks_the_same_broken_version(local_env, monkeypatch):
    """Bekçi bozuk sürümden geri döndüyse aynı sürüm yeniden önerilmez; düzeltilmiş sürüm gelince düğme döner."""
    from apps.axion_local import store, update_check

    monkeypatch.setenv(update_check.SUPERVISOR_ENV, "1")
    monkeypatch.setattr(update_check, "status", lambda now=None: "var")
    (store.data_dir()).mkdir(parents=True, exist_ok=True)
    (store.data_dir() / update_check.ROLLBACK_FILE).write_text("failed=bbb\nreason=kontrol\ntime=2026-09-26T09:00:00\n")
    monkeypatch.setattr(update_check, "_state", {"checked": 1.0, "status": "var", "running": False,
                                                 "remote": "bbb", "local": "aaa"})
    at = start()
    assert any("önceki sürüme döndü" in c.value for c in at.sidebar.caption)
    assert not [b for b in at.sidebar.button if "Güncelle" in b.label]
    update_check._state["remote"] = "ccc"  # düzeltme yayımlandı
    at.run()
    assert not any("önceki sürüme döndü" in c.value for c in at.sidebar.caption)
    assert [b for b in at.sidebar.button if "Güncelle" in b.label]


def test_version_number_in_sidebar(local_env, monkeypatch):
    """Editör (v3.5): kenar çubuğunda sürüm numarası; tek kaynak CHANGELOG'un ilk başlığı."""
    from apps.axion_local import update_check

    number = update_check.version()
    first = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()[0]
    assert number and first.startswith(f"# v{number} ")
    monkeypatch.setattr(update_check, "status", lambda now=None: "guncel")
    at = start()
    assert any(c.value == f"🟢 Axion güncel · v{number}" for c in at.sidebar.caption)
    assert update_check.label(None, number) == f"Axion v{number}" and update_check.label(None) is None
    # 4.0 ön sürümleri (editör: parça parça, alpha): "# v4.0.0-alpha.1 — ..." tam okunur.
    import io
    from unittest import mock

    with mock.patch("pathlib.Path.open", return_value=io.StringIO("# v4.0.0-alpha.1 — Fotoğraf desteği\n")):
        assert update_check.version() == "4.0.0-alpha.1"


def test_self_check_passes_on_this_version_and_catches_broken_ones(tmp_path, monkeypatch):
    """Bekçinin açılış kontrolü: bu sürüm geçer; sözdizimi hatası ve çizilirken hata veren sayfa yakalanır."""
    from apps.axion_local import self_check

    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))  # run() değiştirir; test sonunda eski hâli döner
    monkeypatch.setenv("AXION_INBOX_DIR", str(tmp_path))
    assert self_check.run() == []

    broken = tmp_path / "bozuk.py"
    broken.write_text("import streamlit as st\nst.title('x')\nraise RuntimeError('bozuk sayfa')\n")
    assert any("bozuk sayfa" in error for error in self_check.render_pages(broken, pages=()))

    root = tmp_path / "repo"
    (root / "apps").mkdir(parents=True)
    (root / "shared").mkdir()
    (root / "axion_app.py").write_text("x = 1\n")
    (root / "axion_local.py").write_text("x = 1\n")
    (root / "apps" / "bozuk.py").write_text("def f(:\n")
    monkeypatch.setattr(self_check, "ROOT", root)
    monkeypatch.chdir(tmp_path)  # main() çalışma klasörünü ve sys.path'i değiştirir (sahte axion_app.py sızmasın)
    monkeypatch.setattr(sys, "path", list(sys.path))
    assert [e for e in self_check.compile_all() if e.startswith("apps")]
    assert self_check.main() == 1


def test_select_boxes_do_not_open_the_tablet_keyboard():
    """Editör (v3.5, tablet): seçim kutusuna dokununca klavye açılıyordu (Streamlit'in arama kutusu).
    Her seçim kutusu yazmasız (`filter_mode=None`); çoklu seçimde İngilizce "Select all" yok."""
    import ast

    found = []
    for path in [ROOT / "axion_local.py", *sorted((ROOT / "apps").rglob("*.py"))]:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in {"selectbox", "multiselect"}:
                keywords = {k.arg: k.value for k in node.keywords}
                where = f"{path.relative_to(ROOT)}:{node.lineno}"
                found.append(where)
                assert isinstance(keywords.get("filter_mode"), ast.Constant) and keywords["filter_mode"].value is None, where
                if node.func.attr == "multiselect":
                    assert getattr(keywords.get("select_all"), "value", None) is False, where
    assert len(found) >= 10


def test_diagnostics_file_for_the_developer(local_env):
    """Editör (v3.6.1): tablette proje dosyalarına erişemez; Geliştirici bilgileri'nden tek dosya iner (internete gitmez)."""
    from apps.axion_local import diagnostics

    project = saved_project(media_library())
    store.save_project_json(project, "kurgu_plani.json", {"sahneler": [{"parca": 1, "pencere": "P1", "kaynak_bas": 0.5}]})
    (store.data_dir() / "axion.log").write_bytes(b"x" * 70_000 + b"SON SATIR\n")  # Windows metin kipi CRLF yazardı
    (project.folder / "yazi").mkdir()
    (project.folder / "yazi" / "roportaj_1.json").write_text('{"cumleler": [], "bolumler": []}', encoding="utf-8")
    data = json.loads(diagnostics.package(project.folder, "3.6.1"))
    assert data["dosyalar"]["yazi/roportaj_1.json"] == {"cumleler": [], "bolumler": []}  # yazıya döküm de (v4.0)
    assert data["surum"] == "3.6.1" and data["proje"] == project.folder.name
    assert {"news_package.json", "media_library.json", "kurgu_plani.json"} <= set(data["dosyalar"])
    assert data["dosyalar"]["kurgu_plani.json"]["sahneler"][0]["pencere"] == "P1"
    assert data["gunluk"]["axion.log"].endswith("SON SATIR\n") and len(data["gunluk"]["axion.log"]) <= 60_000
    assert diagnostics.filename(project.folder).startswith("teshis_") and diagnostics.filename(project.folder).endswith(".json")
    at = open_page(project)
    assert not at.exception
    assert any(b.label == "📦 Teşhis dosyasını indir" for b in at.get("download_button"))
    # Editör: "yukarıdaki token tüm işlemlerin mi?" — üç adım ayrı gösterilir, toplam en üstte.
    total = next(m.value for m in at.markdown if "Bu haberin yapay zekâ maliyeti" in m.value)
    assert "(eksik)" in total  # bu testin haberinde metin maliyeti kayıtlı değil (eski proje gibi)
    assert any("sahne seçimi" in c.value and "haber metni —" in c.value for c in at.caption)
    assert any("yalnız bu adımın" in m.value for m in at.markdown)


def test_tablet_session_survives_a_disconnect_and_idle_page_stays_quiet():
    """Editör (v3.7.1): "sayfa inaktifken kendini mi yeniliyor?" Tablette ekran kapanınca bağlantı kopar; Streamlit
    kopan oturumu 2 dk saklıyordu, dönünce sayfa sıfırlanıyordu → 3 saat. Boştaki sayfada kendiliğinden yenilenen
    parçalar (güncelleme satırı, önbellek sayacı) en sık 2 dk'da bir."""
    import re
    import tomllib

    from apps.axion_local import update_check

    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["server"]["disconnectedSessionTTL"] >= 3 * 3600
    assert update_check.REFRESH_SECONDS >= 120
    source = (ROOT / "apps" / "news_studio" / "page.py").read_text(encoding="utf-8")
    assert all(int(n) >= 120 for n in re.findall(r"run_every=(\d+)\)", source))
