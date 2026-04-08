# Milestone 4 — Real TTS

## Context

The stub TTS in `tts.py` generates silent WAV files with fake 250ms-per-word timestamps. Milestone 4 replaces this with real ElevenLabs API calls so shape morphs actually sync with spoken narration. This is a two-step pipeline: TTS synthesis (returns MP3) followed by Forced Alignment (returns precise word-level timestamps). The `TTSResult` interface stays the same, so nothing downstream changes.

## Changes

### 1. `backend/pyproject.toml` — promote httpx to main dependency

Move `"httpx>=0.28"` from `[project.optional-dependencies] dev` into `[project] dependencies`. The real `tts.py` uses `httpx.AsyncClient` for both ElevenLabs endpoints.

Then run: `pip install -e ".[dev]"` to update the environment.

### 2. `backend/src/aether/pipeline/tts.py` — replace stub with real ElevenLabs

Replace the entire file body (keeping `TTSResult` dataclass unchanged). New implementation:

- **Imports**: Replace `struct` with `httpx` and `from aether.config import settings`
- **`render_audio(text, output_dir)`**: Calls `_synthesize` then `_force_align`, writes MP3, extracts timestamps. Same signature, same return type.
- **`_synthesize(text) -> bytes`**: POST to `/v1/text-to-speech/{voice_id}` with JSON payload (model: `eleven_multilingual_v2`, voice_settings: stability 0.5 / similarity_boost 0.75 / style 0.0 / speaker_boost True). Returns raw MP3 bytes.
- **`_force_align(audio_bytes, text) -> dict`**: POST to `/v1/forced-alignment` as **multipart/form-data** (file + text as plain form field, NOT JSON). Returns word-level timestamps.
- **`_extract_word_starts(alignment)`**: Maps `alignment["words"]` to `(word["text"], int(word["start"] * 1000))` tuples.
- **`_extract_duration_ms(alignment)`**: Returns `int(words[-1]["end"] * 1000)` or 0 if empty.

Reference implementation is in `.claude/rules/backend-pipeline.md` lines 175-270 — follow it closely.

**No other files need modification.** The orchestrator, models, config, and tests all work as-is.

## Gotchas

- Forced Alignment `text` must be a form field (`data={"text": text}`), not JSON. Wrong format = 422 error.
- The rules doc shows `import base64` — skip it, it's unused and will trigger ruff F401.
- Timeout: 120s per call (appropriate for background pipeline).
- API key permissions needed: Text to Speech, Forced Alignment, Voices (Read).

## Verification

1. **Existing tests pass**: `cd backend && pytest -v` (orchestrator test mocks `render_audio`, unaffected)
2. **Manual test**: Run server, POST a topic, play the result — listen for shape morphs landing on the right spoken words (not uniform 250ms spacing)
3. **Spot-check timestamps**: The word_starts_ms should be monotonically increasing with realistic gaps (not uniform 250ms)
