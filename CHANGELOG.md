# v1.3.0 — Axion Local (Faz 0) — 2026-09-24

## Added
- `axion_local.py`: Haber Stüdyosu and Video Studio run as one Streamlit app with one password (`st.navigation`). The modules stay separate.
- `apps/axion_local/store.py`: persistent project folder (`data/projects/<time>_<headline>/news_package.json + tts.mp3`) and media inbox listing (default `~/Downloads`, overridable with `AXION_DATA_DIR` / `AXION_INBOX_DIR`).
- News Studio (local mode only): "Projeye kaydet" stores the package together with the audio and its sha256. Saving is blocked when the TTS text changed after the audio was generated.
- Video Studio (local mode only):
  - media can be picked from a local folder and is read in place, without upload or copy (`LocalMediaFile`);
  - saved news projects load caption and TTS audio directly; the audio hash is verified.
- Windows `windows/kurulum.bat`, `axion_baslat.bat`, `guncelle.bat` and the Turkish guide `KURULUM.md` (Tailscale access from the tablet).

## Unchanged
- News generation, prompts and validation. The Streamlit Cloud behaviour of both apps is unchanged outside local mode.

# v1.2.0 — Viral TTS quality — 2026-09-24

## Changed
- News prompt tuned for Turkish social media:
  - first TTS sentence carries the most striking event;
  - every sentence must add new information (restating an event or a number counts as repetition);
  - the duration target is an upper bound — add unused facts, otherwise finish short;
  - conversational tone without agency phrases, semicolons or street-level addresses;
  - no license plates or ID-type details;
  - witness guesses are attributed, not stated as fact;
  - the two headlines must not repeat each other or use verbs that are not in the source.
- Structured output gains `tts_plani` (one short line per TTS sentence, before `tts`), so the model plans distinct facts inside the same call. No extra API call.
- Validation:
  - TTS below the target is now a warning instead of an error, so it no longer triggers a correction call. Below 60% of the minimum is still an error; above the maximum still is too.
  - Heuristic repetition warning for TTS sentences (a shared number plus a shared word stem, or 3+ shared stems).
  - `NN ABC NNN plakalı` is removed automatically, with a warning.
  - TTS semicolons are split into sentences.

## Cost
- About +345 input tokens per request, mostly in the cached system prompt, and about +60 output tokens for the plan. Under-length TTS no longer costs a second request.

# v1.1.2 — Contract revision and fixes — 2026-09-24

## Fixed
- Video Studio: Luna image data URLs were sent as the literal text `{image_mime_type(...)}` (missing f-string), breaking visual analysis for every video. Frames and standalone images now both use the real MIME type from the file extension (`image_data_url`).
- Video Studio: every FFmpeg/FFprobe call goes through `modules/ffmpeg_runner.py`. Probe and frame extraction: 60 s. Proxy transcode (previously no timeout) and scene detection: 4× video duration, clamped to 300–3600 s. A timeout raises a readable `RuntimeError`, and temporary proxy/frame files are removed.
- Video Studio: wrong password now shows "Şifre yanlış."; password comparison uses `hmac.compare_digest`.
- News prompt: the caption source instruction was truncated ("ek." → "ekle.").
- News prompt: `build_correction_prompt` no longer uses a backslash inside an f-string expression (SyntaxError on Python < 3.12). Prompt output is unchanged.
- Retry: `anthropic.OverloadedError` (529) is now treated as transient. The OpenAI/Anthropic SDK internal retries are disabled (`max_retries=0`), so `retry_transient` is the only retry layer (previously up to 3×3 = 9 requests).

## Contract (shared/)
- NewsPackage: `parse_news_package` is the single entry point for every version. 1.0 files (flat, nested `news`, Turkish field names, `schema_version: null`) are migrated to 1.1. Unknown legacy fields are kept under `metadata.legacy_fields`.
- Video Studio's NewsPackage import now uses the shared contract instead of its own parser.
- NewsReference validates `tts_alignment` against `tts_text`.
- EditProject cross-validation:
  - segment text equals `tts_text[char_start:char_end]`;
  - segments are ordered, non-overlapping and cover the whole `tts_text` (whitespace excepted);
  - clip `asset_id` exists in `media` (audio clips: `audio.asset_id` or `media`) and clip `segment_id` exists;
  - timeline end does not exceed the TTS duration;
  - `media` has no duplicate asset ids.
- Timeline and track rules:
  - no overlapping clips within a track;
  - clip and track ids are unique;
  - transition in + out ≤ clip duration;
  - `cut`/`none` transitions have a duration of 0 and `fade` has a duration above 0;
  - segment `order` runs 1..n.
- Media:
  - Shot `start_seconds` ≥ 0;
  - AnalysisWindow must lie inside its Shot, and AnalysisFrame inside its window;
  - fractional rotation is rejected;
  - `exif_orientation` must be 1–8.
- `FramingMode.VERTICAL_CROP` merged into `FILL_CROP` (both are documented). The unused `EditPlan.snapshot_id` field was removed.

## Process
- Tests run with pytest: `make test` (80 tests; previously only 4 unittest tests ran). `pytest` moved to `requirements-dev.txt`.
- `.github/workflows/extract-repo.yml` removed. `.pytest_cache/` and `*.zip` added to `.gitignore`.

## Known / deferred
- Video Studio still builds its draft project with `apps/video_studio/modules/edit_plan.py` (format 1.1). The target contract is `shared/edit_models.py` (2.1); the switch happens when the Edit Planner is connected.
- ElevenLabs TTS calls are not retried, because a retry could consume character quota twice.

# Axion Repo Reset — 2026-09-24

## Included
- Clean monorepo layout for News Studio + Video Studio.
- News app split into AI, prompts, validation, TTS, integration, and models modules.
- Existing editorial prompt rules preserved as the baseline.
- Reset no longer removes authentication state.
- Generated TTS bytes persist in Streamlit session state across reruns.
- Real MP3 duration measured with Mutagen and calibration persisted locally.
- Selected ElevenLabs voice is remembered in session state.
- AI (OpenAI/Claude) transient retry and request timeouts added. ElevenLabs has a request timeout but no retry.
- Censorship terms are reported as validation warnings rather than silently rewritten.
- Simple SQLite production history log added.
- Shared `NewsPackage` contract added for News → Video handoff.
- Video Studio accepts NewsPackage JSON and continues to use GPT-5.6 Luna only for visual analysis.
- Basic unit tests included.

## Deliberately deferred
- AI Edit Planner: not implemented yet; objective media indexing remains separate from editorial selection.
- Final renderer/export pipeline: not implemented yet.
- Durable external database/object storage: not implemented; local SQLite/JSON is ephemeral on Streamlit Cloud.
