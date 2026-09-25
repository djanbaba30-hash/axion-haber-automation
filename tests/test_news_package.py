import unittest
from shared.news_package import NewsPackage

class TestNewsPackage(unittest.TestCase):
    def test_roundtrip(self):
        p=NewsPackage(headline_1="A",headline_2="B",caption="C",tts_text="D")
        q=NewsPackage.model_validate_json(p.model_dump_json())
        self.assertEqual(q.tts_text,"D")

if __name__ == "__main__":
    unittest.main()
