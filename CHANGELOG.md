# v1.6.1 — 2026-09-24

## Changed
- Removed the logo from the sidebar and the password screen; the sidebar starts with the page links. The Axion X mark stays only as the browser tab icon and the desktop icon.
- The desktop icon file is renamed to `windows/axion_x.ico` so Windows' icon cache picks up the new X mark. `guncelle.bat` now recreates the desktop shortcut on every update.

# v1.6.0 — Axion branding, remembered settings, leaner Video Studio — 2026-09-24

## Changed
- White theme in the Axion logo colours (navy `#123249` primary, light blue and green accents). The logo is in the sidebar above custom page links; the X mark is the browser tab icon and the new `windows/axion.ico`.
- Haber Stüdyosu sidebar:
  - style, duration, AI provider, model, reasoning level and voice are always visible;
  - voice fine-tuning sits in a collapsed "Ses ince ayarları" section;
  - all of these settings are remembered across sessions in `data/ayarlar.json` (`apps/axion_local/preferences.py`).
- Video Studio:
  - the shot table moved to developer info;
  - the news text box was removed; the text comes from the project;
  - browser upload became a toggle under "Gelişmiş";
  - status is a single line.

# v1.5.0 — Timed TTS (Faz 1) and a simpler interface — 2026-09-24

## Added
- Faz 1: ElevenLabs `convert_with_timestamps` returns the audio and per-character timings in one call, at no extra cost. The timings are stored as `TTSAlignment` in `news_package.json`. An alignment that does not match the text exactly is dropped; the audio is still used. TTS text is trimmed before synthesis.

## Changed
- Haber Stüdyosu:
  - the sidebar shows only style, duration and voice; AI engine, reasoning level and voice sliders moved under "Gelişmiş ayarlar";
  - headlines sit side by side; validation notes are grouped in one "Kontrol et" box;
  - token usage moved to a collapsed "Geliştirici bilgileri" section;
  - "Sistemi Sıfırla" became "Yeni haber" and keeps the voice and engine choices.
- Video Studio:
  - the steps are "1. Haber" and "2. Görüntüler"; the news text sits in a collapsed section;
  - folder and analysis density moved under "Gelişmiş";
  - the EditProject is built and saved automatically when news, audio and media are ready (no button);
  - cost and the project folder moved to developer info.
- Axion red is the primary colour in both light and dark themes (the system theme is followed). Page top padding is tighter. "Axion'u kapat" sits at the bottom of the sidebar.

# v1.4.0 — Fully local, single linked app — 2026-09-24

## Changed
- Streamlit Cloud support removed. Axion runs only on the editor's PC:
  - no `AXION_LOCAL` mode switch;
  - no per-page passwords (the optional password lives only in `axion_local.py`);
  - no NewsPackage JSON download or upload, no TTS upload;
  - `packages.txt` and `REPO_MANIFEST.txt` deleted.
- Pages renamed to `apps/news_studio/page.py` and `apps/video_studio/page.py`; `axion_local.py` is the only entry point. Streamlit settings moved to `.streamlit/config.toml`.
- News → Video linking:
  - "Kaydet ve Video Studio'ya geç" saves the project and opens it in Video Studio;
  - re-saving the same raw news updates the same project instead of creating a new one;
  - the sidebar shows the active project.
- Video Studio page rewritten (1140 → about 230 lines) in the order 1. news project → 2. media → 3. project:
  - the media pipeline moved to `modules/media_pipeline.py`;
  - a time-coded shot table (usable for manual CapCut cuts) is shown;
  - media analysis and the EditProject are saved to the project folder and restored when the project is reopened, so Luna does not run again.
- Proxy videos and analysis frames are deleted after analysis; previously they piled up in the temp folder.
- News Studio data files use the fixed `data/` folder (`AXION_DATA_DIR`) regardless of the working directory.
- Axion no longer starts with Windows; it runs only when the desktop icon is clicked. `kisayol.ps1` removes the old Startup shortcut.

## Added
- `AGENTS.md`: shared guide for AI developers (rules, code map, where we left off, known debts). `CLAUDE.md` imports it. README rewritten; KURULUM.md covers phone access and full remote desktop.

# v1.3.1 — Axion Local polish — 2026-09-24

## Changed
- Password is optional in local mode: an empty `APP_PASSWORD` opens Axion directly. The apps no longer require `APP_PASSWORD` in local mode. Streamlit Cloud still requires it.
- Windows launcher `windows/axion_baslat.vbs` replaces the console `.bat`:
  - no console window; the log goes to `data/axion.log`;
  - if Axion is already running, it only opens the browser;
  - it waits up to 60 s and opens the log if startup fails.
- `kurulum.bat` creates a desktop shortcut with the Axion icon and a Startup shortcut that launches Axion in the background at login (`windows/kisayol.ps1`). The Streamlit "Deploy" toolbar is hidden.
- "Axion'u kapat" button in the sidebar, shown only when Axion is opened on the home PC itself (Host header is localhost), so it cannot be closed from the tablet by mistake.
- `windows/anahtarlar.bat` opens the API key file. `windows/sorun_giderme.bat` runs Axion in a visible console for troubleshooting. `guncelle.bat` stops, updates and restarts Axion.

## Fixed
- Video Studio's news text box no longer empties when switching between pages.

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
