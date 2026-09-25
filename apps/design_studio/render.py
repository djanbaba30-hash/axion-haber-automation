"""Son video (Faz 5): kaba kurgu + elle blur/mozaik + Axion şablonu → 1080x1920 MP4, tek FFmpeg komutuyla. API yok."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from apps.video_studio.modules.ffmpeg_runner import PROBE_TIMEOUT_SECONDS, long_job_timeout, run_ffmpeg
from apps.video_studio.modules.render import AMF, X264, amd_encoder_available
from shared.axion_template import VIDEO_SLOT

from .blur import BlurPass, mosaic_block, sigma, write_mask_sequences
from .design import Design
from .template import Layers, frame_origin, write_layers

logger = logging.getLogger(__name__)


def _effect_filter(blur: dict[str, Any], width: int, height: int) -> str:
    if blur.get("effect") == "mozaik":
        block = mosaic_block(blur)
        small_w, small_h = max(1, -(-width // block)), max(1, -(-height // block))
        return f"scale={small_w}:{small_h}:flags=area,scale={width}:{height}:flags=neighbor"
    return f"gblur=sigma={sigma(blur):.1f}:enable='between(t,{blur['start']:.3f},{blur['end']:.3f})'"


def build_final_command(
    rough_cut: Path,
    layers: Layers,
    fps: int,
    seconds: float,
    output: Path,
    encoder: list[str],
    blurs: list[BlurPass] | None = None,
) -> list[str]:
    x, y, w, h = VIDEO_SLOT["x"], VIDEO_SLOT["y"], VIDEO_SLOT["width"], VIDEO_SLOT["height"]
    fx, fy = frame_origin()
    duration = f"{seconds:.3f}"
    total = max(1, round(seconds * fps))
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(fps), "-i", str(layers.base),
        "-i", str(rough_cut),
        "-f", "concat", "-safe", "0", "-i", str(layers.frame),
        "-f", "concat", "-safe", "0", "-i", str(layers.graphics),
    ]
    # Kaba kurgu 960x1226 (H.264/4:2:0 çift sayı ister); şablon alanı 960x1225 → alt 1 px en sonda kırpılır.
    even_h = h + h % 2
    filters = [f"[1:v]scale={w}:{even_h},setsar=1,fps={fps},format=yuv420p[v0]"]
    # Elle blur/mozaik: videonun yalnızca kutunun bölgesi kırpılıp işlenir ve kutunun maskesiyle (şekil, açı, yumuşak
    # kenar, opaklık) aynı yere bindirilir; kutunun görünmediği sürede bindirme atlanır.
    for number, item in enumerate(blurs or []):
        index = 4 + number
        rx, ry, rw, rh = item.region
        blur = item.blur
        command += ["-f", "concat", "-safe", "0", "-i", str(item.mask)]
        filters += [
            f"[v{number}]split=2[v{number}a][v{number}b]",
            f"[v{number}b]crop={rw}:{rh}:{rx}:{ry},{_effect_filter(blur, rw, rh)}[b{number}]",
            f"[{index}:v]format=gray,fps={fps}[m{number}]",
            f"[b{number}][m{number}]alphamerge[bm{number}]",
            f"[v{number}a][bm{number}]overlay={rx}:{ry}:enable='between(t,{blur['start']:.3f},{blur['end']:.3f})'[v{number + 1}]",
        ]
    video = f"v{len(blurs or [])}"
    # Hız: zemin PNG'si bir kez okunup bellekte tekrarlanır (her kare yeniden çözülmez); katmanlar kare çoğaltılmadan
    # önce YUV'a çevrilir (her farklı görsel bir kez). Bindirmeler 4:2:0'da yapılır.
    filters += [
        f"[0:v]format=yuv420p,loop=loop={total - 1}:size=1,settb=1/{fps},setpts=N,fps={fps}[base]",
        f"[{video}]crop={w}:{h}:0:0[slot]",
        f"[base][slot]overlay={x}:{y}:eof_action=repeat[s1]",
        f"[2:v]format=yuva420p,fps={fps}[frame]",
        f"[s1][frame]overlay={fx}:{fy}[s2]",
        f"[3:v]format=yuva420p,fps={fps}[graphics]",
        "[s2][graphics]overlay=0:0,format=yuv420p[out]",
    ]
    return command + [
        "-filter_complex", ";".join(filters),
        "-map", "[out]", "-map", "1:a?",
        *encoder,
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-t", duration,
        "-movflags", "+faststart",
        str(output),
    ]


class Cancelled(Exception):
    """Üretim yarıda bırakıldı (editör daha yeni bir tasarımla yeniden başlattı)."""


def _run_cancellable(command: list[str], timeout: float, label: str, cancel: threading.Event | None) -> subprocess.CompletedProcess[str]:
    """run_ffmpeg gibi; `cancel` kurulunca FFmpeg'i hemen durdurur (arka plandaki iş yenisine yer açsın)."""
    if cancel is None:
        return run_ffmpeg(command, timeout, label)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    deadline = time.monotonic() + timeout
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.3)
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            if cancel.is_set() or time.monotonic() > deadline:
                process.kill()
                process.communicate()
                if cancel.is_set():
                    raise Cancelled from None
                raise RuntimeError(f"{label} {timeout:.0f} saniye içinde tamamlanamadı.") from None


FINAL_SIZE = (1080, 1920)
DURATION_TOLERANCE = 0.25  # sn


def _probe(path: Path) -> dict[str, Any] | None:
    """FFprobe akışları ve süre; FFprobe yoksa/çalışmazsa None (kontrol atlanır)."""
    command = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(path)]
    try:
        result = run_ffmpeg(command, PROBE_TIMEOUT_SECONDS, "Son video kontrolü")
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        # Editöre hata gösterilmez (video büyük olasılıkla sağlam); atlandığı günlükte (data/axion.log) görünür.
        logger.warning("Son video kontrolü atlandı (%s): %s", path.name, error)
        return None
    if result.returncode != 0:
        return {"error": result.stderr.strip()[-300:] or "okunamadı"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def check_final(output: Path, seconds: float, rough_cut: Path) -> str | None:
    """Üretilen videoyu doğrular: açılıyor mu, 1080x1920 mi, süre kurguyla aynı mı, kurguda ses varsa seste var mı.

    Sorun varsa editörün anlayacağı kısa açıklama, yoksa None. FFprobe bulunamazsa kontrol atlanır (None).
    """
    info = _probe(output)
    if info is None:
        return None
    if "error" in info:
        return f"Video açılamıyor ({info['error']})."
    streams = info.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        return "Videoda görüntü yok."
    if (video.get("width"), video.get("height")) != FINAL_SIZE:
        return f"Video boyutu {video.get('width')}x{video.get('height')}, 1080x1920 olmalı."
    try:
        duration = float((info.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        return "Videonun süresi okunamadı."
    if abs(duration - seconds) > DURATION_TOLERANCE:
        return f"Video {duration:.1f} sn, kurgu {seconds:.1f} sn olmalı."
    source = _probe(rough_cut)
    source_has_audio = bool(source and any(s.get("codec_type") == "audio" for s in source.get("streams") or []))
    if source_has_audio and not any(s.get("codec_type") == "audio" for s in streams):
        return "Videoda ses yok (kurguda var)."
    return None


def render_final(rough_cut: Path, design: Design, background: Path, fps: int, seconds: float, output: Path,
                 cancel: threading.Event | None = None) -> str:
    """Şablon katmanlarını geçici klasörde hazırlar, videoyu önce geçici ada yazar ve doğrular. Kodlayıcının adını döndürür.

    Donanım kodlayıcısı hata verirse ya da bozuk video üretirse (yanlış boyut/süre, ses yok) x264 ile yeniden dener.
    `cancel` kurulursa (arka plan işi) adımlar arasında ve FFmpeg sırasında durur: Cancelled; eski son video korunur.
    """

    def check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise Cancelled

    if not rough_cut.exists():
        raise FileNotFoundError("Kurgu videosu bulunamadı. Video Stüdyosu'nda videoyu oluştur.")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + ".yaziliyor.mp4")
    attempts = [("AMD donanım (h264_amf)", AMF)] if amd_encoder_available() else []
    attempts.append(("x264 (işlemci)", X264))
    error = ""
    with tempfile.TemporaryDirectory(prefix="axion_sablon_") as folder:
        check_cancel()
        layers = write_layers(Path(folder), design, background, fps, seconds)
        check_cancel()
        blurs = write_mask_sequences(
            Path(folder), design.blurs, fps, max(1, round(seconds * fps)), VIDEO_SLOT["width"], VIDEO_SLOT["height"] + VIDEO_SLOT["height"] % 2
        )
        for name, encoder in attempts:
            check_cancel()
            command = build_final_command(rough_cut, layers, fps, seconds, partial, encoder, blurs)
            try:
                result = _run_cancellable(command, long_job_timeout(seconds * 10), "Son video", cancel)
            except Cancelled:
                partial.unlink(missing_ok=True)
                raise
            except (RuntimeError, OSError, subprocess.SubprocessError) as failure:
                result, error = None, str(failure)
            if result is not None and result.returncode == 0 and partial.exists():
                problem = check_final(partial, seconds, rough_cut)
                if problem is None:
                    partial.replace(output)
                    return name
                error = f"{name}: {problem}"
            elif result is not None:
                error = result.stderr.strip()[-1500:]
            partial.unlink(missing_ok=True)
    raise RuntimeError(f"FFmpeg son videoyu oluşturamadı.\n\n{error}")


PREVIEW_FILENAME = "tasarim_onizleme.mp4"


def timeline_seconds(edit_project: dict[str, Any] | None) -> tuple[int, float] | None:
    """Kurgunun (fps, süre sn) değeri edit_project'ten; kaba kurgu MP4'ü bu süreyle üretilir."""
    try:
        timeline = edit_project["edit_plan"]["timeline"]  # type: ignore[index]
        fps = int(timeline["fps"])
        frames = max(c["start_f"] + c["duration_f"] for t in timeline["tracks"] for c in t["clips"])
    except (KeyError, TypeError, ValueError):
        return None
    return fps, frames / fps


def preview_video(rough_cut: Path, folder: Path) -> Path:
    """Tarayıcıdaki editör için hafif kopya (480 px, sesli). Kurgu değişince yenilenir; olmazsa kurgunun kendisi."""
    preview = folder / PREVIEW_FILENAME
    if preview.exists() and preview.stat().st_mtime >= rough_cut.stat().st_mtime:
        return preview
    folder.mkdir(parents=True, exist_ok=True)
    partial = preview.with_name(preview.stem + ".yaziliyor.mp4")
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(rough_cut),
        "-vf", "scale=480:614,setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-g", "15", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(partial),
    ]
    try:
        result = run_ffmpeg(command, long_job_timeout(None), "Tasarım önizlemesi")
    except (RuntimeError, OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0 and partial.exists():
        partial.replace(preview)
        return preview
    partial.unlink(missing_ok=True)
    return rough_cut


FILMSTRIP_FILENAME = "tasarim_serit.jpg"


def filmstrip(video: Path, folder: Path, seconds: float, frames: int = 16, height: int = 64) -> Path | None:
    """Zaman çizelgesindeki video izi için kare şeridi (tek JPEG, tek FFmpeg komutu). Olmazsa None."""
    strip = folder / FILMSTRIP_FILENAME
    if strip.exists() and strip.stat().st_mtime >= video.stat().st_mtime:
        return strip
    folder.mkdir(parents=True, exist_ok=True)
    rate = frames / max(1.0, seconds)
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps={rate:.4f},scale=-2:{height},tile={frames}x1", "-frames:v", "1", "-q:v", "4", str(strip),
    ]
    try:
        result = run_ffmpeg(command, long_job_timeout(None), "Zaman çizelgesi kareleri")
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return None
    return strip if result.returncode == 0 and strip.exists() else None
