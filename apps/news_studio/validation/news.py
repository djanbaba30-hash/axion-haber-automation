import re
from dataclasses import dataclass

from ..config import TTS_TOLERANCE_CHARS


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]


def turkish_upper(text: str) -> str:
    return text.translate(str.maketrans({"i": "İ", "ı": "I"})).upper()


def count_words(text: str) -> int:
    return len([x for x in text.strip().split() if x])


def validate_news_output(result, raw_text, tts_min_chars, tts_max_chars) -> ValidationResult:
    result.baslik1 = turkish_upper((result.baslik1 or "").strip())
    result.baslik2 = turkish_upper((result.baslik2 or "").strip())
    result.icerik = (result.icerik or "").strip()
    result.tts = (result.tts or "").strip()
    errors=[]; warnings=[]
    for name, value in (("1. başlık",result.baslik1),("2. başlık",result.baslik2),("Caption",result.icerik),("TTS metni",result.tts)):
        if not value: errors.append(f"{name} boş.")
    for i,h in enumerate((result.baslik1,result.baslik2),1):
        if h and count_words(h)>9: errors.append(f"{i}. başlık 9 kelimeden uzun.")
    cap=len(result.icerik); tts=len(result.tts); raw=len(raw_text.strip())
    if cap>2200: errors.append(f"Caption {cap} karakter; maksimum 2200 olmalı.")
    if raw>=2200 and cap<850: errors.append("Uzun ham haber için caption gereğinden fazla kısa.")
    elif raw>=3500 and cap<1100: errors.append("Çok uzun ham haber için caption bilgi açısından fazla kısa.")
    if tts < tts_min_chars-TTS_TOLERANCE_CHARS: errors.append(f"TTS hedefin belirgin şekilde altında: {tts} karakter (hedef {tts_min_chars}-{tts_max_chars}).")
    elif tts > tts_max_chars+TTS_TOLERANCE_CHARS: errors.append(f"TTS hedefin belirgin şekilde üstünde: {tts} karakter (hedef {tts_min_chars}-{tts_max_chars}).")
    if cap>900 and tts>cap*1.10: errors.append("TTS, detaylı caption'dan belirgin şekilde uzun.")
    if cap and tts>=cap: warnings.append("TTS caption kadar uzun veya daha uzun; editoryal kontrol önerilir.")
    return ValidationResult(errors,warnings)


_CENSOR_PATTERNS = [
    (re.compile(r"\bsilah\b", re.I), "s*lah"),
    (re.compile(r"\bbıçak\b", re.I), "b*çak"),
    (re.compile(r"\bcinayet\b", re.I), "c*nayet"),
]


def find_censorship_warnings(text: str) -> list[str]:
    found=[]
    for pattern, replacement in _CENSOR_PATTERNS:
        if pattern.search(text): found.append(f"Sansür kontrolü: '{pattern.pattern}' görüldü; model çıktısı incelenmeli.")
    return found
