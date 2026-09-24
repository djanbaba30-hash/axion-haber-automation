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
    at = start()
    at.switch_page(VIDEO_PAGE).run()
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


def test_render_button_creates_video_with_chosen_framing(local_env, monkeypatch):
    rendered = []

    def fake_render(edit_project, media_library, output):
        rendered.append({c["framing"]["mode"] for t in edit_project["edit_plan"]["timeline"]["tracks"] for c in t["clips"] if t["kind"] == "video"})
        output.write_bytes(b"mp4")
        return "x264 (işlemci)"

    monkeypatch.setattr("apps.video_studio.modules.render.render_rough_cut", fake_render)
    project = saved_project(media_library([{
        "shot_id": "video_001_shot_001", "asset_id": "video_001", "shot_number": 1,
        "start_seconds": 0.0, "end_seconds": 30.0, "duration_seconds": 30.0,
        "visual": {"description": "Kaza", "visual_type": "event", "editorial_role": "establishing"},
    }]))
    at = start()
    at.switch_page(VIDEO_PAGE).run()
    at.segmented_control(key="framing").set_value("Tüm kare").run()
    button(at, "🎬 Videoyu oluştur").click().run()
    assert not at.exception
    assert rendered == [{"fit_blur"}]
    assert (project.folder / store.ROUGH_CUT_FILENAME).exists()
    assert any(b.label == "Videoyu yeniden oluştur" for b in at.button)
    from apps.axion_local.preferences import load_preferences
    assert load_preferences()["framing"] == "Tüm kare"


def test_outdated_media_analysis_asks_for_reanalysis(local_env):
    saved_project({"assets": [{"asset_type": "video", "source": {"filename": "dha.mp4"}, "shots": []}]})
    at = start()
    at.switch_page(VIDEO_PAGE).run()
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
    saved_project(media_library())
    at = start()
    at.switch_page(VIDEO_PAGE).run()
    assert not at.exception
    assert not at.text_area
    assert any(e.label == "✅ 2. Görüntüler — dha.mp4" for e in at.expander)


def test_design_studio_shows_video_and_headlines(local_env):
    project = saved_project(media_library())
    (project.folder / store.ROUGH_CUT_FILENAME).write_bytes(b"mp4")
    at = start()
    at.switch_page(DESIGN_PAGE).run()
    assert not at.exception
    assert title(at) == ["Tasarım Stüdyosu"]
    assert [c.value for c in at.code][:2] == ["KAZA", "B"]
    assert any(b.label == "MP4'ü indir" for b in at.get("download_button"))


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
    at = start()
    at.switch_page(VIDEO_PAGE).run()
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
    at = start()
    at.switch_page(VIDEO_PAGE).run()
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
