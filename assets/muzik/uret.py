"""Axion'un müzik altlıklarını üretir (v4.0.0-alpha.4): sözsüz, döngülü haber müzikleri; yalnız numpy + FFmpeg.

Parçalar bu betikle sıfırdan sentezlendi (örnek/kayıt yok): telif yok, Axion'a ait (CC0 olarak kullanılabilir).
Her şey dairesel (FFT) hesaplanır: yankı ve nota kuyrukları başa sarar, parça dikişsiz döngü olur.
Yeniden üretmek: `python assets/muzik/uret.py` (aynı tohum → aynı dosyalar).
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

RATE = 44100
HERE = Path(__file__).resolve().parent
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}


def freq(name: str) -> float:
    """"A3" → 220 Hz."""
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTES[pitch] + 12 * (octave + 1) - 69) / 12)


class Track:
    def __init__(self, bpm: float, bars: int, seed: int):
        self.beat = 60.0 / bpm
        self.length = round(bars * 4 * self.beat * RATE)
        self.rng = np.random.default_rng(seed)
        self.stems: dict[str, np.ndarray] = {}

    def stem(self, name: str) -> np.ndarray:
        return self.stems.setdefault(name, np.zeros((2, self.length)))

    def add(self, name: str, start_beat: float, sound: np.ndarray, pan: float = 0.0) -> None:
        """Sesi dairesel yerleştirir (parça sonundan taşan baştan devam eder)."""
        buffer = self.stem(name)
        index = (round(start_beat * self.beat * RATE) + np.arange(sound.shape[-1])) % self.length
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        np.add.at(buffer[0], index, sound * left * np.sqrt(2))
        np.add.at(buffer[1], index, sound * right * np.sqrt(2))

    def mix(self, levels: dict[str, float], reverb: dict[str, float], lowpass: dict[str, float],
            highpass: dict[str, float] | None = None) -> np.ndarray:
        out = np.zeros((2, self.length))
        spectrum_f = np.fft.rfftfreq(self.length, 1 / RATE)
        for name, buffer in self.stems.items():
            spectrum = np.fft.rfft(buffer, axis=-1)
            if name in lowpass:
                spectrum *= 1 / np.sqrt(1 + (spectrum_f / lowpass[name]) ** 4)
            if highpass and name in highpass:
                spectrum *= 1 / np.sqrt(1 + (highpass[name] / np.maximum(spectrum_f, 1)) ** 4)
            dry = np.fft.irfft(spectrum, n=self.length, axis=-1)
            wet = self._reverb(spectrum) if reverb.get(name) else 0
            out += levels[name] * ((1 - reverb.get(name, 0)) * dry + reverb.get(name, 0) * wet)
        return out

    def _reverb(self, spectrum: np.ndarray, seconds: float = 2.6) -> np.ndarray:
        n = int(seconds * RATE)
        t = np.arange(n) / RATE
        wet = []
        for channel in range(2):  # sağ/sol ayrı gürültü: geniş yankı
            impulse = np.zeros(self.length)
            impulse[:n] = self.rng.standard_normal(n) * np.exp(-t * 6.9 / seconds) * (1 - np.exp(-t * 400))
            response = np.fft.rfft(impulse)
            response *= 1 / np.sqrt(1 + (np.fft.rfftfreq(self.length, 1 / RATE) / 5000) ** 2)  # koyu yankı
            wet.append(np.fft.irfft(spectrum[channel] * response, n=self.length))
        wet = np.array(wet)
        return wet / (np.sqrt(np.mean(wet ** 2)) + 1e-9) * 0.05


def envelope(n: int, attack: float, release: float, decay: float | None = None) -> np.ndarray:
    t = np.arange(n) / RATE
    env = np.minimum(1, t / max(attack, 1e-4))
    if decay:
        env *= np.exp(-t / decay)
    tail = int(release * RATE)
    if tail:
        env[-tail:] *= np.linspace(1, 0, tail) ** 2
    return env


def pad(f: float, seconds: float, rng: np.random.Generator, voices: int = 3, bright: int = 12) -> np.ndarray:
    """Yumuşak pad: hafif akortsuz, harmonikleri azaltılmış testere (sıcak, sert değil)."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    wave_ = np.zeros(n)
    for v in range(voices):
        detune = f * 2 ** ((v - (voices - 1) / 2) * 0.08 / 12)
        phase = rng.uniform(0, 2 * np.pi)
        for k in range(1, bright + 1):
            wave_ += np.sin(2 * np.pi * detune * k * t + phase * k) / k ** 1.6
    return wave_ / voices * envelope(n, attack=seconds * 0.35, release=seconds * 0.35)


def pluck(f: float, seconds: float, decay: float = 0.6, harmonics: int = 8) -> np.ndarray:
    """Piyano benzeri tel: tiz harmonikler daha hızlı söner."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    wave_ = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * k / decay) / k ** 1.2 for k in range(1, harmonics + 1))
    return wave_ * envelope(n, attack=0.004, release=0.05)


def bass(f: float, seconds: float) -> np.ndarray:
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    wave_ = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return wave_ * envelope(n, attack=0.006, release=seconds * 0.4, decay=seconds * 0.9)


def kick() -> np.ndarray:
    n = int(0.45 * RATE)
    t = np.arange(n) / RATE
    pitch = 45 + 70 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(pitch) / RATE) * np.exp(-t * 9)


def tick(rng: np.random.Generator, bright: float = 1.0) -> np.ndarray:
    """Saat tıkırtısı: çok kısa, tiz."""
    n = int(0.03 * RATE)
    t = np.arange(n) / RATE
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)  # tizleştir
    return (noise * 0.5 + np.sin(2 * np.pi * 3200 * bright * t)) * np.exp(-t * 260)


def boom(rng: np.random.Generator) -> np.ndarray:
    """Timpani benzeri alçak vuruş (gerilim geçişleri)."""
    n = int(2.5 * RATE)
    t = np.arange(n) / RATE
    body = np.sin(2 * np.pi * (48 + 20 * np.exp(-t * 6)) * t) * np.exp(-t * 1.6)
    return body + 0.15 * rng.standard_normal(n) * np.exp(-t * 18)


def chord_tones(root: str, minor: bool) -> list[str]:
    base = NOTES[root[:-1]] + 12 * (int(root[-1]) + 1)
    names = [k for k in NOTES if len(k) == 1 or k in ("C#", "Eb", "F#", "Ab", "Bb")]
    by_pitch = {NOTES[k]: k for k in names}

    def name(midi: int) -> str:
        return f"{by_pitch[midi % 12]}{midi // 12 - 1}"
    return [name(base), name(base + (3 if minor else 4)), name(base + 7), name(base + 12)]


def master(audio: np.ndarray, peak_db: float = -1.5) -> np.ndarray:
    audio = audio - audio.mean(axis=-1, keepdims=True)
    audio = audio / (np.sqrt(np.mean(audio ** 2)) + 1e-9) * 0.12  # ~-18 dBFS RMS
    audio = np.tanh(audio * 1.3) / 1.3  # yumuşak sınırlama
    return audio / max(1e-9, np.abs(audio).max()) * 10 ** (peak_db / 20)


def gundem() -> np.ndarray:
    """Nötr gündem altlığı: 96 BPM, La minör (Am–F–C–G), nabız bas, pad, arpej, saat tıkırtısı."""
    track = Track(96, 32, seed=1)
    progression = [("A2", True), ("F2", False), ("C3", False), ("G2", False)]
    for bar in range(32):
        root, minor = progression[(bar // 2) % 4]
        tones = chord_tones(root, minor)
        beat0 = bar * 4
        if bar % 2 == 0:
            for number, note in enumerate(tones[1:]):
                up = note[:-1] + str(int(note[-1]) + 1)
                track.add("pad", beat0, pad(freq(up), 8 * track.beat + 1.2, track.rng), pan=(number - 1) * 0.5)
        for eighth in range(8):
            track.add("bass", beat0 + eighth / 2, bass(freq(tones[0]), track.beat / 2 * 0.9) * (1 if eighth % 2 == 0 else 0.6))
        if bar >= 4:  # giriş sakin, sonra arpej
            pattern = [0, 2, 1, 3, 2, 1, 3, 2]
            for eighth, pick in enumerate(pattern):
                note = tones[pick]
                high = note[:-1] + str(int(note[-1]) + 2)
                track.add("arp", beat0 + eighth / 2, pluck(freq(high), 1.2, decay=0.5), pan=0.35 if eighth % 2 else -0.35)
        for beat in (0, 2):
            track.add("kick", beat0 + beat, kick())
        for sixteenth in range(16):
            track.add("tick", beat0 + sixteenth / 4, tick(track.rng) * (1 if sixteenth % 4 == 0 else 0.45), pan=0.2)
    audio = track.mix(levels={"pad": 0.5, "bass": 0.55, "arp": 0.22, "kick": 0.35, "tick": 0.05},
                      reverb={"pad": 0.45, "arp": 0.5, "tick": 0.3}, lowpass={"pad": 1800, "bass": 400, "arp": 3500},
                      highpass={"tick": 3000})
    return master(audio)


def gerilim() -> np.ndarray:
    """Asayiş / son dakika: 110 BPM, Re minör (Dm–Dm–Bb–A), 16'lık bas ostinatosu, koyu pad, tıkırtı, vuruşlar."""
    track = Track(110, 32, seed=2)
    progression = [("D2", True), ("D2", True), ("Bb1", False), ("A1", False)]
    ostinato = [0, 0, 2, 0, 0, 3, 0, 2, 0, 0, 2, 0, 3, 0, 2, 1]
    for bar in range(32):
        root, minor = progression[(bar // 2) % 4]
        tones = chord_tones(root, minor)
        beat0 = bar * 4
        if bar % 2 == 0:
            for number, note in enumerate(tones[:3]):
                up = note[:-1] + str(int(note[-1]) + 2)
                track.add("pad", beat0, pad(freq(up), 8 * track.beat + 1.5, track.rng, bright=8), pan=(number - 1) * 0.6)
        for sixteenth, pick in enumerate(ostinato):
            note = tones[pick if pick < 3 else 0]
            octave = note[:-1] + str(int(note[-1]) + (1 if pick == 3 else 0))
            track.add("bass", beat0 + sixteenth / 4, bass(freq(octave), track.beat / 4 * 0.85) * (1 if sixteenth % 4 == 0 else 0.7))
        for eighth in range(8):
            track.add("tick", beat0 + eighth / 2, tick(track.rng, 0.8) * (1 if eighth % 2 == 0 else 0.6), pan=-0.25)
        if bar % 4 == 0:
            track.add("boom", beat0, boom(track.rng))
        if bar % 8 in (4, 5, 6, 7):  # yüksek, uzun gerilim notası
            if bar % 8 == 4:
                track.add("high", beat0, pad(freq("A4"), 16 * track.beat, track.rng, voices=2, bright=5), pan=0.3)
    audio = track.mix(levels={"pad": 0.45, "bass": 0.6, "tick": 0.06, "boom": 0.5, "high": 0.18},
                      reverb={"pad": 0.5, "boom": 0.35, "high": 0.55, "tick": 0.25},
                      lowpass={"pad": 900, "bass": 520, "high": 2500}, highpass={"tick": 2500})
    return master(audio)


def sakin() -> np.ndarray:
    """İnsan hikâyesi / sakin: 80 BPM, Do majör (C–G–Am–F), piyano arpeji, sıcak pad, davul yok."""
    track = Track(80, 24, seed=3)
    progression = [("C3", False), ("G2", False), ("A2", True), ("F2", False)]
    for bar in range(24):
        root, minor = progression[(bar // 2) % 4]
        tones = chord_tones(root, minor)
        beat0 = bar * 4
        if bar % 2 == 0:
            for number, note in enumerate(tones[:3]):
                up = note[:-1] + str(int(note[-1]) + 1)
                track.add("pad", beat0, pad(freq(up), 8 * track.beat + 1.5, track.rng, bright=6), pan=(number - 1) * 0.5)
            track.add("bass", beat0, bass(freq(tones[0]), 8 * track.beat) * 0.8)
        pattern = [0, 1, 2, 3, 2, 1, 2, 3] if bar % 2 == 0 else [0, 2, 3, 2, 1, 2, 3, 2]
        for eighth, pick in enumerate(pattern):
            note = tones[pick]
            high = note[:-1] + str(int(note[-1]) + 1)
            track.add("piano", beat0 + eighth / 2, pluck(freq(high), 2.5, decay=1.1, harmonics=6),
                      pan=-0.3 + 0.6 * pick / 3)
    audio = track.mix(levels={"pad": 0.45, "bass": 0.4, "piano": 0.35}, reverb={"pad": 0.5, "piano": 0.4},
                      lowpass={"pad": 1500, "bass": 300, "piano": 4000})
    return master(audio)


TRACKS = {"gundem": gundem, "gerilim": gerilim, "sakin": sakin}


def write(name: str, audio: np.ndarray) -> Path:
    wav = HERE / f"{name}.wav"
    pcm = (np.clip(audio.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(wav), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())
    mp3 = HERE / f"{name}.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "112k", str(mp3)],
                   check=True)
    wav.unlink()
    return mp3


if __name__ == "__main__":
    for track_name, build in TRACKS.items():
        print(write(track_name, build()))
