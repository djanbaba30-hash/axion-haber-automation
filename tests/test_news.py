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


if __name__ == "__main__": unittest.main()
