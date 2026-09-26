"""v4.0.0-alpha.7: yerel yazıya dökme (faster-whisper; testte sahte model — gerçek model editörün bilgisayarında iner)."""

import time
from types import SimpleNamespace

import numpy as np
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
    assert "hotwords" not in call  # özel adlar modele gitmez (alpha.7.1'de işe yaramadı); yazımı fix_names düzeltir
    assert [s["metin"] for s in result["cumleler"]] == ["Geçtiğimiz günlerde müşterimiz yemek yerken boğazına yemek kaçtı.",
                                                         "Ben de durumu hemen fark ettim.",
                                                         "Daha önce eğitimini aldığım Heimlich manevrasını uyguladım."]
    first = result["cumleler"][0]
    assert first["bas"] == 42.0  # ilk kelimeden 0,1 sn önce
    assert first["son"] <= 47.0 - transcribe.NEXT_WORD_MARGIN  # sonraki cümlenin ilk kelimesine taşmaz
    assert shares[-1] == pytest.approx(56.9 / 70.7) and result["video_sn"] == 70.7 and result["surum"] == 4
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


# Editörün Artvin dökümü (alpha.7.2, ekran görüntüsü): Whisper noktasız yazdı, cümle başlarını büyük harfle ("Ben",
# "Beyefendiye", "Sonra", "Kendisine"); "yanıma [doğru koştu]" 53,7'de bitti ama ses 54,1'e kadar sürüyor.
ARTVIN = [(43.0, 44.4, "Geçtiğimiz günlerde"), (44.6, 45.8, "bir vatandaşımız"), (46.1, 47.4, "müşterimiz burada kendisi"),
          (47.7, 53.7, "yemek yerken bazına yemek kaçması sonucu nefes almakta güçlük çekerek yanıma"),
          (54.6, 55.9, "Ben de durumu hemen"), (56.2, 57.4, "fark ettim"), (58.0, 58.5, "Beyefendiye"),
          (58.7, 60.1, "daha öncesinden eğitimini almış"), (60.4, 61.7, "olduğum Hemlik manevrasını uyguladım"),
          (62.0, 63.5, "Sonra kendisi"), (63.8, 66.0, "tekrardan nefes almaya başladı rahatladı"),
          (66.3, 67.8, "Kendisine çayını içirdik"), (68.0, 68.7, "Uğurladık"), (68.9, 70.6, "Kendisi teşekkür etti bize")]
ARTVIN_NEWS = ("Restoran sahibi Muzaffer Yazıcı, Heimlich manevrasıyla kurtardı. Olay Hopa'da oldu. Yazıcı, \"Ben de "
               "durumu hemen fark ettim. Beyefendiye Heimlich manevrasını uyguladım\" dedi.")


def artvin_words():
    words = []
    for start, end, text in ARTVIN:
        tokens = text.split()
        step = (end - start) / len(tokens)
        words += [(round(start + i * step, 2), round(start + (i + 0.85) * step, 2), " " + token)
                  for i, token in enumerate(tokens)]
    return words


def artvin_levels():
    """Ses seviyesi (dB, 0,02 sn): konuşma -27, sessizlik -50; "yanıma doğru koştu" 54,1'de biter, "Ben de" 55,0'da."""
    level = np.full(round(70.76 / transcribe.LEVEL_STEP), -50.0)
    for start, end in [(43.0, 54.1), (55.0, 70.5)]:
        level[round(start / transcribe.LEVEL_STEP):round(end / transcribe.LEVEL_STEP)] = -27.0
    return level


def test_artvin_interview_splits_where_the_editor_did():
    """Editör kesitleri elle şöyle seçti (düzeltme kaydı): 44,7–54,5 "…yanıma doğru koştu", 55,0–57,6 "Ben de durumu
    hemen fark ettim", 58,0–62,2 "Beyefendiye … uyguladım". Büyük harf yeni cümle, "Heimlich" (haberde özel ad) değil;
    kısa "Uğurladık" öncekine katılır."""
    names = transcribe.hints(ARTVIN_NEWS)
    lines = transcribe.sentences(transcribe.fix_names(artvin_words(), names), 70.76, names, artvin_levels())
    texts = [line["metin"] for line in lines]
    assert texts[-5:] == ["Ben de durumu hemen fark ettim",
                          "Beyefendiye daha öncesinden eğitimini almış olduğum Heimlich manevrasını uyguladım",
                          "Sonra kendisi tekrardan nefes almaya başladı rahatladı",
                          "Kendisine çayını içirdik Uğurladık", "Kendisi teşekkür etti bize"]
    assert " ".join(texts[:-5]).endswith("güçlük çekerek yanıma") and len(texts[:-5]) == 2  # 10,7 sn: ikiye bölünür
    assert all(line["son"] - line["bas"] <= transcribe.MAX_SENTENCE + 0.5 for line in lines)
    run_up = lines[len(texts) - 6]
    assert 54.1 <= run_up["son"] <= 54.6 - transcribe.NEXT_WORD_MARGIN  # ses 54,1'e kadar: "doğru koştu" kesilmez
    assert lines[-5]["bas"] == 54.5 and lines[-4]["bas"] == 57.9


def test_long_run_without_capitals_is_split_after_a_verb():
    """Büyük harf ve noktası olmayan uzun konuşma: 8 sn'den uzunsa fiil sonunda ("koştu") bölünür."""
    text = ("müşterimiz yemek yerken boğazına yemek kaçtı ben de hemen fark ettim yanına koştum daha önce eğitimini "
            "aldığım manevrayı uyguladım yemek çıktı müşterimiz rahatladı").split()
    words = [(40 + i * 0.6, 40 + i * 0.6 + 0.55, " " + token) for i, token in enumerate(text)]
    lines = transcribe.sentences(words, 70.7)
    assert all(line["metin"].split()[-1] in ("kaçtı", "ettim", "koştum", "uyguladım", "rahatladı") for line in lines)
    assert all(line["son"] - line["bas"] <= transcribe.MAX_SENTENCE + 0.4 for line in lines) and len(lines) >= 2


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


def test_two_devices_starting_at_once_get_one_job(tmp_path):
    """GPT V4-G2: aynı haber iki cihazda açıkken iki oturum aynı anda başlatırsa tek iş (kilitli)."""
    import threading

    class Slow(FakeWhisper):
        def transcribe(self, audio, **kwargs):
            time.sleep(0.3)
            return super().transcribe(audio, **kwargs)

    source, jobs, gate = video(tmp_path), [], threading.Barrier(8)

    def begin():
        gate.wait()
        jobs.append(transcribe.start(source, tmp_path / "proje", Slow(SEGMENTS)))

    workers = [threading.Thread(target=begin) for _ in range(8)]
    [w.start() for w in workers]
    [w.join(5) for w in workers]
    assert len({id(job) for job in jobs}) == 1
    jobs[0].thread.join(5)


def test_same_size_file_changed_within_the_same_second_is_transcribed_again(tmp_path):
    """GPT V4-G3: anahtar değişiklik zamanını nanosaniyeyle alır."""
    import os

    source = video(tmp_path, data=b"aaaa")
    os.utime(source, ns=(1_000_000_000_100, 1_000_000_000_100))
    first = transcribe._key(source)
    source.write_bytes(b"bbbb")
    os.utime(source, ns=(1_000_000_000_900, 1_000_000_000_900))
    assert transcribe._key(source) != first


def test_quote_in_the_news_is_found_in_the_artvin_transcript():
    """v4.1.0-alpha.2: DHA metnindeki alıntı ("Ben de durumu hemen fark ettim. Beyefendiye Heimlich manevrasını
    uyguladım") dökümdeki iki cümleye oturur (editörün elle seçtiği 55,0–62,2 ile aynı cümleler); haberde olmayan söz
    ve kısa tırnak öneri üretmez."""
    from apps.video_studio.modules import quotes

    names = transcribe.hints(ARTVIN_NEWS)
    lines = transcribe.sentences(transcribe.fix_names(artvin_words(), names), 70.76, names, artvin_levels())
    [found] = quotes.suggestions(ARTVIN_NEWS, lines)
    assert (found["bas"], found["bitis"]) == (lines[-5]["bas"], lines[-4]["son"])
    assert lines[-5]["metin"].startswith("Ben de") and lines[-4]["metin"].endswith("uyguladım")
    other = ('Olay "Heimlich" diye anıldı. Muhtar, "Mahallede böyle bir olay hiç yaşanmadı, çok şaşırdık" dedi. '
             'Yazıcı "Kendisine çayını içirdik, uğurladık" dedi. Kapanmayan "tırnak burada kalır ve alıntı sayılmaz')
    assert quotes.extract(other) == ["Mahallede böyle bir olay hiç yaşanmadı, çok şaşırdık",
                                     "Kendisine çayını içirdik, uğurladık"]
    assert [q["alinti"] for q in quotes.suggestions(other, lines)] == ["Kendisine çayını içirdik, uğurladık"]
