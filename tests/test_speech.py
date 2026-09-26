"""v4.0.0-alpha.4 (editörün müzik notu): kesitte konuşma var mı — müzik konuşmada "varla yok arası" kısılır.

Örnek konuşma: tests/ornekler/konusma.mp3 (espeak-ng Türkçe sentez, 5 sn); gürültüler FFmpeg'le üretilir.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from apps.video_studio.modules.speech import has_speech

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg kurulu değil")
SPEECH = Path(__file__).parent / "ornekler" / "konusma.mp3"


def sound(tmp_path, name, source, extra=()):
    path = tmp_path / f"{name}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", source, *extra, str(path)], check=True)
    return str(path)


def test_speech_is_found_even_in_street_noise(tmp_path):
    assert has_speech(str(SPEECH)) is True
    assert has_speech(str(SPEECH), 1.0, 2.5) is True  # kesitin bir parçası
    noisy = tmp_path / "gurultulu.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SPEECH), "-f", "lavfi", "-i", "anoisesrc=color=pink:d=6:a=0.08",
                    "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first", str(noisy)], check=True)
    assert has_speech(str(noisy)) is True


@pytest.mark.parametrize("name, source, extra", [
    ("trafik", "anoisesrc=color=brown:d=6:a=0.3", ()),
    ("kalabalik", "anoisesrc=color=pink:d=6:a=0.3", ("-af", "volume='0.6+0.4*sin(2*PI*0.7*t)':eval=frame")),
    ("carpma", "anoisesrc=color=white:d=6:a=0.5", ("-af", "volume='if(lt(mod(t,1.3),0.15),1,0.1)':eval=frame")),
    ("siren", "aevalsrc='0.4*sin(2*PI*(900+400*sin(2*PI*0.5*t))*t)':d=6:s=16000", ()),
])
def test_noise_siren_and_crashes_are_not_speech(tmp_path, name, source, extra):
    assert has_speech(sound(tmp_path, name, source, extra)) is False


def test_silence_is_not_speech_and_too_short_is_unknown(tmp_path):
    assert has_speech(sound(tmp_path, "sessiz", "anullsrc=d=3")) is False
    assert has_speech(str(SPEECH), 0.0, 0.5) is None  # 1 sn'den kısa: karar yok
    assert has_speech(str(tmp_path / "yok.mp3")) is None
