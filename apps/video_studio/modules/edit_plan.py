"""Deterministic EditProject 2.1 builder.

Bu katman henüz otomatik kurgu kararı vermez. Haber/TTS alignment, medya referansları
ve timeline için güvenilir ortak sözleşmeyi üretir; gerçek kurgu seçimi bir sonraki
planner katmanına bırakılır.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from shared.edit_models import (
    AudioReference,
    Clip,
    ClipOrigin,
    ClipType,
    EditPlan,
    EditProject,
    NewsReference,
    NewsSegment,
    Timeline,
    Track,
    TrackKind,
)
from shared.axion_template import VIDEO_HEIGHT, VIDEO_WIDTH
from shared.media_models import MediaLibrary
from shared.news_package import TTSAlignment, ensure_alignment_matches_text


def _clean_news_package(news_package: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(news_package, dict):
        return {}
    return news_package


def _tts_alignment(package: dict[str, Any], tts_text: str) -> TTSAlignment | None:
    raw = package.get("tts_alignment")
    if not isinstance(raw, dict):
        return None
    alignment = TTSAlignment.model_validate(raw)
    ensure_alignment_matches_text(alignment, tts_text)
    return alignment


def _segment_ranges(tts_text: str) -> list[tuple[int, int]]:
    """Cümle/ifade sınırlarını deterministik biçimde bulur; boşlukları segmentlere dahil eder."""
    if not tts_text:
        return []
    ranges: list[tuple[int, int]] = []
    start = 0
    for match in re.finditer(r"""[.!?…]+(?:["”'’»)]*)(?=\s|$)\s*""", tts_text):
        end = match.end()
        content_end = match.start() + len(match.group(0).rstrip())
        if content_end > start:
            ranges.append((start, content_end))
        start = end
    if start < len(tts_text):
        ranges.append((start, len(tts_text)))
    return ranges or [(0, len(tts_text))]


def _segments_from_alignment(tts_text: str, alignment: TTSAlignment | None) -> list[NewsSegment]:
    segments: list[NewsSegment] = []
    for order, (start, end) in enumerate(_segment_ranges(tts_text), 1):
        text = tts_text[start:end]
        if not text.strip():
            continue
        segments.append(
            NewsSegment(
                segment_id=f"segment_{order:03d}",
                order=order,
                text=text,
                char_start=start,
                char_end=end,
            )
        )
    return segments


def _library_id(library: MediaLibrary) -> str:
    material = "|".join(
        f"{asset.asset_id}:{asset.source.sha256}"
        for asset in library.assets
    )
    return "media_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def build_edit_project(
    media_library: dict[str, Any],
    news_text: str = "",
    audio_path: str | None = None,
    audio_duration_seconds: float = 0.0,
    news_package: dict[str, Any] | None = None,
    audio_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package = _clean_news_package(news_package)
    library = MediaLibrary.model_validate(media_library or {})

    tts_text = str(package.get("news", {}).get("tts_text") or package.get("tts_text") or "").strip()
    if not tts_text:
        tts_text = str(news_text or "").strip()

    caption = str(package.get("news", {}).get("caption") or package.get("caption") or news_text or "").strip()
    headline_1 = str(package.get("news", {}).get("headline_1") or package.get("headline_1") or "").strip()
    headline_2 = str(package.get("news", {}).get("headline_2") or package.get("headline_2") or "").strip()
    source_text = str(package.get("news", {}).get("source_text") or package.get("source_text") or "").strip()

    alignment = _tts_alignment(package, tts_text)
    if not alignment and not tts_text:
        raise ValueError("Seslendirme metni boş; kurgu projesi oluşturulamaz.")
    duration = float(audio_duration_seconds or 0.0)
    if alignment:
        alignment_duration = alignment.duration_seconds()
        if alignment_duration > 0:
            duration = max(duration, alignment_duration)

    if not audio_path or duration <= 0:
        raise ValueError("Kurgu için haberin seslendirmesi gerekli.")

    audio_meta = audio_metadata if isinstance(audio_metadata, dict) else {}
    audio_sha = (
        audio_meta.get("sha256")
        or package.get("metadata", {}).get("audio_sha256")
        or package.get("news", {}).get("metadata", {}).get("audio_sha256")
    )

    audio = AudioReference(
        asset_id="audio_tts",
        path=str(audio_path),
        filename=audio_meta.get("filename") or Path(audio_path).name,
        mime_type=audio_meta.get("mime_type") or "audio/mpeg",
        duration_seconds=round(duration, 3),
        sha256=audio_sha,
    )

    segments = _segments_from_alignment(tts_text, alignment)
    timeline = Timeline(fps=30, width=VIDEO_WIDTH, height=VIDEO_HEIGHT, tracks=[
        Track(id="video_main", kind=TrackKind.VIDEO, clips=[]),
        Track(id="overlay_main", kind=TrackKind.OVERLAY, clips=[]),
        Track(id="audio_main", kind=TrackKind.AUDIO, clips=[
            Clip(
                id="audio_tts",
                clip_type=ClipType.AUDIO,
                asset_id=audio.asset_id,
                start_f=0,
                duration_f=round(duration * 30),
                source_in_s=0.0,
                source_out_s=duration,
                origin=ClipOrigin.USER,
                reason="Haber TTS sesi timeline'ın zaman referansıdır.",
            )
        ]),
    ])

    project_id = str(package.get("metadata", {}).get("project_id") or "")
    if not project_id:
        project_id = "news_" + hashlib.sha256((headline_1 + "|" + tts_text).encode("utf-8")).hexdigest()[:16]

    project = EditProject(
        project_id=project_id,
        library_id=_library_id(library),
        news=NewsReference(
            package_schema_version=str(package.get("schema_version") or "1.1"),
            headline_1=headline_1,
            headline_2=headline_2,
            caption=caption,
            tts_text=tts_text,
            source_text=source_text,
            tts_alignment=alignment,
        ),
        audio=audio,
        media=library.asset_refs,
        edit_plan=EditPlan(
            segments=segments,
            timeline=timeline,
        ),
    )
    return project.model_dump(mode="json")
