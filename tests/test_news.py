import unittest
from types import SimpleNamespace

from apps.news_studio.validation.news import count_words, turkish_upper, validate_news_output


class TestNews(unittest.TestCase):
    def test_turkish_upper(self):
        self.assertEqual(turkish_upper("istanbul ıslak"), "İSTANBUL ISLAK")

    def test_word_count(self):
        self.assertEqual(count_words("bir  iki\tüç"), 3)

    def test_caption_limit(self):
        r=SimpleNamespace(baslik1="A",baslik2="B",icerik="x"*2201,tts="k"*200)
        check=validate_news_output(r,"haber",150,300)
        self.assertTrue(any("2200" in e for e in check.errors))


if __name__ == "__main__":
    unittest.main()


def test_headline_must_fit_two_lines_in_video():
    """Editörün temel kuralı: başlık videodaki yazıyla (Google Sans Bold 58 px, 920 px) en fazla 2 satır."""
    from shared.text_layout import check_headline, headline_char_budget

    long_headline = "KAYSERİ'DE KONTROLDEN ÇIKAN TIR KAVŞAKTA BEKLEYEN 3 OTOMOBİLE ÇARPTI"
    r = SimpleNamespace(baslik1=long_headline, baslik2="5 KİŞİ YARALANDI", icerik="x" * 300, tts="k" * 200)
    check = validate_news_output(r, "haber", 150, 300)
    fit_errors = [e for e in check.errors if "2 satıra sığmıyor" in e]
    assert len(fit_errors) == 1 and fit_errors[0].startswith("1. başlık")
    assert "karakter kısalt" in fit_errors[0]  # düzeltme çağrısına somut hedef

    fitting = check_headline("MANSUR YAVAŞ CHP'DEN İSTİFA ETTİ")  # editörün Canva örneği
    assert fitting.fits and fitting.lines == ["MANSUR YAVAŞ", "CHP'DEN İSTİFA ETTİ"]
    assert not check_headline(long_headline).fits
    # Prompt'taki sınır (44 karakter) ölçümle uyumlu: tipik başlıklar bu sınırda sığar.
    assert headline_char_budget() >= 44
    assert check_headline("KONTROLDEN ÇIKAN TIR 3 OTOMOBİLE ÇARPTI").fits


def test_prompts_give_the_same_character_limit():
    from apps.news_studio.prompts.news import HEADLINE_SYSTEM_PROMPT, SYSTEM_PROMPT

    assert "EN FAZLA 44 KARAKTER" in SYSTEM_PROMPT
    assert "EN FAZLA 44 KARAKTER" in HEADLINE_SYSTEM_PROMPT
