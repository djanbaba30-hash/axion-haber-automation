"""Müzik altlığı (v4.0.0-alpha.4, editör: "sözsüz, telifsiz haber müziği; seslendirmenin altında kısılsın").

Hazır parçalar `assets/muzik/` (Axion için `uret.py` ile sentezlendi, telif yok). Editörün eklediği müzikler yalnız bu
bilgisayarda kalır (`data/varliklar/muzik`): repo herkese açık, başkasının müziği GitHub'a yüklenmez.
Son videoda müzik döngüyle videonun sonuna kadar çalar, başta/sonda yumuşak açılıp kapanır; seslendirme ve kaynak sesli
kesit konuşurken kısılır (sidechain), aradaki sessizlikte biraz açılır. Seviye parçaya göre ölçülür (LUFS).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from apps.video_studio.modules.render import measure_loudness

ROOT = Path(__file__).resolve().parents[2]
BUILTIN_DIR = ROOT / "assets" / "muzik"
BUILTIN = {"gundem": "Gündem (nötr)", "gerilim": "Gerilim (asayiş, son dakika)", "sakin": "Sakin (insan hikâyesi)"}
DEFAULT = "gundem"
OFF = "kapali"
EXTENSIONS = (".mp3", ".m4a", ".wav", ".ogg")
USER_PREFIX = "kendi:"
# Seviyeler: seslendirme -18 LUFS; müzik aradaki sessizlikte ~-25, konuşurken ~6 dB daha kısık.
MUSIC_LUFS = -25.0
MAX_BOOST_DB = 10.0
DUCK = "sidechaincompress=threshold=0.03:ratio=2.5:attack=60:release=550:makeup=1"
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


def mix_filters(voice: str, music: str, seconds: float, gain: float) -> list[str]:
    """Kurgunun sesi (`voice`, ör. "1:a") + müzik (`music`, döngülü giriş) → [aout]."""
    fmt = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    return [
        f"[{voice}]{fmt},asplit=2[voice][key]",
        f"[{music}]{fmt},atrim=duration={seconds:.3f},asetpts=PTS-STARTPTS,volume={gain}dB,"
        f"afade=t=in:d={FADE_IN},afade=t=out:st={max(0.0, seconds - FADE_OUT):.3f}:d={FADE_OUT}[bed]",
        f"[bed][key]{DUCK}[ducked]",
        "[voice][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.79:level=disabled[aout]",
    ]
