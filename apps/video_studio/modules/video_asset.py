from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from shared.media_models import (
    AnalysisFrame,
    AnalysisWindow,
    AudioTechnicalInfo,
    DisplayGeometry,
    ImageAsset,
    MediaSource,
    Shot,
    VideoAsset,
    VideoGeometry,
)

# Prompt/şema değişince artır: eski sürümle yapılmış analiz yeniden istenir.
LUNA_PROMPT_VERSION = "media-index-v2.3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_video_asset(
    metadata: dict[str, Any],
    shots: list[dict[str, Any]],
    window_visuals: dict[str, dict[str, Any]],
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
        windows = [
            AnalysisWindow(
                window_id=window["window_id"],
                shot_id=shot_id,
                start_seconds=float(window["start_seconds"]),
                end_seconds=float(window["end_seconds"]),
                frames=[AnalysisFrame(**frame) for frame in window.get("frames", [])],
                visual=window_visuals.get(window["window_id"]),
            )
            for window in shot.get("analysis_windows", [])
        ]
        # Shot özeti: ilk analiz edilmiş pencere (tek pencereli shot'ta aynısı).
        visual = next((w.visual for w in windows if w.visual is not None), None)
        parsed_shots.append(
            Shot(
                shot_id=shot_id,
                asset_id=asset_id,
                shot_number=int(shot["shot_number"]),
                start_seconds=float(shot["start_seconds"]),
                end_seconds=float(shot["end_seconds"]),
                duration_seconds=float(shot["duration_seconds"]),
                analysis_windows=windows,
                visual=visual,
                content_region=shot.get("content_region"),
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


def build_image_asset_model(image: dict[str, Any], visual: dict[str, Any] | None, usage: dict[str, Any]) -> dict[str, Any]:
    path = Path(image["path"])
    return ImageAsset(
        asset_id=image["asset_id"],
        source=MediaSource(
            filename=image["source"]["filename"],
            extension=path.suffix.lower(),
            sha256=sha256_file(path),
            original_path=str(path),
            size_bytes=path.stat().st_size,
        ),
        visual=visual,
        analysis_model=usage.get("model", ""),
        analysis_prompt_version=LUNA_PROMPT_VERSION,
    ).model_dump(mode="json")
