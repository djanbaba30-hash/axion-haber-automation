"""EditProject'in video izini + TTS sesini tek FFmpeg komutuyla MP4'e dönüştürür (Faz 3)."""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from apps.axion_local.store import ROUGH_CUT_FILENAME  # noqa: F401  (sayfa buradan alır)
from shared.axion_template import video_seconds
from shared.edit_models import ClipType, EditProject, Framing, FramingMode, TrackKind
from shared.media_models import MediaLibrary

from .ffmpeg_runner import PROBE_TIMEOUT_SECONDS, long_job_timeout, run_ffmpeg

X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
AMF = ["-c:v", "h264_amf", "-quality", "quality", "-b:v", "10M"]  # AMD ekran kartı donanım kodlayıcısı


@lru_cache(maxsize=1)
def amd_encoder_available() -> bool:
    try:
        result = run_ffmpeg(["ffmpeg", "-hide_banner", "-encoders"], PROBE_TIMEOUT_SECONDS, "FFmpeg kodlayıcı listesi")
    except (RuntimeError, OSError):
        return False
    return " h264_amf " in result.stdout


def _clip_filter(index: int, framing: Framing, width: int, height: int, fps: int, frames: int) -> str:
    size = f"{width}:{height}"
    steps = []
    view = framing.view_region
    if view:
        # Planlayıcının seçtiği alan: öznenin tamamı. Oranı video alanından farklıysa boşluk aynı görüntünün
        # bulanık kopyasıyla dolar (oran aynıysa dolgu görünmez).
        steps.append(f"crop=iw*{view.width}:ih*{view.height}:iw*{view.x}:ih*{view.y}")
        framing = framing.model_copy(update={"mode": FramingMode.FIT_BLUR})
    region = None if view else framing.content_region
    if region:
        # Önce bulanık/siyah kenarları at: kalan asıl görüntü üzerinden kadrajlanır.
        steps.append(f"crop=iw*{region.width}:ih*{region.height}:iw*{region.x}:ih*{region.y}")
    if framing.mode == FramingMode.FIT_BLUR:
        steps.append(
            f"split[b{index}][f{index}];"
            f"[b{index}]scale={size}:force_original_aspect_ratio=increase,crop={size},boxblur=20:2[bb{index}];"
            f"[f{index}]scale={size}:force_original_aspect_ratio=decrease[ff{index}];"
            f"[bb{index}][ff{index}]overlay=(W-w)/2:(H-h)/2"
        )
    else:
        # Kadrajı odak noktasına ortala; görüntü dışına taşmasın diye sınırla.
        x = f"'clip(iw*{framing.focus_x}-{width / 2},0,iw-{width})'"
        y = f"'clip(ih*{framing.focus_y}-{height / 2},0,ih-{height})'"
        steps.append(f"scale={size}:force_original_aspect_ratio=increase,crop={size}:{x}:{y}")
    # tpad + trim: kaynak birkaç kare kısa kalsa bile klip tam `frames` kare olur (ses ile senkron).
    return (
        f"[{index}:v]{','.join(steps)},setsar=1,fps={fps},format=yuv420p,"
        f"tpad=stop_mode=clone:stop=5,trim=end_frame={frames},setpts=PTS-STARTPTS[v{index}]"
    )


def build_render_command(edit_project: dict[str, Any], media_library: dict[str, Any], output: Path, encoder: list[str]) -> list[str]:
    project = EditProject.model_validate(edit_project)
    library = MediaLibrary.model_validate(media_library)
    sources = {asset.asset_id: asset.source.original_path for asset in library.assets}
    timeline = project.edit_plan.timeline
    clips = sorted(
        (c for t in timeline.tracks if t.kind == TrackKind.VIDEO for c in t.clips if c.clip_type == ClipType.MEDIA),
        key=lambda c: c.start_f,
    )
    if not clips:
        raise ValueError("Kurguda video klibi yok.")
    if not project.audio.path or not Path(project.audio.path).exists():
        raise FileNotFoundError("Haberin seslendirme dosyası bulunamadı.")

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    filters = []
    for index, clip in enumerate(clips):
        source = sources.get(clip.asset_id)
        if not source or not Path(source).exists():
            raise FileNotFoundError(
                f"Video bulunamadı: {source or clip.asset_id}. Dosya taşındıysa görüntüleri yeniden seçip analiz et."
            )
        seconds = clip.source_out_s - clip.source_in_s
        command += ["-ss", f"{clip.source_in_s:.3f}", "-t", f"{seconds + 0.2:.3f}", "-i", source]
        filters.append(
            _clip_filter(index, clip.framing, timeline.width, timeline.height, timeline.fps, clip.duration_f)
        )
    audio_index = len(clips)
    command += ["-i", project.audio.path]
    joined = "".join(f"[v{i}]" for i in range(len(clips)))
    filters.append(f"{joined}concat=n={len(clips)}:v=1:a=0[video]")
    filters.append(f"[{audio_index}:a]apad[audio]")  # TTS bitince sessizlik (video en az 20 sn)
    command += [
        "-filter_complex", ";".join(filters),
        "-map", "[video]", "-map", "[audio]",
        *encoder,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{video_seconds(project.audio.duration_seconds):.3f}",
        "-movflags", "+faststart",
        str(output),
    ]
    return command


def render_rough_cut(edit_project: dict[str, Any], media_library: dict[str, Any], output: Path) -> str:
    """MP4'ü önce geçici ada yazar, başarılıysa yerine koyar. Kullanılan kodlayıcının adını döndürür."""
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + ".yaziliyor.mp4")
    duration = video_seconds(edit_project["audio"]["duration_seconds"])
    attempts = [("AMD donanım (h264_amf)", AMF)] if amd_encoder_available() else []
    attempts.append(("x264 (işlemci)", X264))
    error = ""
    for name, encoder in attempts:
        command = build_render_command(edit_project, media_library, partial, encoder)
        try:
            result = run_ffmpeg(command, long_job_timeout(duration * 10), "Video oluşturma")
        except (RuntimeError, OSError, subprocess.SubprocessError) as failure:
            result, error = None, str(failure)
        if result is not None and result.returncode == 0 and partial.exists():
            partial.replace(output)
            return name
        if result is not None:
            error = result.stderr.strip()[-1500:]
        partial.unlink(missing_ok=True)
    raise RuntimeError(f"FFmpeg videoyu oluşturamadı.\n\n{error}")
