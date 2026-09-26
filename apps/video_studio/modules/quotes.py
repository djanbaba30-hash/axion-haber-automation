"""Haberdeki alıntıdan kesit önerisi (v4.1.0-alpha.2; API yok).

DHA metnindeki tırnaklı alıntı ("Ben de durumu hemen fark ettim…" dedi) çoğu zaman videodaki röportajın bir parçasıdır.
Alıntı yazıya dökümün (transcribe.py) ardışık cümleleriyle kelime kelime, sırasıyla eşleştirilir. Whisper'ın yanlış
duyduğu ve ekleri farklı kelimeler için kelimenin ilk harfleri (kökü) karşılaştırılır. Güven düşükse öneri yoktur;
öneri editörün dokunuşuyla aralık olur, kesit kendiliğinden eklenmez.
"""

from __future__ import annotations

import re
from typing import Any

QUOTE_MARK = re.compile(r"[\"“”«»]")
MAX_CHARS = 600
STEM = 5  # kelimenin ilk 5 harfi: "manevrasını" ↔ "manevrasıyla"
MIN_WORDS = 4  # daha kısa tırnak (lakap, tabela, "Heimlich") alıntı sayılmaz
MAX_SENTENCES = 8
MIN_RECALL = 0.6  # alıntının kelimelerinin en az %60'ı dökümde sırasıyla geçmeli
MIN_PRECISION = 0.4  # seçilen cümlelerin kelimelerinin en az %40'ı alıntıdan olmalı
LIMIT = 3


def _stems(text: str) -> list[str]:
    lowered = text.replace("I", "ı").replace("İ", "i").lower()
    return [word[:STEM] for word in re.findall(r"\w+", lowered)]


def extract(source_text: str) -> list[str]:
    """Haberdeki tırnaklı alıntılar (sırasıyla, tekrarsız, en az 4 kelime)."""
    pieces = QUOTE_MARK.split(source_text or "")
    parts = pieces[1:-1:2]  # tırnaklar sırayla eşlenir (1.–2., 3.–4. …); kapanmayan son tırnak alıntı değil
    found = [" ".join(part.split()) for part in parts if len(part) <= MAX_CHARS]
    return list(dict.fromkeys(quote for quote in found if len(_stems(quote)) >= MIN_WORDS))


def _common(a: list[str], b: list[str]) -> int:
    """Sırası korunan ortak kelime sayısı (en uzun ortak alt dizi)."""
    row = [0] * (len(b) + 1)
    for word in a:
        previous = 0
        for index, other in enumerate(b, 1):
            previous, row[index] = row[index], previous + 1 if word == other else max(row[index], row[index - 1])
    return row[-1]


def match(quote: str, sentences: list[dict[str, Any]]) -> tuple[int, int, float] | None:
    """Alıntıya en iyi uyan ardışık cümleler (ilk, son, güven 0–1); güven düşükse None."""
    wanted = _stems(quote)
    words = [_stems(line["metin"]) for line in sentences]
    best: tuple[int, int, float] | None = None
    for first in range(len(sentences)):
        span: list[str] = []
        for last in range(first, min(first + MAX_SENTENCES, len(sentences))):
            span += words[last]
            common = _common(wanted, span)
            recall, precision = common / len(wanted), common / max(1, len(span))
            if recall < MIN_RECALL or precision < MIN_PRECISION:
                continue
            score = 2 * recall * precision / (recall + precision)
            if best is None or score > best[2]:
                best = (first, last, score)
    return best


def suggestions(source_text: str, sentences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dökümde bulunan alıntılar (haberdeki sırasıyla, en fazla 3): {"alinti", "ilk", "son", "bas", "bitis"}."""
    result = []
    for quote in extract(source_text):
        found = match(quote, sentences)
        if found:
            first, last, _ = found
            result.append({"alinti": quote, "ilk": first, "son": last,
                           "bas": sentences[first]["bas"], "bitis": sentences[last]["son"]})
    return result[:LIMIT]
