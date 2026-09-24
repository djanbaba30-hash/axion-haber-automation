# Axion Repo Reset — 2026-09-24

## Included
- Clean monorepo layout for News Studio + Video Studio.
- News app split into AI, prompts, validation, TTS, integration, and models modules.
- Existing editorial prompt rules preserved as the baseline.
- Reset no longer removes authentication state.
- Generated TTS bytes persist in Streamlit session state across reruns.
- Real MP3 duration measured with Mutagen and calibration persisted locally.
- Selected ElevenLabs voice is remembered in session state.
- AI/TTS transient retry and timeout handling added.
- Censorship terms are reported as validation warnings rather than silently rewritten.
- Simple SQLite production history log added.
- Shared `NewsPackage` contract added for News → Video handoff.
- Video Studio accepts NewsPackage JSON and continues to use GPT-5.6 Luna only for visual analysis.
- FFmpeg subprocess calls receive bounded timeouts.
- Visual analysis now derives image MIME type from the actual frame/image extension.
- Basic unit tests included.

## Deliberately deferred
- AI Edit Planner: not implemented yet; objective media indexing remains separate from editorial selection.
- Final renderer/export pipeline: not implemented yet.
- Durable external database/object storage: not implemented; local SQLite/JSON is ephemeral on Streamlit Cloud.
