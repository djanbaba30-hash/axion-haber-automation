"""Medya dosyalarını ortak MediaLibrary 2.1 sözleşmesine dönüştüren pipeline."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from apps.axion_local.metrics import step
from shared.media_models import MediaLibrary

from .framing import detect_content_region, motion_regions
from .local_media import LocalMediaFile
from .media_library import build_image_asset, build_media_library, detect_media_type
from .representative_sampling import extract_representative_frames, split_into_windows
from .shot_detection import detect_shots
from .video_asset import LUNA_PROMPT_VERSION, build_image_asset_model, build_video_asset
from .video_ingestion import create_proxy, probe_video, save_uploaded_video, store_upload
from .visual_analysis import analyze_media_with_luna

PROXY_WIDTH = 640  # Luna'ya giden analiz kareleri de 640 px; daha büyük proxy yalnızca süre kaybı.
MAX_FRAMES_PER_VIDEO = 40
# Süre ölçümünün alt adımları (v4.1; data/olcumler.jsonl "adimlar", Geliştirici bilgileri'nde bu adlarla).
STEP_LABELS = {"okuma": "okuma", "proxy": "analiz kopyası", "sahne_tespiti": "sahne tespiti", "kareler": "kareler",
               "kadraj": "kadraj", "hareket": "hareket", "luna_hazirlik": "Luna hazırlık", "luna_cevap": "Luna cevabı"}
Progress = Callable[[str], None]


def _image_path(file, storage_dir: Path | None = None) -> Path:
    if isinstance(file, LocalMediaFile):
        return file.path
    if storage_dir is not None:
        return store_upload(file, storage_dir)
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix.lower()) as temp:
        temp.write(file.getbuffer())
    return Path(temp.name)


def _scratch_files(metadata: dict[str, Any], shots: list[dict[str, Any]]) -> list[Path]:
    paths = [Path(metadata["proxy"]["path"])]
    for shot in shots:
        paths.extend(Path(frame["path"]) for frame in shot.get("analysis_frames", []))
    return paths


def capped_frame_count(shots: list[dict[str, Any]], frame_count: int) -> int:
    """Pencere başına kare sayısı; bir videodan Luna'ya en fazla MAX_FRAMES_PER_VIDEO kare gitsin (maliyet tavanı).

    Ekonomik modda (1 kare) sınır uygulanmaz: her pencerenin en az bir karesi olmalı.
    """
    windows = sum(len(split_into_windows(float(s["start_seconds"]), float(s["end_seconds"]))) for s in shots)
    if windows * frame_count <= MAX_FRAMES_PER_VIDEO:
        return frame_count
    return max(1, MAX_FRAMES_PER_VIDEO // max(1, windows))


def _ingest_video(file, asset_id: str, frame_count: int, progress: Progress, storage_dir: Path | None = None,
                  steps: dict[str, float] | None = None):
    progress(f"{file.name}: video okunuyor")
    with step(steps, "okuma"):
        video_path = save_uploaded_video(file, storage_dir=storage_dir)
        metadata = probe_video(video_path)
    metadata["original_filename"] = file.name
    metadata["original_path"] = str(video_path)

    progress(f"{file.name}: analiz kopyası (proxy) hazırlanıyor")
    with step(steps, "proxy"):
        proxy_path = create_proxy(video_path, width=PROXY_WIDTH, duration_seconds=metadata.get("duration_seconds"))
    metadata["proxy"] = {
        "path": str(proxy_path),
        "size_mb": round(proxy_path.stat().st_size / (1024 * 1024), 2),
        "width": PROXY_WIDTH,
    }

    try:
        progress(f"{file.name}: sahneler tespit ediliyor")
        with step(steps, "sahne_tespiti"):
            shots = detect_shots(proxy_path, metadata["duration_seconds"])
        with step(steps, "kareler"):
            shots = extract_representative_frames(proxy_path, shots, frame_count=capped_frame_count(shots, frame_count))
    except Exception:
        # Yarıda kalan analiz geçici dosya bırakmasın (başarılıysa temizlik prepare_media_library'de).
        proxy_path.unlink(missing_ok=True)
        raise
    progress(f"{file.name}: kadraj alanı belirleniyor")
    full_frame = []  # tam karedeki pencereler: sabit kamerada hareket bölgesi (yanları dolgulu dikeyde kadraj sabit)
    for shot in shots:
        with step(steps, "kadraj"):
            region = detect_content_region([Path(frame["path"]) for frame in shot["analysis_frames"]])
        shot["content_region"] = region.model_dump() if region else None
        shot["asset_id"] = asset_id
        shot["shot_id"] = f"{asset_id}_shot_{int(shot['shot_number']):03d}"
        for number, window in enumerate(shot["analysis_windows"], 1):
            window["window_id"] = f"{shot['shot_id']}_w{number:02d}"
            if region is None:
                full_frame.append(window)
    spans = [(float(w["start_seconds"]), float(w["end_seconds"])) for w in full_frame]
    with step(steps, "hareket"):
        moving_regions = motion_regions(proxy_path, spans)
    for window, moving in zip(full_frame, moving_regions):
        window["motion_region"] = moving.model_dump() if moving else None
    return metadata, shots


def prepare_media_library(
    files: Sequence,
    frame_count: int,
    analysis_mode: str,
    api_key: str,
    progress: Progress = lambda message: None,
    storage_dir: Path | None = None,
    context: str = "",
    steps: dict[str, float] | None = None,
):
    """`steps` (v4.1): alt adımların süresi (okuma, proxy, sahne tespiti, kareler, kadraj, hareket, Luna hazırlık ve
    cevap; birkaç videoda toplam) buraya yazılır; çağıran ölçüm satırına ekler (data/olcumler.jsonl)."""
    videos = []
    all_shots = []
    images = []
    temp_images: list[Path] = []
    scratch: list[Path] = []

    try:
        for file in files:
            media_type = detect_media_type(file.name)
            if media_type == "video":
                asset_id = f"video_{len(videos) + 1:03d}"
                metadata, shots = _ingest_video(file, asset_id, frame_count, progress, storage_dir=storage_dir,
                                                steps=steps)
                scratch.extend(_scratch_files(metadata, shots))
                videos.append((asset_id, metadata, shots))
                all_shots.extend(shots)
            else:
                image_asset = build_image_asset(file, len(images) + 1)
                image_path = _image_path(file, storage_dir=storage_dir)
                image_asset["path"] = str(image_path)
                images.append(image_asset)
                if not isinstance(file, LocalMediaFile) and storage_dir is None:
                    temp_images.append(image_path)

        progress("Luna görüntüleri analiz ediyor")
        window_visuals, image_visuals, usage = analyze_media_with_luna(all_shots, images, api_key, context, steps)

        assets: list[dict[str, Any]] = [
            build_video_asset(
                metadata=metadata,
                shots=shots,
                window_visuals=window_visuals,
                usage=usage,
                analysis_mode=analysis_mode,
                frame_count_per_shot=frame_count,
                asset_id=asset_id,
            )
            for asset_id, metadata, shots in videos
        ]
        assets.extend(build_image_asset_model(image, image_visuals.get(image["asset_id"]), usage) for image in images)
    finally:
        # Proxy, analiz kareleri ve proje dışına yazılmış geçici görseller artık gereksiz.
        for path in scratch + temp_images:
            path.unlink(missing_ok=True)

    return build_media_library(assets=assets, usage=usage), usage


def is_current_media_library(data: dict[str, Any] | None) -> bool:
    """Kayıtlı analiz bu sürümün sözleşmesi ve Luna prompt'uyla mı yapılmış? Değilse yeniden analiz gerekir."""
    try:
        library = MediaLibrary.model_validate(data or {})
    except ValidationError:
        return False
    return bool(library.assets) and all(a.analysis_prompt_version == LUNA_PROMPT_VERSION for a in library.assets)


def shot_rows(media_library: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for asset in media_library.get("assets", []):
        filename = asset.get("source", {}).get("filename", "")
        if asset.get("asset_type") == "image":  # fotoğraf: tek satır, süresi yok
            visual = asset.get("visual") or {}
            rows.append({"Video": filename, "Sahne": None, "Başlangıç": "fotoğraf", "Bitiş": "", "Süre (sn)": None,
                         "Görüntü": visual.get("visual_type", ""), "Rol": visual.get("editorial_role", ""),
                         "Açıklama": visual.get("description", "")})
            continue
        for shot in asset.get("shots", []):
            visual = shot.get("visual") or {}
            rows.append(
                {
                    "Video": filename,
                    "Sahne": shot.get("shot_number"),
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
