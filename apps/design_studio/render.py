"""Son video (Faz 5): kaba kurgu + elle blur + Axion şablonu → 1080x1920 MP4, tek FFmpeg komutuyla. API yok."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from apps.video_studio.modules.ffmpeg_runner import long_job_timeout, run_ffmpeg
from apps.video_studio.modules.render import AMF, X264, amd_encoder_available
from shared.axion_template import LOGO_BOX, VIDEO_SLOT

from .blur import sigma, write_mask_sequences
from .template import STRIP_Y, Layers, logo_y_expression, write_layers


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
    duration = f"{seconds:.3f}"
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(fps), "-t", duration, "-i", str(layers.base),
        "-i", str(rough_cut),
        "-loop", "1", "-framerate", str(fps), "-t", duration, "-i", str(layers.frame),
        "-f", "concat", "-safe", "0", "-i", str(layers.top),
        "-f", "concat", "-safe", "0", "-i", str(layers.logo),
    ]
    # Kaba kurgu 960x1226 (H.264/4:2:0 çift sayı ister); şablon alanı 960x1225 → alt 1 px en sonda kırpılır.
    even_h = h + h % 2
    filters = [f"[1:v]scale={w}:{even_h},setsar=1,fps={fps},format=yuv420p[v0]"]
    # Elle blur: videonun bulanık kopyası, blur'un maskesi (şekil + opaklık, kare kare konum) ile üstüne bindirilir.
    for number, (blur, mask) in enumerate(zip(blurs or [], masks or [])):
        index = 5 + number
        command += ["-f", "concat", "-safe", "0", "-i", str(mask)]
        filters += [
            f"[v{number}]split=2[v{number}a][v{number}b]",
            f"[v{number}b]gblur=sigma={sigma(blur):.1f}[b{number}]",
            f"[{index}:v]fps={fps},format=gray,scale={w}:{even_h}[m{number}]",
            f"[b{number}][m{number}]alphamerge[bm{number}]",
            f"[v{number}a][bm{number}]overlay=0:0,format=yuv420p[v{number + 1}]",
        ]
    video = f"v{len(masks or [])}"
    filters += [
        "[0:v]format=rgba[base]",
        f"[{video}]crop={w}:{h}:0:0[slot]",
        f"[base][slot]overlay={x}:{y}:eof_action=repeat[s1]",
        "[s1][2:v]overlay=0:0[s2]",
        f"[3:v]fps={fps},format=rgba[top]",
        f"[s2][top]overlay=0:{STRIP_Y}[s3]",
        f"[4:v]fps={fps},format=rgba[logo]",
        f"[s3][logo]overlay=x={LOGO_BOX['x']}:y='{logo_y_expression()}':eval=frame,format=yuv420p[out]",
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


def render_final(
    rough_cut: Path,
    headline_1: str,
    headline_2: str,
    background: int,
    fps: int,
    seconds: float,
    output: Path,
    blurs: list[dict[str, Any]] | None = None,
) -> str:
    """Şablon katmanlarını geçici klasörde hazırlar, videoyu önce geçici ada yazar. Kodlayıcının adını döndürür."""
    if not rough_cut.exists():
        raise FileNotFoundError("Kurgu videosu bulunamadı. Video Stüdyosu'nda videoyu oluştur.")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + ".yaziliyor.mp4")
    attempts = [("AMD donanım (h264_amf)", AMF)] if amd_encoder_available() else []
    attempts.append(("x264 (işlemci)", X264))
    error = ""
    blurs = blurs or []
    with tempfile.TemporaryDirectory(prefix="axion_sablon_") as folder:
        layers = write_layers(Path(folder), headline_1, headline_2, background, fps, seconds)
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
