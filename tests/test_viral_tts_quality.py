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


def test_prompt_editor_rules_2026_09():
    """Editör (Windows denemesi): başlıkta yer adı yok (afet hariç), spiker gibi doğal TTS, röportajda isim açık."""
    from apps.news_studio.prompts.news import HEADLINE_SYSTEM_PROMPT

    assert "nerede" not in SYSTEM_PROMPT.split("BAŞLIKLAR")[1].split("CAPTION")[0]
    for prompt in (SYSTEM_PROMPT, HEADLINE_SYSTEM_PROMPT):
        assert "İl/ilçe" in prompt or "il/ilçe" in prompt
        assert "deprem" in prompt
    assert "haber spikerinin" in SYSTEM_PROMPT
    assert "Röportaj veren" in SYSTEM_PROMPT and "baş harfe çevirme" in SYSTEM_PROMPT


def test_user_prompts_no_longer_push_to_fill_length():
    prompt = build_news_prompt("Standart", "25–26 saniye", (25, 26), 381, 389, 396, "ham", 1.11, {})
    assert "hemen bitirme" not in prompt
    assert "natural" not in prompt
    assert "üst sınırdır" in prompt
    correction = build_correction_prompt("Standart", "25–26", 381, 389, 396, "ham", output("t"), ["hata"])
    assert "tekrar veya dolgu ekleme" in correction


# Kayseri haberi (Windows testi): ElevenLabs "18.00'de" gibi saatleri okuyamıyor; spiker "akşam 6'da" demeli.
KAYSERI_TTS = (
    "Kayseri’de özel halk otobüsünün çarptığı 10 yaşındaki bisikletli çocuk hayatını kaybetti. "
    "Kocasinan’da saat 18.00'de yaşanan kazada çocuk olay yerinde yaşamını yitirdi."
)


def test_clock_times_become_speakable():
    from apps.news_studio.validation.speakable import make_speakable

    assert "akşam 6'da yaşanan" in make_speakable(KAYSERI_TTS)
    cases = {
        "Kaza, saat 18.00 sıralarında meydana geldi.": "Kaza, akşam 6 sıralarında meydana geldi.",
        "Saat 17.00’de ekipler geldi.": "Akşam 5'te ekipler geldi.",
        "saat 09.30'da": "Sabah 9 buçukta",
        "olay 14.15'te yaşandı": "olay öğleden sonra 2'yi çeyrek geçe yaşandı",
        "kaza 23.45'te oldu": "kaza gece 12'ye çeyrek kala oldu",
        "yangın 03.00'te çıktı": "yangın gece 3'te çıktı",
        "13.00'e kadar sürdü": "Öğleden sonra 1'e kadar sürdü",
        "kaza 24.09.2026'da oldu": "kaza 24 Eylül'de oldu",
        "1.500 kişi katıldı": "1500 kişi katıldı",
        "2,5 metre yükseklikten": "2 buçuk metre yükseklikten",
        "bilet 12.50 lira": "bilet 12.50 lira",  # saat bağlamı yok: dokunma
        "akşam 6'da yaşanan": "akşam 6'da yaşanan",
    }
    for text, expected in cases.items():
        assert make_speakable(text) == expected, text


def test_generated_tts_is_made_speakable_and_hard_numbers_warned():
    result = SimpleNamespace(
        baslik1="KAZA", baslik2="YARALI VAR", icerik="Uzun paylaşım metni. " * 20,
        tts="Kaza saat 18.00'de oldu. Araç 3,2 metre sürüklendi.",
    )
    check = validate_news_output(result, "Ham haber", 10, 400)
    assert result.tts == "Kaza akşam 6'da oldu. Araç 3,2 metre sürüklendi."
    assert any("3,2" in w for w in check.warnings)
