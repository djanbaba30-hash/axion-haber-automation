"""Kalite kontrolü (API yok): çıktıda olup ham haberde bulunmayan sayılar ve özel isimler ("kaynakta yok").

Yapay zekânın uydurmasını ya da yanlış aktarmasını editör hızlı görsün diye sarıyla işaretlenir; hata değildir
(ör. "iki" ↔ "2" gibi yazım farkı da işaretlenebilir). Sayılar: rakam dizileri; seslendirmede okunuşa çevrilmiş
saat/tarih için ham haberin okunuşu da kaynak sayılır. İsimler: cümle ortasında büyük harfle başlayan kelimeler,
Türkçe eklerden dolayı ilk 5 harfle karşılaştırılır.
"""

from __future__ import annotations

import re

from .speakable import make_speakable

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
WORD = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû]+(?:['’][a-zçğıöşüâîû]+)?")
SENTENCE_START = re.compile(r"(?:^|[.!?:…\n\"“]\s*)$")
STEM = 5
# Tarihi okunuşa çevirmek ay/gün adı üretir; bunlar kaynakta rakamla yazılmış olabilir.
CALENDAR = {"ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık",
            "pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"}


def _lower(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in NUMBER.findall(text)}


def _stems(text: str) -> set[str]:
    return {_lower(w.split("'")[0].split("’")[0])[:STEM] for w in WORD.findall(text)}


def missing_numbers(output: str, source: str) -> list[str]:
    known = _numbers(source) | _numbers(make_speakable(source))
    found: list[str] = []
    for number in NUMBER.findall(output):
        if number.replace(",", ".") not in known and number not in found:
            found.append(number)
    return found


def missing_names(output: str, source: str) -> list[str]:
    known = _stems(source)
    found: list[str] = []
    for match in WORD.finditer(output):
        word = match.group(0)
        if not word[0].isupper() or (word.isupper() and len(word) <= 3):  # kısaltmalar (DHA, AFAD) genelde kaynakta var
            continue
        if SENTENCE_START.search(output[: match.start()]):
            continue  # cümle başı: özel isim olduğu belli değil
        base = word.split("'")[0].split("’")[0]
        if _lower(base) in CALENDAR or _lower(base)[:STEM] in known:
            continue
        if word not in found:
            found.append(word)
    return found


def unsupported(output: str, source: str) -> list[str]:
    """Ham haberde geçmeyen sayılar ve isimler (sırayla, tekrarsız)."""
    if not output.strip() or not source.strip():
        return []
    return missing_numbers(output, source) + missing_names(output, source)
