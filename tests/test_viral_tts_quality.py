from types import SimpleNamespace

from apps.news_studio.models.news import NewsOutput
from apps.news_studio.prompts.news import SYSTEM_PROMPT, build_correction_prompt, build_news_prompt
from apps.news_studio.validation.news import (
    find_tts_repetitions,
    normalize_tts_punctuation,
    remove_license_plates,
    validate_news_output,
)

# Bayrampaşa kaza haberinin 2026-09-24 testindeki gerçek çıktısı.
BAYRAMPASA_TTS = (
    "İstanbul Bayrampaşa’da iki otomobilin çarpışmasıyla savrulan araç, Kartaltepe Mahallesi "
    "Bilgehan Caddesi’nde kaldırımda bulunan 4 kişiye ve bir berber dükkânına çarptı. Kazada, "
    "aralarında temizlik görevlisinin de bulunduğu 5 kişi yaralandı; 2 yaralının durumunun ağır "
    "olduğu bildirildi. Araç, berber dükkânının camına çarparak durdu. 5 yaralı hastaneye "
    "kaldırıldı; sürücüler gözaltına alındı."
)
NON_REPETITIVE_TTS = (
    "İstanbul Bayrampaşa’da iki otomobilin çarpışması sonrası savrulan araç, kaldırımdaki 4 kişiye "
    "çarptıktan sonra bir berber dükkânına girdi. Kazada, aralarında bir temizlik görevlisinin de "
    "bulunduğu 5 kişi yaralandı; 2 kişinin durumunun ağır olduğu öğrenildi. Yaralılar hastaneye "
    "kaldırılırken, kazaya karışan sürücüler gözaltına alındı."
)
CAPTION = "x" * 1100


def output(tts, caption=CAPTION, b1="A", b2="B"):
    return SimpleNamespace(baslik1=b1, baslik2=b2, icerik=caption, tts=tts)


def test_repeated_event_and_number_are_flagged():
    warnings = find_tts_repetitions(normalize_tts_punctuation(BAYRAMPASA_TTS))
    assert len(warnings) == 2


def test_non_repetitive_tts_is_not_flagged():
    assert find_tts_repetitions(normalize_tts_punctuation(NON_REPETITIVE_TTS)) == []


def test_short_tts_is_warning_not_error_so_no_correction_call():
    check = validate_news_output(output(NON_REPETITIVE_TTS), "ham", 381, 396)
    assert check.errors == []
    assert any("hedefin altında" in w for w in check.warnings)


def test_far_too_short_tts_is_still_an_error():
    check = validate_news_output(output("Kısa metin."), "ham", 381, 396)
    assert any("çok kısa" in e for e in check.errors)


def test_too_long_tts_is_still_an_error():
    check = validate_news_output(output("a" * 500), "ham", 381, 396)
    assert any("üstünde" in e for e in check.errors)


def test_repetition_is_reported_as_warning():
    check = validate_news_output(output(BAYRAMPASA_TTS), "ham", 381, 396)
    assert check.errors == []
    assert sum("tekrarlıyor" in w for w in check.warnings) == 2


def test_semicolons_become_sentences():
    assert normalize_tts_punctuation("5 kişi yaralandı; sürücüler gözaltına alındı.") == (
        "5 kişi yaralandı. Sürücüler gözaltına alındı."
    )
    assert normalize_tts_punctuation("Araç devrildi; İstanbul’da") == "Araç devrildi. İstanbul’da"


def test_license_plate_is_removed_mid_sentence():
    text, removed = remove_license_plates(
        "Edinilen bilgilere göre, 34 FPR 116 plakalı otomobil ile başka bir otomobil çarpıştı."
    )
    assert removed
    assert text == "Edinilen bilgilere göre, otomobil ile başka bir otomobil çarpıştı."


def test_license_plate_is_removed_at_sentence_start():
    text, removed = remove_license_plates("Kaza oldu. 06 ABC 1234 plakalı kamyon devrildi.")
    assert (text, removed) == ("Kaza oldu. Kamyon devrildi.", True)


def test_text_without_plate_is_untouched():
    text = "Kazada 2’si ağır 5 kişi yaralandı. (DHA)"
    assert remove_license_plates(text) == (text, False)


def test_validation_strips_plate_from_caption_and_warns():
    result = output(NON_REPETITIVE_TTS, caption="34 FPR 116 plakalı otomobil savruldu. " + "x" * 1000)
    check = validate_news_output(result, "ham", 381, 396)
    assert "FPR" not in result.icerik
    assert result.icerik.startswith("Otomobil savruldu.")
    assert any("Plaka" in w for w in check.warnings)


def test_plan_field_is_generated_before_tts():
    fields = list(NewsOutput.model_fields)
    assert fields.index("tts_plani") < fields.index("tts")


def test_prompt_contains_viral_tts_rules():
    for rule in ("Plaka", "ikinci kez söyleme", "üst sınırdır", "ajans kalıplarını", "Noktalı virgül", "tts_plani"):
        assert rule in SYSTEM_PROMPT


def test_user_prompts_no_longer_push_to_fill_length():
    prompt = build_news_prompt("Standart", "25–26 saniye", (25, 26), 381, 389, 396, "ham", 1.11, {})
    assert "hemen bitirme" not in prompt
    assert "natural" not in prompt
    assert "üst sınırdır" in prompt
    correction = build_correction_prompt("Standart", "25–26", 381, 389, 396, "ham", output("t"), ["hata"])
    assert "tekrar veya dolgu ekleme" in correction
