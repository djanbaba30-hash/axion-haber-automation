import base64
from types import SimpleNamespace

from apps.news_studio.tts.service import alignment_from_response, synthesize
from shared.news_package import NewsPackage


def raw_alignment(text):
    return SimpleNamespace(
        characters=list(text),
        character_start_times_seconds=[0.1 * i for i in range(len(text))],
        character_end_times_seconds=[0.1 * i + 0.1 for i in range(len(text))],
    )


class FakeTTS:
    def __init__(self, alignment):
        self.alignment = alignment
        self.calls = []

    def convert_with_timestamps(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(audio_base_64=base64.b64encode(b"mp3-bytes").decode(), alignment=self.alignment)


def test_alignment_is_converted_to_contract():
    alignment = alignment_from_response(raw_alignment("Merhaba"), "Merhaba")
    assert alignment.characters == list("Merhaba")
    assert round(alignment.duration_seconds(), 2) == 0.7


def test_mismatched_alignment_is_dropped_not_fatal():
    assert alignment_from_response(raw_alignment("Merhab"), "Merhaba") is None
    assert alignment_from_response(None, "Merhaba") is None


def test_invalid_alignment_times_are_dropped():
    bad = SimpleNamespace(characters=["a", "b"], character_start_times_seconds=[0.5, 0.1], character_end_times_seconds=[0.6, 0.2])
    assert alignment_from_response(bad, "ab") is None


def test_synthesize_returns_audio_and_alignment_in_one_call():
    tts = FakeTTS(raw_alignment("Bayrampaşa'da kaza."))
    client = SimpleNamespace(text_to_speech=tts)
    audio, alignment = synthesize(client, "Bayrampaşa'da kaza.", "voice", 1.11, 0.5, 0.65, 0.1, True)
    assert audio == b"mp3-bytes"
    assert len(tts.calls) == 1 and tts.calls[0]["voice_id"] == "voice"
    package = NewsPackage(headline_1="A", headline_2="B", caption="C", tts_text="Bayrampaşa'da kaza.", tts_alignment=alignment)
    assert package.tts_alignment.characters[-1] == "."
