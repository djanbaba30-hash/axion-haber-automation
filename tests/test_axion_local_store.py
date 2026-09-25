import os
from datetime import datetime

import pytest

from apps.axion_local import store
from apps.video_studio.modules.local_media import LocalMediaFile
from apps.video_studio.modules.video_ingestion import save_uploaded_video
from shared.news_package import NewsPackage


def package(headline="SAVRULAN OTOMOBİL BERBER DÜKKÂNINA ÇARPTI"):
    return NewsPackage(headline_1=headline, headline_2="B", caption="Caption", tts_text="TTS")


def test_save_and_load_project_with_audio(tmp_path):
    folder = store.save_news_project(package(), b"mp3-bytes", base_dir=tmp_path, now=datetime(2026, 9, 24, 14, 5, 0))
    assert folder.name == "20260924-140500_savrulan-otomobil-berber-dukkanina"
    project = store.list_news_projects(tmp_path)[0]
    assert project.created_at == "24.09.2026 14:05"
    loaded, audio = store.load_news_project(project)
    assert loaded.tts_text == "TTS"
    assert audio.read_bytes() == b"mp3-bytes"
    assert len(loaded.metadata["audio_sha256"]) == 64


def test_project_without_audio(tmp_path):
    store.save_news_project(package(), None, base_dir=tmp_path)
    project = store.list_news_projects(tmp_path)[0]
    assert project.audio_path is None
    assert "ses yok" in project.label
    assert store.load_news_project(project)[1] is None


def test_mismatched_audio_is_rejected(tmp_path):
    store.save_news_project(package(), b"original", base_dir=tmp_path)
    project = store.list_news_projects(tmp_path)[0]
    project.audio_path.write_bytes(b"baska-ses")
    with pytest.raises(ValueError, match="eşleşmiyor"):
        store.load_news_project(project)


def test_projects_are_listed_newest_first_and_broken_ones_skipped(tmp_path):
    store.save_news_project(package("ESKI"), None, base_dir=tmp_path, now=datetime(2026, 1, 1))
    store.save_news_project(package("YENI"), None, base_dir=tmp_path, now=datetime(2026, 2, 1))
    (tmp_path / "bozuk").mkdir()
    (tmp_path / "bozuk" / store.PACKAGE_FILENAME).write_text("{bozuk", encoding="utf-8")
    assert [p.headline for p in store.list_news_projects(tmp_path)] == ["YENI", "ESKI"]


def test_missing_projects_dir_returns_empty(tmp_path):
    assert store.list_news_projects(tmp_path / "yok") == []


def test_inbox_lists_only_media_newest_first(tmp_path):
    old = tmp_path / "eski.mp4"; old.write_bytes(b"1")
    new = tmp_path / "yeni.MOV"; new.write_bytes(b"2")
    (tmp_path / "not.txt").write_text("x")
    (tmp_path / "klasor.mp4").mkdir()
    os.utime(old, (1_000, 1_000))
    assert store.list_inbox_media(tmp_path) == [new, old]


def test_inbox_missing_folder_returns_empty(tmp_path):
    assert store.list_inbox_media(tmp_path / "yok") == []


def test_env_overrides_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AXION_INBOX_DIR", str(tmp_path / "gelen"))
    assert store.projects_dir() == tmp_path / "data" / "projects"
    assert store.inbox_dir() == tmp_path / "gelen"


def test_local_video_is_used_in_place_without_copy(tmp_path):
    video = tmp_path / "dha.mp4"
    video.write_bytes(b"video")
    local = LocalMediaFile(video)
    assert (local.name, local.size, local.type) == ("dha.mp4", 5, "video/mp4")
    assert save_uploaded_video(local) == video


def test_local_file_rejects_unsupported_video_extension(tmp_path):
    other = tmp_path / "a.gif"
    other.write_bytes(b"x")
    with pytest.raises(ValueError):
        save_uploaded_video(LocalMediaFile(other))


def test_updating_project_keeps_media_and_drops_stale_edit_project(tmp_path):
    folder = store.save_news_project(package(), b"v1", base_dir=tmp_path)
    project = store.get_news_project(folder.name, base_dir=tmp_path)
    store.save_project_json(project, store.MEDIA_LIBRARY_FILENAME, {"assets": []})
    store.save_project_json(project, store.EDIT_PROJECT_FILENAME, {"old": True})
    (folder / store.FINAL_VIDEO_FILENAME).write_bytes(b"eski son video")

    same = store.save_news_project(package("YENİ BAŞLIK"), b"v2", folder=folder)
    assert not (folder / store.FINAL_VIDEO_FILENAME).exists()  # eski başlık/sesle üretilmişti
    assert same == folder
    project = store.get_news_project(folder.name, base_dir=tmp_path)
    loaded, audio = store.load_news_project(project)
    assert loaded.headline_1 == "YENİ BAŞLIK"
    assert audio.read_bytes() == b"v2"
    assert project.has_media and "medya hazır" in project.label
    assert store.load_project_json(project, store.EDIT_PROJECT_FILENAME) is None


def test_updating_project_without_audio_removes_old_audio(tmp_path):
    folder = store.save_news_project(package(), b"ses", base_dir=tmp_path)
    store.save_news_project(package(), None, folder=folder)
    project = store.get_news_project(folder.name, base_dir=tmp_path)
    assert project.audio_path is None
    assert "audio_sha256" not in store.load_news_project(project)[0].metadata


def test_get_missing_project_returns_none(tmp_path):
    assert store.get_news_project("yok", base_dir=tmp_path) is None


def test_corrupt_project_json_is_ignored(tmp_path):
    folder = store.save_news_project(package(), None, base_dir=tmp_path)
    (folder / store.MEDIA_LIBRARY_FILENAME).write_text("{bozuk", encoding="utf-8")
    project = store.get_news_project(folder.name, base_dir=tmp_path)
    assert store.load_project_json(project, store.MEDIA_LIBRARY_FILENAME) is None


def test_projects_older_than_three_days_are_deleted(tmp_path):
    from datetime import datetime

    now = datetime(2026, 9, 25, 10, 0)
    kept, dropped = [], []
    for when, bucket in [
        (datetime(2026, 9, 25, 9, 0), kept),      # bugün
        (datetime(2026, 9, 23, 2, 30), kept),     # 3. gün (önceki 2 gün)
        (datetime(2026, 9, 23, 1, 30), dropped),  # 3 günden eski (22'sinin iş günü)
        (datetime(2026, 9, 1, 12, 0), dropped),
    ]:
        bucket.append(store.save_news_project(package(f"HABER {when:%d %H%M}"), b"mp3", base_dir=tmp_path, now=when).name)
    (tmp_path / "baska_klasor").mkdir()  # proje olmayan klasöre dokunulmaz

    assert sorted(store.delete_old_projects(tmp_path, now=now)) == sorted(dropped)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(kept + ["baska_klasor"])


def test_old_history_rows_are_deleted(tmp_path):
    import sqlite3
    from datetime import datetime

    from apps.news_studio.integration.history import delete_runs_before

    db = tmp_path / "history.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE news_runs (id INTEGER PRIMARY KEY, created_at TEXT, tts TEXT)")
        con.executemany("INSERT INTO news_runs(created_at, tts) VALUES(?, ?)", [("2026-09-01 10:00:00", "eski"), ("2026-09-25 10:00:00", "yeni")])
    assert delete_runs_before(db, datetime(2026, 9, 23, 2, 0)) == 1
    with sqlite3.connect(db) as con:
        assert [row[0] for row in con.execute("SELECT tts FROM news_runs")] == ["yeni"]


def test_folder_that_cannot_be_deleted_is_logged_not_reported(tmp_path, monkeypatch, caplog):
    import logging
    from datetime import datetime

    old = store.save_news_project(package("ESKİ"), b"mp3", base_dir=tmp_path, now=datetime(2026, 9, 1, 12, 0))

    def locked(path, *args, **kwargs):
        raise PermissionError("dosya başka bir işlem tarafından kullanılıyor")

    monkeypatch.setattr(store.shutil, "rmtree", locked)
    with caplog.at_level(logging.WARNING):
        assert store.delete_old_projects(tmp_path, now=datetime(2026, 9, 25, 10, 0)) == []
    assert old.exists()
    assert "silinemedi" in caplog.text and old.name in caplog.text
