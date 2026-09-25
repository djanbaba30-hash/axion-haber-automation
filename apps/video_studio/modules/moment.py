"""Kaynak sesli kesit için olay anı (API yok): kesit penceresinin varsayılan aralığı olayın olduğu yer olsun.

Editör (v3.2): "otomatik kesit aldığı yer kazanın yaşandığı yerden alakasız" — varsayılan videonun ilk 5 sn'siydi.
360p önizlemeden saniyede 10 örnek:
- Hareket: kare farkı, 8x8 bloklarda en çok değişen 3 blok (güvenlik kamerasında olay küçük bir bölgede olur).
  Kesmelerde (tek karelik sıçrama) sahne ayrılır; elde çekimde (kamera sürekli sallanıyor) hareket sayılmaz.
- Ses: önceki 3 sn'ye göre ani yükselme ve ardından düşme (çarpma, fren, korna); sürekli ses (müzik) başlaması değil.
- Luna analizi varsa `action` rolündeki pencereler öne alınır (en güvenilir işaret).
Her örnekte "önceki 3 sn'ye göre ne kadar arttı" puanı; eşiği geçen yoksa aralık önerilmez (sessizce ilk 5 sn olay gibi
sunulmaz, editör elle seçer). Sonuç önizlemenin yanında JSON olarak saklanır (bir kez hesaplanır).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

RATE = 10  # örnek/sn
HEIGHT = 160  # hareket ölçümü için küçük gri kare
BLOCK = 8
BEFORE_S, AFTER_S = 2.0, 3.0  # önerilen aralık: olaydan 2 sn önce … 3 sn sonra
HISTORY_S = 3.0
MOTION_RATIO = 1.5  # blok hareketi önceki 3 sn'nin medyanının en az bu katı
AUDIO_RISE_DB = 10.0
AUDIO_DROP_DB = 4.0  # ani ses sonra düşer (çarpma); müziğin/konuşmanın başlaması olay değildir
SILENCE_DB = -50.0
HANDHELD = 3.0  # sahnenin tüm kare hareketi medyanı bunun üstündeyse elde çekim: hareket işareti kullanılmaz
CUT = 15.0  # tek örnekte tüm kare farkı bu kadar sıçrarsa kesme
ACTION_BOOST = 2.0  # Luna olay penceresi içinde yarı işaret yeter


def _raw(command: list[str]) -> bytes:
    result = subprocess.run(command, capture_output=True, timeout=300)
    return result.stdout if result.returncode == 0 else b""


def signals(video: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(blok hareketi, tüm kare hareketi, ses dB) — hepsi saniyede RATE örnek; ses yoksa boş."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
         str(video)], capture_output=True, text=True, timeout=60,
    ).stdout.strip().split(",")
    width, height = int(probe[0]), int(probe[1])
    frame_w = max(BLOCK, int(round(width * HEIGHT / height / BLOCK)) * BLOCK)
    frames = np.frombuffer(_raw([
        "ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={RATE},scale={frame_w}:{HEIGHT},format=gray",
        "-f", "rawvideo", "-",
    ]), np.uint8)
    frames = frames[: len(frames) // (HEIGHT * frame_w) * HEIGHT * frame_w].reshape(-1, HEIGHT, frame_w)
    diff = np.abs(np.diff(frames.astype(np.float32), axis=0))
    blocks = diff.reshape(len(diff), HEIGHT // BLOCK, BLOCK, frame_w // BLOCK, BLOCK).mean((2, 4)).reshape(len(diff), -1)
    local = np.sort(blocks, axis=1)[:, -3:].mean(1) if len(blocks) else np.zeros(0)
    whole = blocks.mean(1) if len(blocks) else np.zeros(0)
    samples = np.frombuffer(_raw([
        "ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-",
    ]), np.int16).astype(np.float32) / 32768
    step = 8000 // RATE
    count = len(samples) // step
    rms = np.sqrt((samples[: count * step].reshape(count, step) ** 2).mean(1)) if count else np.zeros(0)
    return local, whole, 20 * np.log10(rms + 1e-6)


def _smooth(values: np.ndarray, width: int) -> np.ndarray:
    return np.convolve(values, np.ones(width) / width, mode="same") if len(values) >= width else values


def scores(local: np.ndarray, whole: np.ndarray, loudness: np.ndarray) -> np.ndarray:
    """Her örnek için "ani olay" puanı (1 = eşik)."""
    count = max(len(local), len(loudness))
    score = np.zeros(count)
    history = int(HISTORY_S * RATE)
    # Kesmeler: tüm kare farkında tek örneklik sıçrama → sahneleri ayır.
    cuts = [0] + [i for i in range(len(whole)) if whole[i] > CUT and whole[i] > 4 * max(
        whole[max(i - 1, 0)] if i else 0, whole[i + 1] if i + 1 < len(whole) else 0, 1.0)] + [len(local)]
    for start, end in zip(cuts, cuts[1:]):
        start += 1 if start else 0  # kesme örneğinin kendisi olay değildir
        if end - start < RATE or np.median(whole[start:end]) > HANDHELD:
            continue
        motion = np.zeros(len(local))
        motion[start:end] = _smooth(local[start:end], 5)  # yumuşatma kesmeyi aşmasın
        for i in range(start + RATE, end):
            base = np.median(local[max(start, i - history):i - 2])
            score[i] = max(score[i], motion[i] / max(base, 1.0) / MOTION_RATIO)
    if len(loudness) and loudness.max() > SILENCE_DB:  # ses var
        loud = _smooth(np.maximum(loudness, SILENCE_DB), 3)
        for i in range(RATE, len(loud) - RATE):
            before = np.median(loud[max(0, i - history):i - 2])
            after = np.median(loud[i + 5:i + 15])
            if loud[i] - after >= AUDIO_DROP_DB:
                score[i] = max(score[i], (loud[i] - before) / AUDIO_RISE_DB)
    return score


def find_moment(score: np.ndarray, actions: list[tuple[float, float]] = ()) -> float | None:
    """Olay anı (sn) ya da None (belirgin bir an yok)."""
    boosted = score.copy()
    for start, end in actions:
        boosted[int(start * RATE):int(end * RATE) + 1] *= ACTION_BOOST
    if len(boosted) and boosted.max() >= 1.0:
        return float(np.argmax(boosted)) / RATE
    if actions:  # işaret yok ama Luna olay penceresi buldu: başına
        return actions[0][0] + BEFORE_S
    return None


def moment_range(moment: float | None, duration: float) -> tuple[float, float] | None:
    if moment is None:
        return None
    start = max(0.0, min(moment - BEFORE_S, duration - BEFORE_S - AFTER_S))
    return round(start, 1), round(min(duration, start + BEFORE_S + AFTER_S), 1)


def action_windows(media_library: dict[str, Any] | None, filename: str) -> list[tuple[float, float]]:
    """Luna'nın bu videoda `action` dediği pencereler (sn)."""
    windows = []
    for asset in (media_library or {}).get("assets", []):
        if asset.get("source", {}).get("filename") != filename:
            continue
        for shot in asset.get("shots", []):
            for window in shot.get("analysis_windows", []) or [shot]:
                visual = window.get("visual") or shot.get("visual") or {}
                if visual.get("editorial_role") == "action":
                    windows.append((float(window["start_seconds"]), float(window["end_seconds"])))
    return sorted(windows)


def suggested_range(preview: Path, duration: float, actions: list[tuple[float, float]] = ()) -> tuple[float, float] | None:
    """Önizlemeden önerilen kesit aralığı; puanlar önizlemenin yanında saklanır (bir kez hesaplanır)."""
    cache = preview.with_suffix(".an.json")
    try:
        score = np.array(json.loads(cache.read_text(encoding="utf-8")), dtype=float)
    except (OSError, ValueError):
        try:
            score = scores(*signals(preview))
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            return None
        cache.write_text(json.dumps([round(float(v), 2) for v in score]), encoding="utf-8")
    return moment_range(find_moment(score, actions), duration)
