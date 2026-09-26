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
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from apps.axion_local.store import data_dir

MODEL = "large-v3-turbo"
LANGUAGE = "tr"
FOLDER = "yazi"
VERSION = 4  # döküm biçimi (v4: büyük harf/fiil sonunda cümle, sesin bittiği yer); değişince yeniden yapılır
PAD_START, PAD_END = 0.1, 0.25  # kesit cümlenin biraz önce/sonrasından (ilk/son hece kesilmesin)
NEXT_WORD_MARGIN = 0.08  # ...ama sonraki kelimeye taşmadan (editör: "sonraki kelimenin ortasında bitiyor")
SENTENCE_GAP = 1.2  # kelimeler arası bu kadar sessizlik varsa yeni cümle
# Konuşma dilinde Whisper çoğu zaman nokta koymaz ama cümle başını büyük harfle yazar ("…fark ettim Beyefendiye…"):
# büyük harfli kelime (haberdeki özel adlar hariç) yeni cümle başlatır. Yine uzun kalan parça (MAX_SENTENCE) fiil
# sonunda ("koştu", "ettim", "uyguladım") ya da en uzun nefes arasında bölünür; tek kelimelik cümle öncekine katılır.
MAX_SENTENCE = 8.0
MIN_PART = 1.5  # bölünen parçaların en kısası
SHORT = 1.0  # bundan kısa (ya da tek kelimelik) cümle öncekine katılır
COMMA_BONUS = 0.3  # sn: virgülden sonraki ara bu kadar daha uzun sayılır
VERB_BONUS = 0.4  # sn: çekimli fiilden sonraki ara bu kadar daha uzun sayılır (Türkçe cümle fiille biter)
VERB_END = re.compile(r"""(?:[dt][ıiuü](?:m|n|k|nız|niz|nuz|nüz|lar|ler)?   # koştu, ettim, içirdik
                             |yor(?:um|sun|uz|sunuz|lar)?                    # geliyor
                             |m[ıiuü]ş(?:ım|im|um|üm|ız|iz|uz|üz|lar|ler)?   # almış
                             |[ae]c[ae]k(?:ım|im|ız|iz|lar|ler)?)$""", re.X)  # gelecek
NAME_MATCH = 0.8  # özel ad düzeltmesi: okunuşu bu kadar benzeyen kelime haberdeki yazımla değişir
# Kelime zamanı sesle düzeltilir: Whisper son kelimeleri bazen yazmıyor ya da erken bitiriyor (Artvin: "yanıma
# [doğru koştu]" 53,7'de bitiyordu, ses 54,1'de) → kesit sesin sustuğu yere kadar uzar (sonraki kelimeyi geçmez).
LEVEL_STEP = 0.02  # sn: ses seviyesi çözünürlüğü
VOICE_DB = 12.0  # konuşma arasındaki sessizliğin (en sessiz %10) bu kadar üstü "ses var"
MAX_EXTEND = 1.5  # sn: kelime zamanından en fazla bu kadar uzar
HOLD = 0.15  # sn: hece arasındaki bu kadarlık düşüş "sustu" sayılmaz
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
    """Haberin metnindeki özel adlar (cümle başı olmayan büyük harfli kelimeler): dökümde yazımları düzeltilir
    (`fix_names`) ve cümle başı sayılmazlar. Cümle başındaki kelimeler (her kelime olabilir) alınmaz."""
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


def _word(text: str) -> str:
    return re.sub(r"[^\w'’]", "", text)


def _verb(text: str) -> bool:
    return bool(VERB_END.search(_word(text).replace("I", "ı").lower()))


def _split(group: list[tuple[float, float, str]]) -> list[list[tuple[float, float, str]]]:
    """Uzun parçayı fiil sonundan ya da en uzun aradan (virgül öne) böler; iki yan en az MIN_PART sn."""
    if group[-1][1] - group[0][0] <= MAX_SENTENCE:
        return [group]
    best, cut = -1.0, 0
    for i in range(1, len(group)):
        if group[i - 1][1] - group[0][0] < MIN_PART or group[-1][1] - group[i][0] < MIN_PART:
            continue
        previous = group[i - 1][2].rstrip()
        gap = (group[i][0] - group[i - 1][1] + (COMMA_BONUS if previous.endswith((",", ";")) else 0)
               + (VERB_BONUS if _verb(previous) else 0))
        if gap > best:
            best, cut = gap, i
    return _split(group[:cut]) + _split(group[cut:]) if cut else [group]


def levels(source: Path) -> np.ndarray | None:
    """Sesin seviyesi (dB, LEVEL_STEP aralıkla); okunamazsa None (kelime zamanları olduğu gibi kalır)."""
    rate = 16000
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(source), "-vn", "-ac", "1", "-ar", str(rate),
                              "-f", "s16le", "-"], capture_output=True, timeout=600).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    step = int(rate * LEVEL_STEP)
    samples = np.frombuffer(raw[: len(raw) // 2 * 2], np.int16).astype(np.float32) / 32768
    count = len(samples) // step
    if count < 10:
        return None
    rms = np.sqrt((samples[: count * step].reshape(count, step) ** 2).mean(1))
    return 20 * np.log10(rms + 1e-6)


def _voiced(level: np.ndarray | None, start: float, end: float) -> Callable[[float], bool]:
    """"Ses var mı": sessizlik tabanı konuşmanın geçtiği aralıktan (videonun sessiz/boş kısımları tabanı düşürmesin)."""
    region = level[int(start / LEVEL_STEP):int(end / LEVEL_STEP) + 1] if level is not None else np.zeros(0)
    region = region[region > -90]
    if len(region) < 10:
        return lambda time: False
    # Konuşma sürekliyse (sessizlik %10'dan az) taban konuşmanın kendisi olur: orta seviyenin 6 dB altı da ses sayılır.
    threshold = min(float(np.percentile(region, 10)) + VOICE_DB, float(np.median(region)) - 6)
    return lambda time: 0 <= int(time / LEVEL_STEP) < len(level) and level[int(time / LEVEL_STEP)] > threshold


def sentences(words: list[tuple[float, float, str]], duration: float, names: str = "",
              level: np.ndarray | None = None) -> list[dict[str, Any]]:
    """Kelimelerden cümleler: nokta/soru/ünlemde, uzun sessizlikte, büyük harfle başlayan kelimede (`names` hariç);
    8 sn'den uzunsa bölünür, tek kelimelik ya da 1 sn'den kısası öncekine katılır. Son kelimeden sonra ses (`level`)
    sürüyorsa kesit uzar. Kesit payı: biraz önce başlar, biraz sonra biter ama sonraki kelimeye taşmaz."""
    known = {name.lower() for name in names.split()}
    sentences_: list[list[tuple[float, float, str]]] = []
    for word in words:
        current = sentences_[-1] if sentences_ else None
        token = _word(word[2])
        capital = token[:1].isupper() and re.split(r"['’]", token.lower())[0] not in known
        if (current is None or current[-1][2].rstrip().endswith((".", "?", "!", "…"))
                or word[0] - current[-1][1] > SENTENCE_GAP or capital):
            sentences_.append([word])
        else:
            current.append(word)
    merged: list[list[tuple[float, float, str]]] = []
    for group in sentences_:  # "Uğurladık" tek başına kesit olmaz: öncekine katılır (arada uzun sessizlik yoksa)
        if (merged and (len("".join(w[2] for w in group).split()) == 1 or group[-1][1] - group[0][0] < SHORT)
                and group[0][0] - merged[-1][-1][1] <= SENTENCE_GAP):
            merged[-1] = merged[-1] + group
        else:
            merged.append(group)
    groups = [part for group in merged for part in _split(group)]
    voiced = _voiced(level, groups[0][0][0], groups[-1][-1][1]) if groups else _voiced(None, 0, 0)
    result = []
    for number, group in enumerate(groups):
        text = "".join(w[2] for w in group).strip()
        if not text:
            continue
        previous_end = groups[number - 1][-1][1] if number else 0.0
        next_start = groups[number + 1][0][0] if number + 1 < len(groups) else duration or group[-1][1] + PAD_END
        first, last = group[0][0], group[-1][1]
        limit, probe = min(next_start - NEXT_WORD_MARGIN, last + MAX_EXTEND), last
        while probe < limit and probe - last <= HOLD:  # ses sürüyor: Whisper son kelimeyi erken bitirdi ya da yazmadı
            if voiced(probe):
                last = min(probe + LEVEL_STEP, limit)
            probe += LEVEL_STEP
        start = max(previous_end, first - PAD_START, 0.0)
        end = max(last, min(last + PAD_END, next_start - NEXT_WORD_MARGIN))
        result.append({"bas": round(start, 2), "son": round(min(end, duration or end), 2), "metin": text})
    return result


def transcribe(source: Path, folder: Path, progress: Callable[[float], None] = lambda share: None,
               model: Any = None, context: str = "") -> dict[str, Any]:
    """Videonun konuşmasını cümlelere döker ve kaydeder. Sessiz yerler atlanır (VAD); dil Türkçe; `context` haberin
    metni (özel adlar ipucu olur)."""
    started = time.monotonic()
    with _LOCK:
        model = model or _load_model()
        # Özel adlar modele ipucu (hotwords) olarak gitmez: alpha.7.1'de "Hemlik"i düzeltmedi; yazım `fix_names` ile.
        segments, info = model.transcribe(str(source), language=LANGUAGE, vad_filter=True, beam_size=5,
                                          condition_on_previous_text=False, word_timestamps=True)
        duration = float(info.duration or 0)
        words: list[tuple[float, float, str]] = []
        raw: list[dict[str, Any]] = []  # Whisper'ın bölümleri olduğu gibi (teşhis dosyası için; sayfada kullanılmaz)
        for segment in segments:  # üreteç: döküm ilerledikçe gelir
            raw.append({"bas": round(segment.start, 2), "son": round(segment.end, 2), "metin": segment.text.strip()})
            if duration and segment.start >= duration - 0.2 or HALLUCINATION.search(segment.text):
                continue  # videonun sonundan sonrası ya da sessizlikte uydurulan altyazı kalıbı
            words += [(w.start, min(w.end, duration or w.end), w.word) for w in (segment.words or [])
                      if not duration or w.start < duration]
            if duration:
                progress(min(1.0, segment.end / duration))
    names = hints(context)
    lines = sentences(fix_names(words, names), duration, names, levels(source))
    result = {"model": MODEL, "surum": VERSION, "sure_sn": round(time.monotonic() - started, 1),
              "video_sn": round(duration, 1), "cumleler": lines, "bolumler": raw}
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
