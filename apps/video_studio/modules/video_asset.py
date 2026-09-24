from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from shared.media_models import (
    AnalysisFrame,
    AnalysisWindow,
    AudioTechnicalInfo,
    DisplayGeometry,
    MediaSource,
    Shot,
    VideoAsset,
    VideoGeometry,
    VisualMetadata,
    VisualType,
    EditorialRole,
)

LUNA_PROMPT_VERSION = "media-index-v2.1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _enum_value(value: str, enum_cls, default):
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "person": "person",
        "people": "people",
        "insan": "person",
        "insanlar": "people",
        "place": "place",
        "mekan": "place",
        "location": "place",
        "event": "event",
        "olay": "event",
        "vehicle": "vehicle",
        "araç": "vehicle",
        "document": "document",
        "belge": "document",
        "screen": "screen",
        "ekran": "screen",
        "product": "product",
        "ürün": "product",
        "landscape": "landscape",
        "manzara": "landscape",
        "graphic": "graphic",
        "grafik": "graphic",
        "action": "action",
        "hareket": "action",
        "reaction": "reaction",
        "tepki": "reaction",
        "detail": "detail",
        "detay": "detail",
        "context": "context",
        "bağlam": "context",
        "evidence": "evidence",
        "kanıt": "evidence",
        "portrait": "portrait",
        "portre": "portrait",
        "establishing": "establishing",
        "genel_plan": "establishing",
        "genel": "establishing",
        "generic_broll": "generic_broll",
        "b_roll": "generic_broll",
    }
    candidate = aliases.get(normalized, normalized)
    try:
        return enum_cls(candidate)
    except ValueError:
        return default


def _visual_metadata(raw: dict[str, Any]) -> VisualMetadata:
    return VisualMetadata(
        description=str(raw.get("description") or ""),
        visual_type=_enum_value(raw.get("visual_type", ""), VisualType, VisualType.UNKNOWN),
        visible_people=bool(raw.get("visible_people", False)),
        location=str(raw.get("location") or "unknown"),
        text_visible=bool(raw.get("text_visible", False)),
        visible_text=str(raw.get("visible_text") or ""),
        editorial_role=_enum_value(raw.get("editorial_role", ""), EditorialRole, EditorialRole.UNKNOWN),
        confidence=float(raw.get("confidence") or 0.0),
    )


def build_video_asset(
    metadata: dict[str, Any],
    shots: list[dict[str, Any]],
    usage: dict[str, Any],
    analysis_mode: str,
    frame_count_per_shot: int,
    asset_id: str,
) -> dict[str, Any]:
    video_info = metadata.get("video", {})
    audio_info = metadata.get("audio", {})
    original_path = Path(metadata["original_path"])
    source = MediaSource(
        filename=str(metadata.get("original_filename") or original_path.name),
        extension=original_path.suffix.lower(),
        sha256=sha256_file(original_path),
        original_path=str(original_path),
        size_bytes=int(metadata.get("file_size_bytes") or original_path.stat().st_size),
        duration_seconds=float(metadata.get("duration_seconds") or 0.0),
    )
    width = int(video_info.get("width") or 0)
    height = int(video_info.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError(f"Video {asset_id} için geçerli çözünürlük bulunamadı.")

    display = DisplayGeometry(width=width, height=height, rotation_degrees=0)
    geometry = VideoGeometry(
        encoded_width=width,
        encoded_height=height,
        display=display,
        fps=video_info.get("fps"),
        codec=video_info.get("codec"),
        pixel_format=video_info.get("pixel_format"),
    )
    audio = None
    if audio_info:
        audio = AudioTechnicalInfo(
            codec=audio_info.get("codec"),
            sample_rate=int(audio_info["sample_rate"]) if audio_info.get("sample_rate") else None,
            channels=int(audio_info["channels"]) if audio_info.get("channels") else None,
            channel_layout=audio_info.get("channel_layout"),
        )

    parsed_shots: list[Shot] = []
    for shot in shots:
        shot_id = str(shot["shot_id"])
        frames = [
            AnalysisFrame(
                frame_index=int(frame["frame_index"]),
                timestamp_seconds=float(frame["timestamp_seconds"]),
                path=str(frame["path"]),
            )
            for frame in shot.get("analysis_frames", [])
        ]
        window = None
        if frames:
            window = AnalysisWindow(
                window_id=f"{shot_id}_window_001",
                shot_id=shot_id,
                start_seconds=float(shot["start_seconds"]),
                end_seconds=float(shot["end_seconds"]),
                frames=frames,
            )
        visual_raw = shot.get("visual_asset") or {}
        parsed_shots.append(
            Shot(
                shot_id=shot_id,
                asset_id=asset_id,
                shot_number=int(shot["shot_number"]),
                start_seconds=float(shot["start_seconds"]),
                end_seconds=float(shot["end_seconds"]),
                duration_seconds=float(shot["duration_seconds"]),
                analysis_windows=[window] if window else [],
                visual=_visual_metadata(visual_raw),
            )
        )

    return VideoAsset(
        asset_id=asset_id,
        source=source,
        geometry=geometry,
        audio=audio,
        shots=parsed_shots,
        analysis_model=usage.get("model", ""),
        analysis_prompt_version=LUNA_PROMPT_VERSION,
        analysis_frame_count=sum(len(s.get("analysis_frames", [])) for s in shots),
        metadata={
            "analysis_mode": analysis_mode,
            "frame_count_per_shot": frame_count_per_shot,
        },
    ).model_dump(mode="json")


def build_image_asset_model(image: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
    path = Path(image["path"])
    size_bytes = path.stat().st_size
    return {
        "asset_id": image["asset_id"],
        "asset_type": "image",
        "schema_version": "1.1",
        "source": {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "sha256": sha256_file(path),
            "original_path": str(path),
            "size_bytes": size_bytes,
        },
        "geometry": None,
        "visual": VisualMetadata.model_validate(
            image.get("visual_asset") or {}
        ).model_dump(mode="json") if image.get("visual_asset") else None,
        "analysis_model": usage.get("model", ""),
        "analysis_prompt_version": LUNA_PROMPT_VERSION,
        "metadata": {},
    }
