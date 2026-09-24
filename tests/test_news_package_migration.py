import json

import pytest
from pydantic import ValidationError

from shared.news_package import (
    NewsPackage,
    TTSAlignment,
    load_news_package,
    parse_news_package,
)


def alignment_for(text):
    return {
        "characters": list(text),
        "start_seconds": [0.1 * i for i in range(len(text))],
        "end_seconds": [0.1 * i + 0.1 for i in range(len(text))],
    }


def test_v1_1_roundtrip_from_news_studio_output():
    package = NewsPackage(
        headline_1="A", headline_2="B", caption="C", tts_text="D", metadata={"style": "x"}
    )
    assert parse_news_package(json.loads(package.model_dump_json())) == package


def test_flat_v1_0_is_migrated():
    package = parse_news_package(
        {"schema_version": "1.0", "headline_1": "A", "headline_2": "B", "caption": "C", "tts_text": "D"}
    )
    assert package.schema_version == "1.1"
    assert package.tts_alignment is None


def test_nested_turkish_legacy_format_is_migrated():
    package = parse_news_package({"news": {"baslik1": "A", "baslik2": "B", "icerik": "C", "tts": "D", "raw_text": "R"}})
    assert (package.headline_1, package.caption, package.tts_text, package.source_text) == ("A", "C", "D", "R")


def test_null_schema_version_is_treated_as_v1_0():
    package = parse_news_package({"schema_version": None, "caption": "C"})
    assert package.schema_version == "1.1"


def test_unknown_legacy_fields_are_kept_in_metadata():
    package = parse_news_package({"schema_version": "1.0", "caption": "C", "audio": {"x": 1}})
    assert package.metadata["legacy_fields"] == {"audio": {"x": 1}}


def test_unsupported_version_is_rejected():
    with pytest.raises(ValueError, match="Desteklenmeyen"):
        parse_news_package({"schema_version": "9.9", "caption": "C"})


def test_v1_1_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        parse_news_package(
            {"schema_version": "1.1", "headline_1": "A", "headline_2": "B", "caption": "C", "tts_text": "D", "extra": 1}
        )


def test_alignment_must_match_tts_text_through_json():
    payload = {
        "headline_1": "A", "headline_2": "B", "caption": "C", "tts_text": "Merhaba",
        "tts_alignment": {"characters": ["X", "Y", "Z"], "start_seconds": [0, 1, 2], "end_seconds": [1, 2, 3]},
    }
    with pytest.raises(ValidationError, match="tts_text"):
        NewsPackage.model_validate_json(json.dumps(payload))


def test_alignment_lengths_must_match():
    with pytest.raises(ValidationError, match="aynı uzunlukta"):
        TTSAlignment(characters=["a", "b"], start_seconds=[0.0], end_seconds=[0.1, 0.2])


def test_valid_alignment_is_accepted():
    package = NewsPackage(
        headline_1="A", headline_2="B", caption="C", tts_text="Merhaba", tts_alignment=alignment_for("Merhaba")
    )
    assert package.tts_alignment.duration_seconds() == pytest.approx(0.7)


def test_load_news_package_migrates_file(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"baslik1": "A", "icerik": "C"}), encoding="utf-8")
    assert load_news_package(path).caption == "C"
