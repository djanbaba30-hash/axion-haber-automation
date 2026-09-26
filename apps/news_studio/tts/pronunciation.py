"""Okunuş sözlüğü (v4.1.0-alpha.1): spikerin yanlış okuduğu kelimeler (ör. Heimlich → Haymlih).

Editör kenar çubuğunda doldurur (`data/okunus.json`). Yalnız ElevenLabs'a giden metne uygulanır; ekrandaki seslendirme
metni, paylaşım metni ve projeye kaydedilen metin değişmez. ElevenLabs'ın karakter zamanları okunan metne göredir;
`remap` onları ekrandaki metne geri taşır (okuyarak dinleme ve kurgu kesmeleri bozulmaz). API çağrısı yok.
"""

from __future__ import annotations

import json
import re

from apps.axion_local.store import data_dir
from shared.news_package import TTSAlignment

FILENAME = "okunus.json"
MAX_WORD = 60

Span = tuple[int, int, int, int]  # ekrandaki [başlangıç, son) ↔ okunan metindeki [başlangıç, son)


def load() -> dict[str, str]:
    try:
        data = json.loads((data_dir() / FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items() if str(k).strip() and str(v).strip()} if isinstance(data, dict) else {}


def save(entries: dict[str, str]) -> None:
    path = data_dir() / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def to_text(entries: dict[str, str]) -> str:
    return "\n".join(f"{word} = {spoken}" for word, spoken in entries.items())


def parse(text: str) -> tuple[dict[str, str], list[str]]:
    """Her satır `yazılış = okunuş`; uymayan satırlar ayrıca döner (editöre gösterilir, kaydedilmez)."""
    entries: dict[str, str] = {}
    bad: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        word, sep, spoken = (part.strip() for part in line.partition("="))
        if not sep or not word or not spoken or len(word) > MAX_WORD or len(spoken) > MAX_WORD:
            bad.append(line.strip())
        else:
            entries[word] = spoken
    return entries, bad


def apply(text: str, entries: dict[str, str]) -> tuple[str, list[Span]]:
    """Sözlükteki kelimeleri (tam kelime, büyük/küçük harf fark etmez; uzun olan önce) okunuşuyla değiştirir.
    "Heimlich'i" gibi ekli yazım da eşleşir (kesme işareti kelime harfi değil)."""
    if not entries:
        return text, []
    words = sorted(entries, key=len, reverse=True)
    pattern = re.compile("|".join(f"(?P<w{i}>(?<!\\w){re.escape(word)}(?!\\w))" for i, word in enumerate(words)),
                         re.IGNORECASE)
    parts: list[str] = []
    spans: list[Span] = []
    last = shift = 0
    for match in pattern.finditer(text):
        spoken = entries[words[int(match.lastgroup[1:])]]
        start, end = match.span()
        parts += [text[last:start], spoken]
        spans.append((start, end, start + shift, start + shift + len(spoken)))
        shift += len(spoken) - (end - start)
        last = end
    parts.append(text[last:])
    return "".join(parts), spans


def used(text: str, entries: dict[str, str]) -> list[str]:
    """Metinde sözlükle okunan kelimeler ("Heimlich → Haymlih"; sesin altında gösterilir)."""
    spoken, spans = apply(text, entries)
    return list(dict.fromkeys(f"{text[a:b]} → {spoken[c:d]}" for a, b, c, d in spans))


def remap(alignment: TTSAlignment, text: str, spans: list[Span]) -> TTSAlignment | None:
    """Okunan metnin karakter zamanlarını ekrandaki metne taşır: değişmeyen karakterler aynen, değiştirilen kelimenin
    harfleri okunuşunun süresine eşit yayılır. Tutmazsa None (zaman bilgisi kaydedilmez, ses yine kullanılır)."""
    starts, ends = alignment.start_seconds, alignment.end_seconds
    new_starts: list[float] = []
    new_ends: list[float] = []
    at = 0
    try:
        for start, end, spoken_start, spoken_end in spans:
            new_starts += starts[at:spoken_start]
            new_ends += ends[at:spoken_start]
            # Harfler, okunuşun ilk ve son harfinin başlangıcı arasına eşit yayılır (zamanların sırası bozulmaz).
            first, last, count = starts[spoken_start], starts[spoken_end - 1], end - start
            points = [first + (last - first) * i / max(1, count - 1) for i in range(count)]
            new_starts += points
            new_ends += points[1:] + [max(ends[spoken_end - 1], points[-1])]
            at = spoken_end
        new_starts += starts[at:]
        new_ends += ends[at:]
        return TTSAlignment(characters=list(text), start_seconds=new_starts, end_seconds=new_ends)
    except (IndexError, ValueError):
        return None
