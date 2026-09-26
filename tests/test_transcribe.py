"""v4.0.0-alpha.7: yerel yazıya dökme (faster-whisper; testte sahte model — gerçek model editörün bilgisayarında iner)."""

import time
from types import SimpleNamespace

import pytest

from apps.video_studio.modules import transcribe


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path / "data"))


class FakeWhisper:
    """faster-whisper `WhisperModel.transcribe` taklidi: (segment üreteci, bilgi)."""

    def __init__(self, segments, duration=70.7, fail=False):
        self.segments, self.duration, self.fail, self.calls = segments, duration, fail, []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("model inemedi")
        parts = (SimpleNamespace(start=s, end=e, text=t) for s, e, t in self.segments)
        return parts, SimpleNamespace(duration=self.duration)


SEGMENTS = [(42.1, 46.8, " Geçtiğimiz günlerde müşterimiz yemek yerken boğazına yemek kaçtı."),
            (47.0, 50.2, " Ben de durumu hemen fark ettim."), (50.5, 51.0, "  "),
            (51.3, 58.9, " Daha önce eğitimini aldığım Heimlich manevrasını uyguladım.")]


def video(tmp_path, name="1524777.mp4", data=b"mp4"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_transcript_is_saved_turkish_with_vad_and_reused(tmp_path):
    source, model, shares = video(tmp_path), FakeWhisper(SEGMENTS), []
    result = transcribe.transcribe(source, tmp_path / "proje", shares.append, model)
    assert model.calls[0]["language"] == "tr" and model.calls[0]["vad_filter"] is True
    assert [s["metin"] for s in result["cumleler"]] == ["Geçtiğimiz günlerde müşterimiz yemek yerken boğazına yemek kaçtı.",
                                                         "Ben de durumu hemen fark ettim.",
                                                         "Daha önce eğitimini aldığım Heimlich manevrasını uyguladım."]
    assert result["cumleler"][0] == {"bas": 42.1, "son": 46.8, "metin": result["cumleler"][0]["metin"]}
    assert shares[-1] == pytest.approx(58.9 / 70.7) and result["video_sn"] == 70.7 and result["model"] == transcribe.MODEL
    assert transcribe.load(tmp_path / "proje", source) == result
    source.write_bytes(b"baska video")  # dosya değişti: eski döküm kullanılmaz
    assert transcribe.load(tmp_path / "proje", source) is None


def test_background_job_reports_progress_and_errors(tmp_path):
    source = video(tmp_path)
    job = transcribe.start(source, tmp_path / "proje", FakeWhisper(SEGMENTS))
    job.thread.join(5)
    assert job.done and job.error is None and transcribe.load(tmp_path / "proje", source)
    assert transcribe.job(source, tmp_path / "proje") is job
    other = video(tmp_path, "bozuk.mp4")
    failed = transcribe.start(other, tmp_path / "proje", FakeWhisper(SEGMENTS, fail=True))
    failed.thread.join(5)
    assert failed.done and failed.error == "model inemedi" and transcribe.load(tmp_path / "proje", other) is None


def test_span_between_two_sentences_in_any_order():
    lines = [{"bas": 1.0, "son": 2.0}, {"bas": 3.0, "son": 4.5}, {"bas": 5.0, "son": 7.0}]
    assert transcribe.span(lines, 2, 0) == (1.0, 7.0) and transcribe.span(lines, 1, 1) == (3.0, 4.5)


def test_model_is_downloaded_once_into_data_folder(tmp_path, monkeypatch):
    assert transcribe.available() and not transcribe.model_ready()
    folder = tmp_path / "data" / "modeller" / "models--x" / "snapshots" / "1"
    folder.mkdir(parents=True)
    (folder / "model.bin").write_bytes(b"0")
    assert transcribe.model_ready()
    made = []
    monkeypatch.setattr("faster_whisper.WhisperModel", lambda *a, **k: made.append((a, k)) or FakeWhisper([]))
    transcribe._MODELS.clear()
    transcribe._load_model()
    transcribe._load_model()
    assert len(made) == 1 and made[0][0] == ("large-v3-turbo",)
    assert made[0][1] == {"device": "cpu", "compute_type": "int8", "download_root": str(tmp_path / "data" / "modeller")}
    transcribe._MODELS.clear()


def test_long_running_job_is_not_started_twice(tmp_path):
    class Slow(FakeWhisper):
        def transcribe(self, audio, **kwargs):
            time.sleep(0.3)
            return super().transcribe(audio, **kwargs)

    source = video(tmp_path)
    first = transcribe.start(source, tmp_path / "proje", Slow(SEGMENTS))
    assert transcribe.start(source, tmp_path / "proje", Slow(SEGMENTS)) is first
    first.thread.join(5)
