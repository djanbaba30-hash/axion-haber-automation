from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SECRETS = {
    "APP_PASSWORD": "Gizli-Şifre1",
    "OPENAI_API_KEY": "sk-test",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "ELEVENLABS_API_KEY": "el-test",
}


@pytest.fixture
def local_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_LOCAL", "1")
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))
    inbox = tmp_path / "Downloads"
    inbox.mkdir()
    (inbox / "dha_kaza.mp4").write_bytes(b"video")
    monkeypatch.setenv("AXION_INBOX_DIR", str(inbox))
    return tmp_path


def login():
    at = AppTest.from_file(str(ROOT / "axion_local.py"), default_timeout=120)
    for key, value in SECRETS.items():
        at.secrets[key] = value
    at.run()
    return at


def button(at, label):
    return next(b for b in at.button if b.label == label)


def test_single_password_opens_both_pages(local_env):
    at = login()
    assert [t.label for t in at.text_input] == ["Şifre"]
    at.text_input[0].input("yanlis").run()
    assert [e.value for e in at.error] == ["Şifre yanlış."]
    at.text_input[0].input("Gizli-Şifre1").run()
    assert not at.exception
    assert [t.value for t in at.title] == ["Axion Haber İçerik Stüdyosu"]
    at.switch_page("apps/video_studio/app.py").run()
    assert not at.exception
    assert [t.value for t in at.title] == ["Axion Video Studio"]


def test_news_project_flows_to_video_studio(local_env):
    at = login()
    at.text_input[0].input("Gizli-Şifre1").run()

    at.session_state["baslik1"] = "SAVRULAN OTOMOBİL BERBER DÜKKÂNINA ÇARPTI"
    at.session_state["baslik2"] = "5 KİŞİ YARALANDI"
    at.session_state["icerik"] = "Bayrampaşa'da savrulan otomobil berber dükkânına çarptı."
    at.session_state["tts_metni"] = "Bayrampaşa'da savrulan otomobil berber dükkânına çarptı."
    at.session_state["last_audio_bytes"] = b"mp3"
    at.session_state["last_audio_text"] = "Bayrampaşa'da savrulan otomobil berber dükkânına çarptı."
    at.run()
    button(at, "Projeye kaydet (Video Studio'da kullan)").click().run()
    assert any("Proje kaydedildi" in s.value for s in at.success)
    assert len(list((local_env / "data" / "projects").iterdir())) == 1

    at.switch_page("apps/video_studio/app.py").run()
    assert "dha_kaza.mp4" in at.multiselect[0].options[0]
    at.session_state["media_library"] = {"assets": [{"asset_id": "video_001"}]}
    at.run()
    assert "SAVRULAN OTOMOBİL" in at.selectbox[-1].options[0]


def test_stale_audio_blocks_project_save(local_env):
    at = login()
    at.text_input[0].input("Gizli-Şifre1").run()
    at.session_state["icerik"] = "Caption"
    at.session_state["tts_metni"] = "Düzenlenmiş TTS"
    at.session_state["last_audio_bytes"] = b"mp3"
    at.session_state["last_audio_text"] = "Eski TTS"
    at.run()
    assert any("sesi yeniden üret" in w.value for w in at.warning)
    assert not any(b.label == "Projeye kaydet (Video Studio'da kullan)" for b in at.button)
