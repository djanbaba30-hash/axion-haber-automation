"""Kurguda sahne değiştirme (v4.0.0-alpha.2, editör; API yok).

Video Stüdyosu'nda her seslendirme sahnesinin küçük karesi görünür; editör bir sahneye dokununca aynı görüntülerden
(fotoğraflar dahil) en uygun birkaç seçenek gelir, birini seçer, yalnız o sahne değişir. Seçim `kurgu_plani.json`'da
`editor` satırı olarak Luna'nın planının üstüne yazılır (`luna_edit.plan` uygular; etiket "user"). Girdiler (haber,
görüntüler, kesitler) değişince ya da "Sahneleri yeniden seç"te editörün seçimi düşer (pencereler başka olur).

Seçenekler kurallı puanla sıralanır (söylenen kelimeler, rol, kapak, tekrar); videoda başka yerde kullanılan an
seçenek olmaz. Küçük kareler sahnenin videodaki kadrajıyla kırpılır, proje klasöründe saklanır (onizleme/kareler).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from shared.axion_template import VIDEO_HEIGHT, VIDEO_WIDTH
from shared.edit_models import Clip, ClipOrigin, EditProject, Framing, TrackKind
from shared.media_models import ImageAsset, MediaLibrary, Region

from . import luna_edit
from .ffmpeg_runner import FRAME_TIMEOUT_SECONDS, run_ffmpeg
from .rough_cut import PHOTO_SECONDS, Prepared, _score, _source_range, _tokens, _Usage, clip_framing

THUMB_FOLDER = "onizleme/kareler"
THUMB_WIDTH = 180
ALTERNATIVE_COUNT = 4


@dataclass
class Scene:
    number: int  # 0'dan
    start_s: float  # videodaki başlangıç
    seconds: float
    clip: Clip  # sahnenin ilk klibi (küçük kare bunun)
    user: bool  # editör değiştirdi


@dataclass
class Alternative:
    index: int  # aday (pencere) no: `luna_edit.window_ids` ile aynı sıra
    start: float  # kaynaktaki başlangıç
    framing: Framing
    description: str
    asset_id: str


def _video_clips(edit_project: dict[str, Any] | EditProject) -> list[Clip]:
    project = edit_project if isinstance(edit_project, EditProject) else EditProject.model_validate(edit_project)
    return sorted((c for t in project.edit_plan.timeline.tracks if t.kind == TrackKind.VIDEO for c in t.clips),
                  key=lambda c: c.start_f)


def scenes(edit_project: dict[str, Any]) -> list[Scene]:
    """Değiştirilebilir sahneler (kaynak sesli kesitler hariç); v4.0 öncesi kurguda boş (sahne numarası yok)."""
    fps = edit_project["edit_plan"]["timeline"]["fps"]
    result: dict[int, Scene] = {}
    for clip in _video_clips(edit_project):
        if clip.scene is None or clip.use_source_audio:
            continue
        scene = result.get(clip.scene)
        if scene is None:
            result[clip.scene] = Scene(clip.scene, clip.start_f / fps, clip.duration_f / fps, clip,
                                       clip.origin == ClipOrigin.USER)
        else:
            scene.seconds += clip.duration_f / fps
    return [result[number] for number in sorted(result)]


def alternatives(prep: Prepared, edit_project: dict[str, Any], number: int,
                 count: int = ALTERNATIVE_COUNT) -> list[Alternative]:
    """`number`. sahnenin yerine konabilecek en uygun görüntüler (şu anki pencere ve videoda kullanılan anlar hariç)."""
    slots = prep.slots()
    if not 0 <= number < len(slots):
        return []
    start, end, spoken = slots[number]
    need = min(end - start, 5.0)
    usage = _Usage(blocked=list(prep.blocked))
    current: list[Clip] = []
    previous_shot = None
    photos = {c.shot_id for c in prep.candidates if c.photo}
    for clip in _video_clips(edit_project):
        if clip.use_source_audio or clip.shot_id is None:
            continue
        if clip.scene == number:
            current.append(clip)
            continue
        if clip.scene is not None and clip.scene < number:
            previous_shot = clip.shot_id
        usage.used.setdefault(clip.shot_id, []).append(
            (0.0, PHOTO_SECONDS) if clip.shot_id in photos else (clip.source_in_s, clip.source_out_s))
        usage.count[clip.shot_id] = usage.count.get(clip.shot_id, 0) + 1
    headline = _tokens(f"{prep.project.news.headline_1} {prep.project.news.headline_2}")
    wanted = _tokens(spoken) + (headline if number == 0 else [])

    current_windows = {_window(prep, clip) for clip in current}

    def is_current(index: int) -> bool:
        return index in current_windows

    ranked = sorted(
        (i for i in range(len(prep.candidates)) if not is_current(i)),
        key=lambda i: (-_score(prep.candidates[i], wanted, number == 0, previous_shot, usage, need), i),
    )
    result: list[Alternative] = []
    shots: set[str] = set()
    for index in ranked:
        candidate = prep.candidates[index]
        source_in, available, repeated = _source_range(candidate, usage, need)
        if repeated or available < min(need, 2.0) or candidate.shot_id in shots:
            continue  # videoda başka yerde görünen an ya da aynı çekimden ikinci seçenek değil
        shots.add(candidate.shot_id)
        result.append(Alternative(index, round(source_in, 2), clip_framing(candidate, seconds=need),
                                  candidate.description, candidate.asset_id))
        if len(result) == count:
            break
    return result


def _window(prep: Prepared, clip: Clip) -> int | None:
    return next((i for i, c in enumerate(prep.candidates)
                 if c.shot_id == clip.shot_id and c.start - 1e-6 <= clip.source_in_s < c.end), None)


def choose(folder: Path, prep: Prepared, edit_project: dict[str, Any], number: int, alternative: Alternative) -> None:
    """Editörün seçimini kaydeder (videoyu sayfa yeniden oluşturur; `luna_edit.plan` uygular). Luna'nın planı yoksa
    (ulaşılamadı) şu anki kurgu `temel` olarak yazılır: kurallar öteki sahneleri yeniden seçmesin, yalnız bu değişsin."""
    ids = luna_edit.window_ids(prep)
    sig = luna_edit.signature(luna_edit.build_prompt(prep))
    stored = luna_edit.read_plan(folder) or {}
    if stored.get("imza") != sig:
        stored = {"imza": sig}  # girdiler değişmiş: eski plan zaten geçersiz
    if not stored.get("sahneler"):
        base = []
        for scene in scenes(edit_project):
            window = _window(prep, scene.clip)
            if window is not None:
                base.append({"parca": scene.number + 1, "pencere": ids[window], "kaynak_bas": scene.clip.source_in_s})
        stored["temel"] = base
    edits = [e for e in stored.get("editor", []) if e.get("parca") != number + 1]
    edits.append({"parca": number + 1, "pencere": ids[alternative.index],
                  "kaynak_bas": alternative.start})
    stored["editor"] = sorted(edits, key=lambda e: e["parca"])
    luna_edit.write_plan(folder, stored)


def thumbnail(library: MediaLibrary, asset_id: str, time: float, view: Region | None, folder: Path) -> Path | None:
    """Sahnenin küçük karesi (videodaki kadrajıyla); dosya yoksa ya da okunamazsa None."""
    asset = next((a for a in library.assets if a.asset_id == asset_id), None)
    source = Path(asset.source.original_path) if asset and asset.source.original_path else None
    if source is None or not source.exists():
        return None
    key = hashlib.sha1(f"{source}|{time:.2f}|{view.model_dump_json() if view else ''}".encode()).hexdigest()[:16]
    output = folder / THUMB_FOLDER / f"{key}.jpg"
    if output.exists():
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = output.with_suffix(".tam.jpg")
    try:
        if isinstance(asset, ImageAsset):
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
        else:
            run_ffmpeg(["ffmpeg", "-v", "error", "-y", "-ss", f"{time:.2f}", "-i", str(source), "-frames:v", "1",
                        "-vf", "scale=720:-2", "-q:v", "4", str(frame)], FRAME_TIMEOUT_SECONDS, "Sahne karesi")
            with Image.open(frame) as opened:
                image = opened.convert("RGB")
        if view:
            w, h = image.size
            image = image.crop((round(view.x * w), round(view.y * h), round((view.x + view.width) * w),
                                round((view.y + view.height) * h)))
        image = image.resize((THUMB_WIDTH, round(THUMB_WIDTH * VIDEO_HEIGHT / VIDEO_WIDTH)), Image.Resampling.LANCZOS)
        image.save(output, "JPEG", quality=80)
    except (OSError, RuntimeError, ValueError):
        return None
    finally:
        frame.unlink(missing_ok=True)
    return output
