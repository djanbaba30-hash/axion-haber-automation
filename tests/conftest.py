"""Ortak test hazırlığı."""

from pathlib import Path

import pytest


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


@pytest.fixture(autouse=True)
def no_update_check(monkeypatch):
    """Testlerde repodaki sürüm sorulmaz (ağ yok, sonuç değişken); güncelleme göstergesi kendi testinde."""
    from apps.axion_local import update_check

    monkeypatch.setattr(update_check, "status", lambda now=None: None)



@pytest.fixture(autouse=True)
def no_luna_edit_calls(monkeypatch):
    """Testlerde sahne seçimi için gerçek Luna çağrısı yapılmaz (kurallara düşülür); Luna kurgusu kendi testinde."""
    def offline(*args, **kwargs):
        raise RuntimeError("testte Luna yok")

    monkeypatch.setattr("apps.video_studio.modules.luna_edit.request", offline)
