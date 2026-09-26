"""Müzik altlığı (v4.0.0-alpha.4, editör: "sözsüz, telifsiz haber müziği; seslendirmenin altında kısılsın").

Hazır parçalar `assets/muzik/` (Axion için `uret.py` ile sentezlendi, telif yok). Editörün eklediği müzikler yalnız bu
bilgisayarda kalır (`data/varliklar/muzik`): repo herkese açık, başkasının müziği GitHub'a yüklenmez.
Son videoda müzik döngüyle videonun sonuna kadar çalar, başta/sonda yumuşak açılıp kapanır. Seviye (editör, alpha.4
denemesi): konuşma varken (seslendirmenin tamamı, röportaj ya da konuşmalı kesit) "varla yok arası"; konuşmasız
kesitlerde ve sessiz kısımlarda duyulur ama yüksek değil. Kesitte konuşma olup olmadığı sesten anlaşılır
(`video_studio/modules/speech.py`, API yok); geçişler yarım saniyede yumuşakça.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from typing import Any

from apps.video_studio.modules.render import measure_loudness
from apps.video_studio.modules.speech import has_speech

ROOT = Path(__file__).resolve().parents[2]
BUILTIN_DIR = ROOT / "assets" / "muzik"
BUILTIN = {"gundem": "Gündem (nötr)", "gerilim": "Gerilim (asayiş, son dakika)", "sakin": "Sakin (insan hikâyesi)"}
DEFAULT = "gundem"
OFF = "kapali"
EXTENSIONS = (".mp3", ".m4a", ".wav", ".ogg")
USER_PREFIX = "kendi:"
# Seviyeler: seslendirme -18, kesit -20 LUFS. Müzik konuşmasız yerde -27 (duyulur, kesitin altında), konuşurken 18 dB
# daha kısık (-45: varla yok arası).
MUSIC_LUFS = -27.0
SPEECH_DUCK_DB = -18.0
RAMP = 0.5
MAX_BOOST_DB = 10.0
FADE_IN, FADE_OUT = 0.4, 1.5


def user_dir() -> Path:
    return Path(os.environ.get("AXION_DATA_DIR") or ROOT / "data") / "varliklar" / "muzik"


def tracks() -> dict[str, str]:
    """Seçilebilir müzikler: {kimlik: ad}; önce hazırlar, sonra editörün ekledikleri."""
    found = {name: label for name, label in BUILTIN.items() if (BUILTIN_DIR / f"{name}.mp3").exists()}
    folder = user_dir()
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in EXTENSIONS:
                found[USER_PREFIX + path.name] = f"{path.stem} (eklenen)"
    return found


def path(track: str | None) -> Path | None:
    """Müziğin dosyası; kapalı ya da dosya yoksa (silinmiş) None."""
    if not track or track == OFF:
        return None
    if track.startswith(USER_PREFIX):
        candidate = user_dir() / Path(track[len(USER_PREFIX):]).name
    else:
        candidate = BUILTIN_DIR / f"{Path(track).name}.mp3"
    return candidate if candidate.is_file() else None


def add(filename: str, data: bytes) -> str:
    """Editörün müziği (yalnız bu bilgisayarda). Döndürür: kimlik."""
    name = Path(filename).name
    if Path(name).suffix.lower() not in EXTENSIONS:
        raise ValueError("Müzik MP3, M4A, WAV ya da OGG olmalı.")
    if not data:
        raise ValueError("Dosya boş.")
    name = re.sub(r"[^\w.\- ]", "_", name)
    folder = user_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return USER_PREFIX + name


def gain_db(file: Path) -> float:
    measured = measure_loudness(str(file))
    return 0.0 if measured is None else round(min(MUSIC_LUFS - measured, MAX_BOOST_DB), 2)


def speech_spans(edit_project: dict[str, Any] | None, rough_cut: Path) -> list[tuple[float, float]] | None:
    """Videoda konuşma olan aralıklar (sn): seslendirmenin tamamı + konuşmalı kaynak sesli kesitler. Kurgu bilgisi yoksa
    None (çağıran tüm videoyu konuşma sayar: müzik hep kısık, güvenli taraf)."""
    try:
        timeline = edit_project["edit_plan"]["timeline"]
        fps, audio = timeline["fps"], edit_project["audio"]
        tracks = timeline["tracks"]
    except (KeyError, TypeError):
        return None
    spans = []
    for track in tracks:
        for clip in track["clips"]:
            start = clip["start_f"] / fps
            if track["kind"] == "audio" and clip.get("asset_id") == audio.get("asset_id"):
                spans.append((start, start + float(audio.get("duration_seconds") or 0)))
            elif track["kind"] == "video" and clip.get("use_source_audio"):
                seconds = clip["duration_f"] / fps
                speaking = has_speech(str(rough_cut), start, seconds)
                if speaking or speaking is None:  # anlaşılamadıysa konuşma say (müzik kısık kalır)
                    spans.append((start, start + seconds))
    return sorted(spans)


def duck_expression(spans: list[tuple[float, float]] | None, seconds: float) -> str:
    """Müziğin zamanla kazancı (FFmpeg ifadesi, dB): konuşmada SPEECH_DUCK_DB, arada 0; RAMP'lik yumuşak geçiş."""
    spans = [(0.0, seconds)] if spans is None else spans
    weights = [f"clip(min((t-{start - RAMP:.3f})/{RAMP},({end + RAMP:.3f}-t)/{RAMP}),0,1)" for start, end in spans]
    if not weights:
        return "0"
    combined = weights[0]
    for weight in weights[1:]:
        combined = f"max({combined},{weight})"
    return f"{SPEECH_DUCK_DB}*{combined}"


def mix_filters(voice: str, music: str, seconds: float, gain: float,
                spans: list[tuple[float, float]] | None = None) -> list[str]:
    """Kurgunun sesi (`voice`, ör. "1:a") + müzik (`music`, döngülü giriş) → [aout]. `spans`: konuşma aralıkları."""
    fmt = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    return [
        f"[{voice}]{fmt}[voice]",
        f"[{music}]{fmt},atrim=duration={seconds:.3f},asetpts=PTS-STARTPTS,"
        f"volume='pow(10,({gain}+{duck_expression(spans, seconds)})/20)':eval=frame,"
        f"afade=t=in:d={FADE_IN},afade=t=out:st={max(0.0, seconds - FADE_OUT):.3f}:d={FADE_OUT}[bed]",
        "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.79:level=disabled[aout]",
    ]
