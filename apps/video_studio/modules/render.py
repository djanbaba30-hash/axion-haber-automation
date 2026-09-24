"""EditProject'in video izini + TTS sesini tek FFmpeg komutuyla MP4'e dönüştürür (Faz 3)."""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from shared.edit_models import ClipType, EditProject, Framing, TrackKind
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
    """Tek kadraj yolu: planlayıcının seçtiği alan kırpılıp video alanına ölçeklenir (hep tam dolu).

    Bulanık dolgu hiçbir durumda üretilmez (editör kararı); `framing.mode` yok sayılır. view_region_end varsa kadraj
    klip boyunca oraya yavaşça kayar. Alan yoksa (eski kayıt) ortadan tam dolu kırpılır.
    """
    size = f"{width}:{height}"
    view = framing.view_region
    if view:
        end = framing.view_region_end or view
        seconds = frames / fps
        x = f"'iw*({view.x}+({end.x - view.x})*min(t/{seconds:.3f},1))'"
        y = f"'ih*({view.y}+({end.y - view.y})*min(t/{seconds:.3f},1))'"
        framing_steps = f"crop=iw*{view.width}:ih*{view.height}:{x}:{y},scale={size}"
    else:
        framing_steps = f"scale={size}:force_original_aspect_ratio=increase,crop={size}"
    # tpad + trim: kaynak birkaç kare kısa kalsa bile klip tam `frames` kare olur (ses ile senkron).
    return (
        f"[{index}:v]{framing_steps},setsar=1,fps={fps},format=yuv420p,"
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
    fps = timeline.fps
    total_f = max(c.start_f + c.duration_f for c in clips)
    tts_clip = next(
        (c for t in timeline.tracks if t.kind == TrackKind.AUDIO for c in t.clips if c.asset_id == project.audio.asset_id),
        None,
    )
    tts_start_f = tts_clip.start_f if tts_clip else 0
    soundbites = [(i, c) for i, c in enumerate(clips) if c.use_source_audio]
    has_audio = {asset.asset_id: getattr(asset, "audio", None) is not None for asset in library.assets}
    tts_index = len(clips)
    command += ["-i", project.audio.path]
    joined = "".join(f"[v{i}]" for i in range(len(clips)))
    filters.append(f"{joined}concat=n={len(clips)}:v=1:a=0[video]")

    # Ses: [öncesi kesitler (kendi sesi)] + [seslendirme, dolgu süresince; sonu sessiz] + [sonrası kesitler].
    # Her parça aynı ses yüksekliğine getirilir (loudnorm), kesit ile spiker arasında ses sıçraması olmasın.
    level = "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    pieces = []
    before = [(i, c) for i, c in soundbites if c.start_f < tts_start_f]
    after = [(i, c) for i, c in soundbites if c.start_f >= tts_start_f]
    extra_index = tts_index + 1
    order = [*before, None, *after]
    after_start_f = after[0][1].start_f if after else total_f
    for number, item in enumerate(order):
        label = f"a{number}"
        if item is None:
            seconds = (after_start_f - tts_start_f) / fps
            filters.append(f"[{tts_index}:a]{level},apad,atrim=duration={seconds:.3f}[{label}]")
        else:
            index, clip = item
            seconds = clip.duration_f / fps
            if has_audio.get(clip.asset_id):
                filters.append(f"[{index}:a]atrim=duration={seconds:.3f},asetpts=PTS-STARTPTS,{level},apad,atrim=duration={seconds:.3f}[{label}]")
            else:  # Kaynak videoda ses yok: sessizlik.
                command += ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
                filters.append(f"[{extra_index}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[{label}]")
                extra_index += 1
        pieces.append(f"[{label}]")
    filters.append(f"{''.join(pieces)}concat=n={len(pieces)}:v=0:a=1[audio]")
    command += [
        "-filter_complex", ";".join(filters),
        "-map", "[video]", "-map", "[audio]",
        *encoder,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_f / fps:.3f}",
        "-movflags", "+faststart",
        str(output),
    ]
    return command


def render_rough_cut(edit_project: dict[str, Any], media_library: dict[str, Any], output: Path) -> str:
    """MP4'ü önce geçici ada yazar, başarılıysa yerine koyar. Kullanılan kodlayıcının adını döndürür."""
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + ".yaziliyor.mp4")
    timeline = edit_project["edit_plan"]["timeline"]
    duration = max((c["start_f"] + c["duration_f"] for t in timeline["tracks"] for c in t["clips"]), default=0) / timeline["fps"]
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
