"""EditProject'in video izini + TTS sesini tek FFmpeg komutuyla MP4'e dönüştürür (Faz 3)."""

from __future__ import annotations

import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from shared.edit_models import Clip, ClipType, EditProject, Framing, TrackKind
from shared.media_models import ImageAsset, MediaLibrary

from .ffmpeg_runner import PROBE_TIMEOUT_SECONDS, long_job_timeout, run_ffmpeg
from .video_asset import image_geometry

X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
AMF = ["-c:v", "h264_amf", "-quality", "quality", "-b:v", "10M"]  # AMD ekran kartı donanım kodlayıcısı


# Ses seviyeleri (editör: CapCut'ta seslendirmeyi ~6 dB kısıyor, kaynak sesi "kırmızıya" çıkmayana dek indiriyordu).
# Her parça ölçülüp sabit kazançla hedefe getirilir (tek geçişli loudnorm kısa kesitlerde pompalama/bozulma yapıyordu);
# sonda sınırlayıcı: hiçbir tepe -2 dBFS'yi geçmez, kulakta patlama olmaz.
TTS_LUFS = -18.0
SOUNDBITE_LUFS = -20.0  # kaynak sesli kesit spikerin biraz altında (bağırma, siren)
MAX_BOOST_DB = 12.0  # sessiz kesitte gürültüyü şişirme (seslendirme temiz kayıt: 20 dB'ye kadar)
FADE_S = 0.03  # kesit kenarlarında çıt sesi olmasın
LIMITER = "alimiter=limit=0.79:attack=5:release=60:level=disabled"
AUDIO_FORMAT = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
# Fotoğraf (v4.0): FFmpeg'in kendi döndürmesi kapalı (-noautorotate; sürüme göre değişiyor), EXIF yönü burada uygulanır.
EXIF_TURN = {2: "hflip", 3: "hflip,vflip", 4: "vflip", 5: "transpose=0", 6: "transpose=1", 7: "transpose=3",
             8: "transpose=2"}
PHOTO_SCALE = 4  # yakınlaşma büyütülmüş karede hesaplanır: zoompan'ın tam piksel adımları titreme yapmasın


@lru_cache(maxsize=128)
def _measure(path: str, start: float, seconds: float, mtime: float) -> float | None:
    command = ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{start:.3f}"]
    command += ["-t", f"{seconds:.3f}"] if seconds > 0 else []
    command += ["-i", path, "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    try:
        result = run_ffmpeg(command, long_job_timeout(seconds or None), "Ses ölçümü")
        stats = json.loads(re.findall(r"\{[^{}]*\}", result.stderr)[-1])
        value = float(stats["input_i"])
    except (RuntimeError, OSError, subprocess.SubprocessError, IndexError, KeyError, ValueError):
        return None
    return value if value > -70 else None  # sessiz / ölçülemedi


def measure_loudness(path: str, start: float = 0.0, seconds: float = 0.0) -> float | None:
    """Parçanın bütünleşik ses yüksekliği (LUFS); ölçülemezse None."""
    try:
        mtime = Path(path).stat().st_mtime
    except OSError:
        return None
    return _measure(str(path), round(start, 3), round(seconds, 3), mtime)


def gain_db(measured: float | None, target: float, max_boost: float = MAX_BOOST_DB) -> float:
    return 0.0 if measured is None else round(min(target - measured, max_boost), 2)


@lru_cache(maxsize=1)
def amd_encoder_available() -> bool:
    try:
        result = run_ffmpeg(["ffmpeg", "-hide_banner", "-encoders"], PROBE_TIMEOUT_SECONDS, "FFmpeg kodlayıcı listesi")
    except (RuntimeError, OSError):
        return False
    return " h264_amf " in result.stdout


def _clip_filter(index: int, framing: Framing, width: int, height: int, fps: int, frames: int, turn: str = "") -> str:
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
        f"[{index}:v]{turn}{framing_steps},setsar=1,fps={fps},format=yuv420p,"
        f"tpad=stop_mode=clone:stop=5,trim=end_frame={frames},setpts=PTS-STARTPTS[v{index}]"
    )


def _zooms(framing: Framing) -> bool:
    start, end = framing.view_region, framing.view_region_end
    return bool(start and end and abs(start.width - end.width) > 1e-4)


def _photo_zoom_filter(index: int, framing: Framing, width: int, height: int, fps: int, frames: int, turn: str) -> str:
    """Fotoğrafta yavaş yakınlaşma/uzaklaşma: büyük alan kırpılıp büyütülür, küçük alana doğru zoompan (alan hep dolu)."""
    start, end = framing.view_region, framing.view_region_end
    outer = start if start.width >= end.width else end

    def relative(region):
        return (region.x - outer.x) / outer.width, (region.y - outer.y) / outer.height, region.width / outer.width

    (sx, sy, sw), (ex, ey, ew) = relative(start), relative(end)
    p = f"on/{max(frames - 1, 1)}"
    return (
        f"[{index}:v]{turn}crop=iw*{outer.width}:ih*{outer.height}:iw*{outer.x}:ih*{outer.y},"
        f"scale={width * PHOTO_SCALE}:{height * PHOTO_SCALE}:flags=lanczos,"
        f"zoompan=z='1/({sw:.5f}+({ew - sw:.5f})*{p})':x='iw*({sx:.5f}+({ex - sx:.5f})*{p})':"
        f"y='ih*({sy:.5f}+({ey - sy:.5f})*{p})':d={frames}:s={width}x{height}:fps={fps},"
        f"setsar=1,format=yuv420p,trim=end_frame={frames},setpts=PTS-STARTPTS[v{index}]"
    )


def _photo_input(asset: ImageAsset, source: str, clip: Clip, index: int, width: int, height: int,
                 fps: int) -> tuple[list[str], str]:
    orientation = asset.geometry.exif_orientation if asset.geometry else image_geometry(Path(source)).exif_orientation
    turn = f"{EXIF_TURN[orientation]}," if orientation in EXIF_TURN else ""
    if _zooms(clip.framing):  # tek kare girer, zoompan klip boyunca kare üretir
        return (["-noautorotate", "-i", source],
                _photo_zoom_filter(index, clip.framing, width, height, fps, clip.duration_f, turn))
    seconds = clip.duration_f / fps + 0.2  # sabit ya da kayan kadraj: kare tekrarlanır, video yolu
    return (["-loop", "1", "-framerate", str(fps), "-t", f"{seconds:.3f}", "-noautorotate", "-i", source],
            _clip_filter(index, clip.framing, width, height, fps, clip.duration_f, turn))


def build_render_command(edit_project: dict[str, Any], media_library: dict[str, Any], output: Path, encoder: list[str]) -> list[str]:
    project = EditProject.model_validate(edit_project)
    library = MediaLibrary.model_validate(media_library)
    sources = {asset.asset_id: asset.source.original_path for asset in library.assets}
    assets = {asset.asset_id: asset for asset in library.assets}
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
                f"Görüntü bulunamadı: {source or clip.asset_id}. Dosya taşındıysa görüntüleri yeniden seçip analiz et."
            )
        if isinstance(assets[clip.asset_id], ImageAsset):
            inputs, graph = _photo_input(assets[clip.asset_id], source, clip, index, timeline.width, timeline.height,
                                         timeline.fps)
            command += inputs
            filters.append(graph)
            continue
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
    labels = [f"[v{i}]" for i in range(len(clips))]
    cover = next((i for i, c in enumerate(clips) if c.scene == 0 and not c.use_source_audio), None)
    if cover and clips[0].use_source_audio and clips[0].duration_f > 1:
        # Kapak (v4.0): seslendirmenin önünde kaynak sesli kesit varsa videonun ilk karesi yine kapak sahnesinden
        # (Reels/Shorts kapağı ilk kare); kesit bir kare geç başlar, ses ve süreler değişmez.
        filters[cover] = filters[cover].replace(f"[v{cover}]", f"[vk{cover}];[vk{cover}]split=2[v{cover}][kapak0]")
        filters.append("[kapak0]trim=end_frame=1,setpts=PTS-STARTPTS[kapak]")
        filters.append("[v0]trim=start_frame=1,setpts=PTS-STARTPTS[v0k]")
        labels[0] = "[kapak][v0k]"
    filters.append(f"{''.join(labels)}concat=n={len(clips) + (labels[0] != '[v0]')}:v=1:a=0[video]")

    # Ses: [öncesi kesitler (kendi sesi)] + [seslendirme, dolgu süresince; sonu sessiz] + [sonrası kesitler].
    # Her parça ölçülüp hedef yüksekliğe sabit kazançla getirilir; kesitlerin kenarı yumuşak (çıt yok); sonda sınırlayıcı.
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
            gain = gain_db(measure_loudness(project.audio.path), TTS_LUFS, max_boost=20.0)
            filters.append(f"[{tts_index}:a]volume={gain}dB,{AUDIO_FORMAT},afade=t=in:d=0.01,apad,"
                           f"atrim=duration={seconds:.3f}[{label}]")
        else:
            index, clip = item
            seconds = clip.duration_f / fps
            if has_audio.get(clip.asset_id):
                gain = gain_db(measure_loudness(sources[clip.asset_id], clip.source_in_s, seconds), SOUNDBITE_LUFS)
                filters.append(
                    f"[{index}:a]atrim=duration={seconds:.3f},asetpts=PTS-STARTPTS,volume={gain}dB,{AUDIO_FORMAT},"
                    f"afade=t=in:d={FADE_S},afade=t=out:st={max(seconds - FADE_S, 0):.3f}:d={FADE_S},apad,"
                    f"atrim=duration={seconds:.3f}[{label}]"
                )
            else:  # Kaynak videoda ses yok: sessizlik.
                command += ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
                filters.append(f"[{extra_index}:a]aformat=sample_fmts=fltp:channel_layouts=stereo[{label}]")
                extra_index += 1
        pieces.append(f"[{label}]")
    filters.append(f"{''.join(pieces)}concat=n={len(pieces)}:v=0:a=1,{LIMITER}[audio]")
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
