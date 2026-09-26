"""v4.1.0-alpha.1: okunuş sözlüğü (yalnız ElevenLabs'a giden metin) ve ElevenLabs hatasının açık nedeni."""

import base64
from types import SimpleNamespace

import httpx
import pytest
from elevenlabs.core.api_error import ApiError

from apps.news_studio.tts import pronunciation
from apps.news_studio.tts.service import error_message, synthesize
from shared.news_package import NewsPackage, TTSAlignment

# Editörün örneği (Artvin haberi, 2026-09-26): spiker "Heimlich"i yanlış okuyordu.
TEXT = "Öğretmen Heimlich manevrası yaptı. Heimlich'i bilen herkes yardım edebilir."
LEXICON = {"Heimlich": "Haymlih", "Heimlich manevrası": "Haymlih manevrası"}


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    return tmp_path


def timed(text):
    """Harf başına 0,1 sn; ElevenLabs gibi."""
    return SimpleNamespace(characters=list(text), character_start_times_seconds=[0.1 * i for i in range(len(text))],
                           character_end_times_seconds=[0.1 * i + 0.1 for i in range(len(text))])


def test_dictionary_is_written_one_entry_per_line_and_kept():
    entries, bad = pronunciation.parse("Heimlich = Haymlih\n\n  Kılıçdaroğlu=Kılıçdaroğlu \nyanlış satır\n= boş\n")
    assert entries == {"Heimlich": "Haymlih", "Kılıçdaroğlu": "Kılıçdaroğlu"}
    assert bad == ["yanlış satır", "= boş"]
    pronunciation.save(entries)
    assert pronunciation.load() == entries
    assert pronunciation.parse(pronunciation.to_text(entries)) == (entries, [])


def test_whole_words_are_replaced_longest_first_with_suffixes():
    spoken, spans = pronunciation.apply(TEXT + " heimlich Heimlichx", LEXICON)
    assert spoken == ("Öğretmen Haymlih manevrası yaptı. Haymlih'i bilen herkes yardım edebilir. Haymlih Heimlichx")
    assert len(spans) == 3
    assert pronunciation.apply(TEXT, {}) == (TEXT, [])
    assert pronunciation.used(TEXT, LEXICON) == ["Heimlich manevrası → Haymlih manevrası", "Heimlich → Haymlih"]


def test_times_are_moved_back_to_the_text_on_screen():
    spoken, spans = pronunciation.apply(TEXT, LEXICON)
    raw = timed(spoken)
    spoken_alignment = TTSAlignment(characters=raw.characters, start_seconds=raw.character_start_times_seconds,
                                    end_seconds=raw.character_end_times_seconds)
    alignment = pronunciation.remap(spoken_alignment, TEXT, spans)
    assert "".join(alignment.characters) == TEXT
    # Değişmeyen harflerin zamanı aynı; kelimenin sonrası ("yaptı") okunan metindeki yerinde.
    assert alignment.start_seconds[:9] == spoken_alignment.start_seconds[:9]
    at_text, at_spoken = TEXT.index("yaptı"), spoken.index("yaptı")
    assert alignment.start_seconds[at_text] == spoken_alignment.start_seconds[at_spoken]
    # Değiştirilen kelime, okunuşunun süresini kaplar; ses sonu aynı.
    first = TEXT.index("Heimlich")
    assert alignment.start_seconds[first] == spoken_alignment.start_seconds[spoken.index("Haymlih")]
    assert alignment.duration_seconds() == spoken_alignment.duration_seconds()


def test_synthesize_sends_the_spoken_text_but_returns_times_for_the_screen():
    calls = []

    def convert(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(audio_base_64=base64.b64encode(b"mp3").decode(), alignment=timed(kwargs["text"]))

    client = SimpleNamespace(text_to_speech=SimpleNamespace(convert_with_timestamps=convert))
    audio, alignment, spoken = synthesize(client, TEXT, "voice", 1.1, 0.5, 0.65, 0.1, True, LEXICON)
    assert calls[0]["text"] == spoken and "Haymlih" in spoken and "Heimlich" not in spoken
    package = NewsPackage(headline_1="A", headline_2="B", caption="C", tts_text=TEXT, tts_alignment=alignment)
    assert "".join(package.tts_alignment.characters) == TEXT


def error(status, detail):
    return ApiError(headers={"date": "Sat, 26 Sep 2026", "content-type": "application/json"}, status_code=status,
                    body={"detail": detail})


def test_elevenlabs_errors_say_the_reason_not_the_headers():
    missing = error(401, {"status": "missing_permissions",
                          "message": "The API key you used is missing the permission user_read to execute this operation."})
    assert error_message(missing).startswith('API anahtarında "User → Read" izni yok')
    assert "geçersiz" in error_message(error(401, {"status": "invalid_api_key", "message": "Invalid API key"}))
    assert "kotası bitti" in error_message(error(401, {"status": "quota_exceeded", "message": "quota"}))
    assert error_message(error(500, "sunucu")) == "ElevenLabs hatası 500: sunucu"
    assert "ulaşılamadı" in error_message(httpx.ConnectError("bağlantı yok"))
    assert error_message(RuntimeError("başka")) == "başka"
