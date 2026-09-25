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


@pytest.fixture
def local_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))
    inbox = tmp_path / "Downloads"
    inbox.mkdir()
    (inbox / "dha_kaza.mp4").write_bytes(b"video")
    monkeypatch.setenv("AXION_INBOX_DIR", str(inbox))
    monkeypatch.setattr(
        "apps.video_studio.modules.audio_ingestion.probe_audio",
        lambda path: {"filename": Path(path).name, "duration_seconds": 24.2, "duration_formatted": "00:24", "file_size_bytes": 3},
    )
    return tmp_path


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
    button(at, "Sadece kaydet").click().run()
    button(at, "Sadece kaydet").click().run()
    assert len(store.list_news_projects()) == 1


def test_headline_regeneration_cost_is_counted(local_env, monkeypatch):
    from types import SimpleNamespace

    usage = {"input_tokens": 50, "output_tokens": 10, "requests": 1, "provider": "OpenAI", "model": "gpt-5.6-luna"}
    monkeypatch.setattr("apps.news_studio.ai.clients.regenerate_headlines",
                        lambda *args: (SimpleNamespace(baslik1="YENİ 1", baslik2="YENİ 2"), usage))
    at = with_generated_news(start())
    at.session_state["last_usage"] = {"input_tokens": 1000, "output_tokens": 300, "requests": 1}
    at.run()
    button(at, "↻ Başlıkları yeniden üret").click().run()
    assert not at.exception
    assert (at.session_state["baslik1"], at.session_state["baslik2"]) == ("YENİ 1", "YENİ 2")
    total = at.session_state["last_usage"]
    assert (total["input_tokens"], total["output_tokens"], total["requests"]) == (1050, 310, 2)


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
    assert not at.code  # paylaşım metni burada yok (yalnızca video tasarımı)

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
    at.slider(key="kesit_range").set_value((3.0, 8.5)).run()
    at.segmented_control(key="kesit_placement").set_value("after").run()
    button(at, "➕ Kesiti ekle").click().run()
    assert not at.exception
    from apps.video_studio.modules.soundbites import SOUNDBITES_FILENAME

    assert store.load_project_json(project, SOUNDBITES_FILENAME) == [
        {"path": str(video), "filename": "roportaj.mp4", "start_s": 3.0, "end_s": 8.5, "placement": "after"}
    ]


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


BROWSER_PAGE = "apps/remote_browser/page.py"


class FakeBrowser:
    closed = False

    def __init__(self):
        from apps.remote_browser.service import Screen

        self.calls = []
        self.screen_value = Screen(b"\xff\xd8jpeg", "about:blank", "", 1)

    def run(self, action, value=None):
        self.calls.append((action, value))

    def screen(self):
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


def test_browser_page_opens_home_page_and_remembers_it(local_env, monkeypatch):
    from apps.axion_local.preferences import load_preferences

    fake = FakeBrowser()
    monkeypatch.setattr("apps.remote_browser.service.find_browser", lambda configured=None: Path("/brave"))
    monkeypatch.setattr("apps.remote_browser.service.shared", lambda executable, profile, inbox, logins=None: fake)
    at = start()
    at.switch_page(BROWSER_PAGE).run()
    assert not at.exception
    assert fake.calls == [("goto", "https://www.dha.com.tr")]  # boş sekme: ana sayfa açılır
    at.sidebar.text_input(key="tarayici_ana_sayfa").set_value("panel.dha.com.tr").run()
    assert load_preferences()["tarayici_ana_sayfa"] == "panel.dha.com.tr"
    assert fake.calls == [("goto", "https://www.dha.com.tr")]  # bir kez


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
    ]
    assert apply_events(fake, events, "gizli", "dha.com.tr") == 6
    assert fake.calls == [
        ("click", (1023.0, 0.0)), ("wheel", (10.0, 10.0, 6000.0)), ("type", "ş" * 2000), ("key", "Enter"),
        ("fill_login", None), ("type", "gizli"), ("goto", "dha.com.tr"),
    ]  # 🔑: önce kayıtlı giriş, yoksa DHA_SIFRE
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
    jobs.cancel(project)  # Video Stüdyosu kurguyu yeniden üretirken
    job = jobs.get(project)
    assert not job.running and job.cancelled and not job.error
    assert not (project.folder / store.FINAL_VIDEO_FILENAME).exists()
