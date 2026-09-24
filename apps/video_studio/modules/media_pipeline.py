"""Medya dosyalarını ortak MediaLibrary 2.1 sözleşmesine dönüştüren pipeline."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .local_media import LocalMediaFile
from .media_library import build_image_asset, build_media_library, detect_media_type
from .representative_sampling import extract_representative_frames
from .shot_detection import detect_shots
from .video_asset import build_image_asset_model, build_video_asset
from .video_ingestion import create_proxy, probe_video, save_uploaded_video
from .visual_analysis import analyze_media_with_luna

PROXY_WIDTH = 960
Progress = Callable[[str], None]


def _image_path(file, storage_dir: Path | None = None) -> Path:
    if isinstance(file, LocalMediaFile):
        return file.path
    if storage_dir is not None:
        storage_dir.mkdir(parents=True, exist_ok=True)
        target = storage_dir / Path(file.name).name
        if target.exists():
            target = storage_dir / f"{target.stem}_{abs(hash(file.name)) & 0xfffffff}{target.suffix}"
        target.write_bytes(file.getbuffer())
        return target
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix.lower()) as temp:
        temp.write(file.getbuffer())
    return Path(temp.name)


def _scratch_files(metadata: dict[str, Any], shots: list[dict[str, Any]]) -> list[Path]:
    paths = [Path(metadata["proxy"]["path"])]
    for shot in shots:
        paths.extend(Path(frame["path"]) for frame in shot.get("analysis_frames", []))
    return paths


def _ingest_video(file, asset_id: str, frame_count: int, progress: Progress, storage_dir: Path | None = None):
    progress(f"{file.name}: video okunuyor")
    video_path = save_uploaded_video(file, storage_dir=storage_dir)
    metadata = probe_video(video_path)
    metadata["original_filename"] = file.name
    metadata["original_path"] = str(video_path)

    progress(f"{file.name}: analiz kopyası (proxy) hazırlanıyor")
    proxy_path = create_proxy(video_path, width=PROXY_WIDTH, duration_seconds=metadata.get("duration_seconds"))
    metadata["proxy"] = {
        "path": str(proxy_path),
        "size_mb": round(proxy_path.stat().st_size / (1024 * 1024), 2),
        "width": PROXY_WIDTH,
    }

    progress(f"{file.name}: sahneler tespit ediliyor")
    shots = detect_shots(proxy_path, metadata["duration_seconds"])
    shots = extract_representative_frames(proxy_path, shots, frame_count=frame_count)
    for shot in shots:
        shot["asset_id"] = asset_id
        shot["shot_id"] = f"{asset_id}_shot_{int(shot['shot_number']):03d}"
    return metadata, shots


def prepare_media_library(
    files: Sequence,
    frame_count: int,
    analysis_mode: str,
    api_key: str,
    progress: Progress = lambda message: None,
    storage_dir: Path | None = None,
):
    videos = []
    all_shots = []
    images = []
    image_paths: list[Path] = []
    scratch: list[Path] = []

    try:
        for file in files:
            media_type = detect_media_type(file.name)
            if media_type == "video":
                asset_id = f"video_{len(videos) + 1:03d}"
                metadata, shots = _ingest_video(file, asset_id, frame_count, progress, storage_dir=storage_dir)
                scratch.extend(_scratch_files(metadata, shots))
                videos.append((asset_id, metadata, shots))
                all_shots.extend(shots)
            else:
                image_asset = build_image_asset(file, len(images) + 1)
                image_path = _image_path(file, storage_dir=storage_dir)
                image_asset["path"] = str(image_path)
                images.append(image_asset)
                image_paths.append(image_path)

        progress("Luna görüntüleri analiz ediyor")
        analyzed_shots, analyzed_images, usage = analyze_media_with_luna(all_shots, images, api_key)
    finally:
        for path in scratch:
            path.unlink(missing_ok=True)
        # Browser upload görselleri geçici olduğundan analizden sonra silinebilir.
        for path, image in zip(image_paths, images):
            if not isinstance(next((f for f in files if getattr(f, "name", None) == image["source"]["filename"]), None), LocalMediaFile):
                path.unlink(missing_ok=True)

    analyzed_by_id = {shot["shot_id"]: shot for shot in analyzed_shots}

    assets: list[dict[str, Any]] = []
    for asset_id, metadata, shots in videos:
        final_shots = [analyzed_by_id.get(shot["shot_id"], shot) for shot in shots]
        assets.append(
            build_video_asset(
                metadata=metadata,
                shots=final_shots,
                usage=usage,
                analysis_mode=analysis_mode,
                frame_count_per_shot=frame_count,
                asset_id=asset_id,
            )
        )
    for image in analyzed_images:
        assets.append(build_image_asset_model(image, usage))

    return build_media_library(assets=assets, usage=usage), usage


def shot_rows(media_library: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for asset in media_library.get("assets", []):
        if asset.get("asset_type") != "video":
            continue
        filename = asset.get("source", {}).get("filename", "")
        for shot in asset.get("shots", []):
            visual = shot.get("visual") or {}
            rows.append(
                {
                    "Video": filename,
                    "Shot": shot.get("shot_number"),
                    "Başlangıç": _format_timestamp(shot.get("start_seconds", 0)),
                    "Bitiş": _format_timestamp(shot.get("end_seconds", 0)),
                    "Süre (sn)": round(float(shot.get("duration_seconds") or 0), 1),
                    "Görüntü": visual.get("visual_type", ""),
                    "Rol": visual.get("editorial_role", ""),
                    "Açıklama": visual.get("description", ""),
                }
            )
    return rows


def _format_timestamp(seconds: float) -> str:
    total = max(0.0, float(seconds))
    minutes = int(total // 60)
    remaining = total - minutes * 60
    return f"{minutes:02d}:{remaining:05.2f}"
