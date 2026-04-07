# Milestone 2 — Backend Pipeline with Stubs

## Context

Milestones 0 (project skeleton) and 1 (particle aesthetic gate) are complete. The backend has a FastAPI shell with stub endpoints and config. The frontend has a working particle system. Milestone 2 builds the real backend pipeline: data models, database, LLM integration, stub TTS/shapes, orchestrator, and job lifecycle. After this, `POST /api/generate` will accept a topic, call Claude Opus 4.6 to write a script, generate fake audio + procedural shapes, and return a complete manifest via `GET /api/jobs/{id}`.

## Files to Create/Modify (in order)

### Phase 1: Foundation

**1. `backend/src/aether/models.py`** (NEW)
Pydantic v2 data models copied from `.claude/rules/backend.md`: `JobStatus` enum, `GenerationRequest`, `ScriptElement`, `ParsedScript`, `ScheduledShape`, `Manifest`, `Job`.

**2. `backend/src/aether/db.py`** (NEW)
SQLAlchemy 2.x async with aiosqlite. Two tables (`JobRow`, `ShapeCacheRow`). Helper functions: `init_db()`, `create_job()`, `get_job()`, `update_job_status()`, `save_job_manifest()`, `lookup_cache()`, `save_cache_entry()`. Each function creates its own session and commits.

**3. `backend/src/aether/prompts/script_writer.txt`** (NEW)
The Claude system prompt copied verbatim from `.claude/rules/backend-pipeline.md`. Contains `{topic}` placeholder substituted at runtime.

### Phase 2: Pipeline

**4. `backend/src/aether/pipeline/__init__.py`** (NEW)
Empty package marker.

**5. `backend/src/aether/pipeline/llm.py`** (NEW)
Real Claude Opus 4.6 call. Loads prompt template at import time. Uses `AsyncAnthropic` with `messages.stream()` + `get_final_message()`, model `claude-opus-4-6`, `thinking={"type": "adaptive"}`. Regex parser extracts `<shape concept="..."/>` and `<say>...</say>` elements into `ParsedScript`.

Gotcha: With adaptive thinking, `message.content` may contain thinking blocks before the text block. Must iterate to find `block.type == "text"`, not blindly take `message.content[0].text`.

**6. `backend/src/aether/pipeline/pointcloud.py`** (NEW)
Five procedural point cloud generators (sphere, cube, torus, helix, octahedron) using numpy. Each returns `ndarray(N, 3)` normalized to unit sphere * 0.85. A `generate_procedural(concept, n_points)` function hashes the concept to pick a shape deterministically.

**7. `backend/src/aether/pipeline/shapes.py`** (NEW — STUB)
Stub shape generator. `cache_key(concept)` uses real sha256 hashing (needed by orchestrator). `generate_shape(concept)` checks DB cache, on miss calls `generate_procedural()`, saves as `.bin` (Float32 xyz), records in cache table. Same interface as the real version, just procedural shapes instead of Flux+Trellis.

**8. `backend/src/aether/pipeline/tts.py`** (NEW — STUB)
Stub TTS. `TTSResult` dataclass with `audio_path`, `duration_ms`, `word_starts_ms`. `render_audio(text, output_dir)` writes a hardcoded minimal silent MP3 to `output_dir/audio.mp3`, generates fake word timestamps at ~250ms intervals (4 words/sec), returns `TTSResult`.

**9. `backend/src/aether/pipeline/orchestrator.py`** (NEW)
Main pipeline coordinator. `run_pipeline(job_id, topic)` wraps everything in try/except (marks FAILED on error). Steps: update status GENERATING_SCRIPT -> call `generate_script` -> update status GENERATING_ASSETS -> launch TTS + shape gen concurrently with `asyncio.create_task` -> await all -> update status ASSEMBLING -> `_schedule_shapes()` maps shape cues to word timestamps (first shape always t=0) -> build `Manifest` -> write `manifest.json` to disk -> `save_job_manifest()` -> update status COMPLETED.

### Phase 3: Wire Up Endpoints

**10. `backend/src/aether/api/generate.py`** (MODIFY)
Replace stub. Accept `GenerationRequest` body, call `create_job()`, add `run_pipeline` as `BackgroundTask`, return `{"job_id": str(job.job_id)}`.

**11. `backend/src/aether/api/jobs.py`** (MODIFY)
Replace stub. Parse UUID, call `get_job()`, return 404 if not found, otherwise return full `Job` model (manifest inlined when complete).

**12. `backend/src/aether/main.py`** (MODIFY)
Add `from aether.db import init_db` and call `await init_db()` in the lifespan before `yield`.

### Phase 4: Tests

**13. `backend/tests/__init__.py`** (NEW) — empty

**14. `backend/tests/conftest.py`** (NEW)
Shared fixtures: temp data directory, in-memory SQLite for test DB.

**15. `backend/tests/test_llm_parser.py`** (NEW)
Tests for `_parse_script`: valid script, script missing opening shape, script with no say elements, duplicate concepts, whitespace normalization, multi-line say text.

**16. `backend/tests/test_pointcloud.py`** (NEW)
Tests for procedural generators: correct output shape `(30000, 3)`, points normalized (centered, max distance <= 1), deterministic concept-to-shape mapping.

**17. `backend/tests/test_orchestrator.py`** (NEW)
Integration test: mock `generate_script`, `render_audio`, `generate_shape`. Run full pipeline, verify job ends COMPLETED, manifest has correct shape count, first shape at t=0, manifest.json written to disk.

## Key Implementation Notes

- **Env vars**: `config.py` uses `env_prefix="AETHER_"`, so the `.env` file needs `AETHER_ANTHROPIC_API_KEY=sk-ant-...` (not `ANTHROPIC_API_KEY`).
- **No `manifest.py`**: Manifest assembly lives in the orchestrator directly per the rules.
- **No `pipeline/manifest.py`**: Not needed — the orchestrator handles this inline.
- **UUID <-> string**: DB stores UUIDs as `String(36)`. Conversion happens in db helper functions.
- **Silent MP3**: Embed a minimal valid MP3 frame as base64 bytes constant (~200 bytes). Avoids needing an audio encoding library.

## Verification

```bash
cd backend

# 1. Run tests
pytest -v

# 2. Start the server (needs AETHER_ANTHROPIC_API_KEY in .env)
uvicorn aether.main:app --reload

# 3. Deliverable check
curl -X POST http://127.0.0.1:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"What is AI?"}'
# Returns: {"job_id": "..."}

# 4. Poll until completed
curl http://127.0.0.1:8000/api/jobs/{job_id}
# Should transition: pending -> generating_script -> generating_assets -> assembling -> completed
# Final response includes manifest with audio_url, shapes[], trigger times
```
