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
        return (segment(*part) for part in self.segments), SimpleNamespace(duration=self.duration)


def segment(start, end, text):
    """Whisper bölümü: kelimeler bölüme eşit dağılır (" kelime" biçiminde, Whisper gibi)."""
    tokens = text.split()
    step = (end - start) / max(1, len(tokens))
    words = [SimpleNamespace(start=start + i * step, end=start + (i + 0.8) * step, word=" " + token)
             for i, token in enumerate(tokens)]
    return SimpleNamespace(start=start, end=end, text=text, words=words)


SEGMENTS = [(42.1, 46.8, " Geçtiğimiz günlerde müşterimiz yemek yerken boğazına yemek kaçtı."),
            (47.0, 50.2, " Ben de durumu hemen fark ettim."), (50.5, 51.0, "  "),
            (51.3, 56.9, " Daha önce eğitimini aldığım Hemlik manevrasını uyguladım.")]


def video(tmp_path, name="1524777.mp4", data=b"mp4"):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_transcript_is_saved_turkish_with_vad_word_times_and_reused(tmp_path):
    source, model, shares = video(tmp_path), FakeWhisper(SEGMENTS), []
    news = "Restoran sahibi Muzaffer Yazıcı, Heimlich manevrasıyla kurtardı. Olay Hopa'da oldu."
    result = transcribe.transcribe(source, tmp_path / "proje", shares.append, model, news)
    call = model.calls[0]
    assert call["language"] == "tr" and call["vad_filter"] is True and call["word_timestamps"] is True
    assert call["hotwords"] == "Muzaffer Yazıcı Heimlich Hopa"  # özel adlar ipucu (cümle başı "Restoran", "Olay" değil)
    assert [s["metin"] for s in result["cumleler"]] == ["Geçtiğimiz günlerde müşterimiz yemek yerken boğazına yemek kaçtı.",
                                                         "Ben de durumu hemen fark ettim.",
                                                         "Daha önce eğitimini aldığım Heimlich manevrasını uyguladım."]
    first = result["cumleler"][0]
    assert first["bas"] == 42.0  # ilk kelimeden 0,1 sn önce
    assert first["son"] <= 47.0 - transcribe.NEXT_WORD_MARGIN  # sonraki cümlenin ilk kelimesine taşmaz
    assert shares[-1] == pytest.approx(56.9 / 70.7) and result["video_sn"] == 70.7 and result["surum"] == 3
    assert transcribe.load(tmp_path / "proje", source) == result
    source.write_bytes(b"baska video")  # dosya değişti: eski döküm kullanılmaz
    assert transcribe.load(tmp_path / "proje", source) is None


def test_sentences_split_on_punctuation_and_silence_with_padding():
    words = [(1.0, 1.4, " Evet,"), (1.5, 2.0, " çok"), (2.1, 2.6, " korktuk."), (2.7, 3.2, " Polis"), (3.3, 3.9, " geldi"),
             (6.0, 6.5, " Allah'tan"), (6.6, 7.0, " ölen"), (7.1, 7.4, " yok")]
    lines = transcribe.sentences(words, 8.0)
    assert [line["metin"] for line in lines] == ["Evet, çok korktuk.", "Polis geldi", "Allah'tan ölen yok"]
    assert lines[0] == {"bas": 0.9, "son": 2.62, "metin": "Evet, çok korktuk."}  # sonraki kelime 2,7'de: 2,62'de biter
    assert lines[1]["son"] == 4.15 and lines[2]["son"] == 7.65  # sessizlik varsa tam pay (0,25 sn)
    assert transcribe.sentences([(7.9, 8.4, " son")], 8.0)[0]["son"] == 8.0  # videonun sonunu geçmez


def test_unpunctuated_speech_is_split_at_breaths_into_short_parts():
    """Editör (alpha.7.1): Artvin röportajı noktasız döküldü, iki upuzun cümle (14 sn) oldu. 7 sn'den uzun parça en uzun
    nefes arasından (virgül öne alınır) bölünür; parçalar en az 1,5 sn."""
    text = ("müşterimiz yemek yerken boğazına yemek kaçtı ben de hemen fark ettim yanına koştum, daha önce eğitimini "
            "aldığım manevrayı uyguladım yemek çıktı müşterimiz rahatladı").split()
    words, time = [], 42.9
    for number, token in enumerate(text):
        pause = {10: 0.5, 12: 0.1, 18: 0.4}.get(number, 0.05)  # "ettim", "koştum," ve "uyguladım" sonrası nefes
        words.append((time, time + 0.55, " " + token))
        time += 0.55 + pause
    lines = transcribe.sentences(words, 70.7)
    assert [line["metin"] for line in lines] == [
        "müşterimiz yemek yerken boğazına yemek kaçtı ben de hemen fark ettim",
        "yanına koştum, daha önce eğitimini aldığım manevrayı uyguladım",  # "yanına koştum," tek başına çok kısa
        "yemek çıktı müşterimiz rahatladı"]
    assert all(line["son"] - line["bas"] <= transcribe.MAX_SENTENCE + 0.4 for line in lines)


def test_names_from_the_news_fix_misheard_words_only():
    names = transcribe.hints("Hopa'da restoran işleten Muzaffer Yazıcı, Heimlich manevrası yaptı. Artvin'de.")
    words = [(0, 1, " Hemlik'in,"), (1, 2, " muzafer"), (2, 3, " yazıcı"), (3, 4, " Artvinli"), (4, 5, " hemen")]
    assert [w[2] for w in transcribe.fix_names(words, names + " Yılmaz")] == [
        " Heimlich'in,", " Muzaffer", " yazıcı", " Artvinli", " hemen"]
    assert transcribe.fix_names([(0, 1, " yılma")], "Yılmaz")[0][2] == " yılma"  # adın başı olan kelime değişmez


def test_hallucinated_subtitle_credits_and_words_after_the_end_are_dropped(tmp_path):
    model = FakeWhisper([(66.9, 69.2, " Kendisine çayını içirdik, uğurladık."), (70.5, 100.5, " Altyazı M.K."),
                         (60.0, 61.0, " İzlediğiniz için teşekkürler.")], duration=70.7)
    result = transcribe.transcribe(video(tmp_path), tmp_path / "proje", model=model)
    assert [s["metin"] for s in result["cumleler"]] == ["Kendisine çayını içirdik, uğurladık."]


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
