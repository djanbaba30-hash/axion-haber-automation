"""Kural tabanlı kaba kurgu (Faz 3): TTS cümlelerine sahne penceresi seçer. API çağrısı yok.

Her TTS cümlesinin süresi alignment'tan (yoksa karakter oranından) bulunur, en fazla MAX_CLIP_SECONDS'lik
kesitlere bölünür; her kesit için Luna açıklaması, rolü ve kullanım geçmişine göre en iyi pencere seçilir.
Faz 4'te bu seçimi Luna Edit Planner yapacak; bu modül onun yedeği olarak kalır.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from shared.edit_models import Clip, ClipOrigin, EditProject, Framing, FramingMode, TrackKind
from shared.media_models import EditorialRole, FocusPoint, MediaLibrary, Region, VideoAsset, VisualType

MAX_CLIP_SECONDS = 3.0
MIN_CLIP_SECONDS = 1.0
EDGE_SECONDS = 0.2  # Shot geçişindeki karışık karelerden kaçın.

# Röportaj (konuşan kişi) sessiz dolgu olarak kötü durur; başka seçenek yoksa kullanılır.
ROLE_BONUS = {
    EditorialRole.PORTRAIT: -6.0,
    EditorialRole.GENERIC_BROLL: -0.5,
}
OPENING_ROLES = {EditorialRole.ESTABLISHING, EditorialRole.ACTION}
OPENING_TYPES = {VisualType.EVENT}

# Haber cümlesindeki kavram → görüntüde karşılığı (kök başları; Türkçe ekler yüzünden önek eşleşmesi).
CONCEPTS = [
    ({"yaral", "hastane", "sağlık", "ambulans", "tedavi"}, {"ambulans", "sağlık", "sedye", "acil"}),
    ({"polis", "gözalt", "güvenlik", "emniyet", "jandarma"}, {"polis", "jandarma", "ekip", "şerit"}),
    ({"itfaiye", "yangın", "sönd", "alev"}, {"itfaiye", "yangın", "alev", "duman"}),
    ({"çarp", "kaza", "savrul", "hasar", "devril"}, {"hasar", "enkaz", "parça", "kırı", "çarp"}),
]
STOPWORDS = {"olarak", "sonra", "ardından", "sırasında", "belirtildi", "alındı", "yerinde", "arasında", "bulunan", "bulunduğu"}
PLATE = re.compile(r"\b\d{2}\s?[A-ZÇĞİÖŞÜ]{1,3}\s?\d{2,4}\b")


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.replace("I", "ı").replace("İ", "i").lower())


def _has(tokens: list[str], stems: set[str]) -> bool:
    return any(token.startswith(stem) for token in tokens for stem in stems)


@dataclass
class Candidate:
    asset_id: str
    shot_id: str
    shot_start: float
    shot_end: float
    start: float
    end: float
    order: int
    tokens: list[str]
    role: EditorialRole
    visual_type: VisualType
    confidence: float
    plate: bool
    description: str
    content_region: Region | None = None
    focus: FocusPoint | None = None


@dataclass
class _Usage:
    cursor: dict[str, float] = field(default_factory=dict)
    count: dict[str, int] = field(default_factory=dict)


def _candidates(library: MediaLibrary) -> list[Candidate]:
    items: list[Candidate] = []
    for asset in library.assets:
        if not isinstance(asset, VideoAsset):
            continue  # Tekil görseller (hareketsiz kare) sonraki fazda.
        for shot in asset.shots:
            windows = shot.analysis_windows or []
            spans = [(w.start_seconds, w.end_seconds, w.visual or shot.visual) for w in windows]
            if not spans:
                spans = [(shot.start_seconds, shot.end_seconds, shot.visual)]
            for start, end, visual in spans:
                description = visual.description if visual else ""
                items.append(
                    Candidate(
                        asset_id=asset.asset_id,
                        shot_id=shot.shot_id,
                        shot_start=shot.start_seconds,
                        shot_end=shot.end_seconds,
                        start=start,
                        end=end,
                        order=len(items),
                        tokens=_tokens(f"{description} {visual.location if visual else ''}"),
                        role=visual.editorial_role if visual else EditorialRole.UNKNOWN,
                        visual_type=visual.visual_type if visual else VisualType.UNKNOWN,
                        confidence=visual.confidence if visual else 0.0,
                        plate=bool(visual and PLATE.search(visual.visible_text.upper())),
                        description=description,
                        content_region=shot.content_region,
                        focus=visual.focus_point if visual else None,
                    )
                )
    return items


def _source_range(candidate: Candidate, usage: _Usage, need: float) -> tuple[float, float, bool]:
    """Pencereden kullanılabilir kaynak aralığı: (başlangıç, kullanılabilir süre, tekrar mı)."""
    lead = EDGE_SECONDS if candidate.start <= candidate.shot_start else 0.0
    limit = candidate.shot_end - EDGE_SECONDS
    fresh = max(candidate.start + lead, usage.cursor.get(candidate.shot_id, 0.0))
    if limit - fresh >= min(need, MIN_CLIP_SECONDS):
        return fresh, limit - fresh, False
    again = candidate.start + lead
    return again, max(0.0, limit - again), True


def _score(candidate: Candidate, segment_tokens: list[str], opening: bool, previous_shot: str | None, usage: _Usage, need: float) -> float:
    words = {t[:5] for t in segment_tokens if len(t) >= 5 and t not in STOPWORDS}
    score = 2.0 * sum(1 for stem in words if _has(candidate.tokens, {stem}))
    for news_stems, visual_stems in CONCEPTS:
        if _has(segment_tokens, news_stems) and _has(candidate.tokens, visual_stems):
            score += 3.0
    score += ROLE_BONUS.get(candidate.role, 0.0)
    if opening and (candidate.role in OPENING_ROLES or candidate.visual_type in OPENING_TYPES):
        score += 2.0
    if candidate.plate:
        score -= 1.0
    score += candidate.confidence * 0.5
    score -= 3.0 * usage.count.get(candidate.shot_id, 0)
    if candidate.shot_id == previous_shot:
        score -= 8.0
    _, available, repeated = _source_range(candidate, usage, need)
    if repeated:
        score -= 2.0
    if available < need:
        score -= 1.5
    if available < MIN_CLIP_SECONDS / 2:
        score -= 50.0
    return score


def clip_framing(mode: FramingMode, candidate: Candidate) -> Framing:
    """Odak noktası (Luna, tüm kareye göre) → asıl görüntü alanına göre odak."""
    fx, fy = (candidate.focus.x, candidate.focus.y) if candidate.focus else (0.5, 0.5)
    region = candidate.content_region
    if region:
        fx = (fx - region.x) / region.width
        fy = (fy - region.y) / region.height
    return Framing(
        mode=mode,
        focus_x=round(min(1.0, max(0.0, fx)), 3),
        focus_y=round(min(1.0, max(0.0, fy)), 3),
        content_region=region,
    )


def segment_times(project: EditProject) -> list[tuple[str, float, float]]:
    """(segment_id, başlangıç, bitiş) — boşluksuz; ilk segment 0'da, son segment ses sonunda biter."""
    segments = sorted(project.edit_plan.segments, key=lambda s: s.order)
    duration = project.audio.duration_seconds
    alignment = project.news.tts_alignment
    total_chars = max(1, len(project.news.tts_text))
    starts = []
    for segment in segments:
        if alignment and segment.char_start < len(alignment.start_seconds):
            starts.append(alignment.start_seconds[segment.char_start])
        else:
            starts.append(duration * segment.char_start / total_chars)
    if starts:
        starts[0] = 0.0
    ends = starts[1:] + [duration]
    return [(s.segment_id, start, end) for s, start, end in zip(segments, starts, ends) if end > start]


def plan_rough_cut(edit_project: dict[str, Any], media_library: dict[str, Any], framing_mode: str = FramingMode.FILL_CROP.value) -> dict[str, Any]:
    """EditProject'in video_main izini kural tabanlı kliplerle doldurur."""
    project = EditProject.model_validate(edit_project)
    candidates = _candidates(MediaLibrary.model_validate(media_library))
    if not candidates:
        raise ValueError("Kurgu için analiz edilmiş video sahnesi yok.")

    fps = project.edit_plan.timeline.fps
    total_f = round(project.audio.duration_seconds * fps)
    mode = FramingMode(framing_mode)
    usage = _Usage()
    clips: list[Clip] = []
    previous_shot: str | None = None
    timed = segment_times(project)
    texts = {s.segment_id: s.text for s in project.edit_plan.segments}

    for index, (segment_id, start, end) in enumerate(timed):
        segment_start_f = round(start * fps)
        segment_end_f = total_f if index == len(timed) - 1 else round(end * fps)
        segment_tokens = _tokens(texts[segment_id])
        pieces = max(1, math.ceil((segment_end_f - segment_start_f) / (MAX_CLIP_SECONDS * fps)))
        cursor_f = segment_start_f
        while cursor_f < segment_end_f:
            remaining_pieces = max(1, pieces - sum(1 for c in clips if c.segment_id == segment_id))
            target_f = math.ceil((segment_end_f - cursor_f) / remaining_pieces)
            need = target_f / fps
            opening = cursor_f == 0
            best = max(candidates, key=lambda c: (_score(c, segment_tokens, opening, previous_shot, usage, need), -c.order))
            source_in, available, _ = _source_range(best, usage, need)
            duration_f = max(1, min(target_f, math.floor(available * fps)))
            source_out = source_in + duration_f / fps
            clips.append(
                Clip(
                    id=f"video_{len(clips) + 1:03d}",
                    asset_id=best.asset_id,
                    shot_id=best.shot_id,
                    segment_id=segment_id,
                    source_in_s=round(source_in, 3),
                    source_out_s=round(source_out, 3),
                    start_f=cursor_f,
                    duration_f=duration_f,
                    framing=clip_framing(mode, best),
                    origin=ClipOrigin.RULE,
                    reason=best.description,
                )
            )
            usage.cursor[best.shot_id] = source_out
            usage.count[best.shot_id] = usage.count.get(best.shot_id, 0) + 1
            previous_shot = best.shot_id
            cursor_f += duration_f

    for track in project.edit_plan.timeline.tracks:
        if track.kind == TrackKind.VIDEO:
            track.clips = clips
            break
    return EditProject.model_validate(project.model_dump(mode="json")).model_dump(mode="json")


def has_rough_cut(edit_project: dict[str, Any] | None) -> bool:
    tracks = ((edit_project or {}).get("edit_plan") or {}).get("timeline", {}).get("tracks", [])
    return any(track.get("kind") == "video" and track.get("clips") for track in tracks)


def set_framing(edit_project: dict[str, Any], framing_mode: str) -> dict[str, Any]:
    """Tüm video kliplerinin kadraj modunu değiştirir (editörün seçimi)."""
    for track in edit_project["edit_plan"]["timeline"]["tracks"]:
        if track["kind"] == "video":
            for clip in track["clips"]:
                clip["framing"]["mode"] = framing_mode
    return edit_project


def clip_rows(edit_project: dict[str, Any]) -> list[dict[str, Any]]:
    """Geliştirici tablosu: hangi TTS cümlesine hangi sahne kesiti kondu."""
    fps = edit_project["edit_plan"]["timeline"]["fps"]
    rows = []
    for track in edit_project["edit_plan"]["timeline"]["tracks"]:
        if track["kind"] != "video":
            continue
        for clip in track["clips"]:
            rows.append(
                {
                    "Zaman (sn)": round(clip["start_f"] / fps, 2),
                    "Süre (sn)": round(clip["duration_f"] / fps, 2),
                    "Cümle": clip["segment_id"],
                    "Shot": clip["shot_id"],
                    "Kaynak (sn)": f"{clip['source_in_s']:.1f}-{clip['source_out_s']:.1f}",
                    "Odak": f"{clip['framing']['focus_x']:.2f}, {clip['framing']['focus_y']:.2f}",
                    "Kenar kırpma": "var" if clip["framing"].get("content_region") else "",
                    "Görüntü": clip["reason"],
                }
            )
    return rows
