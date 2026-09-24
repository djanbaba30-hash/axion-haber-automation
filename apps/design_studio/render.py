"""Son video (Faz 5): kaba kurgu + elle blur/mozaik + Axion şablonu → 1080x1920 MP4, tek FFmpeg komutuyla. API yok."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from apps.video_studio.modules.ffmpeg_runner import long_job_timeout, run_ffmpeg
from apps.video_studio.modules.render import AMF, X264, amd_encoder_available
from shared.axion_template import VIDEO_SLOT

from .blur import mosaic_block, sigma, write_mask_sequences
from .design import Design
from .template import Layers, frame_origin, write_layers


def _effect_filter(blur: dict[str, Any], width: int, height: int) -> str:
    if blur.get("effect") == "mozaik":
        block = mosaic_block(blur)
        small_w, small_h = max(2, width // block // 2 * 2), max(2, height // block // 2 * 2)
        return f"scale={small_w}:{small_h}:flags=area,scale={width}:{height}:flags=neighbor"
    return f"gblur=sigma={sigma(blur):.1f}"


def build_final_command(
    rough_cut: Path,
    layers: Layers,
    fps: int,
    seconds: float,
    output: Path,
    encoder: list[str],
    blurs: list[dict[str, Any]] | None = None,
    masks: list[Path] | None = None,
) -> list[str]:
    x, y, w, h = VIDEO_SLOT["x"], VIDEO_SLOT["y"], VIDEO_SLOT["width"], VIDEO_SLOT["height"]
    fx, fy = frame_origin()
    duration = f"{seconds:.3f}"
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(fps), "-t", duration, "-i", str(layers.base),
        "-i", str(rough_cut),
        "-f", "concat", "-safe", "0", "-i", str(layers.frame),
        "-f", "concat", "-safe", "0", "-i", str(layers.graphics),
    ]
    # Kaba kurgu 960x1226 (H.264/4:2:0 çift sayı ister); şablon alanı 960x1225 → alt 1 px en sonda kırpılır.
    even_h = h + h % 2
    filters = [f"[1:v]scale={w}:{even_h},setsar=1,fps={fps},format=yuv420p[v0]"]
    # Elle blur/mozaik: videonun işlenmiş kopyası, kutunun maskesiyle (şekil, açı, yumuşak kenar, opaklık) bindirilir.
    for number, (blur, mask) in enumerate(zip(blurs or [], masks or [])):
        index = 4 + number
        command += ["-f", "concat", "-safe", "0", "-i", str(mask)]
        filters += [
            f"[v{number}]split=2[v{number}a][v{number}b]",
            f"[v{number}b]{_effect_filter(blur, w, even_h)}[b{number}]",
            f"[{index}:v]fps={fps},format=gray,scale={w}:{even_h}[m{number}]",
            f"[b{number}][m{number}]alphamerge[bm{number}]",
            f"[v{number}a][bm{number}]overlay=0:0,format=yuv420p[v{number + 1}]",
        ]
    video = f"v{len(masks or [])}"
    filters += [
        "[0:v]format=rgba[base]",
        f"[{video}]crop={w}:{h}:0:0[slot]",
        f"[base][slot]overlay={x}:{y}:eof_action=repeat[s1]",
        f"[2:v]fps={fps},format=rgba[frame]",
        f"[s1][frame]overlay={fx}:{fy}[s2]",
        f"[3:v]fps={fps},format=rgba[graphics]",
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


def render_final(rough_cut: Path, design: Design, background: Path, fps: int, seconds: float, output: Path) -> str:
    """Şablon katmanlarını geçici klasörde hazırlar, videoyu önce geçici ada yazar. Kodlayıcının adını döndürür."""
    if not rough_cut.exists():
        raise FileNotFoundError("Kurgu videosu bulunamadı. Video Stüdyosu'nda videoyu oluştur.")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + ".yaziliyor.mp4")
    attempts = [("AMD donanım (h264_amf)", AMF)] if amd_encoder_available() else []
    attempts.append(("x264 (işlemci)", X264))
    error = ""
    blurs = design.blurs
    with tempfile.TemporaryDirectory(prefix="axion_sablon_") as folder:
        layers = write_layers(Path(folder), design, background, fps, seconds)
        masks = write_mask_sequences(
            Path(folder), blurs, fps, max(1, round(seconds * fps)), VIDEO_SLOT["width"], VIDEO_SLOT["height"] + VIDEO_SLOT["height"] % 2
        )
        for name, encoder in attempts:
            command = build_final_command(rough_cut, layers, fps, seconds, partial, encoder, blurs, masks)
            try:
                result = run_ffmpeg(command, long_job_timeout(seconds * 10), "Son video")
            except (RuntimeError, OSError, subprocess.SubprocessError) as failure:
                result, error = None, str(failure)
            if result is not None and result.returncode == 0 and partial.exists():
                partial.replace(output)
                return name
            if result is not None:
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
