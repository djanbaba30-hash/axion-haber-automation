"""v4.0.0-alpha.5: düzeltmelerden öğrenme kaydı (data/duzeltmeler.jsonl; silinmez, internete gitmez)."""

import json

import pytest

from apps.axion_local import corrections


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    return tmp_path


MODEL = {"baslik1": "A", "baslik2": "B", "icerik": "Metin", "tts": "Ses"}


def test_news_records_only_changed_fields_and_keeps_the_last_save():
    corrections.news("p1", MODEL, {**MODEL, "tts": "Ses düzeltildi "}, "ham" * 1000, {"model": "m"})
    [entry] = corrections.entries()
    assert entry["degisen"] == {"tts": {"model": "Ses", "editor": "Ses düzeltildi "}}
    assert entry["degismeyen"] == ["baslik1", "baslik2", "icerik"] and len(entry["ham_haber"]) == corrections.RAW_CHARS
    corrections.news("p1", MODEL, {**MODEL, "baslik1": "A2"}, "ham", {})
    corrections.news("p2", MODEL, dict(MODEL), "ham", {})  # hiç değişmeyen de yazılır (kalite oranı)
    rows = corrections.entries()
    assert [(e["proje"], list(e["degisen"])) for e in rows] == [("p1", ["baslik1"]), ("p2", [])]


def test_without_model_output_nothing_is_recorded():
    corrections.news("p1", None, MODEL, "ham", {})
    assert corrections.entries() == []


def test_scene_and_soundbite_rows(data_dir):
    corrections.scene("p1", 3, "yaralılar", {"aciklama": "ambulans", "secen": "llm"}, {"aciklama": "hasarlı araç"})
    corrections.scene("p1", 3, "yaralılar", {"aciklama": "ambulans", "secen": "llm"}, {"aciklama": "polis"})
    corrections.soundbite("p1", "dha.mp4", (10.0, 15.0), (10.1, 15.2), "before")
    corrections.soundbite("p1", "dha.mp4", (10.0, 15.0), (20.0, 26.0), "after")
    corrections.soundbite("p1", "dha.mp4", None, (30.0, 32.0), "after")
    rows = corrections.entries()
    assert [e["yeni"]["aciklama"] for e in rows if e["tur"] == "sahne"] == ["polis"]  # aynı sahne: son seçim
    assert [e["degisti"] for e in rows if e["tur"] == "kesit"] == [False, True, True]
    (data_dir / corrections.FILENAME).write_text(
        (data_dir / corrections.FILENAME).read_text(encoding="utf-8") + '{"yarım', encoding="utf-8")
    assert len(corrections.entries()) == 4  # bozuk satır atlanır
    assert corrections.summary() == ("Düzeltme kaydı: 0 haber (1. başlık 0, 2. başlık 0, paylaşım metni 0, seslendirme 0 "
                                     "kez düzeltildi) · 1 sahne değişikliği · 3 kesit (2 aralığı değiştirildi)")
    assert json.loads(corrections.export().splitlines()[0])["tur"] == "sahne"


def test_empty_log_and_write_errors_do_not_break_work(data_dir, monkeypatch):
    assert corrections.summary() == "Düzeltme kaydı boş." and corrections.export() == b""
    (data_dir / "dosya").write_text("klasör değil")
    monkeypatch.setattr(corrections, "_path", lambda: data_dir / "dosya" / corrections.FILENAME)
    corrections.news("p1", MODEL, MODEL, "ham", {})  # yazılamasa da hata vermez (editörün kaydı sürer)
