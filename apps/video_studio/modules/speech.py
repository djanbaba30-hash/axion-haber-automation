"""Seste konuşma var mı (v4.0.0-alpha.4; API yok, numpy): müzik altlığı konuşmada "varla yok arası" kısılır.

Kepstrum ile perdeli (sesli harf) kareler sayılır: konuşmada sesli karelerin bir kısmı perdelidir (ünsüzler ve nefes
araları değil), gürültüde (trafik, kalabalık uğultusu, çarpma, yangın) neredeyse hiçbiri; siren/korna gibi kesintisiz
perdeli sesler de hemen hepsidir. Kaba bir tespit (sandbox'ta sentez konuşma ve gürültülerle ayarlandı); yerel yazıya
dökme (4.0 alpha.7) gelince onunla değiştirilebilir.
"""

from __future__ import annotations

import subprocess

import numpy as np

from .ffmpeg_runner import FRAME_TIMEOUT_SECONDS

RATE = 16000
FRAME, HOP, FFT = 640, 160, 1024  # 40 ms kare (alçak ses perdesi sığsın), 10 ms adım
CEPSTRUM_PEAK = 0.22  # kare perdeli: 70–400 Hz'lik perdede kepstrum tepesi
VOICED_MIN, VOICED_MAX = 0.25, 0.85  # konuşma: sesli karelerin %25–85'i perdeli (gürültü ~0, siren ~1)


def _samples(path: str, start: float, seconds: float) -> np.ndarray | None:
    command = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{seconds:.3f}", "-i", path, "-vn", "-ac", "1",
               "-ar", str(RATE), "-f", "f32le", "-"]
    try:
        result = subprocess.run(command, capture_output=True, timeout=FRAME_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    audio = np.frombuffer(result.stdout, dtype="<f4")
    return audio if audio.size >= RATE else None  # 1 sn'den kısa: karar verilemez


def voiced_share(audio: np.ndarray) -> float:
    """Sesli (sessiz olmayan) karelerin perdeli olan payı."""
    count = 1 + (audio.size - FRAME) // HOP
    frames = np.lib.stride_tricks.sliding_window_view(audio, FRAME)[::HOP][:count] * np.hanning(FRAME)
    spectrum = np.abs(np.fft.rfft(frames, n=FFT, axis=1)) ** 2
    freqs = np.fft.rfftfreq(FFT, 1 / RATE)
    level = 10 * np.log10(spectrum[:, (freqs >= 250) & (freqs <= 3500)].sum(axis=1) + 1e-12)
    active = level > max(np.percentile(level, 95) - 30, level.min() + 6)
    if not active.any():
        return 0.0
    cepstrum = np.fft.irfft(np.log(spectrum + 1e-10), axis=1)
    peak = cepstrum[:, RATE // 400: RATE // 70].max(axis=1)
    return float((peak[active] > CEPSTRUM_PEAK).mean())


def has_speech(path: str, start: float = 0.0, seconds: float = 0.0) -> bool | None:
    """Parçada konuşma var mı; ses okunamazsa ya da 1 sn'den kısaysa None (çağıran kendi varsayımını kullanır)."""
    audio = _samples(path, start, seconds or 3600.0)
    if audio is None:
        return None
    if np.abs(audio).max() < 1e-4:
        return False
    return VOICED_MIN <= voiced_share(audio) <= VOICED_MAX
