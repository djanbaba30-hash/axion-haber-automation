import re
from dataclasses import dataclass, field
from itertools import combinations

from shared.text_layout import check_headline

from ..config import TTS_HARD_MIN_RATIO, TTS_TOLERANCE_CHARS
from .speakable import make_speakable, unreadable_numbers


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    headline_errors: dict[int, str] = field(default_factory=dict)  # başlık no → hata (errors içinde de var)

    @property
    def headlines_only(self) -> bool:
        """Hataların hepsi başlıkta mı (tam düzeltme yerine küçük başlık çağrısı yeter)."""
        return bool(self.errors) and len(self.errors) == len(self.headline_errors)


def turkish_upper(text: str) -> str:
    return text.translate(str.maketrans({"i": "İ", "ı": "I"})).upper()


def turkish_lower(text: str) -> str:
    return text.translate(str.maketrans({"İ": "i", "I": "ı"})).lower()


def count_words(text: str) -> int:
    return len([x for x in text.strip().split() if x])


_PLATE_WITH_SUFFIX = re.compile(r"\b\d{2} ?[A-Z]{1,3} ?\d{2,5} plakal[ıi]\s+")
_PLATE = re.compile(r"\b\d{2} ?[A-Z]{1,3} ?\d{2,5}\b")


def remove_license_plates(text: str) -> tuple[str, bool]:
    """'34 FPR 116 plakalı otomobil' → 'otomobil'. Cümle başında kalan harfi büyütür."""
    out: list[str] = []
    last = 0
    for match in _PLATE_WITH_SUFFIX.finditer(text):
        out.append(text[last:match.start()])
        last = match.end()
        prefix = "".join(out).rstrip()
        if (not prefix or prefix[-1] in ".!?") and last < len(text):
            out.append(turkish_upper(text[last]))
            last += 1
    if not out:
        return text, False
    out.append(text[last:])
    return "".join(out), True


def _sentence_case_after(text: str, separator: str) -> str:
    pieces = text.split(separator)
    out = pieces[0]
    for raw_piece in pieces[1:]:
        piece = raw_piece.lstrip()
        out += ". " + (turkish_upper(piece[0]) + piece[1:] if piece else "")
    return out


def normalize_tts_punctuation(text: str) -> str:
    """Noktalı virgül seslendirmede yapay duraksama yaratır; cümleye böler."""
    return _sentence_case_after(text, ";") if ";" in text else text


_STOP_PREFIXES = {
    "olan", "oldu", "olar", "olma", "olur", "bulu", "sonr", "sonu", "için", "gibi",
    "kada", "daha", "ayrı", "ilgi", "edil", "eder", "kişi", "anca", "sade", "yaln",
    "ardı", "önce", "sıra", "şeki", "bunu", "bunl", "onla",
}


def _sentence_signature(sentence: str) -> tuple[set[str], set[str]]:
    lowered = turkish_lower(re.sub(r"[’'][^\s]*", "", sentence))
    numbers = set(re.findall(r"\d+", lowered))
    stems = {
        word[:4]
        for word in re.findall(r"[a-zçğıöşüâîû]+", lowered)
        if len(word) >= 4 and word[:4] not in _STOP_PREFIXES
    }
    return numbers, stems


def find_tts_repetitions(tts: str) -> list[str]:
    """Aynı sayı + ortak içerik kelimesi ya da 3+ ortak içerik kelimesi olan cümle çiftleri."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", tts) if s.strip()]
    signatures = [_sentence_signature(s) for s in sentences]
    found = []
    for (i, (nums_a, stems_a)), (j, (nums_b, stems_b)) in combinations(enumerate(signatures), 2):
        shared_stems = stems_a & stems_b
        if (nums_a & nums_b and shared_stems) or len(shared_stems) >= 3:
            found.append(f"Seslendirme metninin {i + 1}. ve {j + 1}. cümlesi aynı bilgiyi tekrarlıyor olabilir.")
    return found


def validate_news_output(result, raw_text, tts_min_chars, tts_max_chars) -> ValidationResult:
    """Çıktıyı temizler (büyük harf, plaka, okunuş) ve kontrol eder. Hatalar tek düzeltme çağrısına gider, uyarılar
    editöre gösterilir."""
    result.baslik1 = turkish_upper((result.baslik1 or "").strip())
    result.baslik2 = turkish_upper((result.baslik2 or "").strip())
    result.icerik = (result.icerik or "").strip()
    result.tts = make_speakable(normalize_tts_punctuation((result.tts or "").strip()))
    errors: list[str] = []
    warnings: list[str] = []
    hard_numbers = unreadable_numbers(result.tts)
    if hard_numbers:
        warnings.append("Seslendirme metninde spikerin yanlış okuyabileceği sayı var: " + ", ".join(hard_numbers)
                        + ". Kelimeyle yazmayı düşün.")

    plate_removed = False
    for field in ("baslik1", "baslik2", "icerik", "tts"):
        cleaned, removed = remove_license_plates(getattr(result, field))
        setattr(result, field, cleaned)
        plate_removed = plate_removed or removed
    if plate_removed:
        warnings.append("Plaka bilgisi çıktıdan otomatik çıkarıldı.")
    if any(_PLATE.search(getattr(result, f)) for f in ("icerik", "tts")):
        warnings.append("Çıktıda plaka olabilecek bir ifade var; kontrol et.")

    fields = (("1. başlık", result.baslik1), ("2. başlık", result.baslik2), ("Paylaşım metni (caption)", result.icerik),
              ("Seslendirme metni (tts)", result.tts))
    errors.extend(f"{name} boş." for name, value in fields if not value)
    headline_errors: dict[int, str] = {}
    for i, headline in enumerate((result.baslik1, result.baslik2), 1):
        if not headline:
            continue
        problems = ["9 kelimeden uzun"] if count_words(headline) > 9 else []
        fit = check_headline(headline)
        if fit.shrinks:  # küçültülmüş yazıyla 2 satır: hata değil (düzeltme çağrısı yok), editör isterse kısaltır
            warnings.append(f"{i}. başlık videoda küçültülmüş yazıyla ({fit.size} px) 2 satıra sığıyor.")
        elif not fit.fits:
            # Videodaki gerçek yazıyla (Google Sans Flex ExtraBold 58 px) ölçülür; düzeltme çağrısına somut hedef verilir.
            problems.append(f"videoda 2 satıra sığmıyor ({len(headline)} karakter): anlamı koruyarak yaklaşık "
                            f"{fit.over_chars} karakter kısalt, en fazla 44 karakter")
        if problems:
            headline_errors[i] = f"{i}. başlık " + "; ".join(problems) + "."
    errors.extend(headline_errors.values())

    cap, tts, raw = len(result.icerik), len(result.tts), len(raw_text.strip())
    target = f"(hedef {tts_min_chars}-{tts_max_chars})"
    if cap > 2200:
        errors.append(f"Paylaşım metni (caption) {cap} karakter; en fazla 2200 olmalı.")
    if raw >= 2200 and cap < 850:
        errors.append("Uzun ham haber için paylaşım metni (caption) gereğinden fazla kısa.")
    elif raw >= 3500 and cap < 1100:
        errors.append("Çok uzun ham haber için paylaşım metni (caption) bilgi açısından fazla kısa.")
    if tts and tts < tts_min_chars * TTS_HARD_MIN_RATIO:
        errors.append(f"Seslendirme metni (tts) çok kısa: {tts} karakter {target}.")
    elif tts and tts < tts_min_chars - TTS_TOLERANCE_CHARS:
        warnings.append(f"Seslendirme metni hedefin altında: {tts} karakter {target}. "
                        "Tekrar yerine kısa tutulduysa sorun değil.")
    elif tts > tts_max_chars + TTS_TOLERANCE_CHARS:
        errors.append(f"Seslendirme metni (tts) hedefin belirgin şekilde üstünde: {tts} karakter {target}.")
    if cap > 900 and tts > cap * 1.10:
        errors.append("Seslendirme metni (tts), paylaşım metninden (caption) belirgin şekilde uzun.")
    if cap and tts >= cap:
        warnings.append("Seslendirme metni, paylaşım metni kadar uzun veya daha uzun; kontrol etmen önerilir.")
    warnings.extend(find_tts_repetitions(result.tts))
    return ValidationResult(errors, warnings, headline_errors)

_CENSOR_PATTERNS = [
    (re.compile(r"\bsilah\b", re.I), "s*lah"),
    (re.compile(r"\bbıçak\b", re.I), "b*çak"),
    (re.compile(r"\bcinayet\b", re.I), "c*nayet"),
]


def find_censorship_warnings(text: str) -> list[str]:
    return [f"Sansür kontrolü: '{pattern.pattern}' görüldü; model çıktısı incelenmeli."
            for pattern, _ in _CENSOR_PATTERNS if pattern.search(text)]
