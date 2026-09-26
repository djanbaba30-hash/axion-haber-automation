"""Yerel yazıya dökme (v4.0.0-alpha.7; API yok, token yok, bilgisayarda çalışır): kaynak videodaki konuşma → zamanlı
cümleler. Editör kaynak sesli kesiti cümleye dokunarak seçer; ileride altyazı temeli (altyazı şu an ürün kararı gereği
yok).

Motor: faster-whisper (Whisper large-v3-turbo, CTranslate2, işlemcide int8; Türkçe sabit). Model ilk kullanımda bir kez
iner (~1,6 GB, `data/modeller`), sonra internetsiz çalışır. faster-whisper yalnız kullanılırken yüklenir: kurulamazsa
Axion yine açılır, bu özellik "kurulu değil" der. Sonuç projede `yazi/` altında saklanır: aynı video yeniden dökülmez.
Uzun sürebildiği için arka planda (`start`), tablet kapansa da sürer.
"""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from apps.axion_local.store import data_dir

MODEL = "large-v3-turbo"
LANGUAGE = "tr"
FOLDER = "yazi"
VERSION = 3  # döküm biçimi (v3: kısa parçalar, özel ad düzeltmesi); değişince eski dökümler yeniden yapılır
PAD_START, PAD_END = 0.1, 0.25  # kesit cümlenin biraz önce/sonrasından (ilk/son hece kesilmesin)
NEXT_WORD_MARGIN = 0.08  # ...ama sonraki kelimeye taşmadan (editör: "sonraki kelimenin ortasında bitiyor")
SENTENCE_GAP = 1.2  # kelimeler arası bu kadar sessizlik varsa yeni cümle
# Konuşma dilinde Whisper çoğu zaman nokta koymaz (editör: "upuzun cümleler"): uzun parça en uzun nefes arasından
# (virgül öne alınır) bölünür; parçalar en az MIN_PART sn.
MAX_SENTENCE = 7.0
MIN_PART = 1.5
COMMA_BONUS = 0.3  # sn: virgülden sonraki ara bu kadar daha uzun sayılır
NAME_MATCH = 0.8  # özel ad düzeltmesi: okunuşu bu kadar benzeyen kelime haberdeki yazımla değişir
# Whisper'ın sessizlikte uydurduğu (altyazı ekiplerinden öğrendiği) kalıplar: gösterilmez.
HALLUCINATION = re.compile(r"altyaz[ıi]|abone ol|izlediğiniz için|teşekkürler izlediğiniz", re.IGNORECASE)
NAME = re.compile(r"[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}")
_MODELS: dict[str, Any] = {}
_LOCK = threading.Lock()  # model tek; iki döküm aynı anda işlemciyi bölmesin


@dataclass
class Job:
    progress: float = 0.0  # 0–1 (videonun dökülen kısmı)
    started: float = field(default_factory=time.monotonic)
    error: str | None = None
    done: bool = False
    thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


_JOBS: dict[str, Job] = {}


def available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


def model_ready() -> bool:
    """Model bu bilgisayara inmiş mi (ilk döküm uzun sürer: indirme)."""
    folder = data_dir() / "modeller"
    return folder.is_dir() and any(folder.rglob("model.bin"))


def _key(source: Path) -> str:
    stat = source.stat()
    return hashlib.sha1(f"{source.name}|{stat.st_size}|{int(stat.st_mtime)}|{MODEL}|{VERSION}".encode()).hexdigest()[:16]


def _path(folder: Path, source: Path) -> Path:
    return folder / FOLDER / f"{source.stem[:40]}_{_key(source)}.json"


def load(folder: Path, source: Path) -> dict[str, Any] | None:
    """Kayıtlı döküm: {"model", "sure_sn", "video_sn", "cumleler": [{"bas", "son", "metin"}]}; yoksa None."""
    try:
        return json.loads(_path(folder, source).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_model():
    if MODEL not in _MODELS:
        from faster_whisper import WhisperModel

        folder = data_dir() / "modeller"
        folder.mkdir(parents=True, exist_ok=True)
        _MODELS[MODEL] = WhisperModel(MODEL, device="cpu", compute_type="int8", download_root=str(folder))
    return _MODELS[MODEL]


def hints(text: str, limit: int = 20) -> str:
    """Haberin metnindeki özel adlar (cümle başı olmayan büyük harfli kelimeler): modele ipucu, "Heimlich" "hemlik"
    olarak yazılmasın. Cümle başındaki kelimeler (her kelime olabilir) alınmaz."""
    found: list[str] = []
    for match in NAME.finditer(text):
        before = text[:match.start()].rstrip()
        if not before or before[-1] in ".!?:\"'“”‘’\n" or match.group() in found:
            continue
        found.append(match.group())
    return " ".join(found[:limit])


def _sound(word: str) -> str:
    """Karşılaştırma için okunuş: küçük harf, Türkçe harfler sadeleşir, yabancı yazım Türkçe okunuşa (ch → k)."""
    word = word.replace("I", "ı").replace("İ", "i").lower()
    for old, new in (("sch", "ş"), ("ch", "k"), ("ph", "f"), ("th", "t"), ("sh", "ş"), ("w", "v"), ("q", "k"),
                     ("x", "ks")):
        word = word.replace(old, new)
    return word.translate(str.maketrans("ıiöüşçğâîû", "iiouscgaiu"))


def fix_names(words: list[tuple[float, float, str]], names: str) -> list[tuple[float, float, str]]:
    """Haberdeki özel adlara okunuşu benzeyen kelimeler haberdeki yazımla (Whisper "Heimlich"i "Hemlik" yazıyordu;
    `hotwords` yetmedi). Ek kesme işaretinden sonra korunur ("Hemlik'in" → "Heimlich'in"); API yok."""
    known = [(name, _sound(name)) for name in names.split()]
    fixed = []
    for start, end, text in words:
        match = re.fullmatch(r"(\s*)([^\W\d_]+)((?:['’][^\W\d_]+)?[^\w]*)", text)
        if match and len(match.group(2)) >= 4:
            root, sound = match.group(2), _sound(match.group(2))
            for name, name_sound in known:
                # Adın kendisi ya da eki ("Artvinli") ve adın başı olan kelime ("yılma" ↔ "Yılmaz") değişmez.
                if (not sound.startswith(name_sound) and not name_sound.startswith(sound) and sound[0] == name_sound[0]
                        and difflib.SequenceMatcher(None, sound, name_sound).ratio() >= NAME_MATCH):
                    text = match.group(1) + name + match.group(3)
                    break
        fixed.append((start, end, text))
    return fixed


def _split(group: list[tuple[float, float, str]]) -> list[list[tuple[float, float, str]]]:
    """Uzun parçayı en uzun aradan (virgül öne) böler; iki yan en az MIN_PART sn."""
    if group[-1][1] - group[0][0] <= MAX_SENTENCE:
        return [group]
    best, cut = -1.0, 0
    for i in range(1, len(group)):
        if group[i - 1][1] - group[0][0] < MIN_PART or group[-1][1] - group[i][0] < MIN_PART:
            continue
        gap = group[i][0] - group[i - 1][1] + (COMMA_BONUS if group[i - 1][2].rstrip().endswith((",", ";")) else 0)
        if gap > best:
            best, cut = gap, i
    return _split(group[:cut]) + _split(group[cut:]) if cut else [group]


def sentences(words: list[tuple[float, float, str]], duration: float) -> list[dict[str, Any]]:
    """Kelimelerden cümleler: nokta/soru/ünlemde, uzun sessizlikte; 7 sn'den uzunsa en uzun nefes arasından bölünür.
    Kesit payı: biraz önce başlar, biraz sonra biter ama sonraki kelimeye taşmaz."""
    sentences_: list[list[tuple[float, float, str]]] = []
    for word in words:
        current = sentences_[-1] if sentences_ else None
        if (current is None or current[-1][2].rstrip().endswith((".", "?", "!", "…"))
                or word[0] - current[-1][1] > SENTENCE_GAP):
            sentences_.append([word])
        else:
            current.append(word)
    groups = [part for group in sentences_ for part in _split(group)]
    result = []
    for number, group in enumerate(groups):
        text = "".join(w[2] for w in group).strip()
        if not text:
            continue
        previous_end = groups[number - 1][-1][1] if number else 0.0
        next_start = groups[number + 1][0][0] if number + 1 < len(groups) else duration or group[-1][1] + PAD_END
        start = max(previous_end, group[0][0] - PAD_START, 0.0)
        end = max(group[-1][1], min(group[-1][1] + PAD_END, next_start - NEXT_WORD_MARGIN))
        result.append({"bas": round(start, 2), "son": round(min(end, duration or end), 2), "metin": text})
    return result


def transcribe(source: Path, folder: Path, progress: Callable[[float], None] = lambda share: None,
               model: Any = None, context: str = "") -> dict[str, Any]:
    """Videonun konuşmasını cümlelere döker ve kaydeder. Sessiz yerler atlanır (VAD); dil Türkçe; `context` haberin
    metni (özel adlar ipucu olur)."""
    started = time.monotonic()
    with _LOCK:
        model = model or _load_model()
        segments, info = model.transcribe(str(source), language=LANGUAGE, vad_filter=True, beam_size=5,
                                          condition_on_previous_text=False, word_timestamps=True,
                                          hotwords=hints(context) or None)
        duration = float(info.duration or 0)
        words: list[tuple[float, float, str]] = []
        for segment in segments:  # üreteç: döküm ilerledikçe gelir
            if duration and segment.start >= duration - 0.2 or HALLUCINATION.search(segment.text):
                continue  # videonun sonundan sonrası ya da sessizlikte uydurulan altyazı kalıbı
            words += [(w.start, min(w.end, duration or w.end), w.word) for w in (segment.words or [])
                      if not duration or w.start < duration]
            if duration:
                progress(min(1.0, segment.end / duration))
    result = {"model": MODEL, "surum": VERSION, "sure_sn": round(time.monotonic() - started, 1),
              "video_sn": round(duration, 1), "cumleler": sentences(fix_names(words, hints(context)), duration)}
    path = _path(folder, source)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def start(source: Path, folder: Path, model: Any = None, context: str = "") -> Job:
    """Arka planda döker (zaten sürüyorsa onu döndürür)."""
    key = str(_path(folder, source))
    job = _JOBS.get(key)
    if job and job.running:
        return job
    job = Job()

    def run() -> None:
        try:
            transcribe(source, folder, lambda share: setattr(job, "progress", share), model, context)
        except Exception as error:  # noqa: BLE001 — model inemedi, ses okunamadı: sayfada gösterilir
            job.error = str(error)[:400]
        finally:
            job.done = True

    job.thread = threading.Thread(target=run, daemon=True, name="axion-yazi")
    _JOBS[key] = job
    job.thread.start()
    return job


def job(source: Path, folder: Path) -> Job | None:
    return _JOBS.get(str(_path(folder, source)))


def span(sentences: list[dict[str, Any]], first: int, last: int) -> tuple[float, float]:
    """İki cümle arası (ikisi dahil) kaynak aralığı; sıra fark etmez."""
    low, high = sorted((first, last))
    return sentences[low]["bas"], sentences[high]["son"]
