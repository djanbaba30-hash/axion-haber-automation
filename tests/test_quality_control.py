"""Kalite kontrolünü hızlandıran araçlar (API yok): kaynakta yok işaretleri, düzeltme farkı, okuyarak dinleme,
başlık önizlemesi; Haber Stüdyosu'nda uçtan uca."""

from __future__ import annotations

from datetime import date

from apps.news_studio.read_along import word_times
from apps.news_studio.validation.diff import changed_fields, word_diff_html
from apps.news_studio.validation.source_check import missing_numbers, unsupported
from tests.test_axion_local_app import button, start

RAW = ("Bursa'nın İnegöl ilçesinde 24.09.2026 günü saat 18.00'de kontrolden çıkan tır devrildi. Sürücü Ahmet Yılmaz (45) "
       "hafif yaralandı. Olay yerine AFAD ve itfaiye ekipleri sevk edildi. DHA")


def test_numbers_and_names_missing_from_source_are_marked():
    caption = ("Bursa'nın İnegöl ilçesinde tır devrildi. Sürücü Ahmet Yılmaz (45) ile Mehmet Kaya yaralandı, 3 kişi "
               "hastaneye kaldırıldı. Olay 24 Eylül'de yaşandı. AFAD ekipleri bölgede.")
    assert unsupported(caption, RAW) == ["3", "Mehmet", "Kaya"]
    # Seslendirmede okunuşa çevrilmiş saat/tarih kaynak sayılır (18.00 → akşam 6).
    assert unsupported("İnegöl'de akşam 6'da tır devrildi. Sürücü Ahmet Yılmaz yaralandı.", RAW) == []
    assert missing_numbers("TIR DEVRİLDİ, 5 YARALI", RAW) == ["5"]  # başlık: yalnız sayılar (hepsi büyük harf)
    assert unsupported("", RAW) == [] and unsupported("Metin 5", "") == []


def test_correction_diff_marks_removed_and_added_words():
    html = word_diff_html("TIR DEVRİLDİ 5 YARALI VAR", "KONTROLDEN ÇIKAN TIR DEVRİLDİ 5 YARALI")
    assert html == '<div class="fark"><ins>KONTROLDEN ÇIKAN</ins> TIR DEVRİLDİ 5 YARALI <del>VAR</del></div>'
    assert "&lt;b&gt;" in word_diff_html("a", "<b>")  # metin HTML olarak çalışmaz
    assert changed_fields({"a": "1", "b": "2"}, {"a": "1", "b": "3"}) == {"b": ("2", "3")}


def test_word_times_come_from_character_alignment():
    text = "Tır  devrildi."
    starts = [i * 0.1 for i in range(len(text))]
    words = word_times(list(text), starts, [s + 0.1 for s in starts])
    assert [w[0] for w in words] == ["Tır", "devrildi."]
    assert words[1][1] == 0.5 and round(words[1][2], 3) == 1.4


def test_news_studio_shows_quality_checks_end_to_end(local_env, monkeypatch):
    from apps.news_studio.models.news import NewsOutput

    first = NewsOutput(baslik1="TIR DEVRİLDİ VE ARDINDAN ÇOK UZUN BİR BAŞLIK OLARAK SÜRÜP GİTTİ", baslik2="5 YARALI",
                       icerik="Bursa'nın İnegöl ilçesinde tır devrildi. Sürücü Mehmet Kaya yaralandı." * 3,
                       tts_plani=["olay"], tts="İnegöl'de tır devrildi. Sürücü yaralandı.")
    fixed = first.model_copy(update={"baslik1": "KONTROLDEN ÇIKAN TIR DEVRİLDİ"})
    answers = iter([(first, {"input_tokens": 1}), (fixed, {"input_tokens": 1})])
    monkeypatch.setattr("apps.news_studio.ai.clients.generate", lambda *args, **kwargs: next(answers))
    at = start()
    at.session_state["raw_text"] = RAW
    at.run()
    button(at, "Haberi işle").click().run()
    assert not at.exception
    assert at.session_state["baslik1"] == "KONTROLDEN ÇIKAN TIR DEVRİLDİ"  # düzeltme çağrısı başlığı kısalttı
    assert list(at.session_state["last_correction_diff"]) == ["baslik1"]
    assert any(e.label == "🔁 Düzeltme çağrısı neyi değiştirdi" for e in at.expander)
    notes = [m.value for m in at.markdown if "Kaynakta yok" in m.value]
    assert any("[5]" in n for n in notes) and any("Mehmet" in n for n in notes)
    assert not any("videoda böyle görünür" in e.label for e in at.expander)  # v3.3: önizleme yok, satır yazısı yeter


def test_finished_video_is_announced_on_any_page_and_named_after_headline(local_env, monkeypatch):
    import time

    from apps.video_studio import jobs as video_jobs
    from tests.test_axion_local_app import media_library, saved_project

    project = saved_project(media_library())
    assert project.video_filename == f"{project.headline}.mp4"
    at = start()  # Haber Stüdyosu açık
    job = video_jobs.Job()
    job.finished = time.monotonic() + 1
    monkeypatch.setitem(video_jobs._JOBS, str(project.folder), job)
    at.run()
    assert [t.value for t in at.toast] == [f"«{project.headline}» videosu hazır ({job.elapsed:.0f} sn)."]
    at.run()
    assert not at.toast  # bir kez


def test_same_news_open_on_two_devices_is_warned(local_env, monkeypatch):
    from apps.axion_local import presence
    from tests.test_axion_local_app import media_library, saved_project

    project = saved_project(media_library())
    monkeypatch.setattr(presence, "_is_connected", lambda session_id: session_id == "tablet")
    monkeypatch.setitem(presence._OPEN, "tablet", project.id)       # tablette açık, hâlâ bağlı
    monkeypatch.setitem(presence._OPEN, "kapanmis", project.id)     # bağlantısı kopmuş eski oturum sayılmaz
    at = start()
    at.switch_page("apps/video_studio/page.py").run()
    at.selectbox(key="video_project_id").select(project.id).run()
    assert any("başka bir cihazda da açık" in w.value for w in at.warning)
    assert "kapanmis" not in presence._OPEN
    presence._OPEN.pop("tablet")
    at.run()
    assert not any("başka bir cihazda" in w.value for w in at.warning)


def test_step_timings_are_logged_locally(local_env):
    import json

    from apps.axion_local import metrics

    with metrics.timed("kurgu", "haber-1") as info:
        info["kodlayici"] = "x264"
    try:
        with metrics.timed("seslendirme", karakter=300):
            raise RuntimeError("ElevenLabs")
    except RuntimeError:
        pass
    lines = [json.loads(line) for line in metrics.path().read_text(encoding="utf-8").splitlines()]
    assert [(x["adim"], x["haber"], x.get("kodlayici"), x.get("hata")) for x in lines] == [
        ("kurgu", "haber-1", "x264", None), ("seslendirme", None, None, "RuntimeError")]


def test_headline_only_error_uses_the_small_headline_call(local_env, monkeypatch):
    """v3.3 token tasarrufu: yalnız başlık hatalıysa tam düzeltme (sistem + ham haber + tüm çıktı) yerine başlık çağrısı."""
    from types import SimpleNamespace

    from apps.news_studio.models.news import NewsOutput

    first = NewsOutput(baslik1="OTOMOBİL DURAĞA DALDI",
                       baslik2="KONTROLDEN ÇIKAN OTOMOBİL KALDIRIMDAKİ YAYALARA ÇARPIP DURAĞA DALDI",
                       icerik="Antalya'da kontrolden çıkan otomobil yayaya çarptı ve durağa daldı. " * 20,
                       tts_plani=["olay"], tts="Kontrolden çıkan otomobil yayaya çarptı ve durağa daldı. " * 7)
    calls = []
    monkeypatch.setattr("apps.news_studio.ai.clients.generate",
                        lambda *args, **kwargs: calls.append("haber") or (first, {"input_tokens": 3000}))

    def headlines(*args):
        calls.append(("başlık", args[-1]))
        return SimpleNamespace(baslik1="BAŞKA", baslik2="3 KİŞİ YARALANDI"), {"input_tokens": 400, "requests": 1}

    monkeypatch.setattr("apps.news_studio.ai.clients.regenerate_headlines", headlines)
    at = start()
    at.session_state["raw_text"] = RAW
    at.session_state["tts_duration"] = "Kısa (15-20 sn)"
    at.run()
    button(at, "Haberi işle").click().run()
    assert not at.exception
    assert calls[0] == "haber" and calls[1][0] == "başlık" and "2. başlık" in calls[1][1] and len(calls) == 2
    assert (at.session_state["baslik1"], at.session_state["baslik2"]) == ("OTOMOBİL DURAĞA DALDI", "3 KİŞİ YARALANDI")
    assert at.session_state["last_usage"]["input_tokens"] == 3400
