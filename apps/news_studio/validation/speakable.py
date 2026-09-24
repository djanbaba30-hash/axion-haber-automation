"""Seslendirme metnindeki saat, tarih ve ondalık sayıları spikerin okuyacağı biçime çevirir (API yok).

ElevenLabs "18.00'de", "24.09.2026" veya "2,5" gibi yazımları doğru okuyamıyor (editör testi, Kayseri haberi).
Örnekler: "saat 18.00 sıralarında" → "akşam 6 sıralarında", "09.30'da" → "sabah 9 buçukta",
"24.09.2026'da" → "24 Eylül'de", "1.500 kişi" → "1500 kişi", "2,5 metre" → "2 buçuk metre".
"""

from __future__ import annotations

import re

# 1–12 okunuşuna göre ekler (ünlü uyumu + sert ünsüz): yer (-de), yönelme (-e), belirtme (-i).
_LOCATIVE = {1: "de", 2: "de", 3: "te", 4: "te", 5: "te", 6: "da", 7: "de", 8: "de", 9: "da", 10: "da", 11: "de", 12: "de"}
_DATIVE = {1: "e", 2: "ye", 3: "e", 4: "e", 5: "e", 6: "ya", 7: "ye", 8: "e", 9: "a", 10: "a", 11: "e", 12: "ye"}
_ACCUSATIVE = {1: "i", 2: "yi", 3: "ü", 4: "ü", 5: "i", 6: "yı", 7: "yi", 8: "i", 9: "u", 10: "u", 11: "i", 12: "yi"}
_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
_MONTH_LOCATIVE = ["ta", "ta", "ta", "da", "ta", "da", "da", "ta", "de", "de", "da", "ta"]
_MONTH_DATIVE = ["a", "a", "a", "a", "a", "a", "a", "a", "e", "e", "a", "a"]

_APOSTROPHE = "['’]"
_SUFFIX = rf"(?:{_APOSTROPHE}(?P<suffix>[a-zA-ZçğıöşüÇĞİÖŞÜ]+))?"
_TIME = re.compile(
    rf"(?P<saat>\b[Ss]aat\s+)?\b(?P<hour>[01]?\d|2[0-3])[.:](?P<minute>[0-5]\d)\b(?![.,]\d){_SUFFIX}"
    r"(?P<after>\s+(?:sıralarında|sularında|civarında|itibarıyla))?"
)
_DATE = re.compile(rf"\b(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>(?:19|20)\d\d)\b{_SUFFIX}")
_THOUSANDS = re.compile(r"\b\d{1,3}(?:\.\d{3})+\b(?![.,]\d)")
_HALF = re.compile(r"\b(?P<whole>\d+),5\b")
_HARD = re.compile(r"\b\d+[.,]\d+\b")
_SENTENCE_START = re.compile(r"(?:^|[.!?…]\s+)$")


def _kind(suffix: str | None) -> str | None:
    if not suffix:
        return None
    lowered = suffix.lower()
    if lowered in {"de", "da", "te", "ta"}:
        return "loc"
    if lowered in {"e", "a", "ye", "ya"}:
        return "dat"
    return "other"


def _period(hour: int) -> str:
    if 5 <= hour <= 11:
        return "sabah"
    if hour == 12:
        return "öğlen"
    if 13 <= hour <= 16:
        return "öğleden sonra"
    if 17 <= hour <= 20:
        return "akşam"
    return "gece"


def _twelve(hour: int) -> int:
    return hour % 12 or 12


def _spoken_time(match: re.Match) -> str:
    # Saat olduğu bağlamdan belli olmalı ("saat", ek veya "sıralarında"); yoksa (ör. "12.50 lira") dokunma.
    if not (match["saat"] or match["suffix"] or match["after"]):
        return match.group(0)
    spoken = _clock(match) + (match["after"] or "")
    starts_sentence = (match["saat"] or "").startswith("S") or _SENTENCE_START.search(match.string[: match.start()])
    return spoken[0].upper() + spoken[1:] if starts_sentence else spoken


def _clock(match: re.Match) -> str:
    hour, minute = int(match["hour"]), int(match["minute"])
    kind = _kind(match["suffix"])
    if minute == 0:
        h = _twelve(hour)
        tail = {"loc": f"'{_LOCATIVE[h]}", "dat": f"'{_DATIVE[h]}"}.get(kind, "")
        return f"{_period(hour)} {h}{tail}"
    if minute == 30:
        h = _twelve(hour)
        tail = {"loc": "buçukta", "dat": "buçuğa"}.get(kind, "buçuk")
        return f"{_period(hour)} {h} {tail}"
    if minute < 30:
        h = _twelve(hour)
        amount = "çeyrek" if minute == 15 else str(minute)
        return f"{_period(hour)} {h}'{_ACCUSATIVE[h]} {amount} geçe"
    next_hour = (hour + 1) % 24
    h = _twelve(next_hour)
    amount = "çeyrek" if minute == 45 else str(60 - minute)
    return f"{_period(hour)} {h}'{_DATIVE[h]} {amount} kala"


def _spoken_date(match: re.Match) -> str:
    day, month = int(match["day"]), int(match["month"]) - 1
    kind = _kind(match["suffix"])
    tail = {"loc": f"'{_MONTH_LOCATIVE[month]}", "dat": f"'{_MONTH_DATIVE[month]}"}.get(kind, "")
    return f"{day} {_MONTHS[month]}{tail}"


def make_speakable(text: str) -> str:
    """Seslendirme metnini spikerin doğru okuyacağı biçime çevirir; değişiklik yoksa aynı metni döndürür."""
    text = _DATE.sub(_spoken_date, text)
    text = _TIME.sub(_spoken_time, text)
    text = _THOUSANDS.sub(lambda m: m.group(0).replace(".", ""), text)
    return _HALF.sub(lambda m: f"{m['whole']} buçuk", text)


def unreadable_numbers(text: str) -> list[str]:
    """Otomatik çevrilemeyen noktalı/virgüllü sayılar (ör. 3,2 metre): editöre uyarı."""
    return _HARD.findall(text)
