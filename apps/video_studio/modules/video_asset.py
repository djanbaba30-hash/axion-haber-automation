from __future__ import annotations

from typing import Any


def build_video_asset(
    metadata: dict[str, Any],
    shots: list[dict[str, Any]],
    usage: dict[str, Any],
    analysis_mode: str,
    frame_count_per_shot: int,
    asset_id: str,
) -> dict[str, Any]:

    video_info = metadata.get(
        "video",
        {},
    )

    audio_info = metadata.get(
        "audio",
        {},
    )

    total_frame_count = sum(
        len(
            shot.get(
                "analysis_frames",
                [],
            )
        )
        for shot in shots
    )

    video_asset = {
        "asset_id": asset_id,

        "asset_type": "video",

        "schema_version": "1.0",

        "source": {
            "filename": metadata.get(
                "original_filename",
                "",
            ),

            "duration_seconds": metadata.get(
                "duration_seconds",
                0,
            ),

            "duration_formatted": metadata.get(
                "duration_formatted",
                "",
            ),

            "file_size_mb": metadata.get(
                "file_size_mb",
                0,
            ),
        },

        "technical": {
            "video": {
                "codec": video_info.get(
                    "codec"
                ),

                "width": video_info.get(
                    "width"
                ),

                "height": video_info.get(
                    "height"
                ),

                "fps": video_info.get(
                    "fps"
                ),

                "pixel_format": video_info.get(
                    "pixel_format"
                ),
            },

            "audio": {
                "codec": audio_info.get(
                    "codec"
                ),

                "sample_rate": audio_info.get(
                    "sample_rate"
                ),

                "channels": audio_info.get(
                    "channels"
                ),

                "channel_layout": audio_info.get(
                    "channel_layout"
                ),
            },
        },

        "analysis": {
            "model": usage.get(
                "model",
                "",
            ),

            "frame_count": total_frame_count,

            "frame_count_per_shot": (
                frame_count_per_shot
            ),

            "analysis_mode": analysis_mode,
        },

        "shots": [
            build_shot_asset(
                shot,
                asset_id,
            )
            for shot in shots
        ],
    }

    return video_asset


def build_shot_asset(
    shot: dict[str, Any],
    asset_id: str,
) -> dict[str, Any]:

    visual_asset = shot.get(
        "visual_asset",
        {},
    )

    if not isinstance(
        visual_asset,
        dict,
    ):
        visual_asset = {}

    subjects = visual_asset.get(
        "subjects",
        [],
    )

    if not isinstance(
        subjects,
        list,
    ):
        subjects = []

    shot_number = int(
        shot.get(
            "shot_number",
            0,
        )
    )

    shot_id = (
        f"{asset_id}_shot_"
        f"{shot_number:03d}"
    )

    return {
        "shot_id": shot_id,

        "asset_id": asset_id,

        "shot_number": shot_number,

        "start_seconds": shot.get(
            "start_seconds"
        ),

        "end_seconds": shot.get(
            "end_seconds"
        ),

        "duration_seconds": shot.get(
            "duration_seconds"
        ),

        "start_formatted": shot.get(
            "start_formatted"
        ),

        "end_formatted": shot.get(
            "end_formatted"
        ),

        "duration_formatted": shot.get(
            "duration_formatted"
        ),

        "visual": {
            "visual_type": visual_asset.get(
                "visual_type",
                "unknown",
            ),

            "subjects": subjects,

            "location": visual_asset.get(
                "location",
                "unknown",
            ),

            "editorial_role": visual_asset.get(
                "editorial_role",
                "",
            ),

            "confidence": visual_asset.get(
                "confidence",
                0.0,
            ),
        },
    }
